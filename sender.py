"""
sender.py
---------
Outbound email — port of the Pipedream send_or_reply step onto GraphClient.

Handles four actions from pipeline.decide_action():
  - do_nothing / error       -> no email
  - send_reply               -> threaded text reply
  - send_pdf                 -> threaded reply with COI PDF(s) attached
  - send_complex_review      -> (a) client ack reply + (b) NEW review email
                                to Alejandro with draft + originals attached

TEST MODE GUARD (config.TEST_MODE): every client-facing email is redirected
to config.TEST_REDIRECT_TO and CC lists are stripped. The complex-review
email to Alejandro is never redirected — it already goes to him by design.
"""

import base64
import os

import config

ADMIN_INBOX_EMAIL = config.COI_MAILBOX

# Signature appended to every CLIENT-FACING email (text replies, COI
# deliveries, complex-review acks). The internal review email to Alejandro
# does not get it. Claude's reply_text ends at "Regards,"/"Saludos," by rule;
# this is the only place the signature is added.
SIGNATURE_PATH = os.path.join(config.BASE_DIR, "signature.html")
_signature_cache = None


def _load_signature():
    global _signature_cache
    if _signature_cache is None:
        try:
            with open(SIGNATURE_PATH, "r") as f:
                _signature_cache = f.read().strip()
        except FileNotFoundError:
            _signature_cache = ""
    return _signature_cache


def with_signature(html_body):
    sig = _load_signature()
    if not sig:
        return html_body
    return f"{html_body}\n{sig}"


# The signature references an inline LinkedIn icon via cid:. Graph needs the
# PNG attached with isInline + a matching contentId or clients show a broken
# image box.
SIGNATURE_IMAGE_PATH = os.path.join(config.BASE_DIR, "signature_image001.png")
SIGNATURE_IMAGE_CID = "image001.png@01DD0A19.E6D9DA80"
_signature_image_cache = None


def signature_attachments():
    """Inline attachment list for the signature image. Empty if the
    signature (or its image) isn't configured."""
    global _signature_image_cache
    if not _load_signature():
        return []
    if _signature_image_cache is None:
        try:
            with open(SIGNATURE_IMAGE_PATH, "rb") as f:
                _signature_image_cache = base64.b64encode(f.read()).decode("utf-8")
        except FileNotFoundError:
            _signature_image_cache = ""
    if not _signature_image_cache:
        return []
    return [{
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "image001.png",
        "contentType": "image/png",
        "contentBytes": _signature_image_cache,
        "isInline": True,
        "contentId": SIGNATURE_IMAGE_CID,
    }]


def apply_test_mode(to_list, cc_list):
    """In test mode, force To = test redirect and CC = empty.
    Returns (to_list, cc_list, original_to, original_cc)."""
    if not config.TEST_MODE:
        return to_list, cc_list, None, None
    return [config.TEST_REDIRECT_TO], [], list(to_list), list(cc_list)


def first_name_from(display_name, email):
    """Extract a recipient first name. Prefer display name's first token,
    fall back to the local-part of the email (capitalized)."""
    if display_name:
        tokens = display_name.strip().split()
        if tokens:
            return tokens[0]
    if email:
        local = email.split("@", 1)[0]
        local = local.split(".", 1)[0].split("+", 1)[0]
        if local:
            return local.capitalize()
    return "there"


def build_holder_line(parsed):
    """Format the cert holder line for the email body."""
    ch = parsed.get("certificate_holder") or {}
    parts = []
    for key in ("name", "address_line_1", "address_line_2"):
        v = (ch.get(key) or "").strip()
        if v:
            parts.append(v)
    csz = " ".join(
        p for p in [(ch.get("city") or "").strip(), (ch.get("state") or "").strip(), (ch.get("zip") or "").strip()] if p
    )
    if csz:
        parts.append(csz)
    return ", ".join(parts) if parts else ""


def _thread_context(thread_messages, new_email):
    """Find the original client sender + collect every unique participant
    across the thread (senders, To, CC). Excludes our own inbox."""
    original_client_sender = None
    original_client_name = None
    for msg in thread_messages:
        f = msg.get("from", {}).get("emailAddress") or {}
        addr = (f.get("address") or "").strip()
        if addr and addr.lower() != ADMIN_INBOX_EMAIL.lower():
            original_client_sender = addr
            original_client_name = (f.get("name") or "").strip()
            break
    if not original_client_sender:
        original_client_sender = (
            new_email.get("from", {}).get("emailAddress", {}).get("address", "")
        )
        original_client_name = (
            new_email.get("from", {}).get("emailAddress", {}).get("name", "")
        )

    participants = {}

    def add(addr):
        a = (addr or "").strip()
        if a:
            participants.setdefault(a.lower(), a)

    for msg in thread_messages:
        add(msg.get("from", {}).get("emailAddress", {}).get("address"))
        for r in (msg.get("toRecipients") or []):
            add(r.get("emailAddress", {}).get("address"))
        for r in (msg.get("ccRecipients") or []):
            add(r.get("emailAddress", {}).get("address"))

    add(config.PRODUCER_CC_EMAIL)
    participants.pop(ADMIN_INBOX_EMAIL.lower(), None)

    return original_client_sender, original_client_name, participants


def _file_attachment(path):
    with open(path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": os.path.basename(path),
        "contentType": "application/pdf",
        "contentBytes": content_b64,
    }


def _cov_field(cov, keys, default="not stated"):
    """Return the first non-empty value among the given keys.

    coverage_analysis entries arrive in two schemas: the system prompt's
    OUTPUT FORMAT (required_each_occurrence / client_each_occurrence) and
    the legacy renderer schema (required_limit / insured_limit). Accept both
    so limits never render blank; fall back to 'not stated' when absent.
    """
    for key in keys:
        val = cov.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def build_complex_review_body(client_name, request_summary, review_summary,
                              coverage_analysis, send_completed_coi_to,
                              original_client_sender, original_client_name):
    """Review email body sent to Alejandro — same layout as the validated
    Pipedream version."""
    parts = [
        f"<p><b>Complex COI request for {client_name} — draft attached for your review.</b></p>"
    ]
    sender_display = (original_client_name or "").strip()
    sender_addr = (original_client_sender or "").strip()
    if sender_display and sender_addr:
        parts.append(f"<p><b>From client:</b> {sender_display} &lt;{sender_addr}&gt;</p>")
    elif sender_addr:
        parts.append(f"<p><b>From client:</b> {sender_addr}</p>")

    if send_completed_coi_to:
        parts.append(f"<p><b>Send completed COI to:</b> {send_completed_coi_to}</p>")
    if request_summary:
        parts.append(f"<p><b>Request summary:</b><br>{request_summary}</p>")
    if review_summary:
        parts.append(f"<p><b>Review notes:</b><br>{review_summary}</p>")

    if coverage_analysis:
        parts.append("<hr><p><b>Coverage analysis</b></p>")
        required = coverage_analysis.get("required_coverages") or []
        if required:
            parts.append("<p><b>Required coverages:</b></p><ul>")
            for cov in required:
                flag = " — [GAP]" if cov.get("gap") else " — [OK]"
                line = _cov_field(cov, ("line", "coverage_line", "coverage"), default="")
                required_limit = _cov_field(
                    cov, ("required_limit", "required_each_occurrence"))
                insured_limit = _cov_field(
                    cov, ("insured_limit", "client_each_occurrence", "client_limit"))
                parts.append(
                    f"<li><b>{line}</b> — required: {required_limit} | "
                    f"insured carries: {insured_limit}{flag}</li>"
                )
            parts.append("</ul>")
        endorsements = coverage_analysis.get("required_endorsements") or []
        if endorsements:
            parts.append("<p><b>Required endorsements:</b></p><ul>")
            for e in endorsements:
                parts.append(f"<li>{e}</li>")
            parts.append("</ul>")
        special = (coverage_analysis.get("special_language") or "").strip()
        if special:
            parts.append(f"<p><b>Special wording / language:</b><br>{special}</p>")
        notes = (coverage_analysis.get("notes") or "").strip()
        if notes:
            parts.append(f"<p><b>Additional notes:</b><br>{notes}</p>")

    parts.append(
        "<hr>"
        "<p><i>Attached:</i></p>"
        "<ul>"
        "<li><i>The draft COI PDF (filename starts with the client name).</i></li>"
        "<li><i>The original contract / insurance requirements that came in "
        "with the client email (filename prefixed with <b>ORIGINAL -</b>) for "
        "your own review.</i></li>"
        "</ul>"
        "<p><i>The client has been sent an acknowledgment reply in their "
        "thread — they have NOT received the draft. Review and forward "
        "manually if everything checks out.</i></p>"
    )
    return "".join(parts)


def execute_action(graph, new_email, thread_messages, attachments_result,
                   ai_result, decision, dry_run=False):
    """Perform the email action decided by the pipeline.
    dry_run=True builds everything but sends nothing (logged instead)."""
    action = decision.get("action")

    if action in ("do_nothing", "error"):
        return {
            "sent": False,
            "action": action,
            "reason": decision.get("reason", "No email action required"),
        }

    original_msg_id = new_email.get("id")
    parsed = ai_result.get("parsed") or {}
    original_client_sender, original_client_name, participants = _thread_context(
        thread_messages, new_email
    )

    # ------------------------------------------------------------------
    # 2. Threaded text reply
    # ------------------------------------------------------------------
    if action == "send_reply":
        reply_text = decision.get("reply_text", "")
        html_body = with_signature(reply_text.replace("\n", "<br>"))

        to_lower = (original_client_sender or "").lower()
        intended_to = [original_client_sender] if original_client_sender else []
        intended_cc = [v for k, v in participants.items() if k != to_lower]
        to_list, cc_list, orig_to, orig_cc = apply_test_mode(intended_to, intended_cc)

        message_obj = {
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": e}} for e in to_list],
            "ccRecipients": [{"emailAddress": {"address": e}} for e in cc_list],
        }
        sig_atts = signature_attachments()
        if sig_atts:
            message_obj["attachments"] = sig_atts

        if dry_run:
            return {"sent": False, "dry_run": True, "type": "reply",
                    "would_send_to": to_list, "would_cc": cc_list,
                    "reply_text": reply_text}

        ok, resp = graph.reply_to_message(original_msg_id, message_obj)
        result = {
            "sent": ok,
            "type": "reply",
            "test_mode": config.TEST_MODE,
            "to": to_list,
            "cc": cc_list,
            "intended_to_blocked_by_test_mode": orig_to,
            "intended_cc_blocked_by_test_mode": orig_cc,
            "reply_text": reply_text,
        }
        if not ok:
            result["error"] = f"Graph API returned {resp.status_code}"
            result["response"] = resp.text[:500]
        return result

    # ------------------------------------------------------------------
    # 3. PDF as a threaded reply, with optional third-party recipient
    # ------------------------------------------------------------------
    if action == "send_pdf":
        client_name = decision.get("client_name", "Client")
        pdf_paths = decision.get("pdf_paths", [])
        is_revision = bool(decision.get("is_revision", False))
        third_party = parsed.get("send_completed_coi_to")

        if not pdf_paths:
            return {"sent": False, "type": "pdf_reply", "error": "No pdf_paths provided"}

        to_dict = {}
        if original_client_sender:
            to_dict[original_client_sender.lower()] = original_client_sender
        if third_party:
            to_dict[third_party.lower()] = third_party
        intended_to = list(to_dict.values())
        intended_cc = [v for k, v in participants.items() if k not in set(to_dict.keys())]
        to_list, cc_list, orig_to, orig_cc = apply_test_mode(intended_to, intended_cc)

        recipient_first = first_name_from(original_client_name, original_client_sender)
        holder_line = build_holder_line(parsed)
        descriptor = "the revised Certificate of Insurance" if is_revision else "the Certificate of Insurance"
        intro_line = f"Attached please find {descriptor} for {client_name}."
        if holder_line:
            intro_line += f"<br>Cert holder: {holder_line}."

        body_html = with_signature(
            f"<p>{recipient_first},</p>"
            f"<p>{intro_line}</p>"
            "<p>Let us know if you need anything else.</p>"
            "<p>Regards,</p>"
        )

        message_obj = {
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": e}} for e in to_list],
            "ccRecipients": [{"emailAddress": {"address": e}} for e in cc_list],
            "attachments": [_file_attachment(p) for p in pdf_paths] + signature_attachments(),
        }

        if dry_run:
            return {"sent": False, "dry_run": True, "type": "pdf_reply",
                    "would_send_to": to_list, "would_cc": cc_list,
                    "attachments": [os.path.basename(p) for p in pdf_paths]}

        ok, resp = graph.reply_to_message(original_msg_id, message_obj)
        result = {
            "sent": ok,
            "type": "pdf_reply",
            "is_revision": is_revision,
            "test_mode": config.TEST_MODE,
            "client_name": client_name,
            "to": to_list,
            "cc": cc_list,
            "intended_to_blocked_by_test_mode": orig_to,
            "intended_cc_blocked_by_test_mode": orig_cc,
            "third_party_added": bool(third_party),
            "attachment_count": len(pdf_paths),
        }
        if not ok:
            result["error"] = f"Graph API returned {resp.status_code}"
            result["response"] = resp.text[:500]
        return result

    # ------------------------------------------------------------------
    # 4. Complex review: client ack reply + review email to Alejandro
    # ------------------------------------------------------------------
    if action == "send_complex_review":
        client_name = decision.get("client_name", "Client")
        pdf_paths = decision.get("pdf_paths", [])
        client_reply_text = decision.get("client_reply_text", "") or ""

        results = {
            "sent": True,
            "type": "complex_review",
            "test_mode": config.TEST_MODE,
            "client_name": client_name,
        }

        # ---- (a) CLIENT ACK REPLY (in-thread, no attachment) ----
        if client_reply_text:
            ack_html = with_signature(client_reply_text.replace("\n", "<br>"))
            ack_to_lower = (original_client_sender or "").lower()
            ack_intended_to = [original_client_sender] if original_client_sender else []
            ack_intended_cc = [v for k, v in participants.items() if k != ack_to_lower]
            ack_to, ack_cc, ack_orig_to, ack_orig_cc = apply_test_mode(
                ack_intended_to, ack_intended_cc
            )
            ack_obj = {
                "body": {"contentType": "HTML", "content": ack_html},
                "toRecipients": [{"emailAddress": {"address": e}} for e in ack_to],
                "ccRecipients": [{"emailAddress": {"address": e}} for e in ack_cc],
            }
            ack_sig_atts = signature_attachments()
            if ack_sig_atts:
                ack_obj["attachments"] = ack_sig_atts
            if dry_run:
                results["client_ack_dry_run"] = {"would_send_to": ack_to}
            else:
                ok, resp = graph.reply_to_message(original_msg_id, ack_obj)
                results["client_ack_sent"] = ok
                results["client_ack_to"] = ack_to
                results["client_ack_intended_to_blocked_by_test_mode"] = ack_orig_to
                if not ok:
                    results["sent"] = False
                    results["client_ack_error"] = resp.text[:500]
        else:
            results["client_ack_skipped"] = "No client_reply_text provided by AI"

        # ---- (b) REVIEW EMAIL TO ALEJANDRO ----
        if not pdf_paths:
            results["sent"] = False
            results["review_email_error"] = "No pdf_paths to attach"
            return results

        review_body_html = build_complex_review_body(
            client_name=client_name,
            request_summary=decision.get("request_summary", ""),
            review_summary=decision.get("review_summary", ""),
            coverage_analysis=decision.get("coverage_analysis") or {},
            send_completed_coi_to=decision.get("send_completed_coi_to"),
            original_client_sender=original_client_sender,
            original_client_name=original_client_name,
        )

        review_attachments = [_file_attachment(p) for p in pdf_paths]
        # Also attach the ORIGINAL contract / requirements docs that came in
        # with the client email so Alejandro can review them himself.
        forwarded_originals = []
        for orig in (attachments_result.get("attachments") or []):
            orig_bytes = orig.get("contentBytes")
            if not orig_bytes:
                continue
            review_attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"ORIGINAL - {orig.get('name') or 'attachment.pdf'}",
                "contentType": orig.get("media_type") or "application/pdf",
                "contentBytes": orig_bytes,
            })
            forwarded_originals.append(orig.get("name"))

        review_obj = {
            "subject": f"Review needed: Complex COI for {client_name}",
            "body": {"contentType": "HTML", "content": review_body_html},
            "toRecipients": [
                {"emailAddress": {"address": config.REVIEW_RECIPIENT_EMAIL}}
            ],
            "attachments": review_attachments,
        }

        if dry_run:
            results["review_email_dry_run"] = {
                "would_send_to": config.REVIEW_RECIPIENT_EMAIL,
                "attachment_count": len(review_attachments),
            }
            return results

        ok, resp = graph.send_mail(review_obj)
        results["review_email_sent"] = ok
        results["review_email_to"] = config.REVIEW_RECIPIENT_EMAIL
        results["attachment_count"] = len(review_attachments)
        results["forwarded_originals"] = forwarded_originals
        if not ok:
            results["sent"] = False
            results["review_email_error"] = resp.text[:500]
        return results

    return {
        "sent": False,
        "action": action,
        "reason": f"Unknown action: {action}",
    }
