"""
pipeline.py
-----------
Classification branching — port of the Pipedream code step. Decides what
email action to take and generates COI PDFs locally via coi_engine (the
Railway /generate-pdf hop is gone).

Returns an action dict consumed by sender.execute_action():
  action = "do_nothing" | "send_reply" | "send_pdf" | "send_complex_review" | "error"
"""

import re

from coi_engine import process_request

import config
import state
import ziplookup

# Matches the "Missing ZIP" reply template (see coi_system_prompt.txt):
#   "...ZIP code for [Holder Name] at [street, city, state] and I'll..."
#   "...ZIP code de [Holder Name] en [street, city, state] y te lo..."
_MISSING_ZIP_RE = re.compile(
    r"ZIP code (?:for|de) (.+?) (?:at|en) (.+?),\s*([A-Za-z .'\-]+?),\s*([A-Za-z]{2})\b",
    re.IGNORECASE,
)


def _extract_missing_zip_holder(reply_text):
    """Heuristic: does reply_text match the 'missing ZIP' template, and if
    so, what holder name / street / city / state did it cite? Returns a
    dict with those four fields, or None if this doesn't look like a
    missing-ZIP-only reply (e.g. no city, no state — some other field is
    also missing, or the text doesn't match the template shape at all)."""
    if not reply_text or "ZIP code" not in reply_text:
        return None
    m = _MISSING_ZIP_RE.search(reply_text)
    if not m:
        return None
    holder_name, street, city, state_abbr = (g.strip() for g in m.groups())
    if not (holder_name and street and city and state_abbr):
        return None
    return {
        "name": holder_name,
        "address_line_1": street,
        "city": city,
        "state": state_abbr.upper(),
    }


def _try_zip_autofill(parsed, sender=None):
    """When ZIP_LOOKUP is on and this incomplete-request reply is asking
    ONLY for a missing ZIP (holder name + street + city + state already
    known), attempt a Zippopotam.us lookup. On a unique-city-ZIP hit,
    rewrite reply_text to confirm the found ZIP instead of asking for it
    and log 'zip_autofilled'. Any other outcome (multiple ZIPs, not found,
    lookup failure, or the reply doesn't match the missing-ZIP shape)
    leaves parsed/reply_text unchanged. Never raises."""
    if not config.ZIP_LOOKUP:
        return parsed

    reply_text = parsed.get("reply_text")
    holder = _extract_missing_zip_holder(reply_text)
    if not holder:
        return parsed

    try:
        result = ziplookup.lookup_zip_for_city(holder["city"], holder["state"])
    except Exception as e:
        state.log_event("zip_lookup_error", sender=sender, error=str(e))
        return parsed

    if result.get("status") != "unique":
        state.log_event(
            "zip_lookup_no_autofill",
            sender=sender,
            status=result.get("status"),
            city=holder["city"],
            state=holder["state"],
        )
        return parsed

    found_zip = result["zip"]
    address = f"{holder['address_line_1']}, {holder['city']}, {holder['state']} {found_zip}"

    # Rewrite the reply to confirm the ZIP we found rather than asking for
    # it. We deliberately do NOT flip this to a send_pdf/PDF-generation
    # action here: the classifier's coi_request_incomplete payload never
    # carries client_id/template_filename/certificate_holder (by design —
    # client + template identification happens only once the request is
    # judged complete), so coi_engine.process_request() has nothing safe to
    # build a PDF from. Fabricating those fields would mean guessing which
    # client/template to use, which this pipeline is built to avoid.
    new_reply = re.sub(
        r"ZIP code (?:for|de) .+?,?\s*I'll get the COI right out to you\.",
        f"ZIP code for {holder['name']} at {address} — got it from our lookup, "
        f"and I'll get the COI right out to you.",
        reply_text,
    )
    if new_reply == reply_text:
        # Template text didn't match exactly (e.g. slight model phrasing
        # drift) — still confirm the ZIP by appending a short note rather
        # than silently doing nothing.
        new_reply = (
            f"{reply_text}\n\n(Found ZIP {found_zip} for {holder['name']} at "
            f"{address} via lookup — using that unless you tell us otherwise.)"
        )

    parsed = dict(parsed)
    parsed["reply_text"] = new_reply
    parsed["_zip_autofilled"] = found_zip

    state.log_event(
        "zip_autofilled",
        sender=sender,
        holder_name=holder["name"],
        city=holder["city"],
        state=holder["state"],
        zip=found_zip,
    )
    return parsed


def decide_action(ai_result):
    parsed = ai_result.get("parsed")

    # If the classifier failed (no parsed JSON), pass through error details
    if not parsed:
        return {
            "action": "error",
            "reason": "Classifier did not return parsed JSON",
            "stage": ai_result.get("stage"),
            "http_status": ai_result.get("http_status"),
            "api_error": ai_result.get("api_error"),
            "parse_error": ai_result.get("parse_error"),
            "raw_response_preview": (ai_result.get("raw_response") or "")[:500],
        }

    classification = parsed.get("classification")
    reply_text = parsed.get("reply_text")
    sender_email = ai_result.get("sender", "")

    # 1. Classifications that need NO outgoing email
    if classification in ("thank_you", "junk"):
        return {
            "action": "do_nothing",
            "classification": classification,
            "reason": f"Classification is '{classification}', no reply needed",
        }

    # 2. Classifications that need a TEXT reply (no PDF)
    if classification in ("coi_request_incomplete", "question"):
        if classification == "coi_request_incomplete" and reply_text:
            parsed = _try_zip_autofill(parsed, sender=sender_email)
            reply_text = parsed.get("reply_text")
        if not reply_text:
            return {
                "action": "do_nothing",
                "classification": classification,
                "reason": "reply_text is null (likely client said they'll send info later)",
            }
        return {
            "action": "send_reply",
            "classification": classification,
            "reply_text": reply_text,
            "to": sender_email,
        }

    # 3. coi_request_complete / coi_revision_request / coi_complex_review_required
    #    All three generate a PDF:
    #      - complete: send to client (action="send_pdf")
    #      - revision: send to client in-thread (is_revision=True)
    #      - complex_review: draft to Alejandro for review + ack the client
    if classification in ("coi_request_complete", "coi_revision_request", "coi_complex_review_required"):
        is_revision = classification == "coi_revision_request"
        is_complex_review = classification == "coi_complex_review_required"
        if parsed.get("status") != "ready":
            return {
                "action": "do_nothing",
                "classification": classification,
                "reason": f"Status is '{parsed.get('status')}', not ready to generate PDF",
                "flags": parsed.get("flags", []),
            }

        try:
            output_files = process_request(parsed, config.TEMPLATES_DIR, config.OUTPUT_DIR)
        except Exception as e:
            import traceback
            return {
                "action": "error",
                "reason": "coi_engine PDF generation failed",
                "error_detail": str(e),
                "traceback": traceback.format_exc()[-1500:],
            }

        if not output_files:
            return {"action": "error", "reason": "coi_engine produced no PDFs"}

        client_name = parsed.get("client_canonical_name", "Client")

        if is_complex_review:
            return {
                "action": "send_complex_review",
                "classification": classification,
                "client_name": client_name,
                "count": len(output_files),
                "pdf_paths": output_files,
                "to": sender_email,
                "client_reply_text": parsed.get("reply_text") or "",
                "review_summary": parsed.get("review_summary") or "",
                "coverage_analysis": parsed.get("coverage_analysis") or {},
                "request_summary": parsed.get("original_request_summary") or "",
                "send_completed_coi_to": parsed.get("send_completed_coi_to"),
            }

        return {
            "action": "send_pdf",
            "classification": classification,
            "is_revision": is_revision,
            "client_name": client_name,
            "count": len(output_files),
            "pdf_paths": output_files,
            "to": sender_email,
        }

    # Unknown classification (defensive)
    return {
        "action": "do_nothing",
        "classification": classification or "unknown",
        "reason": f"Unrecognized classification: {classification}",
    }
