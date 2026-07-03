"""
apply_holder_decisions.py — apply Alex's holder-review export to the history DB.

Input: holder_review_decisions.json downloaded from training/holder_review.html
(built by training/build_holder_review.py). Flat dict keyed by normalized
holder name (db.normalize_holder):

    { "<holder_key>": { "decision": "confirm" | "edit" | "exclude",
                        "corrected_address": {address_line_1, address_line_2,
                                              city, state, zip},   # edit only
                        "category": "...",     # informational, not applied
                        "note": "..." } }

What it does per decision:
  confirm — no DB change (address already correct; also clears any prior
            exclusion for that holder so autofill can use it).
  edit    — UPDATE all rows in `cois` for that holder_name_norm, setting the
            five address columns to corrected_address (also clears any prior
            exclusion). Idempotent: re-running produces the same rows.
  exclude — upsert into `holder_exclusions` (see below). A10a autofill must
            skip holders present in that table.

Schema change (least invasive — the `cois` table is untouched):

    CREATE TABLE IF NOT EXISTS holder_exclusions (
        holder_name_norm TEXT PRIMARY KEY,   -- db.normalize_holder key
        note             TEXT,               -- Alex's note, if any
        decided_ts       TEXT                -- when the decision was applied
    );

The whole run is one transaction and is idempotent: the export is treated as
ground truth, so a holder whose decision is no longer 'exclude' is removed
from holder_exclusions on the next run.

SAFETY: dry-run by default — prints every change it WOULD make and rolls
back. Pass --apply to commit. Never run against the live DB while unsure;
point --db at a copy first if you want a rehearsal.

Usage:
    .venv/bin/python training/apply_holder_decisions.py holder_review_decisions.json [--db PATH] [--apply]
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402

ADDR_FIELDS = ("address_line_1", "address_line_2", "city", "state", "zip")

_EXCLUSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS holder_exclusions (
    holder_name_norm TEXT PRIMARY KEY,
    note             TEXT,
    decided_ts       TEXT
);
"""


def apply_decisions(decisions_path, db_path=None, commit=False):
    with open(decisions_path) as f:
        decisions = json.load(f)

    path = db_path or db.DB_PATH
    if not os.path.exists(path):
        sys.exit(f"DB not found: {path}")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # explicit BEGIN so even the CREATE TABLE rolls back on a dry run
    # (python sqlite3 autocommits DDL unless a transaction is already open)
    conn.execute("BEGIN")
    conn.execute(_EXCLUSIONS_SCHEMA)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    stats = {"confirm": 0, "edit": 0, "exclude": 0,
             "rows_updated": 0, "unexcluded": 0, "missing": []}
    try:
        for key, entry in sorted(decisions.items()):
            decision = (entry or {}).get("decision")
            if decision not in ("confirm", "edit", "exclude"):
                print(f"  SKIP {key!r}: unknown decision {decision!r}")
                continue

            n_rows = conn.execute(
                "SELECT COUNT(*) FROM cois WHERE holder_name_norm = ?",
                (key,)).fetchone()[0]
            if n_rows == 0:
                stats["missing"].append(key)
                print(f"  WARN {key!r}: no rows in cois — nothing to do")
                continue

            stats[decision] += 1

            if decision == "exclude":
                conn.execute(
                    """INSERT INTO holder_exclusions (holder_name_norm, note, decided_ts)
                       VALUES (?,?,?)
                       ON CONFLICT(holder_name_norm)
                       DO UPDATE SET note = excluded.note""",
                    (key, entry.get("note"), now))
                print(f"  EXCLUDE {key!r} ({n_rows} row(s) will be ignored by autofill)")
                continue

            # confirm / edit both mean "this holder is usable" — drop any
            # exclusion left over from a previous export.
            cur = conn.execute(
                "DELETE FROM holder_exclusions WHERE holder_name_norm = ?", (key,))
            if cur.rowcount:
                stats["unexcluded"] += 1
                print(f"  UN-EXCLUDE {key!r} (was excluded in a prior run)")

            if decision == "edit":
                addr = entry.get("corrected_address") or {}
                values = [(addr.get(f) or None) for f in ADDR_FIELDS]
                if not any(values):
                    print(f"  SKIP {key!r}: edit with empty corrected_address")
                    stats["edit"] -= 1
                    continue
                cur = conn.execute(
                    f"""UPDATE cois SET {', '.join(f'{f} = ?' for f in ADDR_FIELDS)}
                        WHERE holder_name_norm = ?""",
                    values + [key])
                stats["rows_updated"] += cur.rowcount
                pretty = " | ".join(filter(None, values))
                print(f"  EDIT {key!r}: {cur.rowcount} row(s) -> {pretty}")

        n_excl = conn.execute("SELECT COUNT(*) FROM holder_exclusions").fetchone()[0]
        print()
        print(f"decisions: {stats['confirm']} confirm, {stats['edit']} edit, "
              f"{stats['exclude']} exclude; {stats['rows_updated']} cois rows updated; "
              f"{n_excl} holder(s) now in holder_exclusions")
        if stats["missing"]:
            print(f"NOT FOUND in cois ({len(stats['missing'])}): {stats['missing']}")

        if commit:
            conn.commit()
            print("COMMITTED.")
        else:
            conn.rollback()
            print("DRY RUN — nothing written. Re-run with --apply to commit.")
    finally:
        conn.close()
    return stats


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        sys.exit("Usage: apply_holder_decisions.py holder_review_decisions.json "
                 "[--db PATH] [--apply]")
    db_path = None
    if "--db" in argv:
        db_path = argv[argv.index("--db") + 1]
        args = [a for a in args if a != db_path]
    apply_decisions(args[0], db_path=db_path, commit="--apply" in argv)


if __name__ == "__main__":
    main(sys.argv[1:])
