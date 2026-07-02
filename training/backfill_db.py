"""
backfill_db.py — A10: seed the COI history DB from training/graded_cois.json.

Takes the 156 graded historical delivered COIs (from grade_cois.py), parses
each record's holder_text into holder name + address fields, and inserts them
as source='backfill' rows in <BASE_DIR>/data/coi_history.db.

holder_text parsing: lines are split into NAME lines and ADDRESS lines. A
line is an address line if it matches a street pattern (number + street
suffix), a city-state-zip pattern, or a PO Box. Everything before the first
address line is the holder name (joined with a space). Records with an empty
holder_text — or where no name line precedes the address — are skipped.

Idempotent: every run deletes all source='backfill' rows first, then
reinserts. Live rows are never touched.

Usage: .venv/bin/python training/backfill_db.py [--db PATH]
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")

# A line counts as an address line if any of these hit (case-insensitive):
STREET_RE = re.compile(
    r"\d+\s+.*\b("
    r"st|street|ave|avenue|blvd|boulevard|dr|drive|rd|road|way|"
    r"cir|circle|ct|court|ter|terrace|hwy|highway|ln|lane|pl|place|"
    r"pkwy|parkway|trl|trail"
    r")\b\.?",
    re.IGNORECASE,
)
CSZ_RE = re.compile(r",\s*[A-Z]{2},?\s*\d{5}")
PO_BOX_RE = re.compile(r"^p\.?\s*o\.?\s*box\s+\d+", re.IGNORECASE)

# Lenient city/state/zip extractor (comma optional: 'Plantation FL 33324')
CSZ_PARSE_RE = re.compile(r"^(.*?)[,\s]+([A-Z]{2})[,\s]+(\d{5}(?:-\d{4})?)\s*$")


def is_address_line(line):
    return bool(STREET_RE.search(line) or CSZ_RE.search(line) or PO_BOX_RE.match(line))


def parse_holder_text(holder_text):
    """Split a raw holder box text into (name, addr1, addr2, city, state, zip).
    Returns None when no holder name can be extracted."""
    lines = []
    for raw in (holder_text or "").splitlines():
        line = raw.strip()
        # Drop OCR noise (stray 1-char lines) and box header labels
        if len(line) < 2 or not re.search(r"[a-zA-Z0-9]", line):
            continue
        if line.upper() in ("CERTIFICATE HOLDER", "CERTIFICATE HOLDERS"):
            continue
        lines.append(line)
    if not lines:
        return None

    first_addr = next((i for i, l in enumerate(lines) if is_address_line(l)), None)
    if first_addr is None:
        # No address at all — whole text is the name
        return (" ".join(lines), None, None, None, None, None)
    if first_addr == 0:
        # Address with no preceding name line — useless for name lookup
        return None

    name = " ".join(lines[:first_addr])
    addr_lines = lines[first_addr:]

    # Pull city/state/zip from the last line that parses as one
    city = state = zip_code = None
    for i in range(len(addr_lines) - 1, -1, -1):
        m = CSZ_PARSE_RE.match(addr_lines[i])
        if m:
            city = m.group(1).strip(" ,") or None
            state = m.group(2)
            zip_code = m.group(3)
            addr_lines.pop(i)
            break

    addr1 = addr_lines[0] if addr_lines else None
    addr2 = ", ".join(addr_lines[1:]) if len(addr_lines) > 1 else None
    return (name, addr1, addr2, city, state, zip_code)


def _to_iso(message_date):
    """'2026-01-09 18:09:05' -> '2026-01-09T18:09:05Z' (sorts with live rows)."""
    if not message_date:
        return None
    ts = message_date.strip().replace(" ", "T")
    return ts + "Z" if "T" in ts and not ts.endswith("Z") else ts


def backfill(graded_path=GRADED_PATH, db_path=None):
    """Wipe + reinsert all backfill rows. Returns a counts dict."""
    with open(graded_path, "r") as f:
        records = json.load(f)["records"]

    counts = {"records": len(records), "inserted": 0,
              "skipped_empty": 0, "skipped_no_name": 0}

    conn = db.connect(db_path)
    try:
        conn.execute("DELETE FROM cois WHERE source = 'backfill'")
        for rec in records:
            holder_text = (rec.get("holder_text") or "").strip()
            if not holder_text:
                counts["skipped_empty"] += 1
                continue
            parsed = parse_holder_text(holder_text)
            if not parsed:
                counts["skipped_no_name"] += 1
                continue
            name, addr1, addr2, city, state, zip_code = parsed
            threads = rec.get("threads") or []
            db.record_coi(
                client_id=rec.get("client"),
                holder_name=name,
                address_line_1=addr1,
                address_line_2=addr2,
                city=city,
                state=state,
                zip_code=zip_code,
                pdf_filename=rec.get("filename"),
                pdf_path=rec.get("path"),
                thread_subject=threads[0] if threads else None,
                source="backfill",
                created_ts=_to_iso(rec.get("message_date")),
                verdict=rec.get("verdict"),
                request_excerpt=rec.get("request_excerpt"),
                conn=conn,
            )
            counts["inserted"] += 1
        conn.commit()
    finally:
        conn.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Backfill COI history DB from graded_cois.json")
    parser.add_argument("--db", default=None, help="override DB path (default: data/coi_history.db)")
    args = parser.parse_args()

    counts = backfill(db_path=args.db)
    print(f"Graded records:      {counts['records']}")
    print(f"Inserted (backfill): {counts['inserted']}")
    print(f"Skipped empty text:  {counts['skipped_empty']}")
    print(f"Skipped no name:     {counts['skipped_no_name']}")
    print(f"DB: {args.db or db.DB_PATH}")


if __name__ == "__main__":
    main()
