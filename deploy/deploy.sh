#!/bin/bash
# deploy.sh — one-command deploy from the Mac to the server.
#
# Usage:
#   deploy/deploy.sh coi@SERVER_IP              deploy the latest pushed main
#   deploy/deploy.sh --rollback coi@SERVER_IP   undo the most recent deploy
#   SERVER=coi@SERVER_IP deploy/deploy.sh       server via env var instead
#
# A deploy runs on the server: git pull -> pip install (only if
# requirements.txt changed) -> main.py --check -> systemctl restart ->
# confirm a clean "startup" line in the journal -> confirm the service is
# the ONLY poller process. Exits nonzero the moment any step fails.
#
# --rollback resets the server to the commit recorded just before the last
# deploy (one level deep), reinstalls requirements, restarts, and verifies.
#
# Safety: refuses to run while the Mac copy of the poller is still active
# (two pollers on one mailbox double-process emails). Override with
# FORCE_DEPLOY=1 only if you are certain.

set -euo pipefail

APP_DIR="/opt/coi-automation"
UNIT="coi-automation"

usage() {
    sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'
}

MODE="deploy"
SERVER="${SERVER:-}"
for arg in "$@"; do
    case "$arg" in
        --rollback) MODE="rollback" ;;
        -h|--help)  usage; exit 0 ;;
        -*)         echo "Unknown flag: $arg"; usage; exit 2 ;;
        *)          SERVER="$arg" ;;
    esac
done

if [ -z "$SERVER" ]; then
    usage
    exit 2
fi
case "$SERVER" in
    *@*) ;;
    *)   SERVER="coi@$SERVER" ;;
esac

# --- one-poller guard: is the Mac copy still running? -----------------------
# (-i: macOS ps shows the venv python as .../Python.app/.../Python, capital P)
if launchctl list 2>/dev/null | grep -q "com.alepreneur.coi-automation" \
   || pgrep -if "python[^ ]* [^ ]*main\.py" >/dev/null 2>&1; then
    echo "ERROR: a COI poller is still running ON THIS MAC (launchd job or"
    echo "start.sh loop). Two pollers on one mailbox answer every client"
    echo "email twice. Stop the Mac copy first:"
    echo "  launchctl unload ~/Library/LaunchAgents/com.alepreneur.coi-automation.plist"
    echo "  ~/coi-automation/start.sh stop"
    if [ "${FORCE_DEPLOY:-0}" != "1" ]; then
        echo "(Override, at your own risk: FORCE_DEPLOY=1 deploy/deploy.sh ...)"
        exit 1
    fi
    echo "FORCE_DEPLOY=1 set — continuing anyway."
fi

# --- deploy mode: the server pulls from GitHub, so local main must be pushed
if [ "$MODE" = "deploy" ]; then
    REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "--- checking local main is pushed"
        git -C "$REPO_ROOT" fetch origin main --quiet
        LOCAL_HEAD=$(git -C "$REPO_ROOT" rev-parse main)
        REMOTE_HEAD=$(git -C "$REPO_ROOT" rev-parse origin/main)
        if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
            echo "ERROR: local main (${LOCAL_HEAD:0:7}) != origin/main (${REMOTE_HEAD:0:7})."
            echo "The server deploys what is on GitHub. Push first:"
            echo "  git push origin main"
            exit 1
        fi
        if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
            echo "NOTE: you have uncommitted local changes — they will NOT deploy."
        fi
    fi
fi

echo "--- connecting to $SERVER ($MODE)"
ssh -o ConnectTimeout=10 "$SERVER" "MODE=$MODE bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

APP_DIR="/opt/coi-automation"
UNIT="coi-automation"
cd "$APP_DIR"

restart_and_verify() {
    echo "--- restarting $UNIT"
    START_TS=$(date '+%Y-%m-%d %H:%M:%S')
    sudo -n systemctl restart "$UNIT"

    echo "--- waiting for a clean startup line in the journal"
    OK=""
    for _ in $(seq 1 20); do
        sleep 2
        if journalctl -u "$UNIT" --since "$START_TS" --no-pager 2>/dev/null \
                | grep -q " startup mailbox="; then
            OK=1
            break
        fi
        if [ "$(systemctl is-active "$UNIT" || true)" = "failed" ]; then
            break
        fi
    done
    if [ -z "$OK" ]; then
        echo "FAILED: no startup line after restart. Last 30 journal lines:"
        journalctl -u "$UNIT" -n 30 --no-pager || true
        exit 1
    fi
    journalctl -u "$UNIT" --since "$START_TS" --no-pager \
        | grep " startup mailbox=" | tail -1

    echo "--- single-poller check"
    MAIN_PID=$(systemctl show -p MainPID --value "$UNIT")
    STRAY=""
    for PID in $(pgrep -f "python[^ ]* [^ ]*main\.py" || true); do
        [ "$PID" != "$MAIN_PID" ] && STRAY="$STRAY $PID"
    done
    if [ -n "$STRAY" ]; then
        echo "FAILED: poller process(es) running OUTSIDE the service:$STRAY"
        # shellcheck disable=SC2086
        ps -fp $STRAY || true
        echo "Only ONE poller may run or emails get double-processed."
        echo "Kill the strays (kill <pid>), then re-run the deploy."
        exit 1
    fi
    echo "OK: service is the only poller (PID $MAIN_PID)"
}

if [ "$MODE" = "rollback" ]; then
    if [ ! -f state/last_deploy_prev_ref ]; then
        echo "FAILED: no rollback ref recorded (state/last_deploy_prev_ref missing)."
        echo "Nothing was deployed via deploy.sh yet, or the ref was cleaned up."
        exit 1
    fi
    PREV=$(cat state/last_deploy_prev_ref)
    echo "--- rolling back to $PREV"
    git reset --hard "$PREV"
    echo "--- reinstalling requirements (may have differed at that commit)"
    .venv/bin/pip install --quiet -r requirements.txt
    restart_and_verify
    echo "Rollback complete: now at $(git rev-parse --short HEAD)"
    exit 0
fi

echo "--- recording current ref for rollback"
mkdir -p state
git rev-parse HEAD > state/last_deploy_prev_ref

REQ_BEFORE=$(git rev-parse HEAD:requirements.txt)
echo "--- git pull"
git pull --ff-only origin main
REQ_AFTER=$(git rev-parse HEAD:requirements.txt)

if [ "$REQ_BEFORE" != "$REQ_AFTER" ]; then
    echo "--- requirements.txt changed -> pip install"
    .venv/bin/pip install --quiet -r requirements.txt
else
    echo "--- requirements.txt unchanged -> skipping pip install"
fi

echo "--- preflight: main.py --check"
.venv/bin/python main.py --check

restart_and_verify
echo "Deploy complete: now at $(git rev-parse --short HEAD)"
REMOTE_SCRIPT

echo "--- $MODE finished cleanly"
