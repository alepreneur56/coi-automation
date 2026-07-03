"""
build_holder_review.py — A10a gate: certificate-holder review page for Alex.

Before address-autofill (A10a) goes live, every certificate holder in the
COI history DB gets one card on a single self-contained HTML page:

  - holder name + every distinct address variant on file (multiple non-empty
    variants = ADDRESS CONFLICT, Alex picks the right one)
  - which client(s) it was issued for, how many times, most recent issue date
  - any data-quality note carried in from the Clayton backfill staging JSON
  - conservative category heuristic (cities/municipalities, construction,
    property management, other) with a per-card dropdown to recategorize

Per-holder actions: Confirm (address safe for autofill), Edit (inline
correction), Exclude (never autofill), plus a free-text note.

Decisions persist in localStorage under the key `holder_review_decisions`,
keyed by the normalized holder name (db.normalize_holder). The Export button
downloads `holder_review_decisions.json` as a flat dict:

    { "<holder_key>": { "decision": "confirm" | "edit" | "exclude",
                        "corrected_address": {            # edit only
                            "address_line_1": str|null,
                            "address_line_2": str|null,
                            "city": str|null,
                            "state": str|null,
                            "zip": str|null },
                        "category": "gov"|"construction"|"property"|"other",
                        "note": str } }

That file feeds training/apply_holder_decisions.py.

The database is opened READ-ONLY (sqlite URI mode=ro) — this script never
writes to coi_history.db.

Usage: .venv/bin/python training/build_holder_review.py [--db PATH]
Output: training/holder_review.html
"""

import html
import json
import os
import re
import sys
import sqlite3
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import normalize_holder  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(BASE, "data", "coi_history.db")
STAGING_PATH = os.path.join(BASE, "training", "clayton", "history_backfill_staging.json")
OUT_PATH = os.path.join(BASE, "training", "holder_review.html")

ADDR_FIELDS = ("address_line_1", "address_line_2", "city", "state", "zip")

# ---------------------------------------------------------------------------
# CATEGORIES — conservative keyword heuristics on the normalized name.
# Checked in order; first hit wins. Getting one wrong is fine: every card has
# a dropdown and Alex's pick is exported with his other decisions.
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("gov", "Cities & Municipalities"),
    ("construction", "General Contractors / Construction"),
    ("property", "Property Management / Condos / HOAs / Hotels"),
    ("other", "Everything Else"),
]
CATEGORY_LABELS = dict(CATEGORIES)

_GOV_RE = re.compile(
    r"\b(city of|town of|village of|county|school board|school district|"
    r"public schools|housing authority|state of|department|dept|municipal|"
    r"city hall|town hall|university|commission(ers)?|authority|fdot|"
    r"building (division|department|permits|inspections|code|safety)|"
    r"contractor licensing|licensing board)\b"
)
_CONSTRUCTION_RE = re.compile(
    r"\b(construction|constructors|builders?|building|contracting|"
    r"contractors?|development|developers?|gc|structures|concrete|roofing|"
    r"plumbing|electrical?|engineering|mechanical|drywall|masonry|paving|"
    r"restoration|remodeling|renovations?|framing|homes|dragados|jv)\b"
)
_PROPERTY_RE = re.compile(
    r"\b(property management|properties|condominiums?|condos?|hoa|"
    r"homeowners?|apartments?|realty|real estate|hotels?|inn|suites|"
    r"resorts?|villas|towers?|plaza|estates|residences?|lofts|management|"
    r"association)\b"
)


def categorize(norm_name):
    if _GOV_RE.search(norm_name):
        return "gov"
    if _CONSTRUCTION_RE.search(norm_name):
        return "construction"
    if _PROPERTY_RE.search(norm_name):
        return "property"
    return "other"


# ---------------------------------------------------------------------------
# AGGREGATION
# ---------------------------------------------------------------------------

def norm_address(row):
    """Normalized full-address string used to group variants. Empty string
    means no address on file."""
    joined = " ".join(filter(None, (row.get(f) for f in ADDR_FIELDS)))
    return normalize_holder(joined)  # same lowercase/punct-strip treatment


def load_staging_notes():
    """holder_key -> data-quality note from the Clayton backfill staging."""
    notes = {}
    if not os.path.exists(STAGING_PATH):
        return notes
    with open(STAGING_PATH) as f:
        staging = json.load(f)
    for row in staging.get("rows", []):
        note = (row.get("note") or "").strip()
        if note:
            notes[normalize_holder(row.get("holder_name"))] = note
    return notes


def aggregate(db_path):
    """One entry per normalized holder name. READ-ONLY connection."""
    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM cois ORDER BY created_ts ASC, id ASC")]
    finally:
        conn.close()

    notes = load_staging_notes()
    holders = {}
    for r in rows:
        key = r["holder_name_norm"] or normalize_holder(r["holder_name"])
        h = holders.setdefault(key, {
            "key": key,
            "display_name": r["holder_name"],
            "clients": set(),
            "count": 0,
            "last_issued": "",
            "variants": {},          # norm_address -> variant dict
            "note": notes.get(key, ""),
        })
        h["count"] += 1
        h["clients"].add(r["client_id"] or "?")
        ts = r["created_ts"] or ""
        if ts >= h["last_issued"]:
            h["last_issued"] = ts
            h["display_name"] = r["holder_name"]  # most recent spelling wins

        akey = norm_address(r)
        v = h["variants"].setdefault(akey, {
            "count": 0, "last_used": "", "clients": set(),
            **{f: None for f in ADDR_FIELDS},
        })
        v["count"] += 1
        v["clients"].add(r["client_id"] or "?")
        if ts >= v["last_used"]:
            v["last_used"] = ts
            for f in ADDR_FIELDS:
                v[f] = r[f]

    out = []
    for h in holders.values():
        variants = sorted(h["variants"].values(),
                          key=lambda v: v["last_used"], reverse=True)
        for v in variants:
            v["clients"] = sorted(v["clients"])
        nonempty = [v for v in variants
                    if any((v[f] or "").strip() for f in ADDR_FIELDS)]
        h["variants"] = variants
        h["conflict"] = len(nonempty) > 1
        h["no_address"] = len(nonempty) == 0
        h["clients"] = sorted(h["clients"])
        h["category"] = categorize(h["key"])
        # prefill for the Edit panel: most recent variant with an address,
        # else the most recent variant outright
        h["prefill"] = {f: (nonempty[0][f] if nonempty else variants[0][f]) or ""
                        for f in ADDR_FIELDS}
        out.append(h)
    return out


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(s or "")


def variant_html(key, idx, v, conflict):
    lines = []
    if v["address_line_1"]:
        lines.append(esc(v["address_line_1"]))
    if v["address_line_2"]:
        lines.append(esc(v["address_line_2"]))
    csz = " ".join(filter(None, [v["city"],
                                 v["state"],
                                 v["zip"]]))
    if csz:
        lines.append(esc(csz))
    addr = "<br>".join(lines) or "<i>(no address on file)</i>"
    meta = (f"used {v['count']}&times; &middot; last {esc(v['last_used'][:10]) or '?'}"
            f" &middot; {esc(', '.join(v['clients']))}")
    pick = (f'<button class="pick" onclick="pickVariant(\'{key}\',{idx})">'
            f"Use this address</button>") if conflict else ""
    recent = '<span class="badge recent">most recent</span>' if idx == 0 else ""
    return (f'<div class="variant"><div class="addr">{addr}</div>'
            f'<div class="vmeta">{meta} {recent}</div>{pick}</div>')


def card_html(h, seq):
    key = h["key"]
    badges = []
    if h["conflict"]:
        badges.append('<span class="badge conflict">ADDRESS CONFLICT &mdash; pick one</span>')
    if h["no_address"]:
        badges.append('<span class="badge noaddr">NO ADDRESS ON FILE</span>')
    if h["note"]:
        badges.append('<span class="badge dq">DATA-QUALITY NOTE</span>')
    note_html = (f'<div class="dqnote">&#9888; {esc(h["note"])}</div>'
                 if h["note"] else "")
    variants = "".join(variant_html(key, i, v, h["conflict"])
                       for i, v in enumerate(h["variants"]))
    cat_opts = "".join(
        f'<option value="{c}"{" selected" if c == h["category"] else ""}>{label}</option>'
        for c, label in CATEGORIES)
    p = h["prefill"]
    edit_inputs = "".join(
        f'<input type="text" class="ef" id="ef_{f}_{seq}" placeholder="{f}" '
        f'value="{esc(p[f])}" size="{28 if f.startswith("address") else 10}">'
        for f in ADDR_FIELDS)
    return f"""
<div class="card holder" data-key="{key}" data-cat="{h['category']}" data-seq="{seq}">
  <div class="cardhead">
    <b class="hname">{esc(h['display_name'])}</b>
    {''.join(badges)}
    <span class="meta">issued {h['count']}&times; &middot; client{'s' if len(h['clients']) > 1 else ''}:
      {esc(', '.join(h['clients']))} &middot; last {esc(h['last_issued'][:10]) or '?'}</span>
  </div>
  {note_html}
  <div class="variants">{variants}</div>
  <div class="decide">
    <label><input type="radio" name="d{seq}" value="confirm" onchange="decide('{key}','confirm',{seq})"> Confirm &mdash; safe for autofill</label>
    <label><input type="radio" name="d{seq}" value="edit" onchange="decide('{key}','edit',{seq})"> Edit</label>
    <label><input type="radio" name="d{seq}" value="exclude" onchange="decide('{key}','exclude',{seq})"> Exclude &mdash; never autofill</label>
    <select class="catsel" onchange="setCat('{key}',this.value)">{cat_opts}</select>
    <input type="text" class="note" placeholder="note (optional)" onblur="setNote('{key}',this.value)">
  </div>
  <div class="editpanel" id="ep_{seq}">
    {edit_inputs}
    <button onclick="saveAddr('{key}',{seq})">Save correction</button>
    <span class="saved" id="sv_{seq}"></span>
  </div>
</div>"""


def main():
    db_path = DEFAULT_DB
    if "--db" in sys.argv:
        db_path = sys.argv[sys.argv.index("--db") + 1]

    holders = aggregate(db_path)

    by_cat = defaultdict(list)
    for h in holders:
        by_cat[h["category"]].append(h)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda h: (-h["count"], h["key"]))

    seq = 0
    sections = []
    for cat, label in CATEGORIES:
        cards = []
        for h in by_cat.get(cat, []):
            seq += 1
            cards.append(card_html(h, seq))
        n = len(by_cat.get(cat, []))
        sections.append(f"""
<div class="section" data-cat="{cat}">
  <h2>{label} <span class="seccount">({n})</span>
      <span class="secprog" id="prog_{cat}"></span></h2>
  {''.join(cards)}
</div>""")

    total = len(holders)
    n_conflicts = sum(1 for h in holders if h["conflict"])
    n_notes = sum(1 for h in holders if h["note"])
    variants_js = json.dumps(
        {h["key"]: [{f: v[f] for f in ADDR_FIELDS} for v in h["variants"]]
         for h in holders}, separators=(",", ":"))
    counts_line = " / ".join(
        f"{len(by_cat.get(c, []))} {label.lower()}" for c, label in CATEGORIES)

    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>COI Holder Review — A10a autofill gate</title>
<style>
 body {{ font-family: -apple-system, Helvetica, sans-serif; margin: 0; background: #f2f2f4; }}
 header {{ position: sticky; top: 0; background: #1c1c1e; color: #fff; padding: 10px 16px; z-index: 5;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
 header .sub {{ font-size: 12px; color: #b9b9c0; }}
 select, button, input[type=text] {{ font-size: 13px; padding: 4px 8px; }}
 .progress {{ margin-left: auto; font-size: 13px; }}
 h2 {{ margin: 22px 16px 4px 16px; font-size: 16px; color: #1c1c1e;
      border-bottom: 2px solid #d8d8dd; padding-bottom: 6px; }}
 .seccount {{ color: #8e8e93; font-weight: 400; }}
 .secprog {{ float: right; font-size: 12.5px; color: #2e7dd1; font-weight: 400; }}
 .card {{ background: #fff; margin: 10px 16px; border-radius: 8px; padding: 12px 14px;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }}
 .card.done {{ outline: 3px solid #1a7f3733; }}
 .card.done-exclude {{ outline: 3px solid #c6282833; }}
 .cardhead {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }}
 .hname {{ font-size: 14.5px; }}
 .meta {{ font-size: 11.5px; color: #8e8e93; }}
 .badge {{ color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
 .badge.conflict {{ background: #c62828; }}
 .badge.noaddr {{ background: #8e8e93; }}
 .badge.dq {{ background: #b58105; }}
 .badge.recent {{ background: #2e7dd1; font-weight: 500; font-size: 10px; }}
 .dqnote {{ background: #fff8e6; border-left: 4px solid #b58105; font-size: 12.5px;
            padding: 6px 10px; margin: 8px 0; border-radius: 0 6px 6px 0; }}
 .variants {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0; }}
 .variant {{ border: 1px solid #d8d8dd; border-radius: 6px; padding: 8px 10px; min-width: 220px;
             background: #fafafa; }}
 .variant .addr {{ font-size: 13px; line-height: 1.4; }}
 .variant .vmeta {{ font-size: 10.5px; color: #8e8e93; margin-top: 4px; }}
 .variant .pick {{ margin-top: 6px; font-size: 12px; cursor: pointer; }}
 .variant.picked {{ border-color: #1a7f37; background: #eefaf0; }}
 .decide {{ display: flex; gap: 14px; align-items: center; margin-top: 8px; font-size: 13px; flex-wrap: wrap; }}
 .decide .note {{ flex: 1; min-width: 200px; font-size: 12.5px; }}
 .catsel {{ font-size: 12px; }}
 .editpanel {{ display: none; margin-top: 8px; padding: 8px; background: #f5f8fd;
               border: 1px solid #c9d8ef; border-radius: 6px; }}
 .editpanel.open {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
 .editpanel .ef {{ font-size: 12.5px; }}
 .editpanel .saved {{ font-size: 12px; color: #1a7f37; }}
</style></head><body>
<header>
 <b>COI Holder Review</b>
 <span>{total} unique holders &mdash; {counts_line} &mdash; {n_conflicts} address conflict{'s' if n_conflicts != 1 else ''}, {n_notes} data-quality note{'s' if n_notes != 1 else ''}</span>
 <span class="sub">Confirm = address is right, safe for autofill &middot; Edit = fix it inline &middot; Exclude = never autofill</span>
 <button onclick="exportDecisions()">Export decisions JSON</button>
 <span class="progress" id="progress"></span>
</header>
{''.join(sections)}
<script>
const TOTAL = {total};
const VARIANTS = {variants_js};
const KEY = 'holder_review_decisions';
const store = JSON.parse(localStorage.getItem(KEY) || '{{}}');

function persist() {{
  localStorage.setItem(KEY, JSON.stringify(store));
  const decided = k => store[k] && store[k].decision;
  document.getElementById('progress').textContent =
    Object.keys(store).filter(decided).length + ' / ' + TOTAL + ' decided';
  document.querySelectorAll('.section').forEach(sec => {{
    const cards = sec.querySelectorAll('.card');
    let n = 0;
    cards.forEach(c => {{ if (decided(c.dataset.key)) n++; }});
    sec.querySelector('.secprog').textContent = n + ' / ' + cards.length + ' decided';
  }});
}}
function entry(k) {{ return store[k] = store[k] || {{}}; }}
function markCard(k) {{
  const card = document.querySelector('.card[data-key="' + CSS.escape(k) + '"]');
  const d = (store[k] || {{}}).decision;
  card.classList.toggle('done', !!d && d !== 'exclude');
  card.classList.toggle('done-exclude', d === 'exclude');
}}
function decide(k, v, seq) {{
  const e = entry(k);
  e.decision = v;
  if (v !== 'edit') delete e.corrected_address;
  document.getElementById('ep_' + seq).classList.toggle('open', v === 'edit');
  markCard(k); persist();
}}
function saveAddr(k, seq) {{
  const e = entry(k);
  e.decision = 'edit';
  e.corrected_address = {{}};
  ['address_line_1','address_line_2','city','state','zip'].forEach(f => {{
    const val = document.getElementById('ef_' + f + '_' + seq).value.trim();
    e.corrected_address[f] = val || null;
  }});
  document.getElementById('sv_' + seq).textContent = 'saved';
  markCard(k); persist();
}}
function pickVariant(k, idx) {{
  const card = document.querySelector('.card[data-key="' + CSS.escape(k) + '"]');
  const seq = card.dataset.seq;
  const v = VARIANTS[k][idx];
  ['address_line_1','address_line_2','city','state','zip'].forEach(f => {{
    document.getElementById('ef_' + f + '_' + seq).value = v[f] || '';
  }});
  const e = entry(k);
  e.decision = 'edit';
  e.corrected_address = {{}};
  ['address_line_1','address_line_2','city','state','zip'].forEach(f => {{
    e.corrected_address[f] = v[f] || null;
  }});
  const r = card.querySelector('input[value="edit"]');
  if (r) r.checked = true;
  document.getElementById('ep_' + seq).classList.add('open');
  card.querySelectorAll('.variant').forEach((el, i) =>
    el.classList.toggle('picked', i === idx));
  markCard(k); persist();
}}
function setCat(k, v) {{ entry(k).category = v; persist(); }}
function setNote(k, v) {{
  const e = entry(k);
  if (v.trim()) e.note = v.trim(); else delete e.note;
  persist();
}}
function exportDecisions() {{
  const out = {{}};
  const FIELDS = ['decision', 'corrected_address', 'category', 'note'];
  Object.keys(store).forEach(k => {{
    const e = store[k];
    if (!e || !e.decision) return;
    out[k] = {{}};
    FIELDS.forEach(f => {{ if (e[f] !== undefined) out[k][f] = e[f]; }});
  }});
  const blob = new Blob([JSON.stringify(out, null, 1)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'holder_review_decisions.json'; a.click();
}}
// restore prior state
document.querySelectorAll('.card').forEach(card => {{
  const k = card.dataset.key, seq = card.dataset.seq, d = store[k];
  if (!d) return;
  if (d.decision) {{
    const r = card.querySelector('input[value="' + d.decision + '"]');
    if (r) r.checked = true;
    if (d.decision === 'edit') {{
      document.getElementById('ep_' + seq).classList.add('open');
      if (d.corrected_address) {{
        ['address_line_1','address_line_2','city','state','zip'].forEach(f => {{
          document.getElementById('ef_' + f + '_' + seq).value = d.corrected_address[f] || '';
        }});
      }}
    }}
    markCard(k);
  }}
  if (d.category) card.querySelector('.catsel').value = d.category;
  if (d.note) card.querySelector('.note').value = d.note;
}});
persist();
</script></body></html>"""

    with open(OUT_PATH, "w") as f:
        f.write(page)
    print(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e3:.0f} KB)")
    print(f"  {total} unique holders; " + "; ".join(
        f"{len(by_cat.get(c, []))} {c}" for c, _ in CATEGORIES))
    print(f"  {n_conflicts} address conflicts, {n_notes} data-quality notes")


if __name__ == "__main__":
    main()
