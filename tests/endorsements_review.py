"""
endorsements_review.py
----------------------
Offline harness for A9 (endorsement documentation attachments). NO API calls,
NO mailbox — everything runs against endorsements.py, pipeline.decide_action,
and sender.execute_action in dry-run with a fake Graph client.

Covers:
  - detection cases (form numbers, phrases, line inference, conservatism)
  - attach decision matrix (blanket+PDF -> attach; blanket no PDF -> note;
    scheduled -> flag, never attach; none/unverified -> note; unknown client)
  - the Rolando's HVAC scheduled-skip hard rule (auto AI/WOS/P&NC)
  - the AJF no-GAF hard rule (nothing attachable references GAF)
  - pipeline + sender wiring behind ENDORSEMENTS_ENABLED, incl. flag-off
    inertness (TEST_MODE behavior unchanged)

Usage:
    .venv/bin/python tests/endorsements_review.py [--only SUBSTR]
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import endorsements
from pipeline import decide_action
from sender import build_endorsement_section, execute_action

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "endorsements_output")

REPORT = []
FAILS = [0]


def check(name, condition, detail=""):
    if condition:
        REPORT.append(f"[OK]   {name}")
    else:
        FAILS[0] += 1
        REPORT.append(f"[FAIL] {name}" + (f" :: {detail}" if detail else ""))


def types_lines(demands):
    return {(d["type"], d["line"]) for d in demands}


# ---------------------------------------------------------------------------
# Fake Graph (sender dry-run capture)
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


def fake_email(sender="leyva.lrolandoshvac@gmail.com", name="Rolando Leyva"):
    return {
        "id": "msg-endorse-test",
        "subject": "COI request",
        "from": {"emailAddress": {"address": sender, "name": name}},
        "toRecipients": [{"emailAddress": {"address": config.COI_MAILBOX}}],
        "ccRecipients": [],
        "body": {"contentType": "text", "content": "test"},
    }


# ---------------------------------------------------------------------------
# 1. Detection
# ---------------------------------------------------------------------------

def run_detection_tests():
    d = endorsements.detect_demanded_endorsements

    # 1.1 Form numbers in required_endorsements
    demands = d({"coverage_analysis": {"required_endorsements": ["CG 20 10", "CG 24 04 12 19"]}})
    check("detect_form_cg2010_cg2404",
          types_lines(demands) == {("additional_insured", "GL"), ("waiver_of_subrogation", "GL")},
          str(demands))

    # 1.2 WC waiver form
    demands = d({"coverage_analysis": {"required_endorsements": ["WC 00 03 13"]}})
    check("detect_form_wc000313",
          types_lines(demands) == {("waiver_of_subrogation", "WC")}, str(demands))

    # 1.3 Auto AI form
    demands = d({"coverage_analysis": {"required_endorsements": ["CA 20 48"]}})
    check("detect_form_ca2048",
          types_lines(demands) == {("additional_insured", "Auto")}, str(demands))

    # 1.4 Per-project aggregate form + phrase
    demands = d({"coverage_analysis": {"required_endorsements": ["CG 25 03"],
                 "special_language": "General aggregate limit shall apply on a per-project basis."}})
    check("detect_per_project_aggregate",
          ("per_project_aggregate", "GL") in types_lines(demands), str(demands))

    # 1.5 special_language AI/PNC/WOS phrases
    demands = d({"coverage_analysis": {"special_language":
                 "ABC Entity is named additional insured on a primary and "
                 "non-contributory basis with waiver of subrogation. Provide "
                 "a copy of the additional insured endorsement."}})
    got = {t for t, _ in types_lines(demands)}
    check("detect_phrases_ai_pnc_wos",
          got == {"additional_insured", "primary_noncontributory", "waiver_of_subrogation"},
          str(demands))

    # 1.6 Notice of cancellation (30 days)
    demands = d({}, ["Contractor's policies shall provide thirty (30) days "
                     "written notice of cancellation to the Owner."])
    check("detect_notice_of_cancellation",
          {t for t, _ in types_lines(demands)} == {"notice_of_cancellation"}, str(demands))

    # 1.7 Line inference: auto-specific waiver demand
    demands = d({"coverage_analysis": {"special_language":
                 "A waiver of subrogation endorsement is required on the "
                 "automobile liability policy."}})
    check("detect_line_auto_wos",
          ("waiver_of_subrogation", "Auto") in types_lines(demands), str(demands))

    # 1.8 Ambiguous lines -> None (any)
    demands = d({"coverage_analysis": {"special_language":
                 "Waiver of subrogation applies to General Liability, Auto and "
                 "Umbrella policies."}})
    check("detect_line_ambiguous_is_none",
          types_lines(demands) == {("waiver_of_subrogation", None)}, str(demands))

    # 1.9 CONSERVATISM: a plain complete request produces zero demands
    demands = d({
        "classification": "coi_request_complete", "status": "ready",
        "client_id": "rolandos_hvac",
        "certificate_holder": {"name": "Bengoa Construction Inc",
                               "address_line_1": "2200 N Dixie Hwy",
                               "city": "Hollywood", "state": "FL", "zip": "33020"},
    })
    check("detect_plain_request_no_demands", demands == [], str(demands))

    # 1.10 Requirements-doc text drives detection too
    demands = d({}, ["INSURANCE REQUIREMENTS: GL $1M per occurrence. "
                     "Certificate must include copy of the blanket additional "
                     "insured endorsement and the CG 24 04."])
    check("detect_requirements_doc_text",
          {t for t, _ in types_lines(demands)} >= {"additional_insured", "waiver_of_subrogation"},
          str(demands))

    # 1.11 extract_requirements_texts: word/excel extracted_text passthrough
    texts = endorsements.extract_requirements_texts({"attachments": [
        {"kind": "text", "name": "reqs.docx",
         "extracted_text": "Waiver of subrogation endorsement required."},
        {"kind": "image", "name": "photo.jpg"},
    ]})
    check("extract_texts_word_passthrough",
          len(texts) == 1 and "Waiver" in texts[0], str(texts))


# ---------------------------------------------------------------------------
# 2. Attach decision matrix
# ---------------------------------------------------------------------------

def run_attach_tests(tmp_dir):
    reg = endorsements.load_endorsement_registry()

    def seed_pdf(client_id, filename):
        cdir = os.path.join(tmp_dir, client_id)
        os.makedirs(cdir, exist_ok=True)
        path = os.path.join(cdir, filename)
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 dummy endorsement\n%%EOF")
        return path

    # Seed AJF GL trio + Rolando GL AI. Deliberately ALSO seed a rogue file
    # in rolandos_hvac to prove scheduled entries are skipped even if a file
    # exists (scheduled entries have pdf_filename null, but belt-and-braces).
    seed_pdf("ajf_roofing", "ajf_gl_ai.pdf")
    seed_pdf("ajf_roofing", "ajf_gl_pnc.pdf")
    seed_pdf("ajf_roofing", "ajf_gl_wos.pdf")
    seed_pdf("rolandos_hvac", "rolandos_gl_ai.pdf")
    seed_pdf("rolandos_hvac", "rolandos_auto_ai.pdf")  # rogue — must be ignored

    da = lambda cid, demands: endorsements.decide_attachments(
        cid, demands, registry=reg, endorsements_dir=tmp_dir)

    # 2.1 AJF: AI+PNC+WOS demanded (no line) -> GL trio attaches; auto/WC/
    #     umbrella blanket entries lack PDFs -> notes, not attachments
    demands = [{"type": "additional_insured", "line": None, "evidence": "t"},
               {"type": "primary_noncontributory", "line": None, "evidence": "t"},
               {"type": "waiver_of_subrogation", "line": None, "evidence": "t"}]
    plan = da("ajf_roofing", demands)
    attached_ids = {a["entry"]["endorsement_id"] for a in plan["attach"]}
    check("ajf_gl_trio_attaches",
          attached_ids == {"ajf_gl_ai", "ajf_gl_pnc", "ajf_gl_wos"}, str(attached_ids))
    check("ajf_missing_pdfs_noted",
          any("ajf_auto_ai" in n for n in plan["notes"])
          and any("ajf_wc_wos" in n for n in plan["notes"]), str(plan["notes"]))
    check("ajf_no_scheduled_flags", plan["scheduled_flags"] == [], str(plan["scheduled_flags"]))

    # 2.2 HARD RULE — no GAF anywhere in anything attachable/automated.
    all_plan_text = json.dumps(plan).lower()
    check("ajf_no_gaf_in_plan", "gaf" not in all_plan_text)
    entries_text = json.dumps(
        [e for c in reg["clients"].values() for e in c.get("endorsements", [])]
    ).lower()
    check("registry_no_gaf_in_any_endorsement_entry", "gaf" not in entries_text)
    # A GAF-mentioning requirements doc must yield only generic demands —
    # detection is holder-agnostic by construction.
    demands = endorsements.detect_demanded_endorsements(
        {}, ["GAF Materials Corporation must be named additional insured; "
             "provide the additional insured endorsement."])
    check("gaf_requirements_doc_yields_generic_demand",
          {t for t, _ in types_lines(demands)} == {"additional_insured"}
          and all("gaf" not in (d["type"] + str(d["line"])).lower() for d in demands),
          str(demands))

    # 2.3 HARD RULE — Rolando's auto AI demanded -> scheduled flag, NO attach
    #     (even though a rogue rolandos_auto_ai.pdf exists on disk)
    plan = da("rolandos_hvac", [{"type": "additional_insured", "line": "Auto", "evidence": "t"}])
    check("rolandos_auto_ai_never_attached", plan["attach"] == [], str(plan["attach"]))
    check("rolandos_auto_ai_scheduled_flag",
          len(plan["scheduled_flags"]) == 1
          and plan["scheduled_flags"][0]["type"] == "scheduled_endorsement_carrier_request_needed"
          and "carrier endorsement request" in plan["scheduled_flags"][0]["description"],
          str(plan["scheduled_flags"]))

    # 2.4 Rolando's line-unspecified AI demand -> GL attaches AND auto flags
    plan = da("rolandos_hvac", [{"type": "additional_insured", "line": None, "evidence": "t"}])
    check("rolandos_any_ai_gl_attach_auto_flag",
          {a["entry"]["endorsement_id"] for a in plan["attach"]} == {"rolandos_gl_ai"}
          and len(plan["scheduled_flags"]) == 1, str(plan))

    # 2.5 Rolando's auto WOS + PNC also scheduled
    plan = da("rolandos_hvac", [
        {"type": "waiver_of_subrogation", "line": "Auto", "evidence": "t"},
        {"type": "primary_noncontributory", "line": "Auto", "evidence": "t"}])
    check("rolandos_auto_wos_pnc_scheduled",
          plan["attach"] == [] and len(plan["scheduled_flags"]) == 2, str(plan))

    # 2.6 EMP3 WC waiver demanded -> unverified -> note (LUBA pattern)
    plan = da("emp3_solutions", [{"type": "waiver_of_subrogation", "line": "WC", "evidence": "t"}])
    check("emp3_wc_wos_unverified_note",
          plan["attach"] == [] and plan["scheduled_flags"] == []
          and any("unverified" in n for n in plan["notes"]), str(plan))

    # 2.7 305 Power excess WOS demanded -> status none -> note (template bug)
    plan = da("305_power_corp", [{"type": "waiver_of_subrogation", "line": "Excess", "evidence": "t"}])
    check("305_excess_wos_none_note",
          plan["attach"] == [] and any("'none'" in n for n in plan["notes"]), str(plan))

    # 2.8 G&D WC waiver -> none; auto AI -> unverified
    plan = da("gd_mechanical", [
        {"type": "waiver_of_subrogation", "line": "WC", "evidence": "t"},
        {"type": "additional_insured", "line": "Auto", "evidence": "t"}])
    check("gd_wc_none_auto_unverified",
          plan["attach"] == [] and len(plan["notes"]) == 2, str(plan))

    # 2.9 Blanket but PDF not on file -> missing-pdf note (Central Comfort)
    plan = da("central_comfort_ac", [{"type": "waiver_of_subrogation", "line": "WC", "evidence": "t"}])
    check("central_wc_wos_missing_pdf_note",
          plan["attach"] == [] and any("no" in n.lower() and "pdf" in n.lower() for n in plan["notes"]),
          str(plan))

    # 2.10 Clayton (no inventory yet) -> nothing on file note
    plan = da("clayton_mechanical", [{"type": "additional_insured", "line": "GL", "evidence": "t"}])
    check("clayton_no_inventory_note",
          plan["attach"] == [] and any("no endorsement of" in n for n in plan["notes"]), str(plan))

    # 2.11 Unknown client -> graceful note, no crash
    plan = da("nonexistent_client", [{"type": "additional_insured", "line": None, "evidence": "t"}])
    check("unknown_client_graceful",
          plan["attach"] == [] and any("No endorsement inventory" in n for n in plan["notes"]),
          str(plan))

    # 2.12 No demands -> empty plan
    plan = da("ajf_roofing", [])
    check("no_demands_empty_plan",
          plan["attach"] == [] and plan["scheduled_flags"] == [] and plan["notes"] == [])


# ---------------------------------------------------------------------------
# 3. Pipeline + sender wiring (offline; real coi_engine PDF generation)
# ---------------------------------------------------------------------------

def rolandos_complex_parsed():
    """A complex-review parsed payload for Rolando's demanding GL AI/WOS/PNC
    plus an AUTO additional-insured endorsement (the scheduled one)."""
    return {
        "classification": "coi_complex_review_required",
        "reply_text": "Rolando,\n\nThanks for the request. Alejandro is "
                      "reviewing the requirements and will get back to you "
                      "shortly.\n\nRegards,",
        "original_request_summary": "GC requirements demand endorsement copies.",
        "status": "ready",
        "client_id": "rolandos_hvac",
        "client_canonical_name": "Rolando's HVAC LLC",
        "template_id": "rolandos_hvac_gl_auto",
        "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
        "confidence": "high",
        "confidence_notes": "sender match",
        "certificate_holder": {
            "name": "Bengoa Construction Inc",
            "address_line_1": "2200 N Dixie Hwy",
            "address_line_2": None,
            "city": "Hollywood", "state": "FL", "zip": "33020",
        },
        "date_to_insert": None,
        "project_name": None, "project_address": None, "project_unit": None,
        "is_permit": False,
        "send_completed_coi_to": None,
        "flags": [],
        "review_summary": "Requirements demand endorsement copies including "
                          "an additional insured endorsement on the automobile "
                          "liability policy.",
        "coverage_analysis": {
            "required_coverages": [],
            "required_endorsements": ["CG 20 10", "CG 24 04", "CG 20 01", "CA 20 48"],
            "special_language": None,
            "notes": None,
        },
        "edits_to_make": [],
    }


def run_wiring_tests(tmp_dir):
    ai_result = {"parsed": rolandos_complex_parsed(), "sender": "leyva.lrolandoshvac@gmail.com"}

    # 3.1 Flag OFF (the shipped default): decision carries NO endorsement keys
    config.ENDORSEMENTS_ENABLED = False
    decision = decide_action(json.loads(json.dumps(ai_result)))
    check("flag_off_no_endorsement_keys",
          decision.get("action") == "send_complex_review"
          and not any(k.startswith("endorsement") for k in decision),
          str({k: v for k, v in decision.items() if k != "pdf_paths"}))

    # 3.2 Flag ON: complex review decision gains attach paths + scheduled flag
    config.ENDORSEMENTS_ENABLED = True
    old_dir = config.ENDORSEMENTS_DIR
    config.ENDORSEMENTS_DIR = tmp_dir
    endorsements.ENDORSEMENT_REGISTRY_PATH = endorsements.ENDORSEMENT_REGISTRY_PATH  # unchanged
    try:
        decision = decide_action(json.loads(json.dumps(ai_result)))
        attach_names = [os.path.basename(p) for p in decision.get("endorsement_pdf_paths") or []]
        check("flag_on_complex_attaches_gl",
              decision.get("action") == "send_complex_review"
              and "rolandos_gl_ai.pdf" in attach_names
              and "rolandos_auto_ai.pdf" not in attach_names,
              str(attach_names))
        check("flag_on_complex_scheduled_flag",
              len(decision.get("endorsement_flags") or []) == 1
              and "carrier endorsement request" in decision["endorsement_flags"][0]["description"],
              str(decision.get("endorsement_flags")))

        # 3.3 Sender complex-review dry run: review body gets the section,
        #     endorsement PDFs ride the review email, client ack unchanged
        graph = FakeGraph()
        email = fake_email()
        result = execute_action(graph, email, [email], {"attachments": []},
                                ai_result, decision, dry_run=True)
        check("sender_complex_dry_run_endorsement_fields",
              result.get("endorsement_attachments") == ["rolandos_gl_ai.pdf"]
              and result.get("endorsement_flag_count") == 1,
              str(result))

        # 3.4 build_endorsement_section renders all three buckets
        section = build_endorsement_section(
            ["rolandos_gl_ai.pdf"],
            decision.get("endorsement_flags") or [],
            ["some note"])
        check("endorsement_section_renders",
              "rolandos_gl_ai.pdf" in section
              and "NEEDS CARRIER ENDORSEMENT REQUEST" in section
              and "some note" in section, section[:200])

        # 3.5 send_pdf path: endorsement PDFs attach to delivery email and a
        #     producer note fires for the scheduled flag (dry run)
        pdf_decision = dict(decision)
        pdf_decision["action"] = "send_pdf"
        pdf_decision["is_revision"] = False
        result = execute_action(graph, email, [email], {"attachments": []},
                                ai_result, pdf_decision, dry_run=True)
        check("sender_send_pdf_dry_run_endorsements",
              result.get("endorsement_attachments") == ["rolandos_gl_ai.pdf"]
              and (result.get("producer_endorsement_note") or {}).get("flag_count") == 1,
              str(result))

        # 3.6 send_pdf REAL send against FakeGraph: attachment names include
        #     the endorsement PDF; producer note email goes out via sendMail
        graph2 = FakeGraph()
        result = execute_action(graph2, email, [email], {"attachments": []},
                                ai_result, pdf_decision, dry_run=False)
        reply_msgs = [m for kind, _, m in graph2.sent if kind == "reply"]
        note_msgs = [m for kind, _, m in graph2.sent if kind == "sendMail"]
        att_names = {a.get("name") for m in reply_msgs for a in m.get("attachments", [])}
        check("sender_send_pdf_real_attaches_endorsement",
              "rolandos_gl_ai.pdf" in att_names, str(att_names))
        check("sender_send_pdf_producer_note_sent",
              len(note_msgs) == 1
              and "Endorsement attention needed" in note_msgs[0].get("subject", "")
              and note_msgs[0]["toRecipients"][0]["emailAddress"]["address"] == config.PRODUCER_CC_EMAIL,
              str([m.get("subject") for m in note_msgs]))
        check("sender_send_pdf_test_mode_redirect_intact",
              reply_msgs[0]["toRecipients"][0]["emailAddress"]["address"]
              == (config.TEST_REDIRECT_TO if config.TEST_MODE else "leyva.lrolandoshvac@gmail.com"),
              str(reply_msgs[0]["toRecipients"]))

        # 3.7 Plain complete request with flag ON -> no demands -> no keys
        plain = {
            "parsed": {
                "classification": "coi_request_complete", "reply_text": None,
                "status": "ready", "client_id": "rolandos_hvac",
                "client_canonical_name": "Rolando's HVAC LLC",
                "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
                "certificate_holder": {"name": "Bengoa Construction Inc",
                                       "address_line_1": "2200 N Dixie Hwy",
                                       "city": "Hollywood", "state": "FL", "zip": "33020"},
                "project_name": None, "project_address": None,
            },
            "sender": "leyva.lrolandoshvac@gmail.com",
        }
        decision = decide_action(json.loads(json.dumps(plain)))
        check("flag_on_plain_request_inert",
              decision.get("action") == "send_pdf"
              and not any(k.startswith("endorsement") for k in decision),
              str({k: v for k, v in decision.items() if k != "pdf_paths"}))
    finally:
        config.ENDORSEMENTS_ENABLED = False
        config.ENDORSEMENTS_DIR = old_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="endorsements_test_")
    try:
        run_detection_tests()
        run_attach_tests(tmp_dir)
        run_wiring_tests(tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    report = REPORT
    if args.only:
        report = [l for l in report if args.only in l]

    print("\n" + "=" * 72)
    for line in report:
        print(line)
    print("=" * 72)
    print(f"Checks: {len(REPORT)}   FAIL: {FAILS[0]}")
    with open(os.path.join(OUT_DIR, "report.txt"), "w") as fh:
        fh.write("\n".join(REPORT) + "\n")
    return 1 if FAILS[0] else 0


if __name__ == "__main__":
    sys.exit(main())
