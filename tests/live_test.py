"""
live_test.py — self-driving end-to-end tests against the RUNNING loop.

Injects simulated client emails into the admin inbox (sent from the admin
mailbox to itself, tagged with an X-COI-Test header so main.py processes
them), waits for the loop to reply, then pulls the actual outbound replies
and verifies content, style rules, signature, and attachments.

Tests:
  A. Incomplete request (EMP 3, holder without address) -> expect text reply
  B. Spanish incomplete request (Central Comfort)        -> expect Spanish reply
  C. Complete request (Rolando's) -> expect COI PDF reply,
     then an in-thread revision   -> expect revised COI PDF reply

Requires: the polling loop running (./start.sh) and TEST_MODE on.
Usage: .venv/bin/python tests/live_test.py
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from graph_client import GraphClient

RUN_TAG = datetime.now(timezone.utc).strftime("%H%M%S")
LOG_PATH = os.path.join(
    config.LOGS_DIR, f"coi-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
)
WAIT_TIMEOUT = 300  # seconds per test


def send_test_email(graph, subject, body_text, reply_to_msg_id=None):
    """Send a simulated client email into the admin inbox."""
    if reply_to_msg_id:
        message_obj = {
            "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
            "body": {"contentType": "Text", "content": body_text},
            "internetMessageHeaders": [{"name": "X-COI-Test", "value": "client-sim"}],
        }
        ok, resp = graph.reply_to_message(reply_to_msg_id, message_obj)
    else:
        message_obj = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
            "internetMessageHeaders": [{"name": "X-COI-Test", "value": "client-sim"}],
        }
        ok, resp = graph.send_mail(message_obj)
    if not ok:
        raise RuntimeError(f"send failed: {resp.status_code}: {resp.text[:300]}")


def wait_for_processing(subject_token, after_ts):
    """Watch the JSONL log for the full event chain of a message whose
    subject contains subject_token. Returns dict of events."""
    deadline = time.time() + WAIT_TIMEOUT
    events = {}
    msg_id = None
    while time.time() < deadline:
        try:
            with open(LOG_PATH) as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if ev.get("ts", "") < after_ts:
                        continue
                    if ev.get("event") == "processing_start" and subject_token in (ev.get("subject") or ""):
                        msg_id = ev.get("msg_id")
                    if msg_id and ev.get("msg_id") == msg_id:
                        events[ev["event"]] = ev
        except FileNotFoundError:
            pass
        if "send_result" in events:
            return events
        time.sleep(10)
    return events


def get_loop_reply(graph, subject_token, after_ts):
    """Find the loop's outbound reply for a test thread (it lives in the
    mailbox with the same conversation; sender = admin, has our body)."""
    msgs = graph.list_inbox_since("2000-01-01T00:00:00Z", top=5)  # warm call, ignored
    # Search sent items via conversation: find the inbox test message first
    resp = graph._request(
        "GET", graph._mb("/messages"),
        params={
            "$search": f'"subject:{subject_token}"',
            "$top": 20,
        },
        headers={"ConsistencyLevel": "eventual"},
    )
    if resp.status_code != 200:
        return None
    candidates = resp.json().get("value", [])
    conv_ids = {m.get("conversationId") for m in candidates if m.get("conversationId")}
    replies = []
    for cid in conv_ids:
        for m in graph.search_by_conversation(cid):
            frm = (m.get("from", {}).get("emailAddress", {}).get("address") or "").lower()
            if frm == config.COI_MAILBOX.lower() and (m.get("sentDateTime") or "") >= after_ts:
                hdr_check = m.get("internetMessageId")
                body = (m.get("body") or {}).get("content") or ""
                # loop replies contain the signature or reply text; test
                # injections have X-COI-Test, but easiest filter: replies
                # have subject starting Re: and body with HTML content
                if (m.get("subject") or "").lower().startswith("re:"):
                    replies.append(m)
    replies.sort(key=lambda m: m.get("sentDateTime") or "")
    return replies[-1] if replies else None


def style_checks(body_html, expect_spanish=False):
    """Verify locked-in reply style rules. Returns list of problems."""
    text = re.sub(r"<br\s*/?>", "\n", body_html)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").strip()
    # Cut everything after the signature (Laura Rodriguez) for body checks
    body = text.split("Laura Rodriguez")[0].strip()
    problems = []
    if re.match(r"^(hi|hello|hey|hola|buenas)\b", body, re.I):
        problems.append(f"greeting used: {body[:40]!r}")
    first_line = body.split("\n")[0]
    if "," not in first_line[:40]:
        problems.append(f"no name-comma opener: {first_line[:60]!r}")
    for dash in ("—", "–"):
        if dash in body:
            problems.append(f"dash found: {dash!r}")
    if expect_spanish:
        if not body.rstrip().endswith("Saludos,"):
            problems.append(f"Spanish reply does not end with Saludos,: ...{body[-40:]!r}")
        if "mándame" in body.lower() or "mandame" in body.lower():
            problems.append("uses mándame (must be envíame)")
    else:
        if not body.rstrip().endswith("Regards,"):
            problems.append(f"English reply does not end with Regards,: ...{body[-40:]!r}")
    if "Laura Rodriguez" not in text:
        problems.append("signature missing")
    return problems, body


def report(name, events, reply, problems, body_preview):
    cls = (events.get("classified") or {}).get("classification")
    action = (events.get("action_decided") or {}).get("action")
    sent = (events.get("send_result") or {}).get("sent")
    print(f"\n{'='*70}\n{name}")
    print(f"  classification: {cls}   action: {action}   sent: {sent}")
    if reply:
        print(f"  reply subject: {reply.get('subject')}")
        print(f"  reply hasAttachments: {reply.get('hasAttachments')}")
    if body_preview:
        print(f"  reply body (stripped):\n    " + body_preview.replace("\n", "\n    "))
    if problems:
        for p in problems:
            print(f"  [PROBLEM] {p}")
    else:
        print("  [OK] all checks passed")
    return not problems


def main():
    graph = GraphClient()
    all_ok = True

    # ---------- TEST A: incomplete request ----------
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    subj_a = f"[LT-{RUN_TAG}-A] COI needed"
    send_test_email(graph, subj_a,
        "Hi, can I get a COI for EMP 3 Solutions? Certificate holder is "
        "Ruiz Electric Corporation. Thanks")
    print(f"sent A: {subj_a}")

    # ---------- TEST B: Spanish incomplete ----------
    subj_b = f"[LT-{RUN_TAG}-B] Certificado de seguro"
    send_test_email(graph, subj_b,
        "Buenas tardes, necesito un certificado de seguro para Central Comfort. "
        "El certificate holder es Inversiones Marbella LLC. Gracias")
    print(f"sent B: {subj_b}")

    ev_a = wait_for_processing(f"LT-{RUN_TAG}-A", now)
    ev_b = wait_for_processing(f"LT-{RUN_TAG}-B", now)

    reply_a = get_loop_reply(graph, f"LT-{RUN_TAG}-A", now)
    problems_a, body_a = style_checks((reply_a.get("body") or {}).get("content", "")) if reply_a else (["no reply found"], "")
    all_ok &= report("TEST A — incomplete request (EMP 3 / Ruiz Electric, no address)",
                     ev_a, reply_a, problems_a, body_a)

    reply_b = get_loop_reply(graph, f"LT-{RUN_TAG}-B", now)
    problems_b, body_b = style_checks((reply_b.get("body") or {}).get("content", ""), expect_spanish=True) if reply_b else (["no reply found"], "")
    all_ok &= report("TEST B — Spanish incomplete request (Central Comfort / Inversiones Marbella)",
                     ev_b, reply_b, problems_b, body_b)

    # ---------- TEST C: complete request, then revision ----------
    now_c = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    subj_c = f"[LT-{RUN_TAG}-C] COI request Rolandos HVAC"
    send_test_email(graph, subj_c,
        "Good morning, please issue a COI for Rolando's HVAC. Certificate holder: "
        "City of Doral Building Department, 8401 NW 53rd Ter, Doral, FL 33166.")
    print(f"\nsent C1: {subj_c}")
    ev_c1 = wait_for_processing(f"LT-{RUN_TAG}-C", now_c)
    reply_c1 = get_loop_reply(graph, f"LT-{RUN_TAG}-C", now_c)
    ok_c1 = bool(reply_c1 and reply_c1.get("hasAttachments"))
    all_ok &= report("TEST C1 — complete request (expect COI PDF attached)",
                     ev_c1, reply_c1, [] if ok_c1 else ["no reply with attachment"], "")

    # find the INBOX copy of the test email to reply to (start the revision)
    inbox_msgs = graph.list_inbox_since(now_c, top=25)
    c_inbox = [m for m in inbox_msgs if f"LT-{RUN_TAG}-C" in (m.get("subject") or "")]
    if not c_inbox:
        print("[PROBLEM] cannot find C thread inbox message for revision")
        return 1
    now_c2 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    send_test_email(graph, None,
        "Thank you! One correction, the address should be 8300 NW 53rd St, "
        "Suite 100, Doral, FL 33166. Can you resend the certificate?",
        reply_to_msg_id=c_inbox[-1]["id"])
    print(f"sent C2 (in-thread revision)")
    ev_c2 = wait_for_processing(f"LT-{RUN_TAG}-C", now_c2)
    reply_c2 = get_loop_reply(graph, f"LT-{RUN_TAG}-C", now_c2)
    cls_c2 = (ev_c2.get("classified") or {}).get("classification")
    problems_c2 = []
    if cls_c2 != "coi_revision_request":
        problems_c2.append(f"expected coi_revision_request, got {cls_c2}")
    if not (reply_c2 and reply_c2.get("hasAttachments")):
        problems_c2.append("no revised COI attached")
    all_ok &= report("TEST C2 — in-thread revision (expect REVISED COI PDF)",
                     ev_c2, reply_c2, problems_c2, "")

    # verify the revised PDF content from the local output dir
    pdfs = sorted(
        (os.path.join(config.OUTPUT_DIR, f) for f in os.listdir(config.OUTPUT_DIR) if f.endswith(".pdf")),
        key=os.path.getmtime,
    )
    if pdfs:
        import fitz
        doc = fitz.open(pdfs[-1])
        text = doc[0].get_text()
        doc.close()
        print(f"\nLatest generated PDF: {os.path.basename(pdfs[-1])}")
        for needle in ("City of Doral", "8300 NW 53rd St", "Suite 100"):
            mark = "OK" if needle in text else "MISSING"
            print(f"  [{mark}] {needle!r} on the revised COI")
            if mark == "MISSING":
                all_ok = False

    print(f"\n{'='*70}\nRESULT: {'ALL TESTS PASSED' if all_ok else 'PROBLEMS FOUND (see above)'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
