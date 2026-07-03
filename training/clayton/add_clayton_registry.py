"""Append Clayton Mechanical to coi_client_registry.json (worktree copy).

Data source of truth: bound COI 070126.pdf (issued 07/01/2026), cross-checked
against Delta Hotels COI.pdf per training/clayton/CLAYTON_ONBOARDING.md.
"""
import json

PATH = "/private/tmp/wt-clayton/coi_client_registry.json"

DOO = (
    "HVAC Contractor License Number: CAC1817147\n"
    "Project name & Address ( If Applicable)\n"
    "General Liability & Commercial Auto policies includes an automatic "
    "Additional Insured endorsement that provides Additional Insured status "
    "to the Certificate Holder as required by written contract. General "
    "Liability policy applies on a primary & non-contributory basis. A "
    "blanket Waiver of Subrogation applies for General Liability, Commercial "
    "Auto, and Employer's Liability policies. Umbrella Liability policy "
    "follows form."
)

clayton = {
    "client_id": "clayton_mechanical",
    "canonical_name": "Clayton Mechanical",
    "aliases": [
        "clayton",
        "clayton mechanical",
        "clayton air and heating",
        "clayton air & heating",
        "clayton air and heating inc",
        "clayton hvac",
    ],
    "insured_address": "2431 Aloma Ave, Suite 124, Winter Park, FL 32792",
    "trade": "HVAC Contractor",
    "license_number": "CAC1817147",
    "templates": [
        {
            "template_id": "clayton_mechanical_full",
            "filename": "Clayton_Mechanical_COI_Template.pdf",
            "description": "GL + Auto + Umbrella + WC (Westfield / Infinity / National Union / Technology)",
            "lines_of_coverage": ["GL", "Auto", "Umbrella", "WC"],
            "is_default": True,
            "selection_rule": "Only template available. Use for all requests.",
            "editable_fields": {
                "certificate_holder": {
                    "editable": True,
                    "placeholder_text": "NAME\nADDRESS\nSTATE, CITY ZIP CODE",
                    "notes": "Replace three-line placeholder with requester info",
                },
                "date": {
                    "editable": True,
                    "current_value": "MM/DD/YYYY",
                    "notes": "Insert today's date",
                },
                "description_of_operations": {
                    "editable": True,
                    "current_value": DOO,
                    "notes": (
                        "If client provides a project name and address, insert it "
                        "after 'Project name & Address ( If Applicable)'. Do not "
                        "alter the rest of the boilerplate language. NOTE: insured "
                        "prints as legal name 'Clayton Air and Heating, Inc' (DBA "
                        "Clayton Mechanical)."
                    ),
                },
            },
            "carriers": [
                {"letter": "A", "name": "Westfield Insurance Company", "naic": "24112"},
                {"letter": "B", "name": "Infinity Assurance Insurance Company", "naic": "39497"},
                {"letter": "C", "name": "National Union Fire Insurance Company of Pittsburgh, PA.", "naic": "19445"},
                {"letter": "D", "name": "Technology Insurance Company", "naic": "42376"},
            ],
            "policies": [
                {
                    "line": "Commercial General Liability",
                    "insurer_letter": "A",
                    "policy_number": "CWP 530335F",
                    "eff_date": "06/01/2026",
                    "exp_date": "06/01/2027",
                    "addl_insured": True,
                    "subr_wvd": True,
                    "occur": True,
                    "aggregate_basis": "PRO-JECT",
                    "limits": {
                        "each_occurrence": "1,000,000",
                        "damage_to_rented_premises": "500,000",
                        "med_exp": "5,000",
                        "personal_adv_injury": "1,000,000",
                        "general_aggregate": "2,000,000",
                        "products_comp_op_agg": "2,000,000",
                    },
                },
                {
                    "line": "Commercial Auto",
                    "insurer_letter": "B",
                    "policy_number": "CA945173MGA",
                    "eff_date": "06/01/2026",
                    "exp_date": "06/01/2027",
                    "addl_insured": True,
                    "subr_wvd": True,
                    "auto_type": "Any Auto",
                    "limits": {"combined_single_limit": "1,000,000"},
                },
                {
                    "line": "Umbrella Liability",
                    "insurer_letter": "C",
                    "policy_number": "47329390",
                    "eff_date": "06/01/2026",
                    "exp_date": "06/01/2027",
                    "addl_insured": True,
                    "subr_wvd": True,
                    "occur": True,
                    "limits": {"each_occurrence": "2,000,000", "aggregate": "2,000,000"},
                },
                {
                    "line": "Workers Compensation",
                    "insurer_letter": "D",
                    "policy_number": "13705262",
                    "eff_date": "06/01/2026",
                    "exp_date": "06/01/2027",
                    "subr_wvd": True,
                    "officer_member_excluded": True,
                    "limits": {
                        "el_each_accident": "1,000,000",
                        "el_disease_ea_employee": "1,000,000",
                        "el_disease_policy_limit": "1,000,000",
                    },
                },
            ],
        }
    ],
}

with open(PATH) as f:
    reg = json.load(f)

assert not any(c["client_id"] == "clayton_mechanical" for c in reg["clients"]), "already present"
reg["clients"].append(clayton)

with open(PATH, "w") as f:
    json.dump(reg, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"clients now: {len(reg['clients'])}")
