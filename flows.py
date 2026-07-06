"""
flows.py
--------
MVP flows that ACT on Prompt v2's additive classifier signals. The prompt
(coi_system_prompt.txt, PROMPT V2) only EMITS these fields — this module is
the sender-side counterpart that turns them into emails:

  uncontrolled_lines_requested  -> referral line appended to the delivery
                                   reply (English only; Spanish pending Alex)
  limits_shortfall              -> separate "give me a call" email to the
                                   CLIENT + non-compliance breakdown to
                                   Alejandro. Delivery NEVER held.
  ancillary_missing             -> non-compliance email to Alejandro only
                                   (Alex handles the client conversation).
  carrier_endorsement_request   -> Rolando's HVAC scheduled-auto AI SOP:
                                   dedupe against the auto-AI table in
                                   data/coi_history.db, then fire the carrier
                                   endorsement request. Delivery NEVER held.

HARD RULES:
  - The COI delivery itself is never held, delayed, or altered by anything
    here. run_post_send_flows() only runs AFTER a successful delivery send
    and never raises (failures land in the log as 'flows_error').
  - Every send here goes through sender.apply_test_mode — TEST_MODE
    redirects ALL of these to TEST_REDIRECT_TO exactly like existing sends.
  - Style: '[Name],' opener, no dashes in bodies, 'Regards,' closer,
    signature appended only on client-facing emails.

Complex-review routing is untouched: requires_approval cases still classify
coi_complex_review_required and go to Alejandro via sender.py as before.
"""

import json
import os

import config
import db
import state
from language import detect_spanish

# PROPOSED SPANISH REFERRAL WORDING — NOT LIVE, pending Alex's approval.
# Once blessed, wire it into build_referral_line() for Spanish replies:
#   "Tenga en cuenta que nuestra oficina maneja las polizas de [GL y Auto].
#    El certificado de [WC] lo enviara el broker que maneja esa poliza."
# (accented version: "...las pólizas de [GL y Auto]. El certificado de [WC]
#  lo enviará el broker que maneja esa póliza.")
# Until then, Spanish replies get NO referral line; the referral info goes to
# Alejandro in the non-compliance note instead.

SIGNAL_FIELDS = (
    "uncontrolled_lines_requested",
    "limits_shortfall",
    "ancillary_missing",
    "carrier_endorsement_request",
)

_registry_cache = None


def _load_registry():
    global _registry_cache
    if _registry_cache is None:
        path = os.path.join(config.BASE_DIR, "coi_client_registry.json")
        with open(path, "r") as f:
            _registry_cache = json.load(f)
    return _registry_cache


def get_client(client_id):
    """Registry entry for a client_id, or None."""
    if not client_id:
        return None
    for client in _load_registry().get("clients", []):
        if client.get("client_id") == client_id:
            return client
    return None


def _join_and(items):
    items = [str(i) for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _is_spanish_email(new_email):
    return detect_spanish(
        (new_email or {}).get("subject"),
        ((new_email or {}).get("body") or {}).get("content"),
    )


def _fmt_amount(value):
    v = str(value or "").strip()
    if not v:
        return "the carried amount"
    return v if v.startswith("$") else f"${v}"


# ---------------------------------------------------------------------------
# 1. REFERRAL LINE (uncontrolled_lines_requested)
# ---------------------------------------------------------------------------

def build_referral_line(parsed):
    """Approved referral wording (2026-07-04), filled from the client's
    registry controlled_lines + the signal's missing line names. Returns the
    sentence, or None when the signal is absent/empty."""
    signal = (parsed or {}).get("uncontrolled_lines_requested") or []
    missing = [e.get("line") for e in signal if isinstance(e, dict) and e.get("line")]
    if not missing:
        return None
    client = get_client(parsed.get("client_id"))
    controlled = (client or {}).get("controlled_lines") or []
    controlled_txt = _join_and(controlled) or "our"
    if len(missing) == 1:
        return (
            f"Please note our office handles the {controlled_txt} policies. "
            f"The {missing[0]} certificate will come from the broker who "
            f"handles that policy."
        )
    return (
        f"Please note our office handles the {controlled_txt} policies. "
        f"The {_join_and(missing)} certificates will come from the brokers "
        f"who handle those policies."
    )


def append_referral_to_text(reply_text, parsed, is_spanish):
    """Insert the referral line into a plain-text reply body just before the
    final 'Regards,'. Spanish replies are skipped (wording pending Alex) —
    the referral info goes into the producer non-compliance note instead.
    Returns (new_text, appended_bool)."""
    line = build_referral_line(parsed)
    if not line or is_spanish or not reply_text:
        return reply_text, False
    idx = reply_text.rfind("Regards,")
    if idx == -1:
        return reply_text.rstrip() + "\n\n" + line, True
    return reply_text[:idx] + line + "\n\n" + reply_text[idx:], True


# ---------------------------------------------------------------------------
# 2. LIMITS SHORTFALL — client email (never holds delivery)
# ---------------------------------------------------------------------------

def resolve_client_contact(client, requestor_email):
    """Who gets the shortfall client email.
    Order: registry contact_emails first entry -> original request sender if
    their domain matches contact_domains -> nobody (noted in Alex's email).
    Returns (email_or_None, how)."""
    emails = (client or {}).get("contact_emails") or []
    if emails:
        return emails[0], "registry_contact"
    domains = [d.lower().lstrip("@") for d in (client or {}).get("contact_domains") or []]
    req = (requestor_email or "").strip().lower()
    if domains and "@" in req and req.split("@", 1)[1] in domains:
        return requestor_email, "sender_domain_match"
    return None, "unresolved"


def _shortfall_sentences(shortfall):
    """('$1,000,000 in GL limits', '$2,000,000') pieces for the approved
    client template, composed across one or more shortfall lines."""
    carried_bits = []
    demanded_bits = []
    for entry in shortfall:
        line = entry.get("line") or "the requested"
        carried_bits.append(f"{_fmt_amount(entry.get('carried'))} in {line} limits")
        demanded_bits.append(f"{_fmt_amount(entry.get('demanded'))} in {line}")
    if len(demanded_bits) == 1:
        demanded_txt = _fmt_amount(shortfall[0].get("demanded"))
    else:
        demanded_txt = _join_and(demanded_bits)
    return _join_and(carried_bits), demanded_txt


def _send_shortfall_client_email(graph, new_email, parsed, client, shortfall):
    """Approved 'give me a call' email to the CLIENT. Third party is NEVER
    on this email. Returns a dict describing what happened (for the
    non-compliance note + log)."""
    import sender

    requestor_email = (
        (new_email.get("from") or {}).get("emailAddress", {}).get("address", "")
    )
    requestor_name = (
        (new_email.get("from") or {}).get("emailAddress", {}).get("name", "")
    ).strip()
    requestor_display = (
        f"{requestor_name} ({requestor_email})" if requestor_name else requestor_email
    )

    to_email, how = resolve_client_contact(client, requestor_email)
    if not to_email:
        return {"sent": False, "how": how, "to": None}

    first = sender.first_name_from(None, to_email)
    carried_txt, demanded_txt = _shortfall_sentences(shortfall)
    body_html = sender.with_signature(
        f"<p>{first},</p>"
        f"<p>We sent the certificate to {requestor_display}. It shows "
        f"{carried_txt} because that is what your policy currently carries. "
        f"They are requesting {demanded_txt}. Give me a call when you get a "
        f"chance so we can go over the best next step.</p>"
        "<p>Regards,</p>"
    )

    client_name = parsed.get("client_canonical_name") or (client or {}).get(
        "canonical_name", "your company"
    )
    to_list, cc_list, orig_to, orig_cc = sender.apply_test_mode([to_email], [])
    message_obj = {
        "subject": f"Note about your policy limits ({client_name})",
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": e}} for e in to_list],
        "ccRecipients": [],
        "attachments": sender.signature_attachments(),
    }
    ok, resp = graph.send_mail(message_obj)
    state.log_event(
        "shortfall_client_email",
        msg_id=new_email.get("id"),
        client=parsed.get("client_id"),
        sent=ok,
        to=", ".join(to_list),
        intended_to_blocked_by_test_mode=orig_to,
        resolution=how,
        lines=", ".join(e.get("line", "?") for e in shortfall),
        error=None if ok else getattr(resp, "text", "")[:300],
    )
    return {"sent": ok, "how": how, "to": to_email}


# ---------------------------------------------------------------------------
# 2b/3. NON-COMPLIANCE EMAIL TO ALEJANDRO (shortfall breakdown + ancillary
#       list + Spanish-referral note — one email per request)
# ---------------------------------------------------------------------------

def _send_noncompliance_email(graph, new_email, parsed, client,
                              shortfall, ancillary, referral_note,
                              client_email_result):
    import sender

    client_name = parsed.get("client_canonical_name") or (client or {}).get(
        "canonical_name", "Unknown client"
    )
    requestor = (new_email.get("from") or {}).get("emailAddress", {})
    holder = ((parsed.get("certificate_holder") or {}).get("name")) or ""

    sections = []
    parts = [
        f"<p><b>Non-compliance summary for {client_name}</b> "
        "(the certificate was delivered normally; nothing was held).</p>",
        f"<p><b>Requestor:</b> {requestor.get('name', '')} "
        f"&lt;{requestor.get('address', '')}&gt;<br>"
        f"<b>Subject:</b> {new_email.get('subject', '')}"
        + (f"<br><b>Certificate holder:</b> {holder}" if holder else "")
        + "</p>",
    ]

    if shortfall:
        sections.append("limits_shortfall")
        parts.append("<p><b>Limits shortfall (carried vs demanded):</b></p><ul>")
        for entry in shortfall:
            parts.append(
                f"<li><b>{entry.get('line', '?')}</b>: carries "
                f"{_fmt_amount(entry.get('carried'))}, demanded "
                f"{_fmt_amount(entry.get('demanded'))}</li>"
            )
        parts.append("</ul>")
        if client_email_result and client_email_result.get("sent"):
            parts.append(
                f"<p>Client was emailed the approved 'give me a call' note at "
                f"{client_email_result['to']} "
                f"({client_email_result['how'].replace('_', ' ')}).</p>"
            )
        else:
            how = (client_email_result or {}).get("how", "unresolved")
            parts.append(
                "<p><b>No client email was sent</b> (no registry contact and "
                "the requestor's domain does not match the client's contact "
                f"domains; resolution: {how}). Please reach the client "
                "directly about the shortfall.</p>"
            )

    if ancillary:
        sections.append("ancillary_missing")
        parts.append("<p><b>Ancillary lines demanded but not carried:</b></p><ul>")
        for line in ancillary:
            parts.append(f"<li>{line}</li>")
        parts.append("</ul>")
        parts.append(
            "<p>No client email was sent for the ancillary lines. That "
            "conversation is yours.</p>"
        )

    if referral_note:
        sections.append("spanish_referral_pending")
        parts.append(
            "<p><b>Spanish referral wording pending Alex approval.</b> The "
            "reply to the requestor was in Spanish, so the English referral "
            "line was NOT appended. Referral info that would have gone out:</p>"
            f"<p><i>{referral_note}</i></p>"
        )
        broker_notes = [
            f"{e.get('line', '?')}: {e.get('broker_note', '')}"
            for e in (parsed.get("uncontrolled_lines_requested") or [])
            if isinstance(e, dict)
        ]
        if broker_notes:
            parts.append("<p>Broker notes: " + "; ".join(broker_notes) + "</p>")

    if not sections:
        return None

    to_list, cc_list, orig_to, orig_cc = sender.apply_test_mode(
        [config.PRODUCER_CC_EMAIL], []
    )
    message_obj = {
        "subject": f"Non-compliance: {client_name} COI request",
        "body": {"contentType": "HTML", "content": "".join(parts)},
        "toRecipients": [{"emailAddress": {"address": e}} for e in to_list],
        "ccRecipients": [],
    }
    ok, resp = graph.send_mail(message_obj)
    state.log_event(
        "noncompliance_email",
        msg_id=new_email.get("id"),
        client=parsed.get("client_id"),
        sent=ok,
        to=", ".join(to_list),
        intended_to_blocked_by_test_mode=orig_to,
        sections=", ".join(sections),
        error=None if ok else getattr(resp, "text", "")[:300],
    )
    return {"sent": ok, "sections": sections}


# ---------------------------------------------------------------------------
# 4. CARRIER ENDORSEMENT REQUEST (Rolando's scheduled-auto AI SOP)
# ---------------------------------------------------------------------------

def _rolandos_auto_policy_number():
    client = get_client("rolandos_hvac")
    for template in (client or {}).get("templates", []):
        for policy in template.get("policies", []):
            if "auto" in (policy.get("line") or "").lower():
                return policy.get("policy_number") or "auto policy"
    return "auto policy"


def _holder_name_and_address(parsed, signal):
    ch = parsed.get("certificate_holder") or {}
    holder_name = (signal.get("holder") or ch.get("name") or "").strip()
    addr_bits = [ch.get("address_line_1"), ch.get("address_line_2")]
    csz = " ".join(
        filter(None, [(ch.get("city") or "").strip(), (ch.get("state") or "").strip(),
                      (ch.get("zip") or "").strip()])
    )
    addr_bits.append(csz or None)
    # Only trust the parsed holder's address when it belongs to the same
    # holder the signal names (or the signal didn't name one).
    same_holder = (
        not signal.get("holder")
        or db.normalize_holder(signal.get("holder")) == db.normalize_holder(ch.get("name"))
    )
    address = ", ".join(b for b in addr_bits if b) if same_holder else ""
    return holder_name, address


def _handle_carrier_endorsement(graph, new_email, parsed, signal):
    """(a) dedupe against the auto-AI table, (b) send the carrier request,
    (c) record the holder as 'requested'. Delivery is already out the door —
    nothing here can hold it."""
    import sender

    client_id = signal.get("client") or "rolandos_hvac"
    holder_name, address = _holder_name_and_address(parsed, signal)
    if not holder_name:
        state.log_event(
            "carrier_endorsement_skipped",
            msg_id=new_email.get("id"),
            client=client_id,
            reason="signal carried no holder name",
        )
        return

    existing = db.ai_endorsement_lookup(client_id, holder_name)
    if existing:
        state.log_event(
            "carrier_endorsement_skipped",
            msg_id=new_email.get("id"),
            client=client_id,
            holder=holder_name,
            reason=f"already in AI database (status={existing.get('status')}, "
                   f"recorded {str(existing.get('created_ts'))[:10]})",
        )
        return

    policy_number = _rolandos_auto_policy_number()
    holder_full = holder_name + (f", {address}" if address else "")
    body_html = sender.with_signature(
        "<p>Ascendant team,</p>"
        "<p>We are requesting the following additional insured to be added "
        f"to Rolando's HVAC commercial auto policy: {holder_full}.</p>"
        "<p>Please send us the endorsement once processed. In the meantime "
        "please confirm you are processing this request.</p>"
        "<p>Regards,</p>"
    )

    intended_to = [config.ROLANDOS_ENDORSEMENT_TO]
    intended_cc = [config.ROLANDOS_ENDORSEMENT_CC]
    to_list, cc_list, orig_to, orig_cc = sender.apply_test_mode(intended_to, intended_cc)
    message_obj = {
        "subject": f"REF: Rolando's HVAC - {policy_number} - "
                   "Endorsement Request - Additional Insured",
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": e}} for e in to_list],
        "ccRecipients": [{"emailAddress": {"address": e}} for e in cc_list],
        "attachments": sender.signature_attachments(),
    }
    ok, resp = graph.send_mail(message_obj)
    state.log_event(
        "carrier_endorsement_email",
        msg_id=new_email.get("id"),
        client=client_id,
        holder=holder_name,
        policy=policy_number,
        sent=ok,
        to=", ".join(to_list),
        cc=", ".join(cc_list),
        intended_to_blocked_by_test_mode=orig_to,
        intended_cc_blocked_by_test_mode=orig_cc,
        error=None if ok else getattr(resp, "text", "")[:300],
    )
    if ok:
        db.record_ai_endorsement(
            client_id=client_id,
            holder_name=holder_name,
            address=address or None,
            status="requested",
            source="live",
            msg_id=new_email.get("id"),
        )


# ---------------------------------------------------------------------------
# ENTRY POINT — called by sender.execute_action AFTER a successful send
# ---------------------------------------------------------------------------

def run_post_send_flows(graph, new_email, parsed, decision, delivery=True):
    """Fire the signal-driven follow-up emails. delivery=True for send_pdf
    (cert went out); delivery=False for send_reply (text reply only — the
    only flow that applies is the Spanish-referral producer note).

    NEVER raises: the delivery already happened and nothing here may look
    like a delivery failure. All failures land in the log as 'flows_error'."""
    try:
        parsed = parsed or {}
        if not any(parsed.get(f) for f in SIGNAL_FIELDS):
            return

        is_spanish = _is_spanish_email(new_email)
        client = get_client(parsed.get("client_id"))

        referral_note = None
        if parsed.get("uncontrolled_lines_requested") and is_spanish:
            referral_note = build_referral_line(parsed)

        shortfall = (parsed.get("limits_shortfall") or []) if delivery else []
        ancillary = (parsed.get("ancillary_missing") or []) if delivery else []

        client_email_result = None
        if shortfall:
            client_email_result = _send_shortfall_client_email(
                graph, new_email, parsed, client, shortfall
            )

        _send_noncompliance_email(
            graph, new_email, parsed, client,
            shortfall, ancillary, referral_note, client_email_result,
        )

        if delivery and parsed.get("carrier_endorsement_request"):
            _handle_carrier_endorsement(
                graph, new_email, parsed, parsed["carrier_endorsement_request"]
            )
    except Exception as e:
        import traceback
        state.log_event(
            "flows_error",
            msg_id=(new_email or {}).get("id"),
            error=str(e),
            traceback=traceback.format_exc()[-1200:],
        )
