"""
engine_review.py
----------------
Rapid-iteration harness for coi_engine. Runs a battery of scenarios, then for
every produced COI:

  1. Renders labeled review images: template crop vs output crop for the
     three edit zones (date box, certificate holder box, description of
     operations) so a human (or Claude) can eyeball them fast.
  2. Runs programmatic checks: date inserted, placeholders gone, text inside
     safe boundaries, plural boilerplate, border line-art not eaten by
     redactions.

Usage:
    .venv/bin/python tests/engine_review.py [--out DIR] [--only NAME_SUBSTR]

Review images + a checks report land in DIR (default: tests/review_output).
"""

import argparse
import io
import json
import os
import shutil
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from PIL import Image, ImageDraw

from coi_engine import process_request, HOLDER_SAFE_RIGHT, DESC_SAFE_RIGHT

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE, "templates")

TODAY = date.today().strftime("%m/%d/%Y")

# Crop zones (PDF points): (name, rect, dpi)
ZONES = [
    ("date_box", fitz.Rect(495, 15, 600, 58), 300),
    ("holder_box", fitz.Rect(12, 650, 315, 758), 200),
    ("desc_of_ops", fitz.Rect(12, 535, 600, 665), 200),
]

ALL_TEMPLATES = [
    ("305 Power Corp", "305_Power_Corp_COI_Template.pdf"),
    ("Rolando's HVAC LLC", "Rolando_s_HVAC_COI_Template.pdf"),
    ("EMP 3 Solutions, Inc", "EMP_3_Solutions_Template.pdf"),
    ("Central Comfort Air Conditioning", "Central_Comfort_Air_Conditioning_Inc_COI.pdf"),
    ("G & D Mechanical Services LLC", "G___D_Mechanical_Services_COI_Template.pdf"),
    ("Absolute Air Solutions LLC", "Absolute_Air_Solutions_COI_Symbol_789.pdf"),
    ("Absolute Air Solutions LLC", "Absolute_Air_Solutions_COI_Symbol_1-_Copy.pdf"),
    ("AJF Roofing, Inc.", "AJF_Roofing_Inc_COI_Template.pdf"),
    ("APOGEE HVAC SOLUTIONS LLC", "Apogee_HVAC_Solutions_COI_Template.pdf"),
]

HOLDER = {
    "name": "Test Entity Construction Group, Inc.",
    "address_line_1": "9400 S Dadeland Blvd",
    "address_line_2": None,
    "city": "Miami", "state": "FL", "zip": "33156",
}


def simple_req(client, template, **kw):
    req = {
        "status": "ready",
        "classification": "coi_request_complete",
        "client_canonical_name": client,
        "template_filename": template,
        "request_type": "single",
        "certificate_holder": dict(HOLDER),
        "project_name": None,
        "project_address": None,
    }
    req.update(kw)
    return req


def build_scenarios():
    scen = []
    # 1. Every template, simple request (the bread-and-butter path)
    for client, tpl in ALL_TEMPLATES:
        scen.append((f"simple__{tpl[:-4]}", simple_req(client, tpl)))

    r = ("Rolando's HVAC LLC", "Rolando_s_HVAC_COI_Template.pdf")

    # 2. Project variations
    scen.append(("proj_address_only", simple_req(*r, project_address="8950 SW 74th Ct, Miami, FL 33156")))
    scen.append(("proj_name_and_address", simple_req(
        *r, project_name="Dadeland Office Tower Renovation",
        project_address="9400 S Dadeland Blvd, Miami, FL 33156")))
    scen.append(("proj_long_wraps", simple_req(
        *r, project_name="Dadeland Office Tower Phase II Mechanical Systems Replacement and Upgrade Project",
        project_address="9400 South Dadeland Boulevard, Suite 600, Miami, Florida 33156")))
    scen.append(("proj_unit_jobsite", simple_req(*r, project_unit="1203",
                 project_address="2900 NE 7th Ave, Miami, FL 33137")))
    scen.append(("proj_permit", simple_req(*r, is_permit=True,
                 project_address="450 SW 8th St, Miami, FL 33130")))

    # 3. Holder shapes
    long_holder = dict(HOLDER)
    long_holder["name"] = ("The School Board of Miami-Dade County, Florida, its members, "
                           "officers, employees, agents and architects")
    scen.append(("holder_very_long_name", simple_req(*r, certificate_holder=long_holder)))

    suite_holder = dict(HOLDER)
    suite_holder["address_line_2"] = "Suite 1200"
    scen.append(("holder_addr_line_2", simple_req(*r, certificate_holder=suite_holder)))

    # 4. Multi-entity, one COI (plural boilerplate) — on EVERY template.
    #    Five templates store 'Certificate Holder' as an isolated cyan span;
    #    the plural rewrite must not eat the sibling spans on that line.
    for client, tpl in ALL_TEMPLATES:
        multi = simple_req(client, tpl)
        multi["certificate_holder_lines"] = [
            "Brickell Tower Condominium Association",
            "Coconut Grove Residences HOA",
            "Coral Gables Villas LLC",
            HOLDER["address_line_1"],
            "Miami, FL, 33156",
        ]
        scen.append((f"multi3__{tpl[:-4]}", multi))

    # 4b. Long project on 305 Power (template with vertically-overlapping
    #     spans) + combined multi-holder AND wrapping project (the old code
    #     had two colliding redact passes for this).
    scen.append(("proj_long_305power", simple_req(
        "305 Power Corp", "305_Power_Corp_COI_Template.pdf",
        project_name="Brickell City Centre Electrical Infrastructure Modernization Program Phase III",
        project_address="701 S Miami Ave, Miami, FL 33131")))
    combo = simple_req(*r,
        project_name="Dadeland Office Tower Phase II Mechanical Systems Replacement and Upgrade Project",
        project_address="9400 South Dadeland Boulevard, Suite 600, Miami, Florida 33156")
    combo["certificate_holder_lines"] = [
        "Brickell Tower Condominium Association",
        "Coconut Grove Residences HOA",
        "Coral Gables Villas LLC",
        HOLDER["address_line_1"],
        "Miami, FL, 33156",
    ]
    scen.append(("multi3_plus_long_proj", combo))

    # 4c. Input robustness: accents, smart punctuation, absurd unbroken names
    accents = dict(HOLDER)
    accents["name"] = "Construcciones Peña & Muñoz S.A. — José María Núñez"
    scen.append(("holder_accents_smartdash", simple_req(*r, certificate_holder=accents)))
    smart = dict(HOLDER)
    smart["name"] = "Rolando’s “Premier” Contracting LLC"
    scen.append(("holder_smart_quotes", simple_req(*r, certificate_holder=smart)))
    monster = dict(HOLDER)
    monster["name"] = "SUPERCALIFRAGILISTICEXPIALIDOCIOUSHOLDINGSANDDEVELOPMENTCORPORATIONOFAMERICALLC"
    scen.append(("holder_unbroken_80char", simple_req(*r, certificate_holder=monster)))

    # 4d. Multi-entity where the lines' address formatting differs from the
    #     certificate_holder reconstruction ("FL 33154" vs "FL, 33154") —
    #     the city line must NOT leak into the entity list (2026-07-02 bug)
    fmt = simple_req("Central Comfort Air Conditioning",
                     "Central_Comfort_Air_Conditioning_Inc_COI.pdf")
    fmt["certificate_holder"] = {
        "name": "Belle Harbour Condominium Association, Inc.",
        "address_line_1": "9200 Collins Avenue", "address_line_2": None,
        "city": "Miami Beach", "state": "FL", "zip": "33154",
    }
    fmt["certificate_holder_lines"] = [
        "Belle Harbour Condominium Association, Inc.",
        "Keystone Property Management & Consulting, LLC",
        "9200 Collins Avenue",
        "Miami Beach, FL 33154",
    ]
    scen.append(("multi_entity_addr_format_mismatch", fmt))

    # 5. Multi-entity overflow -> split into multiple COIs
    big = simple_req(*r)
    big["certificate_holder_lines"] = [
        f"Overflow Test Entity Number {i} Condominium Association of Greater Miami, Inc." for i in range(1, 15)
    ] + [HOLDER["address_line_1"], "Miami, FL, 33156"]
    scen.append(("multi_entity_split_14", big))

    # 6. Batch (3 individual COIs)
    batch = {
        "status": "ready", "request_type": "batch",
        "client_canonical_name": r[0], "template_filename": r[1],
        "batch_cois": [
            {"certificate_holder": {"name": "Miami Dade County", "address_line_1": "111 NW 1st St",
                                    "city": "Miami", "state": "FL", "zip": "33128"},
             "project_name": None, "project_address": None},
            {"certificate_holder": {"name": "Bengoa Construction Inc", "address_line_1": "2200 N Dixie Hwy",
                                    "city": "Hollywood", "state": "FL", "zip": "33020"},
             "project_address": "600 Marina Blvd, Hollywood, FL 33019"},
            {"certificate_holder": {"name": "City of Coral Gables Building Department",
                                    "address_line_1": "405 Biltmore Way",
                                    "city": "Coral Gables", "state": "FL", "zip": "33134"},
             "is_permit": True, "project_address": "1500 Sunset Dr, Coral Gables, FL 33143"},
        ],
    }
    scen.append(("batch_3", batch))
    return scen


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_zone(pdf_path, rect, dpi):
    doc = fitz.open(pdf_path)
    try:
        zoom = dpi / 72.0
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png")))
    finally:
        doc.close()


def make_review_image(template_path, output_path, save_to):
    """One tall image per COI: for each zone, template crop on top,
    output crop below, labeled."""
    panels = []
    for zone_name, rect, dpi in ZONES:
        for label, path in (("TEMPLATE", template_path), ("OUTPUT", output_path)):
            img = render_zone(path, rect, dpi)
            labeled = Image.new("RGB", (img.width, img.height + 22), "white")
            d = ImageDraw.Draw(labeled)
            d.rectangle([0, 0, img.width, 20], fill=(30, 30, 30) if label == "OUTPUT" else (100, 100, 100))
            d.text((6, 4), f"{label} — {zone_name}", fill="white")
            labeled.paste(img, (0, 22))
            panels.append(labeled)

    width = max(p.width for p in panels)
    height = sum(p.height + 8 for p in panels)
    sheet = Image.new("RGB", (width, height), (220, 220, 220))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y))
        y += p.height + 8
    sheet.save(save_to)


# ---------------------------------------------------------------------------
# Programmatic checks
# ---------------------------------------------------------------------------

def _spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b["lines"]:
            for sp in line["spans"]:
                out.append(sp)
    return out


def _drawings_in(drawings, rect):
    n = 0
    for d in drawings:
        r = d.get("rect")
        if r and fitz.Rect(r).intersects(rect):
            n += 1
    return n


def check_output(template_path, output_path, req, holder_lines_expected=None):
    """Returns list of (severity, message). severity: FAIL or WARN."""
    problems = []
    tdoc = fitz.open(template_path)
    odoc = fitz.open(output_path)
    tpage, opage = tdoc[0], odoc[0]
    text = opage.get_text()
    spans = _spans(opage)

    # Spans WE inserted = spans not present in the template at the same spot.
    # The template's own static text (labels, headers) is never our problem.
    template_keys = {
        (round(s["bbox"][0], 1), round(s["bbox"][1], 1), s["text"]) for s in _spans(tpage)
    }
    new_spans = [
        s for s in spans
        if (round(s["bbox"][0], 1), round(s["bbox"][1], 1), s["text"]) not in template_keys
    ]

    # 1. Date inserted, no leftover placeholder/stale date in the date zone
    date_zone = fitz.Rect(495, 20, 600, 52)
    date_texts = [s["text"].strip() for s in spans if fitz.Rect(s["bbox"]).intersects(date_zone)]
    if TODAY not in " ".join(date_texts):
        problems.append(("FAIL", f"today's date {TODAY} not found in date zone (found: {date_texts})"))
    stale = [
        t for t in date_texts
        if t not in ("", TODAY) and "DATE (MM/DD/YYYY)" not in t and ("/" in t or "MM" in t)
    ]
    if stale:
        problems.append(("FAIL", f"stale date text left in date zone: {stale}"))

    # 2. Project placeholder handling
    has_project = bool(
        req.get("project_name") or req.get("project_address") or req.get("project_unit")
        or req.get("is_permit")
    )
    if "Project name & Address" in text:
        problems.append(("FAIL", "placeholder 'Project name & Address' still present"))
    if req.get("request_type") != "batch" and has_project:
        for key, prefix in (("project_address", None),):
            pass
        # sanity: some 'Project' line should exist
        if "Project" not in text and "Permit" not in text:
            problems.append(("FAIL", "expected a project/permit line, none found"))

    # 3. Safe boundaries — no span WE inserted may cross the box borders
    holder_zone = fitz.Rect(14, 660, 312, 752)
    desc_zone = fitz.Rect(14, 538, 600, 660)
    for s in new_spans:
        r = fitz.Rect(s["bbox"])
        if r.intersects(holder_zone) and r.x1 > HOLDER_SAFE_RIGHT + 1.0:
            problems.append(("FAIL", f"holder text crosses right border (x1={r.x1:.1f}): {s['text'][:60]!r}"))
        if r.intersects(desc_zone) and r.x1 > DESC_SAFE_RIGHT + 1.0:
            problems.append(("FAIL", f"desc text crosses right border (x1={r.x1:.1f}): {s['text'][:60]!r}"))
        # holder text must stay inside the box vertically
        if fitz.Rect(14, 655, 312, 760).intersects(r) and s["text"].strip() and r.y1 > 749.5:
            problems.append(("FAIL", f"holder text below box bottom (y1={r.y1:.1f}): {s['text'][:60]!r}"))
        # inserted DoO text must not spill past the box bottom into the
        # CERTIFICATE HOLDER / CANCELLATION headers (y≈653.8)
        if r.y0 > 560 and r.y0 < 653 and s["text"].strip() and r.y1 > 652.5:
            problems.append(("FAIL", f"DoO text spills past box bottom (y1={r.y1:.1f}): {s['text'][:60]!r}"))

    # 4. Plural boilerplate
    multi = bool(req.get("certificate_holder_lines")) and len(
        [l for l in req.get("certificate_holder_lines", []) if l]
    ) > 3
    if multi and "Certificate Holders" not in text:
        problems.append(("FAIL", "expected plural 'Certificate Holders' in boilerplate"))
    if not multi and "Certificate Holderss" in text:
        problems.append(("FAIL", "double-plural 'Certificate Holderss' found"))

    # 5. Boilerplate integrity — key phrases from the template's DoO must
    #    survive every edit path (this catches sibling-span text loss)
    t_text = tpage.get_text()
    for phrase in ("Additional Insured", "as required by written contract",
                   "Waiver of Subrogation"):
        if phrase in t_text and phrase not in text:
            problems.append(("FAIL", f"boilerplate phrase lost: {phrase!r}"))

    # 5b. No non-black text may survive in the output DoO (cyan normalization)
    for s in spans:
        if s.get("color", 0) != 0 and s["text"].strip() and fitz.Rect(s["bbox"]).intersects(desc_zone):
            problems.append(("WARN", f"non-black text in output DoO: {s['text'][:40]!r} color={hex(s['color'])}"))

    # 6. Border line-art survival: compare drawing counts near the box borders
    t_draw = tpage.get_drawings()
    o_draw = opage.get_drawings()
    border_zones = {
        "date_box_borders": fitz.Rect(505, 20, 597, 52),
        "holder_box_borders": fitz.Rect(15, 660, 310, 752),
        "desc_box_borders": fitz.Rect(15, 535, 597, 663),
    }
    for zname, zrect in border_zones.items():
        before = _drawings_in(t_draw, zrect)
        after = _drawings_in(o_draw, zrect)
        if after < before:
            problems.append(("WARN", f"{zname}: line-art count dropped {before} -> {after} (possible eaten border)"))

    tdoc.close()
    odoc.close()
    return problems


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_output"))
    ap.add_argument("--only", default=None, help="run only scenarios whose name contains this")
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()

    out_dir = args.out
    pdf_dir = os.path.join(out_dir, "pdfs")
    img_dir = os.path.join(out_dir, "images")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    scenarios = build_scenarios()
    if args.only:
        scenarios = [(n, r) for n, r in scenarios if args.only in n]

    report = []
    total_fail = total_warn = 0

    for name, req in scenarios:
        template_path = os.path.join(TEMPLATES_DIR, req["template_filename"])
        try:
            files = process_request(json.loads(json.dumps(req)), TEMPLATES_DIR, pdf_dir)
        except Exception as e:
            report.append(f"[CRASH] {name}: {type(e).__name__}: {e}")
            total_fail += 1
            continue

        for f in files:
            problems = check_output(template_path, f, req)
            tag = os.path.splitext(os.path.basename(f))[0]
            if not args.no_images:
                make_review_image(template_path, f, os.path.join(img_dir, f"{name}__{tag}.png"))
            if problems:
                for sev, msg in problems:
                    report.append(f"[{sev}] {name} :: {os.path.basename(f)} :: {msg}")
                    if sev == "FAIL":
                        total_fail += 1
                    else:
                        total_warn += 1
            else:
                report.append(f"[OK]   {name} :: {os.path.basename(f)}")

    print("\n" + "=" * 72)
    for line in report:
        print(line)
    print("=" * 72)
    print(f"Scenarios: {len(scenarios)}   FAIL: {total_fail}   WARN: {total_warn}")
    print(f"Review images: {img_dir}")
    with open(os.path.join(out_dir, "report.txt"), "w") as fh:
        fh.write("\n".join(report) + "\n")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
