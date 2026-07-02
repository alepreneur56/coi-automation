"""
main.py
-------
COI Automation — local runtime entry point.

Polls the admin@clientpolicyhelp.com inbox via Microsoft Graph, runs each new
email through the pipeline (thread fetch -> attachments -> Claude classifier
-> PDF engine -> Graph send), and logs every step as JSON lines.

Usage:
    python3 main.py                 # run the polling loop forever
    python3 main.py --once          # single poll cycle, then exit
    python3 main.py --dry-run       # process but send nothing (safe test)
    python3 main.py --check         # verify credentials + connectivity, exit
"""

import argparse
import sys
import time
import traceback

import config
import state
from attachments import fetch_attachments
from classifier import classify, load_system_prompt
from graph_client import GraphClient, GraphError
from pipeline import decide_action
from sender import execute_action
from thread_fetch import fetch_thread


def process_message(graph, msg, dry_run=False):
    """Full pipeline for one inbox message. Returns a result dict for logging."""
    msg_id = msg.get("id")
    sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    subject = msg.get("subject", "")

    # Never process our own outbound mail (e.g. self-CC loops) — EXCEPT
    # simulated client emails injected by tests/live_test.py, which carry an
    # X-COI-Test header. The loop's own replies never carry that header, so
    # reply loops remain impossible.
    if sender.lower() == config.COI_MAILBOX.lower():
        hdrs = {
            (h.get("name") or "").lower()
            for h in graph.get_message_headers(msg_id)
        }
        if "x-coi-test" not in hdrs:
            return {"skipped": True, "reason": "message from our own mailbox"}

    state.log_event("processing_start", msg_id=msg_id, sender=sender, subject=subject)

    thread_result = fetch_thread(graph, msg)
    attachments_result = fetch_attachments(graph, msg)
    state.log_event(
        "context_fetched",
        msg_id=msg_id,
        thread_method=thread_result.get("method"),
        thread_count=thread_result.get("thread_message_count"),
        attachment_count=attachments_result.get("attachment_count"),
        pdf_count=attachments_result.get("pdf_count"),
        image_count=attachments_result.get("image_count"),
    )

    ai_result = classify(msg, thread_result["messages"], attachments_result)
    parsed = ai_result.get("parsed") or {}
    state.log_event(
        "classified",
        msg_id=msg_id,
        success=ai_result.get("success"),
        classification=parsed.get("classification"),
        status=parsed.get("status"),
        client=parsed.get("client_canonical_name"),
        api_error=ai_result.get("api_error"),
        parse_error=ai_result.get("parse_error"),
    )

    decision = decide_action(ai_result)
    state.log_event(
        "action_decided",
        msg_id=msg_id,
        action=decision.get("action"),
        reason=decision.get("reason"),
        pdf_count=len(decision.get("pdf_paths", [])),
        error_detail=decision.get("error_detail"),
    )

    send_result = execute_action(
        graph, msg, thread_result["messages"], attachments_result,
        ai_result, decision, dry_run=dry_run,
    )
    state.log_event(
        "send_result",
        msg_id=msg_id,
        action=decision.get("action"),
        sent=send_result.get("sent"),
        type=send_result.get("type"),
        error=send_result.get("error") or send_result.get("review_email_error"),
    )

    if not dry_run:
        graph.mark_read(msg_id)

    return {
        "skipped": False,
        "classification": parsed.get("classification"),
        "action": decision.get("action"),
        "send_result": send_result,
    }


def poll_once(graph, run_state, dry_run=False):
    """One poll cycle. Returns number of messages processed."""
    watermark = run_state.get("watermark") or state.utc_now_iso()
    processed_ids = set(run_state.get("processed_ids", []))

    messages = graph.list_inbox_since(watermark)
    handled = 0
    for msg in messages:
        msg_id = msg.get("id")
        received = msg.get("receivedDateTime", watermark)
        if msg_id in processed_ids:
            continue
        try:
            process_message(graph, msg, dry_run=dry_run)
        except Exception as e:
            state.log_event(
                "processing_error",
                msg_id=msg_id,
                error=str(e),
                traceback=traceback.format_exc()[-1500:],
            )
        # Advance the watermark even on failure — one poison message must
        # never wedge the loop. Failures are in the log for manual follow-up.
        processed_ids.add(msg_id)
        run_state["processed_ids"] = list(processed_ids)[-500:]
        if received > run_state.get("watermark", ""):
            run_state["watermark"] = received
        state.save_state(run_state)
        handled += 1
    return handled


def run_check():
    """Verify config, prompt, templates, Graph auth, and Anthropic key."""
    print("1. Config loaded OK")
    print(f"   Mailbox: {config.COI_MAILBOX}")
    print(f"   TEST_MODE: {config.TEST_MODE} (redirect: {config.TEST_REDIRECT_TO})")
    print(f"   Model: {config.ANTHROPIC_MODEL}")

    prompt = load_system_prompt()
    print(f"2. System prompt + registry OK ({len(prompt):,} chars)")

    import os
    templates = [f for f in os.listdir(config.TEMPLATES_DIR) if f.endswith(".pdf")]
    print(f"3. Templates dir OK ({len(templates)} PDFs)")

    graph = GraphClient()
    try:
        graph._get_token()
        print("4. Graph token OK (client credentials)")
    except GraphError as e:
        print(f"4. FAILED — Graph token: {e}")
        return 1

    try:
        msgs = graph.list_inbox_since("2000-01-01T00:00:00Z", top=1)
        print(f"5. Mailbox read OK (inbox reachable, sample={len(msgs)} message)")
    except GraphError as e:
        print(f"5. FAILED — mailbox read: {e}")
        return 1

    import requests
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.ANTHROPIC_MODEL,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Say OK"}],
        },
        timeout=60,
    )
    if resp.status_code == 200:
        print("6. Anthropic API OK")
    else:
        print(f"6. FAILED — Anthropic API: HTTP {resp.status_code}: {resp.text[:300]}")
        return 1

    print("\nAll checks passed. Ready to run: python3 main.py")
    return 0


def main():
    parser = argparse.ArgumentParser(description="COI automation runtime")
    parser.add_argument("--once", action="store_true", help="one poll cycle, then exit")
    parser.add_argument("--dry-run", action="store_true", help="process but send nothing")
    parser.add_argument("--check", action="store_true", help="verify credentials + connectivity")
    args = parser.parse_args()

    if args.check:
        sys.exit(run_check())

    graph = GraphClient()
    run_state = state.load_state()
    state.log_event(
        "startup",
        mailbox=config.COI_MAILBOX,
        test_mode=config.TEST_MODE,
        dry_run=args.dry_run,
        watermark=run_state.get("watermark"),
        poll_interval=config.POLL_INTERVAL_SECONDS,
    )

    while True:
        try:
            handled = poll_once(graph, run_state, dry_run=args.dry_run)
            if handled:
                state.log_event("poll_cycle", handled=handled)
        except GraphError as e:
            state.log_event("poll_error", error=str(e))
        except Exception as e:
            state.log_event(
                "poll_error", error=str(e),
                traceback=traceback.format_exc()[-1500:],
            )
        if args.once:
            break
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
