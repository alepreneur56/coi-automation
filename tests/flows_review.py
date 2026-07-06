"""
flows_review.py
---------------
Offline harness for the MVP flows (flows.py + sender wiring + db auto-AI
table). NO API calls, NO mailbox — hand-built parsed/decision dicts run
through sender.execute_action against a FakeGraph (same pattern as
tests/spanish_review.py).

Covers:
  1. No-signal requests completely unaffected (one delivery email, body
     unchanged, no DB writes).
  2. Referral line append — English send_pdf + send_reply, wording filled
     from registry controlled_lines, placed before 'Regards,'.
  3. Spanish-skip path — no referral in the Spanish delivery; producer note
     flagged 'Spanish referral wording pending Alex approval'.
  4. Limits shortfall trio — delivery untouched + client email + Alejandro
     non-compliance email, with all three contact-resolution branches
     (registry contact / sender domain match / unresolved-skip).
  5. Ancillary missing — Alejandro email only, no client email.
  6. Carrier endorsement request — subject/recipients, DB record with
     status 'requested', dedupe-skip on a known holder, bulk import.
  7. TEST_MODE redirect on EVERY new send (and real recipients when off).
  8. Style compliance — no em/en dashes, 'Name,' opener, 'Regards,' closer.

Usage:
    .venv/bin/python tests/flows_review.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import db
import flows
from sender import execute_action

# ---------------------------------------------------------------------------
# ISOLATION: never touch the real history DB; pin TEST_MODE per test.
# ---------------------------------------------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="flows_review_")
db.DB_PATH = os.path.join(_tmpdir, "coi_history_test.db")

FAKE_PDF_PATH = os.path.join(_tmpdir, "fake.pdf")
with open(FAKE_PDF_PATH, "wb") as _f:
    _f.write(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n0\n%%EOF"
    )

REPORT = []
FAILS = [0]


def check(name, condition, detail=""):
    if condition:
        REPORT.append(f"[OK]   {name}")
    else:
        FAILS[0] += 1
        REPORT.append(f"[FAIL] {name}" + (f" :: {detail}" if detail else ""))


class FakeGraph:
    def __init__(self):
        self.sent = []

    def reply_to_message(self, msg_id, message_obj):
        self.sent.append(("reply", msg_id, message_obj))
        return True, None

    def send_mail(self, message_obj):
        self.sent.append(("sendMail", None, message_obj))
        return True, None


def graph_msg(msg_id, sender_email, sender_name, subject, body):
    return {
        "id": msg_id,
        "conversationId": "conv-flows-1",
        "subject": subject,
        "sentDateTime": "2026-07-06T15:00:00Z",
        "receivedDateTime": "2026-07-06T15:00:00Z",
        "hasAttachments": False,
        "from": {"emailAddress": {"address": sender_email, "name": sender_name}},
        "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
        "ccRecipients": [],
        "body": {"contentType": "text", "content": body},
        "bodyPreview": body[:150],
    }


EN_BODY = (
    "Hi, I need a certificate of insurance.\n\nCertificate holder:\n"
    "Bengoa Construction Inc\n2200 N Dixie Hwy\nHollywood, FL 33020\n\nThanks!"
)
ES_BODY = (
    "Hola, envíame un COI por favor. Necesito el certificado de seguro "
    "cuanto antes.\n\nCertificate holder:\nConstructora Del Mar LLC\n"
    "7800 NW 25th St\nDoral, FL 33122\n\nGracias!"
)


def base_parsed(client_id="rolandos_hvac",
                client_name="Rolando's HVAC LLC", **extra):
    parsed = {
        "classification": "coi_request_complete",
        "status": "ready",
        "client_id": client_id,
        "client_canonical_name": client_name,
        "certificate_holder": {
            "name": "Bengoa Construction Inc",
            "address_line_1": "2200 N Dixie Hwy",
            "city": "Hollywood", "state": "FL", "zip": "33020",
        },
    }
    parsed.update(extra)
    return parsed


def pdf_decision(client_name="Rolando's HVAC LLC"):
    return {
        "action": "send_pdf",
        "classification": "coi_request_complete",
        "is_revision": False,
        "client_name": client_name,
        "pdf_paths": [FAKE_PDF_PATH],
        "to": "requestor@example.com",
    }


def run(parsed, new_email, decision=None, test_mode=True):
    """execute_action against a fresh FakeGraph with TEST_MODE pinned."""
    saved = config.TEST_MODE
    config.TEST_MODE = test_mode
    try:
        graph = FakeGraph()
        ai_result = {"parsed": parsed,
                     "sender": new_email["from"]["emailAddress"]["address"]}
        result = execute_action(graph, new_email, [new_email],
                                {"attachments": []}, ai_result,
                                decision or pdf_decision(), dry_run=False)
        return graph, result
    finally:
        config.TEST_MODE = saved


def body_of(entry):
    return entry[2]["body"]["content"]


def to_of(entry):
    return [r["emailAddress"]["address"] for r in entry[2].get("toRecipients", [])]


def cc_of(entry):
    return [r["emailAddress"]["address"] for r in entry[2].get("ccRecipients", [])]


def replies(graph):
    return [e for e in graph.sent if e[0] == "reply"]


def new_sends(graph):
    return [e for e in graph.sent if e[0] == "sendMail"]


def style_ok(name, body, closer="Regards,"):
    check(f"{name}: no em/en dashes", "—" not in body and "–" not in body)
    check(f"{name}: {closer} closer present", f"<p>{closer}</p>" in body, body[-200:])


REFERRAL_EN = ("Please note our office handles the GL and Auto policies. "
               "The WC certificate will come from the broker who handles "
               "that policy.")


# ---------------------------------------------------------------------------
# 1. No-signal request completely unaffected
# ---------------------------------------------------------------------------

def test_no_signal_unaffected():
    email = graph_msg("m-nosig", "gc@bengoa.com", "Maria Perez", "COI request", EN_BODY)
    graph, result = run(base_parsed(), email)
    check("no_signal: delivery sent", result.get("sent") is True)
    check("no_signal: exactly one email total", len(graph.sent) == 1,
          str([e[0] for e in graph.sent]))
    body = body_of(graph.sent[0])
    check("no_signal: no referral text in body", "Please note our office" not in body)
    check("no_signal: standard delivery copy intact",
          "Attached please find the Certificate of Insurance for" in body)
    conn = db.connect()
    n = conn.execute("SELECT COUNT(*) c FROM auto_ai_endorsements").fetchone()["c"]
    conn.close()
    check("no_signal: no auto-AI DB rows written", n == 0, f"rows={n}")


# ---------------------------------------------------------------------------
# 2. Referral line — English
# ---------------------------------------------------------------------------

def test_referral_english_pdf():
    email = graph_msg("m-ref-en", "gc@bengoa.com", "Maria Perez", "COI request",
                      EN_BODY + "\nPlease include workers comp.")
    parsed = base_parsed(
        uncontrolled_lines_requested=[{"line": "WC", "broker_note": "another broker"}])
    graph, result = run(parsed, email)
    check("referral_en_pdf: delivery sent", result.get("sent") is True)
    check("referral_en_pdf: only the delivery email (no producer email needed)",
          len(graph.sent) == 1, str([e[0] for e in graph.sent]))
    body = body_of(graph.sent[0])
    check("referral_en_pdf: approved wording, registry-filled",
          REFERRAL_EN in body, body)
    check("referral_en_pdf: referral before Regards,",
          body.find(REFERRAL_EN) < body.find("<p>Regards,</p>"))
    style_ok("referral_en_pdf", body)


def test_referral_english_reply():
    email = graph_msg("m-ref-reply", "gc@bengoa.com", "Maria Perez",
                      "COI request", "Need a COI and your WC cert. Missing the holder zip.")
    parsed = base_parsed(
        uncontrolled_lines_requested=[{"line": "WC", "broker_note": "another broker"}])
    decision = {
        "action": "send_reply",
        "classification": "coi_request_incomplete",
        "reply_text": ("Maria, happy to help. Can you send me the ZIP code "
                       "for Bengoa Construction Inc at 2200 N Dixie Hwy, "
                       "Hollywood, FL and I'll get the COI right out to you.\n\n"
                       "Regards,"),
        "to": "gc@bengoa.com",
    }
    graph, result = run(parsed, email, decision=decision)
    check("referral_en_reply: reply sent", result.get("sent") is True)
    body = body_of(graph.sent[0])
    check("referral_en_reply: referral wording present", REFERRAL_EN in body, body)
    check("referral_en_reply: referral before Regards,",
          body.find(REFERRAL_EN) < body.find("Regards,"))
    check("referral_en_reply: result reply_text carries referral",
          REFERRAL_EN in result.get("reply_text", ""))
    check("referral_en_reply: reply_text still ends with Regards,",
          result.get("reply_text", "").rstrip().endswith("Regards,"))


def test_referral_multiline():
    email = graph_msg("m-ref-multi", "gc@bengoa.com", "Maria Perez", "COI request", EN_BODY)
    parsed = base_parsed(
        client_id="absolute_air_solutions",
        client_name="Absolute Air Solutions LLC",
        uncontrolled_lines_requested=[
            {"line": "GL", "broker_note": "prior broker"},
            {"line": "WC", "broker_note": "prior broker"},
        ])
    line = flows.build_referral_line(parsed)
    check("referral_multi: controlled lines from registry (Auto only)",
          line.startswith("Please note our office handles the Auto policies."), line)
    check("referral_multi: both missing lines named", "GL and WC certificates" in line, line)


# ---------------------------------------------------------------------------
# 3. Referral — Spanish skip path
# ---------------------------------------------------------------------------

def test_referral_spanish_skip():
    email = graph_msg("m-ref-es", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
                      "certificado de seguro", ES_BODY)
    parsed = base_parsed(
        uncontrolled_lines_requested=[{"line": "WC", "broker_note": "another broker"}])
    graph, result = run(parsed, email)
    check("referral_es: delivery sent", result.get("sent") is True)
    delivery = replies(graph)
    check("referral_es: exactly one delivery reply", len(delivery) == 1)
    dbody = body_of(delivery[0])
    check("referral_es: Spanish delivery has NO referral line",
          "Please note our office" not in dbody, dbody)
    check("referral_es: Spanish delivery copy intact", "Adjunto encontrará" in dbody)
    style_ok("referral_es delivery", dbody, closer="Saludos,")

    notes = new_sends(graph)
    check("referral_es: exactly one producer note sent", len(notes) == 1,
          str([e[0] for e in graph.sent]))
    nbody = body_of(notes[0])
    check("referral_es: note flags pending Spanish wording",
          "Spanish referral wording pending Alex approval" in nbody, nbody[:400])
    check("referral_es: note carries the referral info", REFERRAL_EN in nbody)
    check("referral_es: note carries the broker note", "another broker" in nbody)
    check("referral_es: producer note redirected in TEST_MODE",
          to_of(notes[0]) == [config.TEST_REDIRECT_TO], str(to_of(notes[0])))


def test_referral_spanish_skip_on_reply():
    email = graph_msg("m-ref-es-reply", "leyva.lrolandoshvac@gmail.com",
                      "Rolando Leyva", "certificado de seguro", ES_BODY)
    parsed = base_parsed(
        uncontrolled_lines_requested=[{"line": "WC", "broker_note": "another broker"}])
    decision = {
        "action": "send_reply",
        "classification": "coi_request_incomplete",
        "reply_text": "Rolando, me falta el ZIP code del certificate holder.\n\nSaludos,",
        "to": "leyva.lrolandoshvac@gmail.com",
    }
    graph, result = run(parsed, email, decision=decision)
    body = body_of(replies(graph)[0])
    check("referral_es_reply: no referral appended to Spanish reply",
          "Please note our office" not in body)
    notes = new_sends(graph)
    check("referral_es_reply: producer note still sent (delivery=False path)",
          len(notes) == 1 and "Spanish referral wording pending Alex approval" in body_of(notes[0]))


# ---------------------------------------------------------------------------
# 4. Limits shortfall — trio + contact resolution branches
# ---------------------------------------------------------------------------

SHORTFALL = [{"line": "GL", "carried": "1,000,000", "demanded": "2,000,000"}]


def test_shortfall_registry_contact():
    email = graph_msg("m-short-1", "gc@bigbuilder.com", "Bob Smith",
                      "COI needed, $2M GL required", EN_BODY)
    parsed = base_parsed(limits_shortfall=SHORTFALL)

    graph, result = run(parsed, email, test_mode=True)
    check("shortfall_registry: delivery sent untouched", result.get("sent") is True)
    check("shortfall_registry: three emails total (delivery + client + Alejandro)",
          len(graph.sent) == 3, str([e[0] for e in graph.sent]))
    check("shortfall_registry: delivery body has no shortfall talk",
          "currently carries" not in body_of(replies(graph)[0]))

    sends = new_sends(graph)
    client_email = next(e for e in sends if "policy limits" in e[2]["subject"])
    alex_email = next(e for e in sends if e[2]["subject"].startswith("Non-compliance"))

    cbody = body_of(client_email)
    check("shortfall_registry: client email opens 'Leyva,'",
          cbody.startswith("<p>Leyva,</p>"), cbody[:60])
    check("shortfall_registry: approved wording pieces",
          "We sent the certificate to Bob Smith (gc@bigbuilder.com)" in cbody
          and "$1,000,000 in GL limits because that is what your policy currently carries" in cbody
          and "They are requesting $2,000,000" in cbody
          and "Give me a call when you get a chance so we can go over the best next step" in cbody,
          cbody)
    style_ok("shortfall_registry client email", cbody)
    check("shortfall_registry: client email redirected in TEST_MODE",
          to_of(client_email) == [config.TEST_REDIRECT_TO])
    check("shortfall_registry: client email has NO CC (third party never on it)",
          cc_of(client_email) == [])

    abody = body_of(alex_email)
    check("shortfall_registry: Alejandro breakdown carried vs demanded",
          "carries $1,000,000" in abody and "demanded $2,000,000" in abody, abody)
    check("shortfall_registry: Alejandro email notes client was emailed",
          "leyva.lrolandoshvac@gmail.com" in abody)
    check("shortfall_registry: Alejandro email redirected in TEST_MODE",
          to_of(alex_email) == [config.TEST_REDIRECT_TO])

    # TEST_MODE off -> real recipients
    graph2, _ = run(parsed, email, test_mode=False)
    sends2 = new_sends(graph2)
    client2 = next(e for e in sends2 if "policy limits" in e[2]["subject"])
    alex2 = next(e for e in sends2 if e[2]["subject"].startswith("Non-compliance"))
    check("shortfall_registry: TEST_MODE off, client email to registry contact",
          to_of(client2) == ["leyva.lrolandoshvac@gmail.com"], str(to_of(client2)))
    check("shortfall_registry: TEST_MODE off, Alejandro email to PRODUCER_CC_EMAIL",
          to_of(alex2) == [config.PRODUCER_CC_EMAIL], str(to_of(alex2)))


def test_shortfall_domain_match():
    email = graph_msg("m-short-2", "bob@claytonmechanical.com", "Bob Clayton",
                      "COI request", EN_BODY)
    parsed = base_parsed(client_id="clayton_mechanical",
                         client_name="Clayton Mechanical",
                         limits_shortfall=SHORTFALL)
    graph, _ = run(parsed, email, test_mode=False)
    sends = new_sends(graph)
    check("shortfall_domain: three emails total", len(graph.sent) == 3,
          str([e[0] for e in graph.sent]))
    client_email = next(e for e in sends if "policy limits" in e[2]["subject"])
    check("shortfall_domain: client email to domain-matched sender",
          to_of(client_email) == ["bob@claytonmechanical.com"], str(to_of(client_email)))
    check("shortfall_domain: opener from email local part",
          body_of(client_email).startswith("<p>Bob,</p>"), body_of(client_email)[:40])


def test_shortfall_unresolved():
    email = graph_msg("m-short-3", "gc@bigbuilder.com", "Bob Smith",
                      "COI request", EN_BODY)
    parsed = base_parsed(client_id="305_power_corp", client_name="305 Power Corp",
                         limits_shortfall=SHORTFALL)
    graph, result = run(parsed, email, test_mode=True)
    check("shortfall_unresolved: delivery still sent", result.get("sent") is True)
    sends = new_sends(graph)
    check("shortfall_unresolved: only the Alejandro email (client skipped)",
          len(sends) == 1 and sends[0][2]["subject"].startswith("Non-compliance"),
          str([e[2].get("subject") for e in sends]))
    abody = body_of(sends[0])
    check("shortfall_unresolved: skip noted in Alejandro email",
          "No client email was sent" in abody, abody)


# ---------------------------------------------------------------------------
# 5. Ancillary missing — Alejandro only
# ---------------------------------------------------------------------------

def test_ancillary():
    email = graph_msg("m-anc", "gc@bigbuilder.com", "Bob Smith",
                      "COI request, need pollution + EPLI", EN_BODY)
    parsed = base_parsed(ancillary_missing=["Pollution Liability", "EPLI"])
    graph, result = run(parsed, email, test_mode=True)
    check("ancillary: delivery sent untouched", result.get("sent") is True)
    check("ancillary: one delivery + one Alejandro email, nothing else",
          len(replies(graph)) == 1 and len(new_sends(graph)) == 1,
          str([e[0] for e in graph.sent]))
    abody = body_of(new_sends(graph)[0])
    check("ancillary: both lines listed",
          "Pollution Liability" in abody and "EPLI" in abody, abody)
    check("ancillary: no shortfall section", "Limits shortfall" not in abody)
    check("ancillary: client-conversation note present",
          "That conversation is yours" in abody)
    check("ancillary: redirected in TEST_MODE",
          to_of(new_sends(graph)[0]) == [config.TEST_REDIRECT_TO])


# ---------------------------------------------------------------------------
# 6. Carrier endorsement request — send, record, dedupe, import
# ---------------------------------------------------------------------------

CARRIER_SIGNAL = {"client": "rolandos_hvac", "holder": "Bengoa Construction Inc"}
CARRIER_SUBJECT = ("REF: Rolando's HVAC - CA-74829-0 - "
                   "Endorsement Request - Additional Insured")


def _fresh_ai_db():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)


def test_carrier_request():
    _fresh_ai_db()
    email = graph_msg("m-car-1", "gc@bigbuilder.com", "Bob Smith",
                      "COI request, AI on auto policy", EN_BODY)
    parsed = base_parsed(carrier_endorsement_request=dict(CARRIER_SIGNAL))
    graph, result = run(parsed, email, test_mode=True)
    check("carrier: delivery sent untouched", result.get("sent") is True)
    sends = new_sends(graph)
    check("carrier: exactly one carrier email", len(sends) == 1,
          str([e[2].get("subject") for e in sends]))
    subject = sends[0][2]["subject"]
    check("carrier: subject with registry auto policy number",
          subject == CARRIER_SUBJECT, subject)
    cbody = body_of(sends[0])
    check("carrier: opens 'Ascendant team,'", cbody.startswith("<p>Ascendant team,</p>"),
          cbody[:50])
    check("carrier: holder name and address in body",
          "Bengoa Construction Inc, 2200 N Dixie Hwy, Hollywood FL 33020" in cbody, cbody)
    check("carrier: confirmation-request wording",
          "please confirm you are processing this request" in cbody)
    style_ok("carrier email", cbody)
    check("carrier: TEST_MODE redirect (To=test, CC stripped)",
          to_of(sends[0]) == [config.TEST_REDIRECT_TO] and cc_of(sends[0]) == [],
          f"to={to_of(sends[0])} cc={cc_of(sends[0])}")

    row = db.ai_endorsement_lookup("rolandos_hvac", "Bengoa Construction Inc")
    check("carrier: holder recorded with status 'requested'",
          row is not None and row["status"] == "requested" and row["source"] == "live",
          str(row))

    # Second request for the same holder -> dedupe skip, no carrier email
    email2 = graph_msg("m-car-2", "other@builder.com", "Ana Ruiz",
                       "another COI, AI on auto", EN_BODY)
    parsed2 = base_parsed(
        carrier_endorsement_request={"client": "rolandos_hvac",
                                     "holder": "Bengoa Construction, Inc."})
    graph2, result2 = run(parsed2, email2, test_mode=True)
    check("carrier_dedupe: delivery still sent", result2.get("sent") is True)
    check("carrier_dedupe: NO second carrier email (token-matched holder)",
          len(new_sends(graph2)) == 0,
          str([e[2].get("subject") for e in new_sends(graph2)]))
    conn = db.connect()
    n = conn.execute("SELECT COUNT(*) c FROM auto_ai_endorsements").fetchone()["c"]
    conn.close()
    check("carrier_dedupe: still exactly one DB row", n == 1, f"rows={n}")


def test_carrier_real_recipients():
    _fresh_ai_db()
    email = graph_msg("m-car-3", "gc@bigbuilder.com", "Bob Smith",
                      "COI request, AI on auto policy", EN_BODY)
    parsed = base_parsed(carrier_endorsement_request=dict(CARRIER_SIGNAL))
    graph, _ = run(parsed, email, test_mode=False)
    sends = new_sends(graph)
    check("carrier_real: To endorsements@ascendantgroup.com",
          to_of(sends[0]) == ["endorsements@ascendantgroup.com"], str(to_of(sends[0])))
    check("carrier_real: CC alejandro.bello@usi.com",
          cc_of(sends[0]) == ["alejandro.bello@usi.com"], str(cc_of(sends[0])))


def test_bulk_import():
    _fresh_ai_db()
    csv_path = os.path.join(_tmpdir, "bulk.csv")
    with open(csv_path, "w") as f:
        f.write("holder_name,address,status\n"
                "City of Tampa,306 E Jackson St Tampa FL 33602,endorsed\n"
                "Bengoa Construction Inc,,endorsed\n")
    imported, skipped = db.import_ai_endorsements(csv_path)
    check("bulk_import: two rows imported", (imported, skipped) == (2, 0),
          f"imported={imported} skipped={skipped}")
    imported2, skipped2 = db.import_ai_endorsements(csv_path)
    check("bulk_import: re-import fully deduped", (imported2, skipped2) == (0, 2),
          f"imported={imported2} skipped={skipped2}")
    row = db.ai_endorsement_lookup("rolandos_hvac", "City of Tampa, Inc.")
    check("bulk_import: token-match lookup finds bulk row as endorsed",
          row is not None and row["status"] == "endorsed" and row["source"] == "bulk_import",
          str(row))
    check("bulk_import: different holder does NOT match",
          db.ai_endorsement_lookup("rolandos_hvac", "City of Tampa Parks Department") is None)

    # A bulk-endorsed holder must dedupe-skip the live carrier request too
    email = graph_msg("m-car-4", "gc@bigbuilder.com", "Bob Smith",
                      "COI, AI on auto", EN_BODY)
    parsed = base_parsed(
        carrier_endorsement_request={"client": "rolandos_hvac",
                                     "holder": "City of Tampa"})
    graph, _ = run(parsed, email, test_mode=True)
    check("bulk_import: live request for bulk-endorsed holder is skipped",
          len(new_sends(graph)) == 0)


# ---------------------------------------------------------------------------
# 7. Combined signals — one Alejandro email with all sections
# ---------------------------------------------------------------------------

def test_combined_signals():
    _fresh_ai_db()
    email = graph_msg("m-combo", "leyva.lrolandoshvac@gmail.com", "Rolando Leyva",
                      "certificado urgente", ES_BODY)
    parsed = base_parsed(
        uncontrolled_lines_requested=[{"line": "WC", "broker_note": "another broker"}],
        limits_shortfall=SHORTFALL,
        ancillary_missing=["Pollution Liability"],
        carrier_endorsement_request=dict(CARRIER_SIGNAL),
    )
    graph, result = run(parsed, email, test_mode=True)
    check("combined: delivery sent", result.get("sent") is True)
    sends = new_sends(graph)
    subjects = [e[2].get("subject", "") for e in sends]
    check("combined: client + ONE Alejandro + carrier emails",
          len(sends) == 3
          and sum(1 for s in subjects if s.startswith("Non-compliance")) == 1
          and sum(1 for s in subjects if "policy limits" in s) == 1
          and sum(1 for s in subjects if s.startswith("REF:")) == 1,
          str(subjects))
    abody = body_of(next(e for e in sends if e[2]["subject"].startswith("Non-compliance")))
    check("combined: Alejandro email has shortfall + ancillary + Spanish-referral sections",
          "carries $1,000,000" in abody and "Pollution Liability" in abody
          and "Spanish referral wording pending Alex approval" in abody, abody)
    check("combined: every new send redirected in TEST_MODE",
          all(to_of(e) == [config.TEST_REDIRECT_TO] for e in sends),
          str([to_of(e) for e in sends]))


# ---------------------------------------------------------------------------
# 8. Team-hints update in the review tooling
# ---------------------------------------------------------------------------

def test_team_hints():
    try:
        from training.build_review import TEAM_HINTS, is_team_message
    except Exception as e:
        check("team_hints: import training.build_review", False, str(e))
        return
    for name in ("andrea vargas", "katherin molina", "christian devilme"):
        check(f"team_hints: {name} in TEAM_HINTS", name in TEAM_HINTS)
    check("team_hints: any @usi.com sender is team",
          is_team_message({"from": "Random Person <random.person@usi.com>", "body": "hello"}))
    check("team_hints: non-team sender unaffected",
          not is_team_message({"from": "Bob GC <bob@builder.com>", "body": "need a COI"}))


def main():
    test_no_signal_unaffected()
    test_referral_english_pdf()
    test_referral_english_reply()
    test_referral_multiline()
    test_referral_spanish_skip()
    test_referral_spanish_skip_on_reply()
    test_shortfall_registry_contact()
    test_shortfall_domain_match()
    test_shortfall_unresolved()
    test_ancillary()
    test_carrier_request()
    test_carrier_real_recipients()
    test_bulk_import()
    test_combined_signals()
    test_team_hints()

    print("\n" + "=" * 72)
    for line in REPORT:
        print(line)
    print("=" * 72)
    print(f"Checks: {len(REPORT)}   FAIL: {FAILS[0]}")
    return 1 if FAILS[0] else 0


if __name__ == "__main__":
    sys.exit(main())
