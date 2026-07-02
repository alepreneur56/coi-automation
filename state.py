"""
state.py
--------
Persistent runtime state + JSON-line logging.

State file (state/runtime_state.json):
  - watermark: ISO UTC datetime — only messages received AFTER this are
    processed. Initialized to "now" on first run so we never chew through
    the inbox backlog.
  - processed_ids: last N message IDs already handled (dedupe belt-and-
    suspenders on top of the watermark).

Logs: logs/coi-YYYY-MM-DD.jsonl — one JSON object per event.
"""

import json
import os
from datetime import datetime, timezone

import config

STATE_PATH = os.path.join(config.STATE_DIR, "runtime_state.json")
MAX_PROCESSED_IDS = 500


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"watermark": utc_now_iso(), "processed_ids": []}


def save_state(state):
    state["processed_ids"] = state.get("processed_ids", [])[-MAX_PROCESSED_IDS:]
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_PATH)


def log_event(event, **fields):
    """Append a JSON line to today's log file and echo a short line to stdout."""
    record = {"ts": utc_now_iso(), "event": event}
    record.update(fields)
    path = os.path.join(
        config.LOGS_DIR, f"coi-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    )
    try:
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass
    summary = " ".join(
        f"{k}={v}" for k, v in fields.items()
        if isinstance(v, (str, int, bool)) and len(str(v)) <= 80
    )
    print(f"[{record['ts']}] {event} {summary}")
