"""
backfill_clayton_history.py — A10a: backfill Clayton Mechanical's issued
2026-27 COIs into data/coi_history.db so holder-address autofill works.

Client: clayton_mechanical (canonical "Clayton Mechanical", legal name on
certs "Clayton Air and Heating, Inc").

Sources
-------
1. 63 individual issued COI PDFs (Drive: WORK FOLDER/OG Folder/Pushing
   Forward/0000000 WON/Clayton Mechanical/New COIS/, also mirrored at
   USI Organized/01 Clients/Clayton Mechanical/COIs/, folder id
   1x08CH71F694W-z6h4U06zFU5KEBFUzkp). The local copy used for extraction
   (~/Downloads/Clayton_COIs_FULL_BATCH 26-27.zip) was verified byte-size
   identical to the Drive individual PDFs, file by file.
2. COI 070126.pdf (DGO Hotel Owner / Delta Orlando Celebration, issued
   07/01/2026) — local copy byte-identical to Drive id
   1zQYhO5C3btm3gvnvMWxrM6BYbtJZREFP.
3. Two Drive-only certs with no local byte copy, holder blocks transcribed
   from the Drive text reads (see EXTRA_RECORDS): City Of Pompano Beach
   (id 1WDXfKEhTZuKX6yQaRZ9_iTV2TupSUqJC, dated 06/29/2026) and Delta
   Hotels Orlando Celebration (id 1oSU71ra2GxjN9pYtRam0IRiyojxVwTJf,
   dated 06/30/2026).
4. Master sheet "COI LIST CMHQ 2026-2027 v.1 rev.2026.xlsx" (Drive id
   1vgIRnpVYPKGTNuMGV4bpsN6wNOBjjOtj) — used to cross-check every address,
   to fix the one holder whose name wrapped onto the address line
   (La Quinta Inn & Suites - Airport West), and to flag holders that carry
   custom AI/WOS wording (custom_wording: true; wording logic itself is a
   separate feature, deliberately NOT handled here).

Extraction is pure local PyMuPDF (no Anthropic API): the ACORD 25 holder
box (x 19-306, y 664-748) is read word-by-word so text that overflows the
box border to the right is kept (fixes truncated names on 15/28/44).

Rows are inserted with source='backfill_clayton' — NOT 'backfill' —
because training/backfill_db.py wipes all source='backfill' rows on every
run; a distinct source keeps these rows safe.

Usage:
    .venv/bin/python training/clayton/backfill_clayton_history.py build \
        [--pdf-dir /private/tmp/clayton_backfill/pdfs]
    .venv/bin/python training/clayton/backfill_clayton_history.py apply [--db PATH]

`build` writes training/clayton/history_backfill_staging.json.
`apply` is idempotent: rows already present (same client, normalized
holder name, addr line 1 and zip) are deduped, everything inserted in a
single short transaction (WAL DB; the live loop only reads).
"""

import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

import db  # noqa: E402

CLIENT_ID = "clayton_mechanical"
SOURCE = "backfill_clayton"
DEFAULT_PDF_DIR = "/private/tmp/clayton_backfill/pdfs"
STAGING_PATH = os.path.join(BASE, "training", "clayton", "history_backfill_staging.json")

DRIVE_COIS_FOLDER = "1x08CH71F694W-z6h4U06zFU5KEBFUzkp"

# Holder box on these ACORD 25s. Words may overflow x=306 (box border);
# we keep same-baseline continuation words up to x<420.
BOX_TOP, BOX_BOTTOM = 660.0, 752.0
BOX_LEFT, BOX_RIGHT, OVERFLOW_RIGHT = 15.0, 306.0, 420.0

DATE_CLIP = (440, 28, 595, 60)  # ACORD date field, top right
DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

STREET_LINE_RE = re.compile(r"^(\d|p\.?\s*o\.?\s*box\b|ste\.?\s|suite\s)", re.IGNORECASE)
# City/state/zip, tolerant of this corpus's 'FL.' style and optional comma:
CSZ_RE = re.compile(r"^(.*?)[,\s]+([A-Z]{2})\.?[,\s]+(\d{5}(?:-\d{4})?)\s*$")

# 38_La Quinta: the PDF wraps the name's trailing 'West' onto the street
# line ("West 7931 Daetwyler Drive"). Master xlsx confirms the intended
# split. Keyed by filename.
OVERRIDES = {
    "38_La Quinta Inn _ Suites - Airport.pdf": {
        "holder_name": "La Quinta Inn & Suites - Airport West",
        "address_line_1": "7931 Daetwyler Drive",
        "address_line_2": None,
        "city": "Orlando", "state": "FL", "zip": "32812",
        "note": "PDF wraps 'West' onto street line; split per master xlsx",
    },
}

# Files whose holder carries custom AI/WOS language in the master xlsx
# (DESCRIPTION OF OPERATIONS column non-empty). Flag only — no wording logic.
CUSTOM_WORDING_FILES = {
    "04_Bali Condominium Association_ Inc.pdf",
    "05_Benderson Development Company LLC.pdf",
    "06_Blue Tree Resort at Lake Buena Vista.pdf",
    "10_City of Orlando.pdf",
    "13_Courtyard _ Lake Buena Vista.pdf",
    "15_Cypress Pointe Resort at Lake Buena Vista Condominium Association.pdf",
    "17_Embassy Suites by Hilton Orlando North.pdf",
    "18_Fairfield Inn and Suites _Lake Buena Vista.pdf",
    "41_Magnolia Towers_ Inc.pdf",
    "42_AFP109 Corp._ United Capital Corp.pdf",
    "43_MtronPTI Headquarters.pdf",
    "44_Orange County Board of County Commissioners Division of Building Safety.pdf",
    "51_Simpson Property Group.pdf",
    "52_RPM Living_ LLC.pdf",
    "53_Pinar Center_ LLC.pdf",
    "55_Springhill Suites _ Lake Buena Vista.pdf",
    "56_Springhill Suites Orlando Airport.pdf",
    "60_Trinity Quorum Center LLC and.pdf",
    "61_CFI - Westgate Resorts.pdf",
    "65_Winter Park Racquet Club.pdf",
}

DATA_QUALITY_NOTES = {
    "19_Forest City Spanish Seventh-day Adventist Church.pdf":
        "No address on cert; master xlsx also has name only.",
    "20_Foley Properties_ LLC.pdf":
        "xlsx description column holds a stray second address "
        "('498 Palm Springs Drive Altamonte Springs, FL 32701') flagged "
        "questionable in the sheet itself; cert address used.",
    "34_Homewood Suites - Winter Garden.pdf":
        "Cert zip 32787 is likely a typo for 34787 (Winter Garden); "
        "kept as issued.",
    "50_Residence Inn.pdf":
        "Street spelled 'Flager Ave.' on cert (likely 'Flagler'); kept as issued.",
}

# Drive-only certs (no byte-identical local copy). Holder blocks and dates
# transcribed from Drive text reads of the listed file ids.
EXTRA_RECORDS = [
    {
        "pdf_filename": "City of Pompano Beach.pdf",
        "source_file": "drive:1WDXfKEhTZuKX6yQaRZ9_iTV2TupSUqJC (Copy of City of Pompano Beach.pdf)",
        "holder_name": "City Of Pompano Beach",
        "address_line_1": "100 West Atlantic Blvd.",
        "address_line_2": None,
        "city": "Pompano Beach", "state": "FL", "zip": "33060",
        "cert_date": "2026-06-29",
        "custom_wording": False,
    },
    {
        "pdf_filename": "Delta Hotels COI.pdf",
        "source_file": "drive:1oSU71ra2GxjN9pYtRam0IRiyojxVwTJf (Copy of Delta Hotels COI.pdf)",
        "holder_name": "Delta Hotels Orlando Celebration",
        "address_line_1": "2900 Parkway Blvd",
        "address_line_2": None,
        "city": "Kissimmee", "state": "FL", "zip": "32747",
        "cert_date": "2026-06-30",
        "custom_wording": False,
    },
]


def extract_holder_lines(page):
    """Holder-box text as lines, keeping words that overflow the box border."""
    words = page.get_text("words")
    band = [w for w in words
            if BOX_TOP <= w[1] and w[3] <= BOX_BOTTOM and BOX_LEFT <= w[0] < OVERFLOW_RIGHT]
    lines = {}
    for w in band:
        mid = round((w[1] + w[3]) / 2)
        key = next((k for k in lines if abs(k - mid) <= 2), mid)
        lines.setdefault(key, []).append(w)
    out = []
    for k in sorted(lines):
        ws = sorted(lines[k], key=lambda w: w[0])
        if ws[0][0] >= BOX_RIGHT:  # line starts outside holder box
            continue
        kept = [ws[0]]
        for w in ws[1:]:
            if w[0] - kept[-1][2] < 12:  # same-line continuation
                kept.append(w)
            else:
                break
        out.append(" ".join(w[4] for w in kept))
    return out


def extract_cert_date(page):
    import fitz
    m = DATE_RE.search(page.get_text("text", clip=fitz.Rect(*DATE_CLIP)))
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else None


def parse_holder_lines(lines):
    """(name, addr1, addr2, city, state, zip). Last line is city/state/zip;
    street lines walk up from there; everything above is the name (matches
    training/backfill_db.py convention: attn/c-o/ref lines stay in name)."""
    lines = [l.strip() for l in lines if l.strip()]
    if not lines:
        return None
    m = CSZ_RE.match(lines[-1])
    if not m:
        return (" ".join(lines), None, None, None, None, None)
    city, state, zip_code = m.group(1).strip(" ,"), m.group(2), m.group(3)
    body = lines[:-1]
    street = []
    while body and STREET_LINE_RE.match(body[-1]):
        street.insert(0, body.pop())
    # A 'Ste./Suite' trailer belongs to the street block even mid-walk;
    # ensure at least the last body line is treated as street if it starts
    # with a digit (already covered) — remaining body is the holder name.
    name = " ".join(body)
    addr1 = street[0] if street else None
    addr2 = ", ".join(street[1:]) if len(street) > 1 else None
    return (name, addr1, addr2, city, state, zip_code)


def build(pdf_dir):
    import fitz
    rows = []
    skipped = []
    for fn in sorted(os.listdir(pdf_dir)):
        if not fn.lower().endswith(".pdf"):
            continue
        doc = fitz.open(os.path.join(pdf_dir, fn))
        page = doc[0]
        cert_date = extract_cert_date(page)
        raw_lines = extract_holder_lines(page)
        doc.close()

        row = {
            "pdf_filename": fn,
            "source_file": f"local:{os.path.join(pdf_dir, fn)} "
                           f"(byte-identical to Drive folder {DRIVE_COIS_FOLDER})",
            "cert_date": cert_date,
            "custom_wording": fn in CUSTOM_WORDING_FILES,
        }
        if fn in OVERRIDES:
            ov = OVERRIDES[fn]
            row.update({k: ov[k] for k in
                        ("holder_name", "address_line_1", "address_line_2",
                         "city", "state", "zip")})
            row["note"] = ov["note"]
        else:
            parsed = parse_holder_lines(raw_lines)
            if not parsed or not parsed[0]:
                skipped.append({"pdf_filename": fn, "reason": "no holder name",
                                "raw_lines": raw_lines})
                continue
            name, addr1, addr2, city, state, zip_code = parsed
            row.update({"holder_name": name, "address_line_1": addr1,
                        "address_line_2": addr2, "city": city,
                        "state": state, "zip": zip_code})
        if fn in DATA_QUALITY_NOTES:
            row["note"] = DATA_QUALITY_NOTES[fn]
        rows.append(row)

    rows.extend(EXTRA_RECORDS)
    staging = {
        "client_id": CLIENT_ID,
        "source": SOURCE,
        "built_from": pdf_dir,
        "drive_cois_folder_id": DRIVE_COIS_FOLDER,
        "xlsx_cross_check": "COI LIST CMHQ 2026-2027 v.1 rev.2026.xlsx "
                            "(drive:1vgIRnpVYPKGTNuMGV4bpsN6wNOBjjOtj)",
        "rows": rows,
        "skipped_unparseable": skipped,
    }
    with open(STAGING_PATH, "w") as f:
        json.dump(staging, f, indent=1)
    print(f"Staged {len(rows)} rows ({len(skipped)} skipped) -> {STAGING_PATH}")
    return staging


def _dedupe_key(name, addr1, zip_code):
    return (db.normalize_holder(name),
            db.normalize_holder(addr1 or ""),
            (zip_code or "").strip())


def apply(db_path=None):
    with open(STAGING_PATH) as f:
        staging = json.load(f)
    rows = staging["rows"]

    conn = db.connect(db_path)
    inserted = deduped = 0
    try:
        existing = {
            _dedupe_key(r["holder_name"], r["address_line_1"], r["zip"])
            for r in conn.execute(
                "SELECT holder_name, address_line_1, zip FROM cois WHERE client_id = ?",
                (CLIENT_ID,))
        }
        for row in rows:
            key = _dedupe_key(row["holder_name"], row.get("address_line_1"),
                              row.get("zip"))
            if key in existing:
                deduped += 1
                continue
            existing.add(key)
            cert_date = row.get("cert_date")
            db.record_coi(
                client_id=CLIENT_ID,
                holder_name=row["holder_name"],
                address_line_1=row.get("address_line_1"),
                address_line_2=row.get("address_line_2"),
                city=row.get("city"),
                state=row.get("state"),
                zip_code=row.get("zip"),
                pdf_filename=row["pdf_filename"],
                pdf_path=row.get("source_file"),
                source=SOURCE,
                created_ts=f"{cert_date}T00:00:00Z" if cert_date else None,
                conn=conn,
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    print(f"Inserted: {inserted}  Deduped: {deduped}  "
          f"(staging rows: {len(rows)}, skipped at build: "
          f"{len(staging.get('skipped_unparseable', []))})")
    return inserted, deduped


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR)
    a = sub.add_parser("apply")
    a.add_argument("--db", default=None)
    args = p.parse_args()
    if args.cmd == "build":
        build(args.pdf_dir)
    else:
        apply(args.db)


if __name__ == "__main__":
    main()
