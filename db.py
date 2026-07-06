"""
db.py
-----
A10: SQLite history of every COI this system has delivered (plus a backfill
of historical delivered COIs from training/graded_cois.json).

One row per generated PDF in table `cois`. Live rows are written by main.py
after a successful send; backfill rows come from training/backfill_db.py.

The lookup side (lookup_holder / history_hints) powers A10a address-autofill:
given a holder name mentioned in a request, return the full addresses we've
used for that holder before, most recent first.

Database file: <BASE_DIR>/data/coi_history.db (WAL mode, gitignored).

CLI:
    python3 db.py lookup "Some Holder Name" [client_id]
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

import config

DB_PATH = os.path.join(config.BASE_DIR, "data", "coi_history.db")

# Tokens too generic to identify a holder — ignored when matching names.
# "bengoa construction" must find "Bengoa Construction, Inc." and
# "3 island condominium association" must not match every other condo.
GENERIC_TOKENS = {
    "inc", "llc", "corp", "corporation", "company", "co", "ltd", "llp",
    "lp", "pa", "pllc", "association", "assn", "condominium", "condo",
    "the", "of", "and", "a", "an", "at", "dba",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cois (
    id              INTEGER PRIMARY KEY,
    created_ts      TEXT,
    source          TEXT,               -- 'live' or 'backfill'
    client_id       TEXT,
    holder_name     TEXT,
    holder_name_norm TEXT,              -- lowercased, punctuation stripped
    address_line_1  TEXT,
    address_line_2  TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    project_text    TEXT,
    pdf_filename    TEXT,
    pdf_path        TEXT,
    msg_id          TEXT,
    thread_subject  TEXT,
    verdict         TEXT,               -- backfill only (grade from A3)
    request_excerpt TEXT                -- backfill only
);
CREATE INDEX IF NOT EXISTS idx_cois_holder_name_norm ON cois (holder_name_norm);

CREATE TABLE IF NOT EXISTS auto_ai_endorsements (
    id              INTEGER PRIMARY KEY,
    created_ts      TEXT,
    client_id       TEXT,               -- 'rolandos_hvac' (only client with scheduled auto AI today)
    holder_name     TEXT,
    holder_name_norm TEXT,              -- lowercased, punctuation stripped
    address         TEXT,
    status          TEXT,               -- 'requested' (carrier email fired) | 'endorsed' (confirmed on policy)
    source          TEXT,               -- 'live' or 'bulk_import'
    msg_id          TEXT
);
CREATE INDEX IF NOT EXISTS idx_auto_ai_client_holder
    ON auto_ai_endorsements (client_id, holder_name_norm);
"""


# ---------------------------------------------------------------------------
# NAME NORMALIZATION + TOKEN MATCHING
# ---------------------------------------------------------------------------

def normalize_holder(name):
    """Lowercase, strip punctuation, collapse whitespace."""
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def significant_tokens(name):
    """Tokens of the normalized name minus generic suffixes/stopwords.
    Falls back to all tokens if nothing significant remains ('The Company')."""
    tokens = normalize_holder(name).split()
    sig = [t for t in tokens if t not in GENERIC_TOKENS]
    return sig or tokens


# ---------------------------------------------------------------------------
# CONNECTION + SCHEMA
# ---------------------------------------------------------------------------

def connect(db_path=None):
    """Open (creating if needed) the history DB. WAL mode, dict-style rows."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# WRITE PATH
# ---------------------------------------------------------------------------

def record_coi(
    client_id,
    holder_name,
    address_line_1=None,
    address_line_2=None,
    city=None,
    state=None,
    zip_code=None,
    project_text=None,
    pdf_filename=None,
    pdf_path=None,
    msg_id=None,
    thread_subject=None,
    source="live",
    created_ts=None,
    verdict=None,
    request_excerpt=None,
    conn=None,
    db_path=None,
):
    """Insert one delivered-COI row. Returns the new row id.

    Pass an open `conn` to batch many inserts (caller commits/closes);
    otherwise a connection is opened, committed, and closed per call.
    """
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO cois
               (created_ts, source, client_id, holder_name, holder_name_norm,
                address_line_1, address_line_2, city, state, zip, project_text,
                pdf_filename, pdf_path, msg_id, thread_subject, verdict,
                request_excerpt)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                created_ts or _utc_now_iso(),
                source,
                client_id,
                holder_name,
                normalize_holder(holder_name),
                address_line_1,
                address_line_2,
                city,
                state,
                zip_code,
                project_text,
                pdf_filename,
                pdf_path,
                msg_id,
                thread_subject,
                verdict,
                request_excerpt,
            ),
        )
        if own_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if own_conn:
            conn.close()


# ---------------------------------------------------------------------------
# LOOKUP (powers A10a address-autofill)
# ---------------------------------------------------------------------------

def lookup_holder(name, client_id=None, limit=25, conn=None, db_path=None):
    """Find historical rows for a holder name, most recent first.

    Match rule: every significant token of `name` (generic tokens like
    inc/llc/corp ignored) must appear as a whole token in the stored
    holder_name_norm. So 'Bengoa Construction' finds
    'Bengoa Construction, Inc.' but 'Bengoa Const' does not match 'Bengoa'.

    Returns a list of dicts (column -> value).
    """
    query_tokens = significant_tokens(name)
    if not query_tokens:
        return []

    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
    try:
        # SQL prefilter on the rarest-looking (longest) token, exact token
        # match verified in Python below.
        anchor = max(query_tokens, key=len)
        sql = (
            "SELECT * FROM cois WHERE holder_name_norm LIKE ? "
            "ORDER BY created_ts DESC"
        )
        params = [f"%{anchor}%"]
        if client_id:
            sql = (
                "SELECT * FROM cois WHERE holder_name_norm LIKE ? "
                "AND client_id = ? ORDER BY created_ts DESC"
            )
            params.append(client_id)
        rows = conn.execute(sql, params).fetchall()
    finally:
        if own_conn:
            conn.close()

    want = set(query_tokens)
    matches = []
    for row in rows:
        have = set((row["holder_name_norm"] or "").split())
        if want <= have:
            matches.append(dict(row))
        if len(matches) >= limit:
            break
    return matches


def history_hints(candidate_name, client_id=None, limit=3, conn=None, db_path=None):
    """Format the top known addresses for a holder name as prompt-ready text.

    Returns e.g.:
        KNOWN CERTIFICATE HOLDERS FROM HISTORY:
        Bengoa Construction Inc | 2200 N Dixie Hwy | Hollywood FL 33020 (last used 2026-04-20)

    Returns "" when there is no match. Intended for the classifier prompt
    (A10a) — NOT wired in yet.
    """
    rows = lookup_holder(candidate_name, client_id=client_id, conn=conn, db_path=db_path)
    if not rows:
        return ""

    lines = []
    seen = set()
    for row in rows:  # already most recent first
        addr_bits = [row.get("address_line_1"), row.get("address_line_2")]
        csz = " ".join(filter(None, [row.get("city"), row.get("state"), row.get("zip")]))
        addr_bits.append(csz or None)
        key = (row.get("holder_name_norm"), tuple(b for b in addr_bits if b))
        if key in seen:
            continue
        seen.add(key)
        parts = [row.get("holder_name") or "?"] + [b for b in addr_bits if b]
        last_used = (row.get("created_ts") or "")[:10]
        lines.append(" | ".join(parts) + (f" (last used {last_used})" if last_used else ""))
        if len(lines) >= limit:
            break

    return "KNOWN CERTIFICATE HOLDERS FROM HISTORY:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# AUTO-AI ENDORSEMENTS (Rolando's scheduled-auto SOP — see flows.py)
# ---------------------------------------------------------------------------

def ai_endorsement_lookup(client_id, holder_name, conn=None, db_path=None):
    """Existing endorsement row for this holder, or None.

    Match rule: significant-token SET equality (generic tokens like inc/llc
    stripped), so 'City of Tampa, Inc.' matches 'City of Tampa' but NOT
    'City of Tampa Parks Department'. Conservative on purpose — a near-miss
    fires a duplicate carrier request rather than silently skipping one."""
    want = set(significant_tokens(holder_name))
    if not want:
        return None
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM auto_ai_endorsements WHERE client_id = ? "
            "ORDER BY created_ts DESC",
            (client_id,),
        ).fetchall()
    finally:
        if own_conn:
            conn.close()
    for row in rows:
        if set(significant_tokens(row["holder_name"])) == want:
            return dict(row)
    return None


def record_ai_endorsement(client_id, holder_name, address=None,
                          status="requested", source="live", msg_id=None,
                          created_ts=None, conn=None, db_path=None):
    """Insert one auto-AI endorsement row. Returns the new row id."""
    own_conn = conn is None
    if own_conn:
        conn = connect(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO auto_ai_endorsements
               (created_ts, client_id, holder_name, holder_name_norm,
                address, status, source, msg_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                created_ts or _utc_now_iso(),
                client_id,
                holder_name,
                normalize_holder(holder_name),
                address,
                status,
                source,
                msg_id,
            ),
        )
        if own_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if own_conn:
            conn.close()


def import_ai_endorsements(path, client_id="rolandos_hvac", status="endorsed",
                           db_path=None):
    """Bulk-import Alex's already-endorsed holder list into the auto-AI table.

    Accepts:
      - CSV with a 'holder_name' header column (optional 'address' and
        'status' columns), or a headerless single-column CSV of names.
      - JSON: a list of strings, or a list of {"holder_name": ...,
        "address": ..., "status": ...} objects.

    Rows whose holder already exists (token match) are skipped. Imported
    rows default to status='endorsed', source='bulk_import'.
    Returns (imported_count, skipped_count).
    """
    import csv

    entries = []
    if path.lower().endswith(".json"):
        with open(path, "r") as f:
            data = json.load(f)
        for item in data:
            if isinstance(item, str):
                entries.append({"holder_name": item})
            elif isinstance(item, dict) and item.get("holder_name"):
                entries.append(item)
    else:
        with open(path, "r", newline="") as f:
            reader = csv.reader(f)
            rows = [r for r in reader if any(cell.strip() for cell in r)]
        if rows and "holder_name" in [c.strip().lower() for c in rows[0]]:
            header = [c.strip().lower() for c in rows[0]]
            for r in rows[1:]:
                rec = dict(zip(header, (c.strip() for c in r)))
                if rec.get("holder_name"):
                    entries.append(rec)
        else:
            for r in rows:
                if r and r[0].strip():
                    entries.append({"holder_name": r[0].strip(),
                                    "address": r[1].strip() if len(r) > 1 else None})

    conn = connect(db_path)
    imported = skipped = 0
    try:
        for rec in entries:
            name = rec["holder_name"]
            if ai_endorsement_lookup(client_id, name, conn=conn):
                skipped += 1
                continue
            record_ai_endorsement(
                client_id=client_id,
                holder_name=name,
                address=rec.get("address") or None,
                status=rec.get("status") or status,
                source="bulk_import",
                conn=conn,
            )
            imported += 1
        conn.commit()
    finally:
        conn.close()
    return imported, skipped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(argv):
    if len(argv) >= 2 and argv[0] == "lookup":
        name = argv[1]
        client_id = argv[2] if len(argv) > 2 else None
        rows = lookup_holder(name, client_id=client_id)
        if not rows:
            print(f"No history for: {name}")
            return 1
        print(f"{len(rows)} match(es) for '{name}':")
        for r in rows:
            csz = " ".join(filter(None, [r.get("city"), r.get("state"), r.get("zip")]))
            addr = " | ".join(filter(None, [r.get("address_line_1"), r.get("address_line_2"), csz]))
            print(
                f"  [{(r.get('created_ts') or '?')[:10]}] {r.get('holder_name')}"
                f" | {addr}  ({r.get('source')}, client={r.get('client_id')})"
            )
        print()
        print(history_hints(name, client_id=client_id))
        return 0
    if len(argv) >= 2 and argv[0] == "import-auto-ai":
        path = argv[1]
        client_id = argv[2] if len(argv) > 2 else "rolandos_hvac"
        imported, skipped = import_ai_endorsements(path, client_id=client_id)
        print(f"Imported {imported} holder(s), skipped {skipped} already-known "
              f"holder(s) into auto_ai_endorsements (client={client_id})")
        return 0
    if len(argv) >= 2 and argv[0] == "ai-lookup":
        name = argv[1]
        client_id = argv[2] if len(argv) > 2 else "rolandos_hvac"
        row = ai_endorsement_lookup(client_id, name)
        if row:
            print(f"FOUND: {row['holder_name']} status={row['status']} "
                  f"source={row['source']} recorded={row['created_ts']}")
        else:
            print(f"No auto-AI record for: {name} (client={client_id})")
        return 0
    print('Usage: python3 db.py lookup "Some Holder Name" [client_id]\n'
          '       python3 db.py import-auto-ai <file.csv|file.json> [client_id]\n'
          '       python3 db.py ai-lookup "Holder Name" [client_id]')
    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
