"""
ops.py
------
Operational hardening for the COI automation loop.

Three jobs, all driven from main.py once per poll cycle (cheap no-ops when
not due):

  - build_daily_digest(date_str)              -> (subject, html) for one day
  - send_digest_if_due(graph, run_state)      -> yesterday's digest, once per
                                                 day after DIGEST_HOUR local
  - send_error_alert(graph, run_state, ev)    -> immediate owner alert on
                                                 processing_error/poll_error,
                                                 at most one per 30 minutes
  - rotate_logs(run_state)                    -> delete old logs/*.jsonl and
                                                 output/*.pdf, once per day

Every public function catches its own exceptions and logs an 'ops_error'
event — an ops failure must NEVER break the mail loop. Scheduling state
(last_digest_date, last_alert_ts, last_rotation_date) lives in run_state and
is persisted via state.save_state.
"""

import html
import json
import os
import time
import traceback
from datetime import datetime, timedelta, timezone

import config
import state

ALERT_MIN_INTERVAL_SECONDS = 30 * 60


def _ops_error(op, exc):
    """Log an ops failure without letting it propagate to the mail loop."""
    state.log_event(
        "ops_error",
        op=op,
        error=str(exc),
        traceback=traceback.format_exc()[-800:],
    )


def _esc(value):
    """HTML-escape a value for safe embedding in the digest/alert body."""
    return html.escape(str(value if value is not None else ""))


# ---------------------------------------------------------------------------
# Daily digest
# ---------------------------------------------------------------------------

def _read_log_events(date_str, logs_dir=None):
    """All JSONL events for one local date. [] if the file doesn't exist."""
    path = os.path.join(logs_dir or config.LOGS_DIR, f"coi-{date_str}.jsonl")
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue  # never let one corrupt line kill the digest
    return events


def _local_hhmm(ts):
    """UTC ISO timestamp -> local HH:MM (falls back to the raw string)."""
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%H:%M")
    except Exception:
        return ts or ""


def _estimated_cost(totals):
    """Estimated $ for the day's classifier calls, or None if any of the
    three COST_*_PER_MTOK settings is unset. No pricing is hardcoded here;
    cache-write tokens are counted at the plain input rate."""
    rates = (
        config.COST_INPUT_PER_MTOK,
        config.COST_CACHED_INPUT_PER_MTOK,
        config.COST_OUTPUT_PER_MTOK,
    )
    if any(r is None for r in rates):
        return None
    in_rate, cached_rate, out_rate = rates
    return (
        (totals["input_tokens"] + totals["cache_creation_input_tokens"]) * in_rate
        + totals["cache_read_input_tokens"] * cached_rate
        + totals["output_tokens"] * out_rate
    ) / 1_000_000.0


def build_daily_digest(date_str, logs_dir=None):
    """Summarize one day's JSONL log. Returns (subject, html_body).

    Works even when the log file is missing or empty — the owner wants a
    heartbeat email every day, so a 'no activity' digest is still built.
    """
    events = _read_log_events(date_str, logs_dir)

    emails = {}   # msg_id -> row dict
    order = []    # msg_ids in first-seen order
    errors = []   # processing_error / poll_error events
    classifier_calls = 0
    # MVP flow emails (see flows.py) — counted for the digest
    flow_counts = {
        "referral_appended": 0,
        "shortfall_client_email": 0,
        "noncompliance_email": 0,
        "carrier_endorsement_email": 0,
    }
    totals = {
        "input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 0,
    }

    def row_for(msg_id):
        if msg_id not in emails:
            emails[msg_id] = {
                "ts": "", "sender": "", "subject": "",
                "classification": None, "action": None,
                "sent": None, "send_error": None,
            }
            order.append(msg_id)
        return emails[msg_id]

    for ev in events:
        name = ev.get("event")
        msg_id = ev.get("msg_id")
        if name == "processing_start" and msg_id:
            row = row_for(msg_id)
            row["ts"] = ev.get("ts", "")
            row["sender"] = ev.get("sender", "")
            row["subject"] = ev.get("subject", "")
        elif name == "classified" and msg_id:
            row = row_for(msg_id)
            row["classification"] = ev.get("classification")
            classifier_calls += 1
            usage = ev.get("usage") or {}
            for key in totals:
                totals[key] += usage.get(key) or 0
        elif name == "action_decided" and msg_id:
            row_for(msg_id)["action"] = ev.get("action")
        elif name == "send_result" and msg_id:
            row = row_for(msg_id)
            row["sent"] = ev.get("sent")
            row["send_error"] = ev.get("error")
        elif name in ("processing_error", "poll_error"):
            errors.append(ev)
        elif name in flow_counts:
            flow_counts[name] += 1

    n_emails = len(order)
    n_errors = len(errors)

    # --- Subject -----------------------------------------------------------
    if n_emails == 0 and n_errors == 0:
        subject = f"COI Daily Digest - {date_str}: no activity"
    else:
        subject = (
            f"COI Daily Digest - {date_str}: "
            f"{n_emails} email{'s' if n_emails != 1 else ''}, "
            f"{n_errors} error{'s' if n_errors != 1 else ''}"
        )

    # --- HTML body ---------------------------------------------------------
    cell = "padding: 6px 10px; border-bottom: 1px solid #ddd; text-align: left;"
    head = cell + " background: #f2f2f2; font-weight: bold;"
    parts = [
        '<div style="font-family: Arial, Helvetica, sans-serif; color: #222; '
        'font-size: 14px; max-width: 760px;">',
        f'<h2 style="margin: 0 0 4px;">COI Daily Digest</h2>',
        f'<p style="margin: 0 0 16px; color: #666;">{_esc(date_str)}</p>',
    ]

    # Emails processed
    parts.append(f'<h3 style="margin: 16px 0 8px;">Emails processed: {n_emails}</h3>')
    if order:
        parts.append('<table style="border-collapse: collapse; width: 100%;">')
        parts.append(
            "<tr>"
            f'<th style="{head}">Time</th>'
            f'<th style="{head}">Sender</th>'
            f'<th style="{head}">Subject</th>'
            f'<th style="{head}">Classification</th>'
            f'<th style="{head}">Action</th>'
            f'<th style="{head}">Sent</th>'
            "</tr>"
        )
        for msg_id in order:
            row = emails[msg_id]
            if row["action"] == "do_nothing":
                sent_html = '<span style="color: #666;">n/a</span>'
            elif row["sent"]:
                sent_html = '<span style="color: #1a7f37;">ok</span>'
            elif row["send_error"]:
                sent_html = (
                    f'<span style="color: #c0392b;">FAILED: '
                    f'{_esc(str(row["send_error"])[:120])}</span>'
                )
            else:
                sent_html = '<span style="color: #666;">no</span>'
            parts.append(
                "<tr>"
                f'<td style="{cell}">{_esc(_local_hhmm(row["ts"]))}</td>'
                f'<td style="{cell}">{_esc(row["sender"])}</td>'
                f'<td style="{cell}">{_esc(row["subject"])}</td>'
                f'<td style="{cell}">{_esc(row["classification"] or "-")}</td>'
                f'<td style="{cell}">{_esc(row["action"] or "-")}</td>'
                f'<td style="{cell}">{sent_html}</td>'
                "</tr>"
            )
        parts.append("</table>")
    else:
        parts.append('<p style="color: #666;">No emails processed.</p>')

    # Errors
    parts.append(
        f'<h3 style="margin: 16px 0 8px;">Errors: {n_errors}</h3>'
    )
    if errors:
        for ev in errors:
            detail = [
                f'<p style="margin: 4px 0;"><b>{_esc(_local_hhmm(ev.get("ts", "")))}'
                f' {_esc(ev.get("event"))}</b>: {_esc(ev.get("error"))}</p>'
            ]
            if ev.get("msg_id"):
                detail.append(
                    f'<p style="margin: 2px 0 4px; color: #666;">msg_id: '
                    f'{_esc(str(ev.get("msg_id"))[:60])}...</p>'
                )
            if ev.get("traceback"):
                detail.append(
                    '<pre style="background: #f7f7f7; border: 1px solid #ddd; '
                    'padding: 8px; font-size: 12px; overflow-x: auto; '
                    f'white-space: pre-wrap;">{_esc(str(ev.get("traceback"))[-400:])}</pre>'
                )
            parts.append(
                '<div style="border-left: 3px solid #c0392b; padding-left: 10px; '
                'margin: 8px 0;">' + "".join(detail) + "</div>"
            )
    else:
        parts.append('<p style="color: #666;">None.</p>')

    # Flow emails (referral / shortfall / non-compliance / carrier request)
    if any(flow_counts.values()):
        parts.append('<h3 style="margin: 16px 0 8px;">Flow emails</h3>')
        parts.append('<table style="border-collapse: collapse;">')
        for label, key in (
            ("Referral lines appended", "referral_appended"),
            ("Shortfall client emails", "shortfall_client_email"),
            ("Non-compliance emails (Alejandro)", "noncompliance_email"),
            ("Carrier endorsement requests", "carrier_endorsement_email"),
        ):
            if flow_counts[key]:
                parts.append(
                    f'<tr><td style="{cell}">{label}</td>'
                    f'<td style="{cell} text-align: right;">{flow_counts[key]}</td></tr>'
                )
        parts.append("</table>")

    # Token usage
    parts.append('<h3 style="margin: 16px 0 8px;">Token usage</h3>')
    total_tokens = sum(totals.values())
    parts.append('<table style="border-collapse: collapse;">')
    for label, key in (
        ("Input", "input_tokens"),
        ("Cache write", "cache_creation_input_tokens"),
        ("Cache read", "cache_read_input_tokens"),
        ("Output", "output_tokens"),
    ):
        parts.append(
            f'<tr><td style="{cell}">{label}</td>'
            f'<td style="{cell} text-align: right;">{totals[key]:,}</td></tr>'
        )
    parts.append(
        f'<tr><td style="{head}">Total ({classifier_calls} classifier '
        f'call{"s" if classifier_calls != 1 else ""})</td>'
        f'<td style="{head} text-align: right;">{total_tokens:,}</td></tr>'
    )
    parts.append("</table>")

    cost = _estimated_cost(totals)
    if cost is not None:
        parts.append(
            f'<p style="margin: 8px 0;"><b>Estimated API cost:</b> ${cost:,.4f}</p>'
        )

    parts.append(
        '<p style="margin: 20px 0 0; color: #999; font-size: 12px;">'
        f"Generated by the COI automation. Full log: logs/coi-{_esc(date_str)}.jsonl</p>"
    )
    parts.append("</div>")

    return subject, "".join(parts)


def send_digest_if_due(graph, run_state, now=None):
    """Send yesterday's digest to DIGEST_TO once per day after DIGEST_HOUR
    local time. Cheap no-op otherwise. Returns True only when a digest was
    sent successfully."""
    try:
        if not config.DIGEST_ENABLED:
            return False
        now = now or datetime.now()
        if now.hour < config.DIGEST_HOUR:
            return False
        target_date = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        if run_state.get("last_digest_date") == target_date:
            return False

        # Mark the attempt BEFORE sending — one attempt per day, never a
        # retry storm if Graph rejects the payload. Failures land in the log.
        run_state["last_digest_date"] = target_date
        state.save_state(run_state)

        subject, html_body = build_daily_digest(target_date)
        ok, resp = graph.send_mail({
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": config.DIGEST_TO}}],
        })
        state.log_event(
            "digest_sent",
            date=target_date,
            to=config.DIGEST_TO,
            ok=ok,
            error=None if ok else _resp_snippet(resp),
        )
        return ok
    except Exception as e:
        _ops_error("send_digest_if_due", e)
        return False


# ---------------------------------------------------------------------------
# Error alerts
# ---------------------------------------------------------------------------

def send_error_alert(graph, run_state, error_event, now_ts=None):
    """Immediate email to ALERT_TO on processing_error / poll_error.
    Rate-limited: at most one alert email per 30 minutes (last_alert_ts in
    run_state). Suppressed errors are already in the JSONL log."""
    try:
        now_ts = time.time() if now_ts is None else now_ts
        last_ts = run_state.get("last_alert_ts") or 0
        if now_ts - last_ts < ALERT_MIN_INTERVAL_SECONDS:
            return False

        # Mark the attempt BEFORE sending so a failing send can't hammer Graph.
        run_state["last_alert_ts"] = now_ts
        state.save_state(run_state)

        event_name = error_event.get("event", "error")
        error_text = str(error_event.get("error") or "unknown error")
        date_str = datetime.now().strftime("%Y-%m-%d")

        lines = [
            '<div style="font-family: Arial, Helvetica, sans-serif; color: #222; '
            'font-size: 14px;">',
            f'<p>The COI automation hit a <b>{_esc(event_name)}</b>.</p>',
            f'<p><b>Error:</b> {_esc(error_text)}</p>',
        ]
        if error_event.get("subject") or error_event.get("sender"):
            lines.append(
                f'<p><b>Email:</b> {_esc(error_event.get("subject") or "(no subject)")} '
                f'from {_esc(error_event.get("sender") or "(unknown sender)")}</p>'
            )
        lines.append(
            f"<p>The loop is still running; check logs/coi-{date_str}.jsonl "
            "for details. At most one alert email is sent per 30 minutes; any "
            "further errors in that window are only in the log.</p>"
        )
        lines.append("</div>")

        ok, resp = graph.send_mail({
            "subject": f"COI automation {event_name}: {error_text[:80]}",
            "body": {"contentType": "HTML", "content": "".join(lines)},
            "toRecipients": [{"emailAddress": {"address": config.ALERT_TO}}],
        })
        state.log_event(
            "alert_sent",
            source_event=event_name,
            to=config.ALERT_TO,
            ok=ok,
            error=None if ok else _resp_snippet(resp),
        )
        return ok
    except Exception as e:
        _ops_error("send_error_alert", e)
        return False


def _resp_snippet(resp):
    """Short diagnostic string from a Graph Response (may be None)."""
    if resp is None:
        return "no response"
    status = getattr(resp, "status_code", None)
    text = getattr(resp, "text", "") or ""
    return f"HTTP {status}: {text[:200]}"


# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------

def rotate_logs(run_state, now=None, logs_dir=None, output_dir=None):
    """Delete logs/*.jsonl older than LOG_RETENTION_DAYS and output/*.pdf
    older than PDF_RETENTION_DAYS. Runs at most once per day
    (last_rotation_date in run_state) and never deletes today's files."""
    try:
        now = now or datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        if run_state.get("last_rotation_date") == today_str:
            return {"skipped": True, "deleted_logs": [], "deleted_pdfs": []}

        run_state["last_rotation_date"] = today_str
        state.save_state(run_state)

        deleted_logs = _delete_older_than(
            logs_dir or config.LOGS_DIR, ".jsonl",
            config.LOG_RETENTION_DAYS, now, today_str,
        )
        deleted_pdfs = _delete_older_than(
            output_dir or config.OUTPUT_DIR, ".pdf",
            config.PDF_RETENTION_DAYS, now, today_str,
        )
        state.log_event(
            "rotation",
            deleted_log_count=len(deleted_logs),
            deleted_pdf_count=len(deleted_pdfs),
            deleted_logs=deleted_logs,
            deleted_pdfs=deleted_pdfs,
            log_retention_days=config.LOG_RETENTION_DAYS,
            pdf_retention_days=config.PDF_RETENTION_DAYS,
        )
        return {"skipped": False, "deleted_logs": deleted_logs,
                "deleted_pdfs": deleted_pdfs}
    except Exception as e:
        _ops_error("rotate_logs", e)
        return {"skipped": True, "deleted_logs": [], "deleted_pdfs": []}


def _delete_older_than(directory, ext, retention_days, now, today_str):
    """Delete files in directory ending with ext whose mtime is older than
    retention_days. Today's files (by mtime date OR by today's date in the
    filename) are never touched. Returns deleted filenames."""
    if not os.path.isdir(directory):
        return []
    cutoff_ts = now.timestamp() - retention_days * 86400
    deleted = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(ext):
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime >= cutoff_ts:
            continue
        # Belt and suspenders: never delete anything from today.
        if datetime.fromtimestamp(mtime).strftime("%Y-%m-%d") == today_str:
            continue
        if today_str in name:
            continue
        try:
            os.remove(path)
            deleted.append(name)
        except OSError:
            continue
    return deleted
