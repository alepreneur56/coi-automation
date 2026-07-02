"""
ops_review.py
-------------
Ops-module test harness. Four sections:

  1. Digest built from REAL log files (copied into a temp dir) — rendered
     HTML lands in tests/ops_output/ for eyeball inspection. Also covers
     token totals + cost line via a synthetic 'classified' event with usage,
     and the missing-log-file 'no activity' heartbeat.
  2. Alert rate-limiting with a fake clock (now_ts injection).
  3. Digest scheduling (DIGEST_HOUR gate, once per day, DIGEST_ENABLED off).
  4. Rotation against temp files with faked mtimes (os.utime) — old files
     deleted, recent/today/non-matching files kept, once-per-day guard.

Nothing is sent — a FakeGraph captures every outbound payload (same pattern
as tests/pipeline_review.py).

Usage:
    .venv/bin/python tests/ops_review.py
"""

import glob
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import ops

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ops_output")

# Real production logs live in the deployed checkout; fall back to this
# checkout's logs/ when reviewing elsewhere.
REAL_LOGS_DIR = os.environ.get(
    "COI_REAL_LOGS_DIR", os.path.expanduser("~/coi-automation/logs")
)
if not os.path.isdir(REAL_LOGS_DIR):
    REAL_LOGS_DIR = config.LOGS_DIR


# ---------------------------------------------------------------------------
# Fake Graph — captures outbound payloads, sends nothing
# ---------------------------------------------------------------------------

class FakeGraph:
    def __init__(self):
        self.sent = []

    def send_mail(self, message_obj):
        self.sent.append(message_obj)
        return True, None


def recipient(payload):
    return payload["toRecipients"][0]["emailAddress"]["address"]


# ---------------------------------------------------------------------------
# 1. Digest from real logs
# ---------------------------------------------------------------------------

def test_digest_from_real_logs():
    problems = []
    real_logs = sorted(glob.glob(os.path.join(REAL_LOGS_DIR, "coi-*.jsonl")))
    if not real_logs:
        return [f"no real log files found in {REAL_LOGS_DIR}"]

    tmp = tempfile.mkdtemp(prefix="ops_digest_")
    try:
        for src in real_logs:
            shutil.copy(src, tmp)

        for src in real_logs:
            date_str = os.path.basename(src)[len("coi-"):-len(".jsonl")]
            subject, html_body = ops.build_daily_digest(date_str, logs_dir=tmp)

            out_path = os.path.join(OUT_DIR, f"digest-{date_str}.html")
            with open(out_path, "w") as f:
                f.write(html_body)
            print(f"  digest {date_str}: subject={subject!r}")
            print(f"    -> {out_path}")

            if date_str not in subject:
                problems.append(f"{date_str}: date missing from subject: {subject!r}")
            # Every processing_start sender in the log must appear in the HTML
            with open(src) as f:
                for line in f:
                    ev = json.loads(line)
                    if ev.get("event") == "processing_start" and ev.get("sender"):
                        if ev["sender"] not in html_body:
                            problems.append(
                                f"{date_str}: sender {ev['sender']!r} missing from digest HTML")
                        break
            if "Token usage" not in html_body:
                problems.append(f"{date_str}: token usage section missing")

        # --- Synthetic usage + cost line -------------------------------
        synth_date = "2026-01-15"
        synth_path = os.path.join(tmp, f"coi-{synth_date}.jsonl")
        usage = {"input_tokens": 4000, "cache_creation_input_tokens": 30000,
                 "cache_read_input_tokens": 120000, "output_tokens": 900}
        events = [
            {"ts": "2026-01-15T14:00:00Z", "event": "processing_start",
             "msg_id": "m1", "sender": "client@example.com",
             "subject": "COI needed <today>"},
            {"ts": "2026-01-15T14:00:05Z", "event": "classified", "msg_id": "m1",
             "success": True, "classification": "coi_request_complete",
             "usage": usage},
            {"ts": "2026-01-15T14:00:06Z", "event": "action_decided",
             "msg_id": "m1", "action": "send_pdf"},
            {"ts": "2026-01-15T14:00:08Z", "event": "send_result", "msg_id": "m1",
             "action": "send_pdf", "sent": True, "type": "pdf_reply", "error": None},
            {"ts": "2026-01-15T15:00:00Z", "event": "poll_error",
             "error": "Token request failed: HTTP 500"},
        ]
        with open(synth_path, "w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        # No cost vars set -> no cost line
        saved = (config.COST_INPUT_PER_MTOK, config.COST_CACHED_INPUT_PER_MTOK,
                 config.COST_OUTPUT_PER_MTOK)
        try:
            config.COST_INPUT_PER_MTOK = None
            config.COST_CACHED_INPUT_PER_MTOK = None
            config.COST_OUTPUT_PER_MTOK = None
            subject, html_body = ops.build_daily_digest(synth_date, logs_dir=tmp)
            if "Estimated API cost" in html_body:
                problems.append("cost line shown with COST_* vars unset")
            if "1 email" not in subject or "1 error" not in subject:
                problems.append(f"synthetic subject wrong: {subject!r}")
            if "154,900" not in html_body:  # 4000+30000+120000+900 total tokens
                problems.append("token totals not summed correctly")
            if "&lt;today&gt;" not in html_body:
                problems.append("subject not HTML-escaped in digest")

            # All three cost vars set -> cost line appears with the math
            config.COST_INPUT_PER_MTOK = 3.0
            config.COST_CACHED_INPUT_PER_MTOK = 0.3
            config.COST_OUTPUT_PER_MTOK = 15.0
            _, html_body = ops.build_daily_digest(synth_date, logs_dir=tmp)
            # (4000+30000)*3.0 + 120000*0.3 + 900*15.0 = 102000+36000+13500
            # = 151500 / 1e6 = $0.1515
            if "Estimated API cost" not in html_body or "$0.1515" not in html_body:
                problems.append("cost line missing or wrong with COST_* vars set")
        finally:
            (config.COST_INPUT_PER_MTOK, config.COST_CACHED_INPUT_PER_MTOK,
             config.COST_OUTPUT_PER_MTOK) = saved

        with open(os.path.join(OUT_DIR, f"digest-{synth_date}-synthetic.html"), "w") as f:
            f.write(html_body)
        print(f"  synthetic digest -> {OUT_DIR}/digest-{synth_date}-synthetic.html")

        # --- Missing log file -> heartbeat digest ----------------------
        subject, html_body = ops.build_daily_digest("1999-01-01", logs_dir=tmp)
        if "no activity" not in subject:
            problems.append(f"missing-file subject should say no activity: {subject!r}")
        if "No emails processed" not in html_body:
            problems.append("missing-file digest body lacks 'No emails processed'")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


# ---------------------------------------------------------------------------
# 2. Alert rate-limiting (fake clock)
# ---------------------------------------------------------------------------

def test_alert_rate_limiting():
    problems = []
    graph = FakeGraph()
    run_state = {}
    t0 = 1_750_000_000.0

    ev = {"event": "processing_error", "msg_id": "m1",
          "sender": "client@example.com", "subject": "COI <urgent>",
          "error": "boom: PDF engine exploded"}

    if not ops.send_error_alert(graph, run_state, ev, now_ts=t0):
        problems.append("first alert was not sent")
    if len(graph.sent) != 1:
        problems.append(f"expected 1 sent after first alert, got {len(graph.sent)}")

    # Inside the 30-min window -> suppressed
    if ops.send_error_alert(graph, run_state, ev, now_ts=t0 + 60):
        problems.append("alert sent 60s after previous (should be suppressed)")
    if ops.send_error_alert(graph, run_state, ev, now_ts=t0 + 1799):
        problems.append("alert sent at +1799s (should be suppressed)")
    if len(graph.sent) != 1:
        problems.append(f"suppressed alerts still sent mail ({len(graph.sent)})")

    # Past the window -> sent again
    if not ops.send_error_alert(
        graph, run_state, {"event": "poll_error", "error": "Graph down"},
        now_ts=t0 + 1801,
    ):
        problems.append("alert not sent at +1801s (window elapsed)")
    if len(graph.sent) != 2:
        problems.append(f"expected 2 sent after window elapsed, got {len(graph.sent)}")
    if run_state.get("last_alert_ts") != t0 + 1801:
        problems.append(f"last_alert_ts not updated: {run_state.get('last_alert_ts')}")

    # Payload checks on the first alert
    payload = graph.sent[0]
    body = payload["body"]["content"]
    if recipient(payload) != config.ALERT_TO:
        problems.append(f"alert recipient {recipient(payload)!r} != ALERT_TO")
    if "processing_error" not in payload["subject"]:
        problems.append(f"alert subject lacks event name: {payload['subject']!r}")
    if "boom: PDF engine exploded" not in body:
        problems.append("alert body lacks error text")
    if "client@example.com" not in body or "COI &lt;urgent&gt;" not in body:
        problems.append("alert body lacks (escaped) email sender/subject")
    if "loop is still running" not in body or "logs/coi-" not in body:
        problems.append("alert body lacks 'loop is still running' + log pointer")
    return problems


# ---------------------------------------------------------------------------
# 3. Digest scheduling
# ---------------------------------------------------------------------------

def test_digest_scheduling():
    problems = []
    graph = FakeGraph()
    run_state = {}
    saved = (config.DIGEST_ENABLED, config.DIGEST_HOUR)
    try:
        config.DIGEST_ENABLED = True
        config.DIGEST_HOUR = 8

        # Before DIGEST_HOUR -> nothing
        if ops.send_digest_if_due(graph, run_state, now=datetime(2026, 7, 2, 7, 59)):
            problems.append("digest sent before DIGEST_HOUR")
        if graph.sent:
            problems.append("mail sent before DIGEST_HOUR")

        # After DIGEST_HOUR -> yesterday's digest, once
        if not ops.send_digest_if_due(graph, run_state, now=datetime(2026, 7, 2, 8, 5)):
            problems.append("digest not sent after DIGEST_HOUR")
        if run_state.get("last_digest_date") != "2026-07-01":
            problems.append(f"last_digest_date wrong: {run_state.get('last_digest_date')!r}")
        if ops.send_digest_if_due(graph, run_state, now=datetime(2026, 7, 2, 12, 0)):
            problems.append("digest sent twice on the same day")
        if len(graph.sent) != 1:
            problems.append(f"expected 1 digest sent, got {len(graph.sent)}")

        # Next day -> sent again for the new yesterday
        if not ops.send_digest_if_due(graph, run_state, now=datetime(2026, 7, 3, 8, 1)):
            problems.append("digest not sent the following day")
        if run_state.get("last_digest_date") != "2026-07-02":
            problems.append(f"day-2 last_digest_date wrong: {run_state.get('last_digest_date')!r}")

        payload = graph.sent[0]
        if recipient(payload) != config.DIGEST_TO:
            problems.append(f"digest recipient {recipient(payload)!r} != DIGEST_TO")
        if payload["body"]["contentType"] != "HTML":
            problems.append("digest body is not HTML")
        if "2026-07-01" not in payload["subject"]:
            problems.append(f"digest subject lacks target date: {payload['subject']!r}")

        # Disabled -> no send even when due
        config.DIGEST_ENABLED = False
        run_state2 = {}
        if ops.send_digest_if_due(graph, run_state2, now=datetime(2026, 7, 2, 9, 0)):
            problems.append("digest sent with DIGEST_ENABLED=false")
    finally:
        config.DIGEST_ENABLED, config.DIGEST_HOUR = saved
    return problems


# ---------------------------------------------------------------------------
# 4. Rotation (temp files, faked mtimes)
# ---------------------------------------------------------------------------

def set_age(path, days, content=b"x"):
    with open(path, "wb") as f:
        f.write(content)
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def test_rotation():
    problems = []
    logs_tmp = tempfile.mkdtemp(prefix="ops_rot_logs_")
    out_tmp = tempfile.mkdtemp(prefix="ops_rot_pdfs_")
    try:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # logs/: retention 60 days
        set_age(os.path.join(logs_tmp, "coi-2026-01-01.jsonl"), 100)   # delete
        set_age(os.path.join(logs_tmp, "coi-recent.jsonl"), 5)         # keep
        set_age(os.path.join(logs_tmp, f"coi-{today_str}.jsonl"), 100) # keep: today's name
        set_age(os.path.join(logs_tmp, "launchd.log"), 100)            # keep: not .jsonl
        # output/: retention 180 days
        set_age(os.path.join(out_tmp, "Old_Client_Old_Holder.pdf"), 200)  # delete
        set_age(os.path.join(out_tmp, "Recent_COI.pdf"), 30)              # keep
        set_age(os.path.join(out_tmp, "notes.txt"), 400)                  # keep: not .pdf

        run_state = {}
        result = ops.rotate_logs(run_state, now=now, logs_dir=logs_tmp, output_dir=out_tmp)

        if result["deleted_logs"] != ["coi-2026-01-01.jsonl"]:
            problems.append(f"deleted_logs wrong: {result['deleted_logs']}")
        if result["deleted_pdfs"] != ["Old_Client_Old_Holder.pdf"]:
            problems.append(f"deleted_pdfs wrong: {result['deleted_pdfs']}")
        for kept in ("coi-recent.jsonl", f"coi-{today_str}.jsonl", "launchd.log"):
            if not os.path.exists(os.path.join(logs_tmp, kept)):
                problems.append(f"{kept} was deleted (must be kept)")
        for kept in ("Recent_COI.pdf", "notes.txt"):
            if not os.path.exists(os.path.join(out_tmp, kept)):
                problems.append(f"{kept} was deleted (must be kept)")
        if os.path.exists(os.path.join(logs_tmp, "coi-2026-01-01.jsonl")):
            problems.append("old log still on disk after rotation")
        if run_state.get("last_rotation_date") != today_str:
            problems.append(f"last_rotation_date wrong: {run_state.get('last_rotation_date')!r}")

        # Same day again -> skipped, even with a fresh old file present
        set_age(os.path.join(logs_tmp, "coi-2026-01-02.jsonl"), 100)
        result2 = ops.rotate_logs(run_state, now=now, logs_dir=logs_tmp, output_dir=out_tmp)
        if not result2["skipped"]:
            problems.append("second rotation on the same day was not skipped")
        if not os.path.exists(os.path.join(logs_tmp, "coi-2026-01-02.jsonl")):
            problems.append("same-day second rotation deleted a file")

        # Next day -> runs again and catches it. The coi-{today}.jsonl file
        # (faked 100-day-old mtime) also goes now: it is no longer "today",
        # so only the mtime rule applies.
        result3 = ops.rotate_logs(
            run_state, now=now + timedelta(days=1),
            logs_dir=logs_tmp, output_dir=out_tmp,
        )
        expected = sorted(["coi-2026-01-02.jsonl", f"coi-{today_str}.jsonl"])
        if sorted(result3["deleted_logs"]) != expected:
            problems.append(f"next-day rotation deleted_logs wrong: {result3['deleted_logs']}")
    finally:
        shutil.rmtree(logs_tmp, ignore_errors=True)
        shutil.rmtree(out_tmp, ignore_errors=True)
    return problems


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    sections = [
        ("digest_from_real_logs", test_digest_from_real_logs),
        ("alert_rate_limiting", test_alert_rate_limiting),
        ("digest_scheduling", test_digest_scheduling),
        ("rotation", test_rotation),
    ]

    report = []
    fails = 0
    for name, fn in sections:
        print(f"\n--- {name} ---")
        try:
            problems = fn()
        except Exception as e:
            import traceback
            problems = [f"CRASH: {type(e).__name__}: {e}"]
            print(traceback.format_exc()[-800:])
        if problems:
            fails += 1
            report.append(f"[FAIL] {name}")
            for p in problems:
                report.append(f"         - {p}")
        else:
            report.append(f"[OK]   {name}")

    print("\n" + "=" * 72)
    for line in report:
        print(line)
    print("=" * 72)
    print(f"Sections: {len(sections)}   FAIL: {fails}")
    print(f"Rendered digests: {OUT_DIR}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
