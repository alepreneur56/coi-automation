#!/bin/bash
# provision.sh — first-time setup of a fresh Ubuntu 24.04 server for the
# COI automation loop. Run as root ON THE SERVER:
#
#   scp deploy/provision.sh root@SERVER_IP:/root/provision.sh
#   ssh root@SERVER_IP bash /root/provision.sh
#
# Idempotent: safe to re-run at any time; completed steps are skipped.
# The first run stops after generating the GitHub deploy key so you can
# register it — add the key, then run the script again to finish.
#
# What it does:
#   1. Installs git + python3-venv
#   2. Creates the dedicated non-root user 'coi'
#   3. Generates a read-only GitHub deploy key for the server
#   4. Clones the repo to /opt/coi-automation
#   5. Creates the venv and installs requirements.txt
#   6. Creates data/ logs/ output/ state/ dirs
#   7. Grants 'coi' journal access + sudo for this one service only
#   8. Installs and enables the systemd unit (does NOT start it — no .env yet)
#   9. Prints the post-install checklist

set -euo pipefail

APP_USER="coi"
APP_HOME="/home/$APP_USER"
APP_DIR="/opt/coi-automation"
REPO_SSH="git@github.com:alepreneur56/coi-automation.git"
UNIT="coi-automation"

say()  { printf '\n==> %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run as root (ssh in as root, or: sudo bash provision.sh)"
    exit 1
fi

# --- 1. OS packages --------------------------------------------------------
say "Installing OS packages (git, python3-venv)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    git python3 python3-venv ca-certificates openssh-client >/dev/null
note "done"

# --- 2. Dedicated user -----------------------------------------------------
say "Creating user '$APP_USER'"
if id -u "$APP_USER" >/dev/null 2>&1; then
    note "user already exists — skipping"
else
    useradd --create-home --shell /bin/bash "$APP_USER"
    note "created"
fi

install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$APP_HOME/.ssh"

# Hetzner/DO install your SSH key for root only. Copy it to 'coi' so you can
# ssh coi@SERVER directly (deploy.sh needs this).
if [ -f /root/.ssh/authorized_keys ] && [ ! -f "$APP_HOME/.ssh/authorized_keys" ]; then
    say "Copying root's authorized_keys to '$APP_USER' (enables: ssh coi@SERVER)"
    install -m 600 -o "$APP_USER" -g "$APP_USER" \
        /root/.ssh/authorized_keys "$APP_HOME/.ssh/authorized_keys"
fi

# --- 3. GitHub deploy key --------------------------------------------------
say "GitHub deploy key"
KEY_FILE="$APP_HOME/.ssh/id_ed25519"
if [ ! -f "$KEY_FILE" ]; then
    sudo -H -u "$APP_USER" ssh-keygen -t ed25519 -N "" \
        -C "coi-automation deploy key ($(hostname))" -f "$KEY_FILE" >/dev/null
    note "generated $KEY_FILE"
else
    note "key already exists — skipping"
fi

# Pre-trust github.com so git never hangs on an interactive host prompt
sudo -H -u "$APP_USER" bash -c '
    touch ~/.ssh/known_hosts && chmod 600 ~/.ssh/known_hosts
    if ! grep -q "^github.com" ~/.ssh/known_hosts; then
        ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
    fi'

# Can the server reach the private repo yet?
if ! sudo -H -u "$APP_USER" git ls-remote "$REPO_SSH" >/dev/null 2>&1; then
    cat <<EOF

============================================================================
ACTION NEEDED — register the deploy key on GitHub, then re-run this script.

1. Copy this public key (the whole line):

$(cat "$KEY_FILE.pub")

2. In a browser: github.com/alepreneur56/coi-automation
   -> Settings -> Deploy keys -> Add deploy key
   -> Title: coi-server
   -> Key: paste the line above
   -> Leave "Allow write access" UNCHECKED (read-only)
   -> Add key

3. Run this script again — it picks up where it left off:
   ssh root@SERVER_IP bash /root/provision.sh
============================================================================
EOF
    exit 1
fi
note "GitHub access OK"

# --- 4. Clone --------------------------------------------------------------
say "Cloning repo to $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    note "already cloned — skipping (use deploy.sh to update)"
else
    install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR"
    sudo -H -u "$APP_USER" git clone --quiet "$REPO_SSH" "$APP_DIR"
    note "cloned"
fi

# --- 5. Virtualenv + dependencies ------------------------------------------
say "Python venv + dependencies"
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    sudo -H -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
    note "venv created"
fi
sudo -H -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
note "requirements installed"

# --- 6. Runtime directories -------------------------------------------------
say "Runtime directories (data/ logs/ output/ state/)"
sudo -H -u "$APP_USER" mkdir -p \
    "$APP_DIR/data" "$APP_DIR/logs" "$APP_DIR/output" "$APP_DIR/state"
note "done"

# --- 7. Journal access + scoped sudo for deploy.sh --------------------------
say "Granting '$APP_USER' journal read access + service-only sudo"
usermod -aG systemd-journal "$APP_USER"
cat > /etc/sudoers.d/coi-automation <<'EOF'
# deploy.sh (run as coi) may manage the coi-automation service — nothing else
coi ALL=(root) NOPASSWD: /usr/bin/systemctl start coi-automation, /usr/bin/systemctl stop coi-automation, /usr/bin/systemctl restart coi-automation, /usr/bin/systemctl start coi-automation.service, /usr/bin/systemctl stop coi-automation.service, /usr/bin/systemctl restart coi-automation.service
EOF
chmod 440 /etc/sudoers.d/coi-automation
visudo -cf /etc/sudoers.d/coi-automation >/dev/null
note "done"

# --- 8. systemd unit ---------------------------------------------------------
say "Installing systemd unit ($UNIT)"
cp "$APP_DIR/deploy/coi-automation.service" "/etc/systemd/system/$UNIT.service"
systemctl daemon-reload
systemctl enable "$UNIT" 2>/dev/null
note "installed + enabled (starts on boot; NOT started yet)"

# --- 9. Checklist -------------------------------------------------------------
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<EOF

============================================================================
PROVISIONING COMPLETE — finish these steps by hand (in order):

1. Copy the secrets file from the Mac (NEVER commit .env to git):
     scp ~/coi-automation/.env coi@${SERVER_IP:-SERVER_IP}:$APP_DIR/.env
     ssh coi@${SERVER_IP:-SERVER_IP} chmod 600 $APP_DIR/.env

2. Optional but recommended — carry over the COI history DB (powers
   address autofill) and the runtime watermark (prevents a mail gap or
   backlog replay at cutover):
     scp ~/coi-automation/data/coi_history.db coi@${SERVER_IP:-SERVER_IP}:$APP_DIR/data/
     scp ~/coi-automation/state/runtime_state.json coi@${SERVER_IP:-SERVER_IP}:$APP_DIR/state/

3. Set the timezone (daily digest + log rotation use LOCAL server time):
     timedatectl set-timezone America/New_York

4. Verify credentials and connectivity:
     sudo -H -u coi $APP_DIR/.venv/bin/python $APP_DIR/main.py --check

5. Start the service and watch it come up:
     systemctl start $UNIT
     journalctl -u $UNIT -f

Optional firewall (nothing listens for inbound traffic; SSH only):
     ufw allow OpenSSH && ufw enable

============================================================================
WARNING — ONLY ONE POLLER MAY RUN AT A TIME.
If the Mac copy (launchd job com.alepreneur.coi-automation or start.sh) is
still running against the same mailbox, every client email will be processed
and answered TWICE. Before 'systemctl start' here, stop the Mac copy:
     launchctl unload ~/Library/LaunchAgents/com.alepreneur.coi-automation.plist
See deploy/RUNBOOK.md, section "Cutover from the Mac".
============================================================================
EOF
