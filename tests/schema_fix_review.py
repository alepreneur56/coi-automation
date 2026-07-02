"""
schema_fix_review.py
--------------------
Regression test for the coverage_analysis schema mismatch: the system
prompt's OUTPUT FORMAT emits required_each_occurrence / client_each_occurrence
per coverage, while build_complex_review_body historically read
required_limit / insured_limit — so complex-review emails rendered blank
limits. Verifies the renderer now accepts BOTH schemas and falls back to
'not stated' when a limit is truly absent.

Usage:
    .venv/bin/python tests/schema_fix_review.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sender import build_complex_review_body

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")


def render(coverage_analysis):
    return build_complex_review_body(
        client_name="Leyva Roland's HVAC Corp",
        request_summary="GC contract attached requiring $2M GL.",
        review_summary="Contract requires $2M GL; client carries $1M.",
        coverage_analysis=coverage_analysis,
        send_completed_coi_to=None,
        original_client_sender="leyva.lrolandoshvac@gmail.com",
        original_client_name="Rolando Leyva",
    )


# --- 1. Prompt schema (copied from coi_system_prompt.txt OUTPUT FORMAT) ----
print("[1] Prompt schema: required_each_occurrence / client_each_occurrence")
prompt_schema = {
    "required_coverages": [
        {"line": "GL", "required_each_occurrence": "2,000,000",
         "client_each_occurrence": "1,000,000", "gap": True,
         "note": "Client GL is $1M; contract requires $2M"},
        {"line": "Pollution Liability", "required_each_occurrence": "1,000,000",
         "client_each_occurrence": None, "gap": True,
         "note": "Client does not carry Pollution Liability"},
    ],
    "required_endorsements": ["CG 20 10", "CG 24 04 12 19"],
    "special_language": "ABC Entity, its officers, employees, agents and "
                        "assigns are listed as Additional Insured.",
    "notes": "Verify AI wording before issuing.",
}
body = render(prompt_schema)
check("GL required limit rendered", "required: 2,000,000" in body, body)
check("GL insured limit rendered", "insured carries: 1,000,000" in body)
check("no blank 'required: |' output", "required:  |" not in body
      and "required: <" not in body)
check("null client limit -> 'not stated'",
      "insured carries: not stated — [GAP]" in body)
check("gap flag preserved", body.count("[GAP]") == 2)
check("endorsements rendered", "CG 20 10" in body)

# --- 2. Legacy renderer schema: required_limit / insured_limit -------------
print("[2] Legacy schema: required_limit / insured_limit")
legacy_schema = {
    "required_coverages": [
        {"line": "GL", "required_limit": "$2,000,000 / occurrence",
         "insured_limit": "$1,000,000 / occurrence", "gap": True},
        {"line": "Auto", "required_limit": "$1,000,000 CSL",
         "insured_limit": "$1,000,000 CSL", "gap": False},
    ],
}
body = render(legacy_schema)
check("required_limit rendered", "required: $2,000,000 / occurrence" in body)
check("insured_limit rendered", "insured carries: $1,000,000 CSL — [OK]" in body)
check("gap/ok flags", "[GAP]" in body and "[OK]" in body)

# --- 3. Empty / missing limits ---------------------------------------------
print("[3] Empty entries -> 'not stated', no crash")
empty_schema = {
    "required_coverages": [
        {"line": "Umbrella"},
        {"line": "WC", "required_each_occurrence": "", "insured_limit": "   "},
    ],
}
body = render(empty_schema)
check("missing keys -> 'not stated'",
      "required: not stated | insured carries: not stated" in body)
check("empty/whitespace values -> 'not stated'",
      body.count("not stated") == 4)

# --- 4. No coverage_analysis at all ----------------------------------------
print("[4] coverage_analysis None/empty")
body = render(None)
check("None coverage_analysis -> no section, no crash",
      "Coverage analysis" not in body and "draft attached" in body)
body = render({})
check("empty dict -> no coverage section, no crash",
      "Required coverages" not in body)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
