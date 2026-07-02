"""
build_review.py — A3 step 3: generate the human review page for Alex.

THREAD-CENTRIC version: one card per email thread, showing the complete
back-and-forth (client messages and team replies in order, full bodies),
every attachment clickable where it appeared (labeled "came with request"
vs "sent in response"), and for each delivered COI: issue-date crop, FULL
certificate-holder box, FULL description-of-operations box, verdict and
findings, with Agree / Disagree / Skip controls.

Decisions persist in localStorage (keyed by COI content hash); the Export
button downloads a decisions JSON that feeds the training-library builder.

Usage: .venv/bin/python training/build_review.py
Output: training/coi_review.html
"""

import base64
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

from training.grade_cois import _spans, find_label  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")
IDX_PATH = os.path.join(BASE, "training", "corpus_index.json")
OUT_PATH = os.path.join(BASE, "training", "coi_review.html")

DPI = 120
TEAM_HINTS = ("alejandro bello", "jade harris", "laura rodriguez")


def full_regions(page):
    """FULL holder box and FULL DoO box (label to label, border to border),
    plus the date box. More generous than the grader's analysis clips."""
    spans = _spans(page)
    W, H = page.rect.width, page.rect.height

    ch = find_label(spans, lambda t: t.upper().startswith("CERTIFICATE HOLDER") and t.upper() == t)
    canc = find_label(spans, lambda t: t.upper().startswith("CANCELLATION") and t.upper() == t)
    desc = find_label(spans, lambda t: t.upper().startswith("DESCRIPTION OF OPERATIONS"))
    date_lbl = find_label(spans, lambda t: "DATE (MM/DD/YYYY)" in t.upper())

    # FULL holder box: from the CERTIFICATE HOLDER label down to page bottom
    # margin (the ACORD footer), full left column width.
    if ch is not None:
        right = canc.x0 - 2 if canc is not None else min(312, W * 0.53)
        holder = fitz.Rect(max(ch.x0 - 6, 8), ch.y0 - 2, right, min(ch.y1 + 105, H - 28))
    else:
        holder = fitz.Rect(12, 650, 312, 760)

    # FULL DoO box: from the DESCRIPTION label down to the CERTIFICATE HOLDER
    # section, full page width. Layouts vary (Epic, portals, our templates),
    # so after anchoring we EXTEND the bottom until no text line is sliced.
    if desc is not None:
        candidates = []
        if ch is not None and ch.y0 > desc.y1:
            candidates.append(ch.y0 - 2)
        if canc is not None and canc.y0 > desc.y1:
            candidates.append(canc.y0 - 2)
        bottom = min(candidates) if candidates else min(desc.y1 + 110, H - 28)
        left = max(desc.x0 - 6, 8)
        # straddle-extension: any span that starts inside the region but
        # crosses the bottom edge means the anchor was wrong — grow past it
        for _ in range(6):
            grew = False
            for sp in spans:
                r = fitz.Rect(sp["bbox"])
                if not sp["text"].strip():
                    continue
                if r.x0 >= left and r.x0 < W - 10 and desc.y1 < r.y0 < bottom + 1 and r.y1 > bottom:
                    bottom = r.y1 + 2
                    grew = True
            if not grew:
                break
        doo = fitz.Rect(left, desc.y0 - 2, W - 10, min(bottom, H - 20))
    else:
        doo = fitz.Rect(12, 560, 600, 662)

    if date_lbl is not None and date_lbl.y0 < 120:
        date = fitz.Rect(date_lbl.x0 - 8, date_lbl.y0 - 4, date_lbl.x1 + 14, date_lbl.y1 + 24)
    else:
        date = fitz.Rect(495, 18, 600, 54)

    return date, holder, doo


def render_coi_crops(path):
    try:
        doc = fitz.open(path)
        page = doc[0]
        date, holder, doo = full_regions(page)
        zoom = DPI / 72.0
        crops = {}
        for name, clip in (("issue date", date), ("certificate holder box (full)", holder),
                           ("description of operations (full)", doo)):
            clip = fitz.Rect(clip) & page.rect
            if clip.is_empty:
                continue
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
            crops[name] = base64.b64encode(pix.tobytes("jpg", jpg_quality=64)).decode()
        doc.close()
        return crops
    except Exception:
        return {}


def is_team_message(msg):
    frm = (msg.get("from") or "").lower()
    if "(sent)" in frm or msg.get("folder") == "Sent Items":
        return True
    if any(h in frm for h in TEAM_HINTS):
        return True
    body_head = (msg.get("body") or "")[:300].lower()
    return "attached please find" in body_head


def clean_body(body):
    """Trim quoted history and export junk, then normalize whitespace so the
    message reads like an email instead of a text dump."""
    if not body:
        return ""
    body = re.sub(r"P \{margin-top:0;margin-bottom:0;?\}", "", body)
    body = body.replace(" ", " ").replace("�", "'")
    # cut at the first quoted-reply marker to keep each message's OWN text
    cut = re.search(r"\n\s*(From|Sent|De):\s.{0,80}(<|@)", body)
    if cut and cut.start() > 40:
        body = body[:cut.start()] + "\n\n[... quoted history trimmed ...]"
    # normalize: strip per-line noise, collapse space runs and blank-line runs
    lines = []
    for line in body.splitlines():
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:3500]


VERDICT_COLORS = {"correct": "#1a7f37", "questionable": "#b58105", "incorrect": "#c62828"}


def file_href(path):
    from urllib.parse import quote
    return "file://" + quote(path)


def main():
    with open(GRADED_PATH) as f:
        graded = json.load(f)
    with open(IDX_PATH) as f:
        idx = json.load(f)

    graded_by_path = {r["path"]: r for r in graded["records"]}

    # Threads that contain at least one graded COI
    order = {"incorrect": 0, "questionable": 1, "correct": 2}
    thread_cards = []
    used_paths = set()

    for tkey, msgs in idx["threads"].items():
        coi_recs = []
        for m in msgs:
            for a in m.get("attachments", []):
                if a["path"] in graded_by_path:
                    coi_recs.append(graded_by_path[a["path"]])
        if not coi_recs:
            continue
        worst = min(order[r["verdict"]] for r in coi_recs)
        thread_cards.append((worst, tkey, msgs, coi_recs))
        used_paths.update(r["path"] for r in coi_recs)

    thread_cards.sort(key=lambda t: (t[0], t[1]))

    # Graded COIs whose thread linkage failed (orphans) still need review
    orphans = [r for r in graded["records"] if r["path"] not in used_paths]

    radio_seq = 0
    all_hashes = set()

    def coi_block(rec, role_label="", is_final=False):
        nonlocal radio_seq
        radio_seq += 1
        all_hashes.add(rec["hash"])
        role_html = ""
        if role_label:
            color = "#1a7f37" if "DELIVERED" in role_label else "#2e7dd1"
            role_html = f'<span class="badge" style="background:{color}">{role_label}</span>'
        if is_final:
            role_html += ' <span class="badge" style="background:#5b21b6">FINAL DELIVERED VERSION</span>'
        crops = render_coi_crops(rec["path"])
        imgs = "".join(
            f'<div class="zone"><div class="zlabel">{z}</div>'
            f'<img src="data:image/jpeg;base64,{b64}"></div>'
            for z, b64 in crops.items()
        )
        problems_html = "".join(
            f'<li class="sev-{p["severity"]}"><b>{p["code"]} {p["severity"]}</b> — {html.escape(p["message"])}</li>'
            for p in rec["problems"]
        ) or "<li class='sev-OK'>no issues found by the automated checks</li>"
        std = ("<span class='badge std-yes'>meets current standard</span>"
               if rec.get("meets_current_standard")
               else "<span class='badge std-no'>pre-standard format</span>")
        vcol = VERDICT_COLORS[rec["verdict"]]
        return f"""
  <div class="coigrade" data-hash="{rec['hash']}">
    <div class="cardhead">
      {role_html}
      <span class="badge verdict" style="background:{vcol}">{rec['verdict'].upper()}</span>
      {std}
      <a class="fname" href="{file_href(rec['path'])}" target="_blank">{html.escape(rec['filename'])}</a>
    </div>
    <div class="zones">{imgs}</div>
    <details><summary>Automated findings ({len(rec['problems'])})</summary>
      <ul class="problems">{problems_html}</ul></details>
    <div class="decide">
      <label><input type="radio" name="d{radio_seq}" value="approve" onchange="save('{rec['hash']}','approve')"> Agree with verdict</label>
      <label><input type="radio" name="d{radio_seq}" value="disagree" onchange="save('{rec['hash']}','disagree')"> Disagree</label>
      <label><input type="radio" name="d{radio_seq}" value="skip" onchange="save('{rec['hash']}','skip')"> Skip</label>
      <input type="text" class="note" placeholder="why? (optional note)" onblur="note('{rec['hash']}',this.value)">
    </div>
  </div>"""

    cards = []
    for worst, tkey, msgs, coi_recs in thread_cards:
        clients = sorted({r["client"] for r in coi_recs})
        verdict_name = ["incorrect", "questionable", "correct"][worst]
        vcol = VERDICT_COLORS[verdict_name]

        timeline = []
        rendered_paths = set()
        # the LAST team-delivered graded COI in the thread is the final version
        final_path = None
        for m in msgs:
            if is_team_message(m):
                for a in m.get("attachments", []):
                    if a["path"] in graded_by_path:
                        final_path = a["path"]
        for m in msgs:
            team = is_team_message(m)
            who = "YOUR TEAM" if team else "CLIENT / REQUESTER"
            body = clean_body(m.get("body"))
            body_html = html.escape(body) if body else "<i>(no body — sent-items export has attachments only)</i>"
            att_links = []
            for a in m.get("attachments", []):
                label = "sent in response" if team else "came with request"
                icon = "&#128206;"
                att_links.append(
                    f'<a class="att {"team" if team else "client"}" href="{file_href(a["path"])}" '
                    f'target="_blank">{icon} {html.escape(a["name"])}</a>'
                    f'<span class="attlabel">({label})</span>'
                )
            coi_blocks = ""
            for a in m.get("attachments", []):
                rec = graded_by_path.get(a["path"])
                if rec and a["path"] not in rendered_paths:
                    rendered_paths.add(a["path"])
                    role = ("DELIVERED COI" if team
                            else "CLIENT-PROVIDED COI (reference/old cert)")
                    coi_blocks += coi_block(rec, role_label=role,
                                            is_final=(a["path"] == final_path))
            timeline.append(f"""
  <div class="msg {'team' if team else 'client'}">
    <div class="msghead"><span class="who">{who}</span>
      <span class="mfrom">{html.escape(m.get('from') or '')}</span>
      <span class="mdate">{html.escape(m.get('date') or '')}</span>
      <span class="msubj">{html.escape(m.get('subject') or '')}</span></div>
    <div class="mbody">{body_html}</div>
    <div class="atts">{''.join(att_links)}</div>
    {coi_blocks}
  </div>""")

        # COIs in this thread whose message linkage was ambiguous
        for rec in coi_recs:
            if rec["path"] not in rendered_paths:
                rendered_paths.add(rec["path"])
                timeline.append(coi_block(rec))

        cards.append(f"""
<div class="card" data-client="{clients[0]}" data-verdict="{verdict_name}">
  <div class="cardhead threadhead">
    <span class="badge verdict" style="background:{vcol}">worst: {verdict_name.upper()}</span>
    <span class="client">{', '.join(clients)}</span>
    <b class="tsubj">{html.escape(tkey or '(no subject)')}</b>
    <span class="fdate">{len(msgs)} message(s), {len(coi_recs)} COI(s)</span>
  </div>
  <div class="timeline">{''.join(timeline)}</div>
</div>""")

    for rec in sorted(orphans, key=lambda r: order[r["verdict"]]):
        cards.append(f"""
<div class="card" data-client="{rec['client']}" data-verdict="{rec['verdict']}">
  <div class="cardhead threadhead">
    <span class="badge" style="background:#8e8e93">NO THREAD CONTEXT</span>
    <span class="client">{rec['client']}</span></div>
  {coi_block(rec)}
</div>""")

    counts = graded["counts"]
    total = len(all_hashes)
    all_clients = sorted({r["client"] for r in graded["records"]})
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>COI Training Review — threads</title>
<style>
 body {{ font-family: -apple-system, Helvetica, sans-serif; margin: 0; background: #f2f2f4; }}
 header {{ position: sticky; top: 0; background: #1c1c1e; color: #fff; padding: 10px 16px; z-index: 5;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
 select, button {{ font-size: 13px; padding: 4px 8px; }}
 .progress {{ margin-left: auto; font-size: 13px; }}
 .card {{ background: #fff; margin: 14px 16px; border-radius: 8px; padding: 12px 14px;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }}
 .cardhead {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }}
 .threadhead {{ border-bottom: 2px solid #e5e5ea; padding-bottom: 8px; }}
 .tsubj {{ font-size: 14px; }}
 .badge {{ color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
 .std-yes {{ background: #2e7dd1; }} .std-no {{ background: #8e8e93; }}
 .client {{ font-weight: 600; font-size: 13px; }}
 .fname {{ font-size: 12.5px; color: #2e7dd1; text-decoration: none; }}
 .fdate {{ font-size: 11px; color: #8e8e93; }}
 .msg {{ margin: 10px 0 10px 0; padding: 8px 12px; border-radius: 8px; }}
 .msg.client {{ background: #eef3fb; border-left: 4px solid #2e7dd1; margin-right: 60px; }}
 .msg.team {{ background: #eefaf0; border-left: 4px solid #1a7f37; margin-left: 60px; }}
 .msghead {{ font-size: 11.5px; color: #555; display: flex; gap: 10px; flex-wrap: wrap; }}
 .who {{ font-weight: 700; }}
 .msg.client .who {{ color: #2e7dd1; }} .msg.team .who {{ color: #1a7f37; }}
 .mbody {{ font-size: 12.5px; white-space: pre-wrap; margin: 6px 0; max-height: 260px; overflow-y: auto; }}
 .atts {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
 .att {{ font-size: 12px; text-decoration: none; background: #fff; border: 1px solid #c9c9ce;
         border-radius: 5px; padding: 3px 8px; color: #1c1c1e; }}
 .attlabel {{ font-size: 10.5px; color: #8e8e93; margin-right: 8px; }}
 .coigrade {{ border: 1px solid #d8d8dd; border-radius: 8px; padding: 10px; margin-top: 10px; background: #fff; }}
 .zones {{ display: flex; gap: 12px; margin: 10px 0; flex-wrap: wrap; }}
 .zone img {{ max-width: 900px; width: 100%; border: 1px solid #d0d0d5; display: block; }}
 .zone {{ max-width: 900px; }}
 .zlabel {{ font-size: 10px; color: #8e8e93; text-transform: uppercase; margin-bottom: 2px; }}
 .problems li {{ font-size: 12.5px; margin: 2px 0; }}
 .sev-FAIL {{ color: #c62828; }} .sev-WARN {{ color: #b58105; }} .sev-INFO {{ color: #666; }} .sev-OK {{ color: #1a7f37; }}
 .decide {{ display: flex; gap: 16px; align-items: center; margin-top: 8px; font-size: 13px; flex-wrap: wrap; }}
 .decide .note {{ flex: 1; min-width: 220px; padding: 4px 6px; font-size: 12.5px; }}
 details summary {{ font-size: 12.5px; color: #444; cursor: pointer; }}
 .coigrade.done {{ outline: 3px solid #1a7f3733; }}
</style></head><body>
<header>
 <b>COI Training Review</b>
 <span>{len(thread_cards)} threads / {total} unique COIs — {counts['incorrect']} incorrect / {counts['questionable']} questionable / {counts['correct']} correct</span>
 <select id="fclient" onchange="filter()"><option value="">all clients</option>
  {''.join(f'<option>{c}</option>' for c in all_clients)}</select>
 <select id="fverdict" onchange="filter()"><option value="">all verdicts</option>
  <option>incorrect</option><option>questionable</option><option>correct</option></select>
 <button onclick="exportDecisions()">Export decisions JSON</button>
 <span class="progress" id="progress"></span>
</header>
{''.join(cards)}
<script>
const TOTAL = {total};
const store = JSON.parse(localStorage.getItem('coi_decisions') || '{{}}');
function persist() {{
  localStorage.setItem('coi_decisions', JSON.stringify(store));
  const n = new Set(Object.keys(store).filter(h => store[h].decision)).size;
  document.getElementById('progress').textContent = n + ' / ' + TOTAL + ' reviewed';
}}
function save(h, v) {{ (store[h] = store[h] || {{}}).decision = v; persist();
  document.querySelectorAll('[data-hash="'+h+'"]').forEach(el => el.classList.add('done')); }}
function note(h, v) {{ (store[h] = store[h] || {{}}).note = v; persist(); }}
function filter() {{
  const c = document.getElementById('fclient').value, v = document.getElementById('fverdict').value;
  document.querySelectorAll('.card').forEach(el => {{
    el.style.display = ((!c || el.dataset.client === c) && (!v || el.dataset.verdict === v)) ? '' : 'none';
  }});
}}
function exportDecisions() {{
  const blob = new Blob([JSON.stringify(store, null, 1)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'coi_review_decisions.json'; a.click();
}}
document.querySelectorAll('.coigrade').forEach(el => {{
  const d = store[el.dataset.hash];
  if (d && d.decision) {{
    el.classList.add('done');
    const r = el.querySelector('input[value="' + d.decision + '"]');
    if (r) r.checked = true;
    if (d.note) el.querySelector('.note').value = d.note;
  }}
}});
persist();
</script></body></html>"""

    with open(OUT_PATH, "w") as f:
        f.write(page)
    print(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e6:.1f} MB, "
          f"{len(thread_cards)} thread cards, {len(orphans)} orphan COIs)")


if __name__ == "__main__":
    main()
