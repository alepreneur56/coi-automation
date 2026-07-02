"""
pipeline_review.py
------------------
Full-pipeline test harness: synthetic client emails run through the REAL
classifier (live Anthropic call), REAL pipeline (coi_engine PDFs), and REAL
sender in dry-run mode against a fake Graph client. No mailbox involved,
nothing is sent.

Checks per scenario:
  - expected classification + action
  - client-facing reply style rules (name-comma opener, no Hi/Hello, no
    dashes, Regards,/Saludos, endings, envíame-not-mándame, no signature)
  - produced PDFs (right template, holder present)

Usage:
    .venv/bin/python tests/pipeline_review.py [--only SUBSTR]
Artifacts land in tests/pipeline_output/.
"""

import argparse
import base64
import json
import os
import re
import shutil
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

import config
from attachments import fetch_attachments
from classifier import classify
from pipeline import decide_action
from sender import execute_action
from thread_fetch import fetch_thread

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_ATTACH_DIR = os.path.join(os.path.dirname(BASE), "COI_Test_Attachments")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_output")

TODAY = date.today().strftime("%m/%d/%Y")

CLIENT_SENDER = "leyva.lrolandoshvac@gmail.com"


# ---------------------------------------------------------------------------
# Fake Graph — feeds canned threads/attachments, captures outbound payloads
# ---------------------------------------------------------------------------

class FakeGraph:
    def __init__(self, thread=None, raw_attachments=None):
        self.thread = thread or []
        self.raw_attachments = raw_attachments or []
        self.sent = []

    def search_by_conversation(self, conv_id):
        return [m for m in self.thread if m.get("conversationId") == conv_id]

    def get_message_headers(self, msg_id):
        return []

    def find_message_by_internet_id(self, internet_msg_id):
        return None

    def list_attachments(self, msg_id):
        return self.raw_attachments

    def mark_read(self, msg_id):
        return True

    def reply_to_message(self, msg_id, message_obj):
        self.sent.append(("reply", msg_id, message_obj))
        return True, None

    def send_mail(self, message_obj):
        self.sent.append(("sendMail", None, message_obj))
        return True, None


def graph_msg(msg_id, sender_email, sender_name, subject, body,
              conv_id="conv-test-1", sent_dt="2026-07-01T15:00:00Z",
              has_attachments=False):
    return {
        "id": msg_id,
        "conversationId": conv_id,
        "subject": subject,
        "sentDateTime": sent_dt,
        "receivedDateTime": sent_dt,
        "hasAttachments": has_attachments,
        "from": {"emailAddress": {"address": sender_email, "name": sender_name}},
        "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
        "ccRecipients": [],
        "body": {"contentType": "text", "content": body},
        "bodyPreview": body[:150],
    }


def file_attachment(path):
    with open(path, "rb") as f:
        data = f.read()
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": os.path.basename(path),
        "contentType": "application/pdf",
        "size": len(data),
        "contentBytes": base64.b64encode(data).decode(),
    }


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def build_scenarios():
    scen = []

    def add(name, body, subject="COI request", sender=CLIENT_SENDER,
            sender_name="Rolando Leyva", expect_class=None, expect_action=None,
            lang=None, thread=None, attachments=None, msg_kwargs=None,
            expect_template=None, expect_holder=None, expect_third_party=None):
        scen.append({
            "name": name, "body": body, "subject": subject,
            "sender": sender, "sender_name": sender_name,
            "expect_class": expect_class or [], "expect_action": expect_action,
            "lang": lang, "thread": thread, "attachments": attachments or [],
            "msg_kwargs": msg_kwargs or {},
            "expect_template": expect_template,
            "expect_holder": expect_holder,
            "expect_third_party": expect_third_party,
        })

    # 1. Complete simple request
    add("complete_simple",
        "Hi, I need a certificate of insurance.\n\nCertificate holder:\n"
        "Bengoa Construction Inc\n2200 N Dixie Hwy\nHollywood, FL 33020\n\nThanks!",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_template="Rolando_s_HVAC_COI_Template.pdf",
        expect_holder="Bengoa Construction Inc")

    # 2. Incomplete — no address anywhere, holder name is not lookupable
    add("incomplete_no_address",
        "Hey I need a COI for a new job, the certificate holder is JB Prime "
        "Holdings. Send it over as soon as you can please.",
        expect_class=["coi_request_incomplete"], expect_action=["send_reply", "do_nothing"],
        lang="en")

    # 3. Question — no COI
    add("question_gl_limits",
        "Quick question, what are my general liability limits on my current "
        "policy? A GC is asking me before they send the contract.",
        subject="question about my policy",
        expect_class=["question"], expect_action="send_reply", lang="en")

    # 4. Spanish incomplete request
    add("spanish_incomplete",
        "Hola, necesito un certificado de seguro para un trabajo nuevo. El "
        "certificate holder es Grupo Constructor del Sol. Gracias.",
        subject="certificado de seguro",
        expect_class=["coi_request_incomplete"], expect_action=["send_reply", "do_nothing"],
        lang="es")

    # 5. Spanish complete request
    add("spanish_complete",
        "Hola, envíame un COI por favor.\n\nCertificate holder:\n"
        "Constructora Del Mar LLC\n7800 NW 25th St\nDoral, FL 33122\n\nGracias!",
        subject="COI urgente",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_template="Rolando_s_HVAC_COI_Template.pdf",
        expect_holder="Constructora Del Mar LLC")

    # 6. Junk / marketing
    add("junk_marketing",
        "LAST CHANCE: Grow your HVAC business with our AI-powered lead "
        "platform! 50% off annual plans this week only. Unsubscribe here.",
        subject="50% off - grow your business",
        sender="promo@leadblastpro.com", sender_name="LeadBlast Pro",
        expect_class=["junk"], expect_action="do_nothing")

    # 7. Thank-you
    add("thank_you",
        "Perfect, got it. Thank you!",
        subject="Re: Certificate of Insurance - Rolando's HVAC LLC",
        expect_class=["thank_you"], expect_action="do_nothing")

    # 8. Revision in-thread (prior COI in history)
    prior_thread = [
        graph_msg("m1", CLIENT_SENDER, "Rolando Leyva", "COI request",
                  "Need a COI. Holder: Bengoa Construction Inc, 2200 N Dixie Hwy, "
                  "Hollywood, FL 33020.",
                  sent_dt="2026-07-01T14:00:00Z"),
        graph_msg("m2", config.COI_MAILBOX, "Client Policy Help",
                  "Re: COI request",
                  "Rolando, Attached please find the Certificate of Insurance for "
                  "Rolando's HVAC LLC. Cert holder: Bengoa Construction Inc, 2200 N "
                  "Dixie Hwy, Hollywood, FL 33020. Regards,",
                  sent_dt="2026-07-01T14:05:00Z", has_attachments=True),
    ]
    add("revision_change_address",
        "Actually the GC says the certificate holder address should be their "
        "corporate office: 5900 Stirling Rd, Hollywood, FL 33021. Can you fix "
        "and resend?",
        subject="Re: COI request",
        expect_class=["coi_revision_request"], expect_action="send_pdf",
        thread=prior_thread,
        expect_holder="Bengoa Construction Inc",
        msg_kwargs={"conv_id": "conv-test-1", "sent_dt": "2026-07-01T15:00:00Z"})

    # 9. Third-party recipient
    add("third_party_recipient",
        "Please issue a COI with certificate holder City of Miami Building "
        "Department, 444 SW 2nd Ave, Miami, FL 33130, and send it directly to "
        "permits@miamigov.com. Thanks.",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_third_party="permits@miamigov.com",
        expect_holder="City of Miami Building Department")

    # 10. Multi-holder single COI
    add("multi_holder",
        "Need one COI listing these as certificate holders:\n"
        "Sunset Bay Master Association Inc\nSunset Bay Tower I Condominium Inc\n"
        "Sunset Bay Tower II Condominium Inc\nAll at 2001 Sunset Bay Dr, Miami, FL 33132.",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_holder="Sunset Bay Master Association Inc")

    # 11. Batch — each holder its own address -> separate COIs
    add("batch_two",
        "I need two separate COIs:\n\n1) Miami Dade County, 111 NW 1st St, "
        "Miami, FL 33128\n2) City of Hialeah, 501 Palm Ave, Hialeah, FL 33010",
        expect_class=["coi_request_complete"], expect_action="send_pdf")

    # 12. Absolute Air — default Symbol 789
    add("absolute_default",
        "Hi, COI for Absolute Air Solutions please. Certificate holder: AIO "
        "Realty & Property Management, 3105 NW 107th Ave, Doral, FL 33172.",
        sender="office@absoluteairsolutions.com", sender_name="Absolute Air",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_template="Absolute_Air_Solutions_COI_Symbol_789.pdf")

    # 13. Absolute Air — 'any auto' -> Symbol 1
    add("absolute_any_auto",
        "COI for Absolute Air Solutions. Holder: AIO Realty & Property "
        "Management, 3105 NW 107th Ave, Doral, FL 33172. The contract requires "
        "ANY AUTO coverage on the auto line.",
        sender="office@absoluteairsolutions.com", sender_name="Absolute Air",
        expect_class=["coi_request_complete"], expect_action="send_pdf",
        expect_template="Absolute_Air_Solutions_COI_Symbol_1-_Copy.pdf")

    # 14. Attachment: client forwards an old COI PDF as the source
    old_coi = os.path.join(TEST_ATTACH_DIR, "Rolando's HVAC_Test Entity.pdf")
    if os.path.exists(old_coi):
        add("attachment_old_coi",
            "Please issue a new COI same as the attached one from last year. "
            "Same certificate holder and everything, just current dates.",
            attachments=[file_attachment(old_coi)],
            msg_kwargs={"has_attachments": True},
            expect_class=["coi_request_complete", "coi_complex_review_required",
                          "coi_request_incomplete"],
            expect_action=["send_pdf", "send_complex_review", "send_reply"])

    return scen


# ---------------------------------------------------------------------------
# Reply style checks (locked-in rules from PROJECT_BRIEF)
# ---------------------------------------------------------------------------

def check_reply_style(reply_text, lang):
    problems = []
    if not reply_text:
        return problems
    text = reply_text.strip()
    first_line = text.split("\n")[0]

    if re.match(r"^(hi|hello|hey|dear|hola|buenas)\b", first_line, re.I):
        problems.append(f"greeting used (must be 'Name,'): {first_line[:50]!r}")
    if "," not in first_line[:40]:
        problems.append(f"first line missing 'Name,' opener: {first_line[:50]!r}")
    for dash in ("—", "–"):
        if dash in text:
            problems.append(f"em/en dash found (forbidden): ...{text[max(0, text.find(dash)-20):text.find(dash)+20]!r}...")
    if lang == "en" and not text.rstrip().endswith("Regards,"):
        problems.append(f"English reply must end with 'Regards,' (ends: {text[-40:]!r})")
    if lang == "es":
        if not text.rstrip().endswith("Saludos,"):
            problems.append(f"Spanish reply must end with 'Saludos,' (ends: {text[-40:]!r})")
        if re.search(r"m[áa]ndame", text, re.I):
            problems.append("uses 'mándame' (must be 'envíame')")
        if "certificate holder" not in text.lower():
            pass  # only required when referring to the holder — not enforced
    if "USI Insurance" in text or "786-355-0449" in text:
        problems.append("signature text included (Pipedream/sender appends it)")
    return problems


def check_pdf(path, expect_holder=None):
    problems = []
    doc = fitz.open(path)
    page = doc[0]
    text = page.get_text()
    if TODAY not in text:
        problems.append(f"today's date {TODAY} missing from PDF")
    if "Project name & Address" in text:
        problems.append("placeholder 'Project name & Address' still present")
    if expect_holder:
        norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
        if norm(expect_holder)[:25] not in norm(text):
            problems.append(f"holder {expect_holder!r} not found in PDF")
    doc.close()
    return problems


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    scenarios = build_scenarios()
    if args.only:
        scenarios = [s for s in scenarios if args.only in s["name"]]

    report = []
    fails = 0

    for sc in scenarios:
        name = sc["name"]
        msg = graph_msg(
            f"msg-{name}", sc["sender"], sc["sender_name"], sc["subject"],
            sc["body"], **sc["msg_kwargs"]
        )
        thread = list(sc["thread"] or [])
        thread.append(msg)
        graph = FakeGraph(thread=thread, raw_attachments=sc["attachments"])

        try:
            thread_result = fetch_thread(graph, msg)
            attachments_result = fetch_attachments(graph, msg)
            ai_result = classify(msg, thread_result["messages"], attachments_result)
            parsed = ai_result.get("parsed") or {}
            decision = decide_action(ai_result)
            send_result = execute_action(
                graph, msg, thread_result["messages"], attachments_result,
                ai_result, decision, dry_run=True,
            )
        except Exception as e:
            import traceback
            report.append(f"[CRASH] {name}: {type(e).__name__}: {e}")
            report.append(traceback.format_exc()[-800:])
            fails += 1
            continue

        problems = []
        classification = parsed.get("classification")
        action = decision.get("action")

        if sc["expect_class"] and classification not in sc["expect_class"]:
            problems.append(f"classification={classification!r}, expected {sc['expect_class']}")
        expect_action = sc["expect_action"]
        if expect_action:
            allowed = expect_action if isinstance(expect_action, list) else [expect_action]
            if action not in allowed:
                problems.append(f"action={action!r}, expected {allowed} (reason: {decision.get('reason')})")

        reply_text = decision.get("reply_text") or parsed.get("reply_text")
        if action in ("send_reply", "send_complex_review") or (reply_text and action == "send_reply"):
            problems.extend(check_reply_style(reply_text, sc["lang"]))

        if sc["expect_template"] and parsed.get("template_filename") != sc["expect_template"]:
            problems.append(
                f"template={parsed.get('template_filename')!r}, expected {sc['expect_template']!r}")
        if sc["expect_third_party"]:
            if (parsed.get("send_completed_coi_to") or "").lower() != sc["expect_third_party"]:
                problems.append(
                    f"send_completed_coi_to={parsed.get('send_completed_coi_to')!r}, "
                    f"expected {sc['expect_third_party']!r}")

        pdf_paths = decision.get("pdf_paths") or []
        for p in pdf_paths:
            problems.extend(check_pdf(p, sc["expect_holder"]))
            shutil.copy(p, os.path.join(OUT_DIR, f"{name}__{os.path.basename(p)}"))

        # Persist full artifacts for eyeballing
        with open(os.path.join(OUT_DIR, f"{name}.json"), "w") as fh:
            json.dump({
                "scenario_body": sc["body"],
                "classification": classification,
                "status": parsed.get("status"),
                "action": action,
                "reply_text": reply_text,
                "parsed": parsed,
                "decision_reason": decision.get("reason"),
                "send_result": send_result,
                "pdfs": [os.path.basename(p) for p in pdf_paths],
            }, fh, indent=2, ensure_ascii=False)

        if problems:
            fails += 1
            report.append(f"[FAIL] {name} (class={classification}, action={action})")
            for p in problems:
                report.append(f"         - {p}")
        else:
            extra = f", {len(pdf_paths)} PDF(s)" if pdf_paths else ""
            report.append(f"[OK]   {name} (class={classification}, action={action}{extra})")

    print("\n" + "=" * 72)
    for line in report:
        print(line)
    print("=" * 72)
    print(f"Scenarios: {len(scenarios)}   FAIL: {fails}")
    print(f"Artifacts: {OUT_DIR}")
    with open(os.path.join(OUT_DIR, "report.txt"), "w") as fh:
        fh.write("\n".join(report) + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
