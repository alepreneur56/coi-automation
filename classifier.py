"""
classifier.py
-------------
Claude call — port of the Pipedream anthropic step.

Builds the user message (new email + thread history + attachment summary +
Excel/Word text), sends it to Claude with the full system prompt (registry
injected, prompt-cached), and parses the JSON decision.

The system prompt and registry are loaded from LOCAL files now (they used to
be fetched from GitHub raw) — this folder IS the source of truth.
"""

import json
import time
from datetime import date

import requests

import config

MAX_RETRIES = 3
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504, 529}

REGISTRY_MARKER = (
    "## REGISTRY\n\nThe full client registry is provided as a separate JSON "
    "file. Load it alongside this prompt before processing any request."
)

_full_system_prompt_cache = None


def load_system_prompt():
    """Load coi_system_prompt.txt with coi_client_registry.json injected."""
    global _full_system_prompt_cache
    if _full_system_prompt_cache is not None:
        return _full_system_prompt_cache
    import os
    base = config.BASE_DIR
    with open(os.path.join(base, "coi_system_prompt.txt"), "r") as f:
        system_prompt = f.read()
    with open(os.path.join(base, "coi_client_registry.json"), "r") as f:
        registry = f.read()
    full = system_prompt.replace(REGISTRY_MARKER, f"## REGISTRY\n\n{registry}")
    if full == system_prompt:
        raise RuntimeError(
            "Registry marker not found in coi_system_prompt.txt — "
            "registry was NOT injected. Check the marker text."
        )
    _full_system_prompt_cache = full
    return full


def _call_anthropic(payload, max_retries=MAX_RETRIES):
    """Call Anthropic API with retry on transient failures.
    Returns (http_status, response_dict, attempts_made, error_or_none)."""
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=180,
            )
            try:
                body = resp.json()
            except Exception:
                body = {"raw_text": resp.text[:1500]}

            if resp.status_code == 200:
                return resp.status_code, body, attempt + 1, None

            if resp.status_code in RETRYABLE_STATUS and attempt < max_retries:
                # Longer backoff for 429 — its window resets per minute
                if resp.status_code == 429:
                    wait = [30, 60, 60][min(attempt, 2)]
                else:
                    wait = 2 ** attempt
                last_error = f"HTTP {resp.status_code} on attempt {attempt + 1}: {str(body)[:400]}"
                time.sleep(wait)
                continue

            return resp.status_code, body, attempt + 1, f"HTTP {resp.status_code}: {str(body)[:400]}"

        except requests.RequestException as e:
            last_error = f"Request error on attempt {attempt + 1}: {e}"
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            return 0, {}, attempt + 1, last_error

    return 0, {}, max_retries + 1, last_error or "Max retries exceeded"


def build_user_message(new_email, thread_messages, attachments_result):
    """Assemble the text portion of the user message. Same layout the
    validated Pipedream step produced."""
    sender_email = new_email.get("from", {}).get("emailAddress", {}).get("address", "unknown")
    sender_name = new_email.get("from", {}).get("emailAddress", {}).get("name", "")
    subject = new_email.get("subject", "")
    body_content = new_email.get("body", {}).get("content") or new_email.get("bodyPreview", "")
    new_email_id = new_email.get("id")
    new_sent = new_email.get("sentDateTime", "")

    all_attachments = attachments_result.get("attachments", []) or []
    pdf_attachments = [a for a in all_attachments if a.get("kind") == "pdf"]
    image_attachments = [a for a in all_attachments if a.get("kind") == "image"]
    text_attachments = [a for a in all_attachments if a.get("kind") in ("excel", "text")]

    today_str = date.today().strftime("%m/%d/%Y")

    parts = [f"TODAY'S DATE: {today_str}", ""]

    summary_segments = []
    if pdf_attachments:
        names = ", ".join(a.get("name", "unnamed.pdf") for a in pdf_attachments)
        summary_segments.append(f"{len(pdf_attachments)} PDF(s) — {names}")
    if image_attachments:
        names = ", ".join(a.get("name", "unnamed.image") for a in image_attachments)
        summary_segments.append(f"{len(image_attachments)} image(s) — {names}")
    if text_attachments:
        names = ", ".join(a.get("name", "unnamed") for a in text_attachments)
        summary_segments.append(f"{len(text_attachments)} text/Excel — {names}")
    parts.append("ATTACHMENTS: " + ("; ".join(summary_segments) if summary_segments else "none"))
    parts.append("")
    parts.append("=" * 60)
    parts.append("NEW EMAIL (just received, this is what requires action)")
    parts.append("=" * 60)
    parts.append(f"From: {sender_name} <{sender_email}>")
    parts.append(f"Subject: {subject}")
    parts.append(f"Sent: {new_sent}")
    parts.append("Body:")
    parts.append(body_content)
    parts.append("")

    history = [m for m in thread_messages if m.get("id") != new_email_id]
    if history:
        parts.append("=" * 60)
        parts.append("CONVERSATION HISTORY (oldest first, for context only)")
        parts.append("=" * 60)
        for i, m in enumerate(history, 1):
            m_from = m.get("from", {}).get("emailAddress", {})
            m_body = m.get("body", {}).get("content") or m.get("bodyPreview", "")
            parts.append("")
            parts.append(f"--- Message {i} ---")
            parts.append(f"From: {m_from.get('name', '')} <{m_from.get('address', 'unknown')}>")
            parts.append(f"Subject: {m.get('subject', '')}")
            parts.append(f"Sent: {m.get('sentDateTime', '')}")
            parts.append(f"Has attachments: {'yes' if m.get('hasAttachments') else 'no'}")
            parts.append("Body:")
            parts.append(m_body)
    else:
        parts.append("(No prior messages in this conversation, this is the first email in the thread.)")

    # Excel / Word-fallback text content goes at the END under clear headers
    for att in text_attachments:
        text = (att.get("extracted_text") or "").strip()
        if not text:
            continue
        label = "EXCEL ATTACHMENT CONTENT" if att.get("kind") == "excel" else "WORD ATTACHMENT TEXT CONTENT"
        parts.append("")
        parts.append("=" * 60)
        parts.append(f"{label}: {att.get('name', 'unnamed')}")
        parts.append("=" * 60)
        parts.append(text)

    return "\n".join(parts)


def classify(new_email, thread_messages, attachments_result):
    """Full classifier call. Returns the same shape the Pipedream anthropic
    step returned (parsed JSON under 'parsed', diagnostics alongside)."""
    user_message = build_user_message(new_email, thread_messages, attachments_result)

    all_attachments = attachments_result.get("attachments", []) or []
    message_content = [{"type": "text", "text": user_message}]
    for att in all_attachments:
        b64 = att.get("contentBytes")
        if not b64:
            continue
        if att.get("kind") == "pdf":
            message_content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": att.get("media_type", "application/pdf"),
                    "data": b64,
                },
            })
        elif att.get("kind") == "image":
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": att.get("media_type", "image/jpeg"),
                    "data": b64,
                },
            })

    payload = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": 4000,
        # cache_control marks the big system prompt as cacheable — subsequent
        # requests within ~5 min read it from cache (cheaper + faster).
        "system": [
            {
                "type": "text",
                "text": load_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": message_content}],
    }

    http_status, response_body, attempts, api_error = _call_anthropic(payload)

    claude_text = ""
    stop_reason = None
    cache_usage = None
    if http_status == 200 and "content" in response_body:
        try:
            content_arr = response_body.get("content", [])
            if content_arr and isinstance(content_arr, list):
                claude_text = content_arr[0].get("text", "") if isinstance(content_arr[0], dict) else ""
            stop_reason = response_body.get("stop_reason")
            usage = response_body.get("usage", {})
            cache_usage = {
                "input_tokens": usage.get("input_tokens"),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            }
        except Exception:
            claude_text = ""

    parsed = None
    parse_error = None
    if claude_text:
        try:
            clean = claude_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
        except Exception as e:
            parse_error = f"JSON parse failed: {e}. First 300 chars: {claude_text[:300]}"

    success = parsed is not None
    sender_email = new_email.get("from", {}).get("emailAddress", {}).get("address", "unknown")

    return {
        "success": success,
        "stage": "complete" if success else ("api" if api_error else ("parse" if parse_error else "empty_response")),
        "sender": sender_email,
        "subject": new_email.get("subject", ""),
        "http_status": http_status,
        "anthropic_attempts": attempts,
        "stop_reason": stop_reason,
        "cache_usage": cache_usage,
        "api_error": api_error,
        "parse_error": parse_error,
        "raw_response": claude_text,
        "parsed": parsed,
    }
