"""
app.py
------
COI Automation Backend — USI Insurance Services / Alejandro Bello
Flask server that handles incoming COI requests from email and WhatsApp,
processes them with Claude AI, and produces finished COI PDFs.

Endpoints:
    POST /email      — receives parsed email data
    POST /whatsapp   — receives Twilio WhatsApp webhook
    GET  /health     — health check for Railway
"""

import os
import json
import re
import base64
import tempfile
import traceback
from datetime import date
from flask import Flask, request, jsonify, Response
import anthropic

from coi_engine import process_request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION — set these as environment variables in Railway
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
TEMPLATES_DIR      = os.environ.get("TEMPLATES_DIR", "./templates")
OUTPUT_DIR         = os.environ.get("OUTPUT_DIR", "./output")
SENDGRID_API_KEY   = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL         = os.environ.get("FROM_EMAIL", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")

# Load system prompt and registry at startup
with open("coi_system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

with open("coi_client_registry.json", "r") as f:
    REGISTRY = json.load(f)

FULL_SYSTEM_PROMPT = SYSTEM_PROMPT.replace(
    "## REGISTRY\n\nThe full client registry is provided as a separate JSON file. Load it alongside this prompt before processing any request.",
    f"## REGISTRY\n\n{json.dumps(REGISTRY, indent=2)}"
)

client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# AI PROCESSING
# ---------------------------------------------------------------------------

def call_claude(message_text: str, attachments: list = None) -> dict:
    """
    Send a COI request to Claude and get back a structured JSON decision.

    Args:
        message_text: The raw message from the client
        attachments:  List of dicts with keys: filename, content_type, data (base64)

    Returns:
        Parsed JSON dict from Claude
    """
    content = []

    # Add any attachments (PDFs or images)
    if attachments:
        for att in attachments:
            if att["content_type"] == "application/pdf":
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": att["data"]
                    }
                })
            elif att["content_type"].startswith("image/"):
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": att["content_type"],
                        "data": att["data"]
                    }
                })

    content.append({"type": "text", "text": message_text})

    response = client_ai.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=FULL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )

    raw = response.content[0].text
    # Strip any markdown fences if present
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# EMAIL DELIVERY
# ---------------------------------------------------------------------------

def send_email_with_pdfs(to_email: str, subject: str, body: str, pdf_paths: list):
    """Send completed COIs via SendGrid."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import (
            Mail, Attachment, FileContent, FileName,
            FileType, Disposition
        )

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )

        for pdf_path in pdf_paths:
            with open(pdf_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            filename = os.path.basename(pdf_path)
            attachment = Attachment(
                FileContent(data),
                FileName(filename),
                FileType("application/pdf"),
                Disposition("attachment")
            )
            message.add_attachment(attachment)

        sg.send(message)
        print(f"  [email] Sent {len(pdf_paths)} COI(s) to {to_email}")
        return True

    except Exception as e:
        print(f"  [email] Send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# WHATSAPP DELIVERY
# ---------------------------------------------------------------------------

def send_whatsapp_message(to_number: str, body: str, pdf_paths: list = None):
    """Send a WhatsApp message (and optionally media) via Twilio."""
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        if pdf_paths:
            # Send each PDF as a media message
            for pdf_path in pdf_paths:
                # Note: Twilio requires a public URL for media
                # In production, upload PDF to a temp storage URL first
                # For MVP, send a text confirmation and attach via URL
                pass

        twilio_client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{to_number}",
            body=body
        )
        print(f"  [whatsapp] Sent message to {to_number}")
        return True

    except Exception as e:
        print(f"  [whatsapp] Send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# CORE PIPELINE
# ---------------------------------------------------------------------------

def run_coi_pipeline(message_text: str, attachments: list, reply_to: str, channel: str):
    """
    Full pipeline: AI parsing → PDF generation → delivery.

    Args:
        message_text: Raw message from client
        attachments:  List of attachment dicts
        reply_to:     Email address or WhatsApp number to reply to
        channel:      "email" or "whatsapp"
    """
    print(f"\n{'='*60}")
    print(f"New request via {channel} from {reply_to}")
    print(f"Message: {message_text[:200]}")
    print(f"Attachments: {len(attachments)}")

    # Step 1 — Call Claude AI
    try:
        ai_result = call_claude(message_text, attachments)
        print(f"  [ai] Status: {ai_result.get('status')}  Client: {ai_result.get('client_canonical_name')}")
    except Exception as e:
        print(f"  [ai] Error: {e}")
        error_reply = "I had trouble processing your request. Please try again or contact Alejandro directly."
        if channel == "whatsapp":
            send_whatsapp_message(reply_to, error_reply)
        return {"status": "error", "error": str(e)}

    status = ai_result.get("status")

    # Step 2 — Handle non-ready statuses
    if status == "needs_clarification":
        flags = ai_result.get("flags", [])
        clarification_msg = flags[0]["description"] if flags else "Could you please provide more details for your COI request?"
        if channel == "whatsapp":
            send_whatsapp_message(reply_to, clarification_msg)
        elif channel == "email":
            send_email_with_pdfs(
                to_email=reply_to,
                subject="COI Request — Additional Information Needed",
                body=clarification_msg,
                pdf_paths=[]
            )
        return {"status": "needs_clarification", "message": clarification_msg}

    if status == "flag_for_review":
        flags = ai_result.get("flags", [])
        flag_msg = "\n".join(f["description"] for f in flags)
        # Notify Alejandro directly
        alert_msg = f"COI request flagged for manual review from {reply_to}:\n\n{flag_msg}\n\nOriginal request: {message_text}"
        print(f"  [flag] Flagged for review: {flag_msg}")
        # For MVP — send acknowledgment to client
        ack = "Thank you for your request. I need to review a few details and will get back to you shortly."
        if channel == "whatsapp":
            send_whatsapp_message(reply_to, ack)
        elif channel == "email":
            send_email_with_pdfs(
                to_email=reply_to,
                subject="COI Request — Under Review",
                body=ack,
                pdf_paths=[]
            )
        return {"status": "flag_for_review", "flags": flags}

    # Step 3 — Generate PDFs
    if status == "ready":
        try:
            output_files = process_request(ai_result, TEMPLATES_DIR, OUTPUT_DIR)
            print(f"  [pdf] Generated {len(output_files)} file(s): {[os.path.basename(f) for f in output_files]}")
        except Exception as e:
            print(f"  [pdf] Error: {e}")
            traceback.print_exc()
            error_reply = "I encountered an error generating your COI. Alejandro has been notified."
            if channel == "whatsapp":
                send_whatsapp_message(reply_to, error_reply)
            return {"status": "error", "error": str(e)}

        # Step 4 — Deliver
        client_name = ai_result.get("client_canonical_name", "")
        num = len(output_files)

        if channel == "email":
            subject = f"Certificate of Insurance — {client_name}"
            body = (
                f"Hello,\n\nPlease find your {'COI' if num == 1 else f'{num} COIs'} attached.\n\n"
                f"Best regards,\nAlejandro Bello\nUSI Insurance Services\n786-355-0449"
            )
            # Send to the address in the request if provided, else reply to sender
            send_to = ai_result.get("send_completed_coi_to") or reply_to
            send_email_with_pdfs(send_to, subject, body, output_files)

        elif channel == "whatsapp":
            confirmation = (
                f"Your {'COI is' if num == 1 else f'{num} COIs are'} ready! "
                f"Sending {'it' if num == 1 else 'them'} now."
            )
            send_whatsapp_message(reply_to, confirmation)
            # TODO: attach PDFs via Twilio media URL in production

        return {"status": "ready", "files": [os.path.basename(f) for f in output_files]}

    return {"status": "unknown"}


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check — Railway uses this to confirm the app is running."""
    return jsonify({"status": "ok", "date": date.today().isoformat()})


@app.route("/email", methods=["POST"])
def email_webhook():
    """
    Receives email data from Make.com.
    Accepts JSON, form-encoded, or raw data.
    """
    # Try JSON first
    data = request.get_json(force=True, silent=True)

    # If not JSON, try form data
    if not data:
        data = {
            "from": request.form.get("from", request.form.get("sender", "")),
            "subject": request.form.get("subject", ""),
            "body": request.form.get("body", request.form.get("text", "")),
            "attachments": []
        }

    # If still nothing, try raw urlencoded
    if not data.get("from") and not data.get("body"):
        try:
            from urllib.parse import parse_qs
            raw = request.data.decode("utf-8")
            parsed = parse_qs(raw)
            data = {
                "from": parsed.get("from", [""])[0],
                "subject": parsed.get("subject", [""])[0],
                "body": parsed.get("body", [""])[0],
                "attachments": []
            }
        except:
            pass

    sender      = data.get("from", "")
    body        = data.get("body", "")
    subject     = data.get("subject", "")
    attachments = data.get("attachments", [])

    if not sender and not body:
        return jsonify({"error": "No data received"}), 400

    full_message = f"Subject: {subject}\n\n{body}" if subject else body

    result = run_coi_pipeline(
        message_text=full_message,
        attachments=attachments,
        reply_to=sender,
        channel="email"
    )
    return jsonify(result)


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Receives Twilio WhatsApp webhook (application/x-www-form-urlencoded).
    Twilio sends: From, Body, NumMedia, MediaUrl0, MediaContentType0, etc.
    """
    from_number = request.form.get("From", "").replace("whatsapp:", "")
    body        = request.form.get("Body", "")
    num_media   = int(request.form.get("NumMedia", 0))

    # Download any media attachments
    attachments = []
    for i in range(num_media):
        media_url  = request.form.get(f"MediaUrl{i}")
        media_type = request.form.get(f"MediaContentType{i}", "application/octet-stream")
        if media_url:
            try:
                import requests as req_lib
                from requests.auth import HTTPBasicAuth
                resp = req_lib.get(
                    media_url,
                    auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                )
                if resp.status_code == 200:
                    attachments.append({
                        "filename": f"attachment_{i}",
                        "content_type": media_type,
                        "data": base64.b64encode(resp.content).decode()
                    })
            except Exception as e:
                print(f"  [whatsapp] Could not download media: {e}")

    result = run_coi_pipeline(
        message_text=body,
        attachments=attachments,
        reply_to=from_number,
        channel="whatsapp"
    )

    # Twilio expects a TwiML response
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        mimetype="text/xml"
    )


@app.route("/test", methods=["POST"])
def test_endpoint():
    """
    Manual test endpoint — send a JSON body with a message to test the pipeline
    without needing a real email or WhatsApp connection.
    {
        "message": "I need a COI for Rolando's HVAC...",
        "channel": "email",
        "reply_to": "test@example.com"
    }
    """
    data = request.get_json(force=True)
    result = run_coi_pipeline(
        message_text=data.get("message", ""),
        attachments=data.get("attachments", []),
        reply_to=data.get("reply_to", "test@example.com"),
        channel=data.get("channel", "email")
    )
    return jsonify(result)


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf_endpoint():
    """
    Endpoint for external workflow tools (Pipedream, etc.) to generate
    a COI PDF from a pre-parsed JSON request (already processed by Claude elsewhere).
    
    Input JSON: the full parsed Claude response with status, template_filename,
                certificate_holder, etc.
    
    Output JSON:
        {
            "status": "ready",
            "filename": "...",
            "pdf_base64": "...",
            "pdf_size_bytes": 12345
        }
    """
    import base64
    from coi_engine import process_request
    
    parsed = request.get_json(force=True)
    if not parsed:
        return jsonify({"status": "error", "reason": "No JSON body"}), 400
    
    if parsed.get("status") != "ready":
        return jsonify({
            "status": "not_ready",
            "reason": parsed.get("status", "unknown"),
            "flags": parsed.get("flags", [])
        })
    
    try:
        output_files = process_request(parsed, TEMPLATES_DIR, OUTPUT_DIR)
        if not output_files:
            return jsonify({"status": "error", "reason": "No files produced"}), 500
        
        # Return first (or all) PDFs as base64
        pdfs = []
        for filepath in output_files:
            with open(filepath, "rb") as f:
                pdf_bytes = f.read()
            pdfs.append({
                "filename": os.path.basename(filepath),
                "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
                "pdf_size_bytes": len(pdf_bytes)
            })
        
        return jsonify({
            "status": "ready",
            "client_name": parsed.get("client_canonical_name"),
            "pdfs": pdfs,
            "count": len(pdfs)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "reason": str(e)}), 500


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
