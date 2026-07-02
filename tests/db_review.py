"""
db_review.py
------------
Review harness for db.py (A10 COI history database). Three parts:

  1. Unit checks on a throwaway temp DB — record_coi + lookup_holder
     matching, including fuzzy cases ('Bengoa Construction' must find
     'Bengoa Construction, Inc.'), client_id filtering, recency ordering,
     and history_hints formatting.
  2. Real backfill — runs training/backfill_db.py's backfill() against the
     real training/graded_cois.json into a temp DB, prints the row count and
     5 sample parsed rows for eyeball checking.
  3. Simulated main.py write path — calls db.record_coi with parsed-shaped
     dicts (single + batch), exactly the field mapping main.record_sent_cois
     uses, and verifies the rows land.

Usage: .venv/bin/python tests/db_review.py
"""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "training"))

import db
from backfill_db import backfill

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def temp_db(tag):
    return os.path.join(tempfile.mkdtemp(prefix=f"coi_db_{tag}_"), "coi_history.db")


# ---------------------------------------------------------------------------
# 1. UNIT CHECKS — record + lookup matching
# ---------------------------------------------------------------------------

def part1_unit_checks():
    print("\n=== 1. record_coi + lookup_holder unit checks ===")
    path = temp_db("unit")

    db.record_coi(
        client_id="ajf_roofing", holder_name="Bengoa Construction, Inc.",
        address_line_1="2200 N Dixie Hwy", city="Hollywood", state="FL",
        zip_code="33020", created_ts="2026-04-20T10:00:00Z", db_path=path,
    )
    db.record_coi(
        client_id="ajf_roofing", holder_name="Bengoa Construction, Inc.",
        address_line_1="999 Old Address Rd", city="Miami", state="FL",
        zip_code="33130", created_ts="2026-01-05T10:00:00Z", db_path=path,
    )
    db.record_coi(
        client_id="apogee_hvac", holder_name="LaGreca Construction, LLC",
        address_line_1="12565 Orange Dr", address_line_2="Suite 401C",
        city="Davie", state="FL", zip_code="33330",
        created_ts="2026-02-10T10:00:00Z", db_path=path,
    )
    db.record_coi(
        client_id="apogee_hvac",
        holder_name="3 Island Condominium Association, Inc",
        address_line_1="3 Island Ave.", city="Miami", state="FL",
        zip_code="33139", created_ts="2026-03-01T10:00:00Z", db_path=path,
    )

    # Fuzzy: query without suffix finds the suffixed row
    rows = db.lookup_holder("Bengoa Construction", db_path=path)
    check("'Bengoa Construction' finds 'Bengoa Construction, Inc.'",
          len(rows) == 2 and rows[0]["holder_name"] == "Bengoa Construction, Inc.",
          f"got {[(r['holder_name'], r['created_ts']) for r in rows]}")
    check("most recent first",
          len(rows) == 2 and rows[0]["created_ts"] > rows[1]["created_ts"])

    # Fuzzy: extra generic tokens in the query are ignored
    rows = db.lookup_holder("bengoa construction company llc", db_path=path)
    check("generic tokens in query ignored", len(rows) == 2)

    # Punctuation/case insensitive
    rows = db.lookup_holder("LAGRECA construction", db_path=path)
    check("case-insensitive match", len(rows) == 1 and rows[0]["city"] == "Davie")

    # Generic-token holder tokens don't cross-match
    rows = db.lookup_holder("3 Island", db_path=path)
    check("'3 Island' finds the condo association", len(rows) == 1)
    rows = db.lookup_holder("Island Gardens Condominium Association", db_path=path)
    check("different condo association does NOT match", len(rows) == 0)

    # Partial token is not a match ('Bengo' is not the token 'bengoa')
    rows = db.lookup_holder("Bengo Construction", db_path=path)
    check("partial token does not match", len(rows) == 0)

    # client_id filter
    rows = db.lookup_holder("Bengoa Construction", client_id="apogee_hvac", db_path=path)
    check("client_id filter excludes other clients", len(rows) == 0)
    rows = db.lookup_holder("Bengoa Construction", client_id="ajf_roofing", db_path=path)
    check("client_id filter keeps own client", len(rows) == 2)

    # history_hints
    hint = db.history_hints("Bengoa Construction", db_path=path)
    print("  --- history_hints output ---")
    for line in hint.splitlines():
        print(f"  | {line}")
    check("hints header present", hint.startswith("KNOWN CERTIFICATE HOLDERS FROM HISTORY:"))
    check("hints most recent address first",
          "2200 N Dixie Hwy | Hollywood FL 33020 (last used 2026-04-20)" in hint.splitlines()[1])
    check("hints include older distinct address", "999 Old Address Rd" in hint)
    check("no-match returns empty string",
          db.history_hints("Zzyzx Nonexistent Holdings", db_path=path) == "")


# ---------------------------------------------------------------------------
# 2. REAL BACKFILL — graded_cois.json into a temp DB
# ---------------------------------------------------------------------------

def part2_backfill():
    print("\n=== 2. backfill from real graded_cois.json ===")
    path = temp_db("backfill")

    counts = backfill(db_path=path)
    print(f"  records={counts['records']} inserted={counts['inserted']} "
          f"skipped_empty={counts['skipped_empty']} skipped_no_name={counts['skipped_no_name']}")
    check("all records accounted for",
          counts["inserted"] + counts["skipped_empty"] + counts["skipped_no_name"]
          == counts["records"])
    check("inserted a healthy share (>= 80%)",
          counts["inserted"] >= 0.8 * counts["records"],
          f"only {counts['inserted']}/{counts['records']}")

    # Idempotency: run again, same count, no duplicates
    counts2 = backfill(db_path=path)
    conn = db.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM cois WHERE source='backfill'").fetchone()[0]
    check("idempotent rerun (wipe + reinsert, no duplicates)",
          n == counts2["inserted"] == counts["inserted"], f"db has {n}")

    print("  --- 5 sample parsed rows (eyeball check) ---")
    rows = conn.execute(
        "SELECT * FROM cois WHERE source='backfill' ORDER BY id LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"  | client={r['client_id']}  verdict={r['verdict']}  ts={r['created_ts']}")
        print(f"  |   name:  {r['holder_name']}")
        print(f"  |   addr:  {r['address_line_1']} / {r['address_line_2']} "
              f"/ {r['city']}, {r['state']} {r['zip']}")
    conn.close()

    # Known holder from the corpus must be findable
    rows = db.lookup_holder("LaGreca Construction", db_path=path)
    check("backfilled 'LaGreca Construction' is findable", len(rows) >= 1,
          "no rows returned")
    if rows:
        check("backfilled row has city/state/zip parsed",
              rows[0]["state"] == "FL" and rows[0]["zip"] is not None,
              f"state={rows[0]['state']} zip={rows[0]['zip']}")

    return counts


# ---------------------------------------------------------------------------
# 3. SIMULATED main.py WRITE PATH — parsed-shaped dicts
# ---------------------------------------------------------------------------

def part3_write_path():
    print("\n=== 3. simulated main.py write path ===")
    path = temp_db("live")

    # Single request — same mapping main.record_sent_cois applies to
    # ai_result['parsed'] + decision['pdf_paths']
    parsed = {
        "client_id": "central_comfort_ac",
        "client_canonical_name": "Central Comfort Air Conditioning",
        "request_type": "single",
        "certificate_holder": {
            "name": "Vista Gardens Condo Association, Inc.",
            "address_line_1": "100 Vista Gardens Way",
            "address_line_2": None,
            "city": "Boca Raton", "state": "FL", "zip": "33433",
        },
        "project_name": None, "project_address": None, "project_unit": "305",
        "is_permit": False,
    }
    decision = {"action": "send_pdf",
                "pdf_paths": ["/tmp/out/CentralComfort_VistaGardens_07022026.pdf"]}
    ch = parsed["certificate_holder"]
    for p in decision["pdf_paths"]:
        db.record_coi(
            client_id=parsed["client_id"],
            holder_name=ch["name"],
            address_line_1=ch["address_line_1"],
            address_line_2=ch["address_line_2"],
            city=ch["city"], state=ch["state"], zip_code=ch["zip"],
            project_text="Project: Unit 305",
            pdf_filename=os.path.basename(p), pdf_path=p,
            msg_id="AAMkTEST123", thread_subject="COI request - Vista Gardens",
            source="live", db_path=path,
        )

    rows = db.lookup_holder("vista gardens condo", db_path=path)
    check("live single row recorded + findable",
          len(rows) == 1 and rows[0]["source"] == "live"
          and rows[0]["pdf_filename"] == "CentralComfort_VistaGardens_07022026.pdf"
          and rows[0]["msg_id"] == "AAMkTEST123")
    check("live row verdict is NULL", rows and rows[0]["verdict"] is None)

    # Batch request — one row per batch_cois item
    batch_parsed = {
        "client_id": "ajf_roofing",
        "request_type": "batch",
        "batch_cois": [
            {"certificate_holder": {"name": "City of North Miami",
                                    "address_line_1": "776 NE 125 Street",
                                    "city": "North Miami", "state": "FL", "zip": "33161"}},
            {"certificate_holder": {"name": "Barron Development Corporation",
                                    "address_line_1": "2890 Marina Mile Blvd",
                                    "city": "Fort Lauderdale", "state": "FL", "zip": "33312"}},
        ],
    }
    batch_paths = ["/tmp/out/AJF_CityNorthMiami.pdf", "/tmp/out/AJF_Barron.pdf"]
    for i, item in enumerate(batch_parsed["batch_cois"]):
        ch = item["certificate_holder"]
        db.record_coi(
            client_id=batch_parsed["client_id"],
            holder_name=ch["name"],
            address_line_1=ch.get("address_line_1"),
            address_line_2=ch.get("address_line_2"),
            city=ch.get("city"), state=ch.get("state"), zip_code=ch.get("zip"),
            pdf_filename=os.path.basename(batch_paths[i]), pdf_path=batch_paths[i],
            msg_id="AAMkBATCH456", thread_subject="Need 2 COIs",
            source="live", db_path=path,
        )

    conn = db.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM cois WHERE msg_id='AAMkBATCH456'").fetchone()[0]
    conn.close()
    check("batch recorded one row per item", n == 2)
    rows = db.lookup_holder("Barron Development", db_path=path)
    check("batch holder findable", len(rows) == 1 and rows[0]["zip"] == "33312")


def main():
    part1_unit_checks()
    part2_backfill()
    part3_write_path()

    print(f"\n{'=' * 50}")
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
