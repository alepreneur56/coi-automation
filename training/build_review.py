"""
build_review.py — A3 step 3: generate the human review page for Alex.

Reads training/graded_cois.json, renders three crops per COI (date box,
certificate holder box, description of operations) with the same anchored
geometry the grader used, and writes a single self-contained HTML file with
Approve / Disagree / Skip controls per COI. Decisions persist in
localStorage; the Export button downloads a decisions JSON that feeds the
training-library builder.

Usage: .venv/bin/python training/build_review.py
Output: training/coi_review.html
"""

import base64
import html
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

from training.grade_cois import detect_regions  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_PATH = os.path.join(BASE, "training", "graded_cois.json")
OUT_PATH = os.path.join(BASE, "training", "coi_review.html")

DPI = 110


def render_crops(path):
    """Returns dict of base64 JPEG crops keyed by zone name."""
    try:
        doc = fitz.open(path)
        page = doc[0]
        holder_clip, desc_clip, date_clip = detect_regions(page)
        zoom = DPI / 72.0
        crops = {}
        for name, clip in (("date", date_clip), ("holder", holder_clip), ("desc", desc_clip)):
            clip = fitz.Rect(clip) & page.rect
            if clip.is_empty:
                continue
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
            crops[name] = base64.b64encode(pix.tobytes("jpg", jpg_quality=62)).decode()
        doc.close()
        return crops
    except Exception:
        return {}


VERDICT_COLORS = {"correct": "#1a7f37", "questionable": "#b58105", "incorrect": "#c62828"}


def main():
    with open(IN_PATH) as f:
        data = json.load(f)
    records = data["records"]
    # Order: incorrect first (most important for Alex), then questionable, correct
    order = {"incorrect": 0, "questionable": 1, "correct": 2}
    records.sort(key=lambda r: (order[r["verdict"]], r["client"]))

    cards = []
    for i, rec in enumerate(records):
        crops = render_crops(rec["path"])
        problems_html = "".join(
            f'<li class="sev-{p["severity"]}"><b>{p["code"]} {p["severity"]}</b> — {html.escape(p["message"])}</li>'
            for p in rec["problems"]
        ) or "<li class='sev-OK'>no issues found by the automated checks</li>"
        req = html.escape(rec.get("request_excerpt") or "(no request text found in the archive for this thread — sent-items only)")
        imgs = "".join(
            f'<div class="zone"><div class="zlabel">{z}</div><img src="data:image/jpeg;base64,{b64}"></div>'
            for z, b64 in crops.items()
        )
        std = ("<span class='badge std-yes'>meets current standard</span>"
               if rec.get("meets_current_standard")
               else "<span class='badge std-no'>pre-standard format</span>")
        vcol = VERDICT_COLORS[rec["verdict"]]
        pdf_href = "file://" + rec["path"].replace(" ", "%20")
        cards.append(f"""
<div class="card" data-client="{rec['client']}" data-verdict="{rec['verdict']}" data-hash="{rec['hash']}">
  <div class="cardhead">
    <span class="badge verdict" style="background:{vcol}">{rec['verdict'].upper()}</span>
    {std}
    <span class="client">{rec['client']}</span>
    <a class="fname" href="{pdf_href}" target="_blank" title="open the PDF">{html.escape(rec['filename'])}</a>
    <span class="fdate">{html.escape(rec.get('message_date') or '')}</span>
  </div>
  <div class="zones">{imgs}</div>
  <details><summary>Automated findings ({len(rec['problems'])}) + request excerpt</summary>
    <ul class="problems">{problems_html}</ul>
    <div class="request"><b>Request excerpt:</b><br>{req}</div>
  </details>
  <div class="decide">
    <label><input type="radio" name="d{i}" value="approve" onchange="save('{rec['hash']}','approve')"> Agree with verdict</label>
    <label><input type="radio" name="d{i}" value="disagree" onchange="save('{rec['hash']}','disagree')"> Disagree</label>
    <label><input type="radio" name="d{i}" value="skip" onchange="save('{rec['hash']}','skip')"> Skip</label>
    <input type="text" class="note" placeholder="why? (optional note)" onblur="note('{rec['hash']}',this.value)">
  </div>
</div>""")

    counts = data["counts"]
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>COI Training Review — {len(records)} certificates</title>
<style>
 body {{ font-family: -apple-system, Helvetica, sans-serif; margin: 0; background: #f2f2f4; }}
 header {{ position: sticky; top: 0; background: #1c1c1e; color: #fff; padding: 10px 16px; z-index: 5;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
 header b {{ font-size: 15px; }}
 select, button {{ font-size: 13px; padding: 4px 8px; }}
 .progress {{ margin-left: auto; font-size: 13px; }}
 .card {{ background: #fff; margin: 12px 16px; border-radius: 8px; padding: 12px 14px;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }}
 .cardhead {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }}
 .badge {{ color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
 .std-yes {{ background: #2e7dd1; }} .std-no {{ background: #8e8e93; }}
 .client {{ font-weight: 600; font-size: 13px; }}
 .fname {{ font-size: 12px; color: #2e7dd1; text-decoration: none; max-width: 420px;
           overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
 .fdate {{ font-size: 11px; color: #8e8e93; }}
 .zones {{ display: flex; gap: 10px; margin: 10px 0; flex-wrap: wrap; }}
 .zone img {{ max-width: 560px; max-height: 150px; border: 1px solid #d0d0d5; display: block; }}
 .zlabel {{ font-size: 10px; color: #8e8e93; text-transform: uppercase; margin-bottom: 2px; }}
 .problems li {{ font-size: 12.5px; margin: 2px 0; }}
 .sev-FAIL {{ color: #c62828; }} .sev-WARN {{ color: #b58105; }} .sev-INFO {{ color: #666; }} .sev-OK {{ color: #1a7f37; }}
 .request {{ font-size: 12px; background: #f6f6f8; padding: 8px; border-radius: 6px; margin-top: 6px;
             white-space: pre-wrap; max-height: 180px; overflow-y: auto; }}
 .decide {{ display: flex; gap: 16px; align-items: center; margin-top: 8px; font-size: 13px; flex-wrap: wrap; }}
 .decide .note {{ flex: 1; min-width: 220px; padding: 4px 6px; font-size: 12.5px; }}
 details summary {{ font-size: 12.5px; color: #444; cursor: pointer; }}
 .done {{ outline: 3px solid #1a7f3733; }}
</style></head><body>
<header>
 <b>COI Training Review</b>
 <span>{len(records)} certificates — {counts['incorrect']} incorrect / {counts['questionable']} questionable / {counts['correct']} correct</span>
 <select id="fclient" onchange="filter()"><option value="">all clients</option>
  {''.join(f'<option>{c}</option>' for c in sorted({r["client"] for r in records}))}</select>
 <select id="fverdict" onchange="filter()"><option value="">all verdicts</option>
  <option>incorrect</option><option>questionable</option><option>correct</option></select>
 <button onclick="exportDecisions()">Export decisions JSON</button>
 <span class="progress" id="progress"></span>
</header>
{''.join(cards)}
<script>
const store = JSON.parse(localStorage.getItem('coi_decisions') || '{{}}');
function persist() {{
  localStorage.setItem('coi_decisions', JSON.stringify(store));
  const n = Object.values(store).filter(d => d.decision).length;
  document.getElementById('progress').textContent = n + ' / {len(records)} reviewed';
}}
function save(h, v) {{ (store[h] = store[h] || {{}}).decision = v; persist();
  document.querySelector('[data-hash="'+h+'"]').classList.add('done'); }}
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
// restore prior decisions into the UI
document.querySelectorAll('.card').forEach((el, i) => {{
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
    print(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e6:.1f} MB, {len(records)} cards)")


if __name__ == "__main__":
    main()
