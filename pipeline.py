"""
pipeline.py
-----------
Classification branching — port of the Pipedream code step. Decides what
email action to take and generates COI PDFs locally via coi_engine (the
Railway /generate-pdf hop is gone).

Returns an action dict consumed by sender.execute_action():
  action = "do_nothing" | "send_reply" | "send_pdf" | "send_complex_review" | "error"
"""

from coi_engine import process_request

import config


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
