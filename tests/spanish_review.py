"""
spanish_review.py
------------------
Unit + integration tests for Spanish delivery emails (language.py +
sender.py send_pdf / complex-review paths).

Covers:
  1. detect_spanish() heuristic — Spanish / English / mixed / short bodies.
  2. sender.execute_action() send_pdf body assembly for both languages via
     dry_run against a FakeGraph (same pattern as tests/pipeline_review.py).
  3. Style-rule checks on the generated Spanish body: no dashes, name-comma
     opener, ends with 'Saludos,', 'Cert holder' label stays English,
     revision variant says 'el Certificado de Seguro revisado'.

No live API calls — parsed/decision dicts are built by hand so this runs
fast and deterministically.

Usage:
    .venv/bin/python tests/spanish_review.py
"""

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from language import detect_spanish
from sender import execute_action

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Minimal valid-enough PDF bytes so _file_attachment() can open/read it.
# We don't exercise PDF content here (that's tests/pipeline_review.py's job
# via coi_engine) — this just needs to be a real, readable file on disk.
_FAKE_PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n0\n%%EOF"
)
_tmpdir = tempfile.mkdtemp(prefix="spanish_review_")
FAKE_PDF_PATH = os.path.join(_tmpdir, "fake.pdf")
with open(FAKE_PDF_PATH, "wb") as _f:
    _f.write(_FAKE_PDF_BYTES)


# ---------------------------------------------------------------------------
# FakeGraph (same pattern as tests/pipeline_review.py)
# ---------------------------------------------------------------------------

class FakeGraph:
    def __init__(self):
        self.sent = []

    def reply_to_message(self, msg_id, message_obj):
        self.sent.append(("reply", msg_id, message_obj))
        return True, None

    def send_mail(self, message_obj):
        self.sent.append(("sendMail", None, message_obj))
        return True, None


def graph_msg(msg_id, sender_email, sender_name, subject, body,
              conv_id="conv-test-1", sent_dt="2026-07-01T15:00:00Z"):
    return {
        "id": msg_id,
        "conversationId": conv_id,
        "subject": subject,
        "sentDateTime": sent_dt,
        "receivedDateTime": sent_dt,
        "hasAttachments": False,
        "from": {"emailAddress": {"address": sender_email, "name": sender_name}},
        "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
        "ccRecipients": [],
        "body": {"contentType": "text", "content": body},
        "bodyPreview": body[:150],
    }


report = []
fails = 0


def check(label, condition, detail=""):
    global fails
    if condition:
        report.append(f"[OK]   {label}")
    else:
        fails += 1
        report.append(f"[FAIL] {label}" + (f" -- {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# 1. detect_spanish() unit tests
# ---------------------------------------------------------------------------

def test_detector():
    cases = [
        # (subject, body, expected, label)
        ("COI request", "Hi, I need a certificate of insurance for a new job. "
         "Certificate holder: ABC Corp, 123 Main St, Miami, FL 33101. Thanks!",
         False, "plain english request"),

        ("certificado de seguro", "Hola, necesito un certificado de seguro para un "
         "trabajo nuevo. El certificate holder es Grupo Constructor del Sol. "
         "Por favor envíamelo. Gracias.",
         True, "plain spanish request"),

        ("COI urgente", "Hola, envíame un COI por favor.\n\nCertificate holder:\n"
         "Constructora Del Mar LLC\n7800 NW 25th St\nDoral, FL 33122\n\nGracias!",
         True, "spanish complete request (pipeline_review scenario body)"),

        ("Re: policy", "Necesito saber cuáles son mis límites de responsabilidad "
         "civil general en mi póliza actual antes de firmar el contrato.",
         True, "spanish question, no english cert vocab"),

        ("question about my policy", "Quick question, what are my general "
         "liability limits on my current policy? A GC is asking me before "
         "they send the contract.",
         False, "plain english question"),

        ("Re: COI", "Thanks!", False, "short english thank-you"),
        ("Re: COI", "Gracias!", False, "short spanish thank-you (below min length)"),
        ("", "ok", False, "trivially short body"),
        ("", "", False, "empty subject and body"),

        # Mixed: english body with a single incidental accented name shouldn't flip
        ("COI request", "Hi, please send the COI to José at the office, "
         "certificate holder ABC Corp, 123 Main St, Miami, FL 33101.",
         False, "single accented name in otherwise-english email"),

        # Mixed: english body containing the word 'para' as false-positive risk
        # needs a second signal to flip — with only 'para' present, stay English.
        ("Request", "Attn: Compania Para Todos - please issue the COI as usual.",
         False, "lone weak marker without corroboration stays english"),

        # Strong spanish signal via accented density alone (no marker words)
        ("Cotización", "Confirmación: número de póliza según información "
         "compañía. Revisión válida según cláusula.",
         True, "accented-character density without core marker words"),

        ("Nueva dirección", "Buenos días, la nueva dirección del titular es "
         "distinta, favor de actualizar el certificado. Gracias.",
         True, "buenos días + multiple markers"),
    ]

    for subject, body, expected, label in cases:
        got = detect_spanish(subject, body)
        check(f"detector: {label}", got == expected,
              f"detect_spanish(subject={subject!r}, body={body!r}) = {got}, expected {expected}")


# ---------------------------------------------------------------------------
# 2 & 3. sender.execute_action send_pdf body assembly + style checks
# ---------------------------------------------------------------------------

def _make_pdf_decision(is_revision=False):
    # We don't need a real PDF for dry_run — execute_action only reads
    # pdf_paths to report attachment names in dry_run mode, it doesn't open
    # the file.
    return {
        "action": "send_pdf",
        "classification": "coi_revision_request" if is_revision else "coi_request_complete",
        "is_revision": is_revision,
        "client_name": "Rolando's HVAC LLC",
        "pdf_paths": [FAKE_PDF_PATH],
        "to": "leyva.lrolandoshvac@gmail.com",
    }


def _make_parsed(with_holder=True):
    parsed = {
        "classification": "coi_request_complete",
        "status": "ready",
        "client_canonical_name": "Rolando's HVAC LLC",
    }
    if with_holder:
        parsed["certificate_holder"] = {
            "name": "Constructora Del Mar LLC",
            "address_line_1": "7800 NW 25th St",
            "city": "Doral", "state": "FL", "zip": "33122",
        }
    return parsed


def get_body_html(graph_call_result_sent):
    """Extract HTML body from a FakeGraph.sent entry."""
    _, _, message_obj = graph_call_result_sent
    return message_obj["body"]["content"]


def test_send_pdf_spanish():
    graph = FakeGraph()
    new_email = graph_msg(
        "msg-1", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
        "COI urgente",
        "Hola, envíame un COI por favor.\n\nCertificate holder:\n"
        "Constructora Del Mar LLC\n7800 NW 25th St\nDoral, FL 33122\n\nGracias!",
    )
    parsed = _make_parsed()
    ai_result = {"parsed": parsed, "sender": new_email["from"]["emailAddress"]["address"]}
    decision = _make_pdf_decision(is_revision=False)
    attachments_result = {"attachments": []}

    result = execute_action(graph, new_email, [new_email], attachments_result,
                             ai_result, decision, dry_run=True)

    check("send_pdf(es): dry_run returns type pdf_reply", result.get("type") == "pdf_reply")

    # dry_run doesn't populate graph.sent, so rebuild body via a live (non-dry)
    # call against a second FakeGraph to inspect the actual HTML payload.
    graph2 = FakeGraph()
    result2 = execute_action(graph2, new_email, [new_email], attachments_result,
                              ai_result, decision, dry_run=False)
    check("send_pdf(es): sent successfully", result2.get("sent") is True)
    check("send_pdf(es): exactly one reply sent", len(graph2.sent) == 1)

    body = get_body_html(graph2.sent[0])
    global _last_es_body
    _last_es_body = body

    check("send_pdf(es): opens with recipient first name + comma",
          body.startswith("<p>Rolando,</p>"), body[:60])
    check("send_pdf(es): contains 'Adjunto encontrará'", "Adjunto encontrará" in body)
    check("send_pdf(es): contains 'el Certificado de Seguro' (non-revision)",
          "el Certificado de Seguro para" in body)
    check("send_pdf(es): does NOT use revision wording",
          "revisado" not in body)
    check("send_pdf(es): 'Cert holder' label stays English",
          "Cert holder:" in body)
    check("send_pdf(es): holder value present",
          "Constructora Del Mar LLC" in body)
    check("send_pdf(es): closer uses 'Cualquier revisión, con gusto la hacemos.'",
          "Cualquier revisión, con gusto la hacemos." in body)
    check("send_pdf(es): ends with Saludos,",
          "<p>Saludos,</p>" in body)
    check("send_pdf(es): no 'mándame'", not re.search(r"m[áa]ndame", body, re.I))
    check("send_pdf(es): no em/en dashes",
          "—" not in body and "–" not in body)


def test_send_pdf_spanish_revision():
    graph = FakeGraph()
    new_email = graph_msg(
        "msg-2", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
        "Re: COI urgente",
        "Hola, la dirección del titular cambió, favor de corregir y reenviar "
        "el certificado. Gracias.",
    )
    parsed = _make_parsed()
    ai_result = {"parsed": parsed, "sender": new_email["from"]["emailAddress"]["address"]}
    decision = _make_pdf_decision(is_revision=True)
    attachments_result = {"attachments": []}

    result = execute_action(graph, new_email, [new_email], attachments_result,
                             ai_result, decision, dry_run=False)
    check("send_pdf(es, revision): sent successfully", result.get("sent") is True)
    body = get_body_html(graph.sent[0])
    check("send_pdf(es, revision): uses 'el Certificado de Seguro revisado'",
          "el Certificado de Seguro revisado" in body, body)
    # Body text (pre-signature) ends with 'Saludos,' — the signature HTML is
    # appended after by with_signature(), so check for the marker's presence
    # rather than the tail of the full (signature-appended) string.
    check("send_pdf(es, revision): Saludos, ending", "<p>Saludos,</p>" in body)
    check("send_pdf(es, revision): no dashes",
          "—" not in body and "–" not in body)


def test_send_pdf_english_unchanged():
    graph = FakeGraph()
    new_email = graph_msg(
        "msg-3", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
        "COI request",
        "Hi, I need a certificate of insurance.\n\nCertificate holder:\n"
        "Bengoa Construction Inc\n2200 N Dixie Hwy\nHollywood, FL 33020\n\nThanks!",
    )
    parsed = {
        "classification": "coi_request_complete",
        "status": "ready",
        "client_canonical_name": "Rolando's HVAC LLC",
        "certificate_holder": {
            "name": "Bengoa Construction Inc",
            "address_line_1": "2200 N Dixie Hwy",
            "city": "Hollywood", "state": "FL", "zip": "33020",
        },
    }
    ai_result = {"parsed": parsed, "sender": new_email["from"]["emailAddress"]["address"]}
    decision = _make_pdf_decision(is_revision=False)
    attachments_result = {"attachments": []}

    result = execute_action(graph, new_email, [new_email], attachments_result,
                             ai_result, decision, dry_run=False)
    check("send_pdf(en): sent successfully", result.get("sent") is True)
    body = get_body_html(graph.sent[0])
    check("send_pdf(en): unchanged English copy",
          "Attached please find the Certificate of Insurance for" in body)
    check("send_pdf(en): ends with Regards,", "<p>Regards,</p>" in body)
    check("send_pdf(en): no Spanish closer leaked in",
          "Cualquier revisión" not in body and "Saludos," not in body)


def test_complex_review_ack_language_passthrough():
    """The complex-review client ack is 100% model-generated text
    (client_reply_text / parsed['reply_text']), and the system prompt
    (line ~435) already instructs the model to match the client's language
    for this kind of client-facing reply. sender.py does not hardcode any
    English/Spanish copy for the ack — it just relays client_reply_text
    verbatim (wrapped in with_signature). Confirm that passthrough holds:
    whatever language the model produced is exactly what goes out, with no
    sender-side alteration or default text substituted in either direction.
    """
    graph_es = FakeGraph()
    new_email_es = graph_msg(
        "msg-4", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
        "certificado de seguro",
        "Adjunto el contrato con los requisitos de seguro. Necesito el COI "
        "cuanto antes, por favor.",
    )
    spanish_ack = ("Rolando,\n\nRecibimos su solicitud y el contrato adjunto. "
                   "Alejandro revisará los requisitos y le daremos seguimiento "
                   "en breve.\n\nSaludos,")
    decision_es = {
        "action": "send_complex_review",
        "client_name": "Rolando's HVAC LLC",
        "pdf_paths": [FAKE_PDF_PATH],
        "client_reply_text": spanish_ack,
        "review_summary": "Contract requires higher GL limits than carried.",
        "coverage_analysis": {},
        "request_summary": "Client requests COI with attached insurance requirements.",
        "send_completed_coi_to": None,
    }
    attachments_result = {"attachments": []}
    ai_result = {"parsed": {}, "sender": new_email_es["from"]["emailAddress"]["address"]}

    result = execute_action(graph_es, new_email_es, [new_email_es], attachments_result,
                             ai_result, decision_es, dry_run=False)
    check("complex_review ack(es): client_ack_sent True", result.get("client_ack_sent") is True)
    ack_call = next(c for c in graph_es.sent if c[1] == new_email_es["id"])
    ack_body = get_body_html(ack_call)
    check("complex_review ack(es): Spanish model text relayed verbatim",
          "Recibimos su solicitud" in ack_body and "Saludos," in ack_body)
    check("complex_review ack(es): no English default text substituted",
          "We received your request" not in ack_body)


def main():
    test_detector()
    test_send_pdf_spanish()
    test_send_pdf_spanish_revision()
    test_send_pdf_english_unchanged()
    test_complex_review_ack_language_passthrough()

    print("\n" + "=" * 72)
    for line in report:
        print(line)
    print("=" * 72)
    print(f"Checks: {len(report)}   FAIL: {fails}")

    if "_last_es_body" in globals():
        print("\nSample Spanish send_pdf body (HTML):\n")
        print(_last_es_body)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
