"""
build_review.py — A3 step 3: generate the human review page for Alex.

PAIRED version: the page has TWO sections.

Section 1 — "Delivery review": every COI that has recoverable request
context shows the client's request email (subject, sender, date, full body
— and the whole thread timeline when there are several messages) SIDE BY
SIDE with the delivered COI crops (issue date, producer band, full holder
box, full DoO box) and the Agree / Disagree / Skip controls.

Request context is recovered from three sources, in order of directness:
  1. inbound (non-team) message bodies already in corpus_index.json;
  2. the raw archive: the Sent-Items export carries no bodies and its
     folder-name subjects keep "RE_"/"FW_" prefixes that normalize_subject
     never stripped, so sent-only threads failed to merge with the inbox
     threads holding the actual request. We re-scan Inbox + Deleted Items
     (ALL messages, not just COI-pattern matches) and fuzzy-match subjects
     (prefix match, truncation-tolerant) to pull those requests back in;
  3. quoted history inside a team reply (the client's request travels in
     the "From: ..." quote block).

Section 2 — "No request on file — template quality check only": COIs with
no recoverable request. No Agree/Disagree on the delivery decision (there
is nothing to judge it against); instead one simpler question: "Does this
COI meet current template standards?" (Yes / No + note).

Decisions persist in localStorage under the SAME key scheme as before
('coi_decisions', keyed by COI content hash) and the export is the same
flat {hash: {decision, note}} JSON, so earlier saved decisions carry over.
Section-2 answers use decision values 'std_yes' / 'std_no' (the library
builder treats unknown decisions as skip, so they are safely inert there).

Usage: .venv/bin/python training/build_review.py
Output: training/coi_review.html
"""

import base64
import html
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

from training.grade_cois import _spans, find_label, find_desc_label  # noqa: E402
from training.mine_corpus import ARCHIVE, parse_message  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")
IDX_PATH = os.path.join(BASE, "training", "corpus_index.json")
OUT_PATH = os.path.join(BASE, "training", "coi_review.html")

DPI = 120
TEAM_HINTS = ("alejandro bello", "jade harris", "laura rodriguez")

# archive recovery: fuzzy-subject matches need at least this much subject
# (after stripping RE/FW noise) so "re: coi" can't match everything
MIN_FUZZ = 12
# recovered messages must land within this many days of the thread activity
DATE_WINDOW_DAYS = 120

JUNK_SUBJECT = re.compile(r"automatic reply|out of office|undeliverable", re.I)


def full_regions(page):
    """FULL holder box and FULL DoO box (label to label, border to border),
    plus the date box. More generous than the grader's analysis clips."""
    spans = _spans(page)
    W, H = page.rect.width, page.rect.height

    ch = find_label(spans, lambda t: t.upper().startswith("CERTIFICATE HOLDER") and t.upper() == t)
    canc = find_label(spans, lambda t: t.upper().startswith("CANCELLATION") and t.upper() == t)
    desc = find_desc_label(spans)
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


def producer_region(page, spans):
    """The PRODUCER band at the top of the ACORD (producer + contact block):
    from the PRODUCER label down to the INSURED label."""
    prod = find_label(spans, lambda t: t.upper().startswith("PRODUCER"))
    insured = find_label(spans, lambda t: t.upper() == "INSURED")
    W = page.rect.width
    if prod is not None:
        bottom = insured.y0 - 2 if (insured is not None and insured.y0 > prod.y1) else prod.y1 + 55
        return fitz.Rect(max(prod.x0 - 6, 8), prod.y0 - 2, W - 10, bottom)
    return fitz.Rect(12, 78, W - 10, 135)


def render_coi_crops(path):
    """Returns (crops dict, prepared_by string)."""
    try:
        doc = fitz.open(path)
        page = doc[0]
        spans = _spans(page)
        date, holder, doo = full_regions(page)
        prod = producer_region(page, spans)
        prod_text = page.get_text(clip=prod).lower()
        if "usi insurance" in prod_text or "alejandro bello" in prod_text:
            prepared_by = "usi"
        elif prod_text.strip():
            prepared_by = "external"
        else:
            prepared_by = "unknown"
        zoom = DPI / 72.0
        crops = {}
        for name, clip in (("issue date", date),
                           ("producer / prepared by", prod),
                           ("certificate holder box (full)", holder),
                           ("description of operations (full)", doo)):
            clip = fitz.Rect(clip) & page.rect
            if clip.is_empty:
                continue
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
            crops[name] = base64.b64encode(pix.tobytes("jpg", jpg_quality=64)).decode()
        doc.close()
        return crops, prepared_by
    except Exception:
        return {}, "unknown"


def is_team_message(msg):
    frm = (msg.get("from") or "").lower()
    if "(sent)" in frm or msg.get("folder") == "Sent Items":
        return True
    if any(h in frm for h in TEAM_HINTS):
        return True
    body_head = (msg.get("body") or "")[:300].lower()
    return "attached please find" in body_head


DISCLAIMER_PATTERNS = [
    r"This e-?mail and any files transmitted[^.]*\.(\s*It is solely[^.]*\.)?",
    r"If you receive(d)? this e-?mail in error[^.]*\.",
    r"do not disclose, copy, distribute[^.]*\.",
    r"(and )?delete it from your system\.?",
    r"Any other use of this e-?mail is prohibited\.?",
    r"Thank you for your compliance\.?",
    r"Confidentiality Notice:.{0,600}?original message\.\s*(Thank [Yy]ou\.?)?",
    r"Please note that you may not rely on email communication[^.]*\.",
    r"[A-Za-z ]+would love your feedback\. Post a Review to our profile\.\s*\S*",
    r"even if addressed incorrectly\.?",
    r"please notify the sender;?",
    r"or take any action in reliance on the contents of this information;?",
]

QUOTE_HEAD = re.compile(r"(From|De)\s*:\s*[^:]{0,80}?(<[^>]+@[^>]+>|@)", re.I)


def _strip_noise(text):
    # Outlook/Word CSS + VML fragments (e.g. "v\:* {behavior:url(#default#VML);}")
    text = re.sub(r"[\w.\\:*#\- ]{0,24}\{[^{}]{0,220}\}", " ", text)
    text = text.replace("\u00a0", " ").replace("\ufffd", "'")
    for pat in DISCLAIMER_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.I)
    return text


def _rebreak_headers(text):
    """The export flattens quoted messages onto single lines. Re-insert line
    breaks so From/Sent/To/Cc/Subject read like an email header block."""
    text = QUOTE_HEAD.sub(lambda m: "\n\n" + m.group(0), text)
    for h in ("Sent", "To", "Cc", "Subject", "Importance", "Enviado", "Para", "Asunto"):
        text = re.sub(rf"(?<!\n)\s(?={h}\s*:\s)", "\n", text)
    # a quoted body often runs straight on after the Subject line — break at
    # the first greeting-like word so the message text starts on its own line
    text = re.sub(
        r"((?:Subject|Asunto)\s*:[^\n]{0,140}?)\s"
        r"(?=(Hello|Hi |Hey |Good (morning|afternoon|evening)|Dear |Thank you|"
        r"Thanks|Attached|Please|Following|Buenas|Buenos|Hola)\b)",
        r"\1\n\n", text)
    return text


def _paragraphs(text):
    lines = [re.sub(r"[ \t]{2,}", " ", l).strip() for l in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def clean_body(body):
    """Returns (own_text, quoted_text): the message's own words, and the
    quoted/forwarded history it carried (both cleaned and re-broken)."""
    if not body:
        return "", ""
    body = _rebreak_headers(_strip_noise(body))
    m = QUOTE_HEAD.search(body)
    if m and m.start() > 30:
        own, quoted = body[:m.start()], body[m.start():]
    else:
        own, quoted = body, ""
    return _paragraphs(own)[:3000], _paragraphs(quoted)[:6000]


VERDICT_COLORS = {"correct": "#1a7f37", "questionable": "#b58105", "incorrect": "#c62828"}


def file_href(path):
    from urllib.parse import quote
    return "file://" + quote(path)


# ------------------------------------------------------- request recovery

def fuzz_subject(s):
    """Aggressive subject key for cross-folder matching: strips RE/FW noise
    including the underscore variants the Sent-Items folder names use
    ("RE_ ..."), then collapses to alphanumerics."""
    s = (s or "").lower()
    s = re.sub(r"^\s*((re|fw|fwd|rv|automatic reply)[_:\s]+)+", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _fuzz_match(a, b):
    """Prefix match either way (Sent-Items folder names truncate the subject
    at ~50 chars), both sides long enough to be meaningful."""
    return (len(a) >= MIN_FUZZ and len(b) >= MIN_FUZZ
            and (a.startswith(b) or b.startswith(a)))


def _parse_dt(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def load_archive_inbound():
    """Re-scan the raw archive (Inbox + Deleted Items, ALL messages — not
    just the COI-pattern subset that made corpus_index.json) for inbound
    messages with bodies. Read-only. Returns fuzz-subject -> [msgs]."""
    by_fuzz = {}
    count = 0
    for folder in ("Inbox", "Deleted Items"):
        base = os.path.join(ARCHIVE, folder)
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            mdir = os.path.join(base, entry)
            mpath = os.path.join(mdir, "message.txt")
            if not os.path.isfile(mpath):
                continue
            msg = parse_message(mpath)
            if msg is None:
                continue
            msg["folder"] = folder
            msg["dir"] = mdir
            if is_team_message(msg) or not (msg.get("body") or "").strip():
                continue
            if JUNK_SUBJECT.search(msg.get("subject") or ""):
                continue
            key = fuzz_subject(msg["subject"])
            if len(key) >= MIN_FUZZ:
                by_fuzz.setdefault(key, []).append(msg)
                count += 1
    print(f"archive re-scan: {count} inbound candidate messages "
          f"({len(by_fuzz)} distinct subjects)")
    return by_fuzz


def recover_archive_msgs(tkeys, known_dirs, anchor_dates, by_fuzz):
    """Inbound messages from the raw archive whose subject fuzzy-matches one
    of this card's thread keys, that corpus_index doesn't already carry, and
    that fall within the date window of the thread's activity."""
    out, seen = [], set(known_dirs)
    for tkey in tkeys:
        fk = fuzz_subject(tkey)
        if len(fk) < MIN_FUZZ:
            continue
        for ik, msgs in by_fuzz.items():
            if not _fuzz_match(fk, ik):
                continue
            for m in msgs:
                if m["dir"] in seen:
                    continue
                md = _parse_dt(m.get("date"))
                if anchor_dates and md is not None and not any(
                        abs((md - d).days) <= DATE_WINDOW_DAYS for d in anchor_dates):
                    continue
                seen.add(m["dir"])
                out.append(m)
    out.sort(key=lambda m: m.get("date") or "")
    return out


def main():
    with open(GRADED_PATH) as f:
        graded = json.load(f)
    with open(IDX_PATH) as f:
        idx = json.load(f)

    graded_by_path = {r["path"]: r for r in graded["records"]}
    threads = idx["threads"]

    # path -> thread keys (attachment linkage), plus the record's own list
    path_threads = {}
    for tkey, msgs in threads.items():
        for m in msgs:
            for a in m.get("attachments", []):
                if a["path"] in graded_by_path:
                    path_threads.setdefault(a["path"], set()).add(tkey)

    def rec_tkeys(rec):
        keys = set(path_threads.get(rec["path"], set()))
        keys.update(k for k in (rec.get("threads") or []) if k in threads)
        return keys

    by_fuzz = load_archive_inbound()

    # ---- per-record request context: which section does each COI go to?
    rec_sources = {}       # hash -> set of source tags
    for rec in graded["records"]:
        tkeys = rec_tkeys(rec)
        msgs = [m for k in tkeys for m in threads[k]]
        known_dirs = {m.get("dir") for m in msgs}
        anchors = [d for d in (_parse_dt(m.get("date")) for m in msgs) if d]
        rd = _parse_dt(rec.get("message_date"))
        if rd:
            anchors.append(rd)
        src = set()
        if any(not is_team_message(m) and (m.get("body") or "").strip() for m in msgs):
            src.add("inbound")
        if recover_archive_msgs(tkeys, known_dirs, anchors, by_fuzz):
            src.add("archive")
        if any(is_team_message(m) and QUOTE_HEAD.search(m.get("body") or "") for m in msgs):
            src.add("quoted")
        rec_sources[rec["hash"]] = src

    gradeable_hashes = {h for h, s in rec_sources.items() if s}
    recovered_only = {h for h, s in rec_sources.items()
                      if s and "inbound" not in s}
    excerpt_hashes = {r["hash"] for r in graded["records"] if r.get("request_excerpt")}
    print(f"request context: {len(gradeable_hashes)} gradeable / "
          f"{len(rec_sources) - len(gradeable_hashes)} no-request")
    print(f"  recovered beyond corpus_index inbound bodies "
          f"(archive/quoted only): {len(recovered_only)}")
    print(f"  had a request_excerpt: {len(excerpt_hashes)}; "
          f"newly recovered without one: {len(recovered_only - excerpt_hashes)}")

    order = {"incorrect": 0, "questionable": 1, "correct": 2}

    radio_seq = 0
    rendered_hashes = set()

    def coi_block(rec, role_label="", is_final=False, template_check=False):
        nonlocal radio_seq
        radio_seq += 1
        rendered_hashes.add(rec["hash"])
        role_html = ""
        if role_label:
            color = "#1a7f37" if "DELIVERED" in role_label else "#2e7dd1"
            role_html = f'<span class="badge" style="background:{color}">{role_label}</span>'
        if is_final:
            role_html += ' <span class="badge" style="background:#5b21b6">FINAL DELIVERED VERSION</span>'
        crops, prepared_by = render_coi_crops(rec["path"])
        if prepared_by == "usi":
            role_html += ' <span class="badge" style="background:#0a6e5c">MADE BY US (USI)</span>'
        elif prepared_by == "external":
            role_html += ' <span class="badge" style="background:#a3541c">EXTERNAL PRODUCER</span>'
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
        if template_check:
            decide = f"""
    <div class="decide">
      <span class="q">Does this COI meet current template standards?</span>
      <label><input type="radio" name="d{radio_seq}" value="std_yes" onchange="save('{rec['hash']}','std_yes')"> Yes</label>
      <label><input type="radio" name="d{radio_seq}" value="std_no" onchange="save('{rec['hash']}','std_no')"> No</label>
      <input type="text" class="note" placeholder="note (optional)" onblur="note('{rec['hash']}',this.value)">
    </div>"""
        else:
            decide = f"""
    <div class="decide">
      <label><input type="radio" name="d{radio_seq}" value="approve" onchange="save('{rec['hash']}','approve')"> Agree with verdict</label>
      <label><input type="radio" name="d{radio_seq}" value="disagree" onchange="save('{rec['hash']}','disagree')"> Disagree</label>
      <label><input type="radio" name="d{radio_seq}" value="skip" onchange="save('{rec['hash']}','skip')"> Skip</label>
      <input type="text" class="note" placeholder="why? (optional note)" onblur="note('{rec['hash']}',this.value)">
    </div>"""
        section = "2" if template_check else "1"
        return f"""
  <div class="coigrade" data-hash="{rec['hash']}" data-section="{section}">
    <div class="cardhead">
      {role_html}
      <span class="badge verdict" style="background:{vcol}">{rec['verdict'].upper()}</span>
      {std}
      <a class="fname" href="{file_href(rec['path'])}" target="_blank">{html.escape(rec['filename'])}</a>
    </div>
    <div class="zones">{imgs}</div>
    <details><summary>Automated findings ({len(rec['problems'])})</summary>
      <ul class="problems">{problems_html}</ul></details>
    {decide}
  </div>"""

    def msg_html(m, recovered=False, open_quote=False):
        team = is_team_message(m)
        who = "YOUR TEAM" if team else "CLIENT / REQUESTER"
        own, quoted = clean_body(m.get("body"))
        if own:
            paras = "".join(
                f"<p>{html.escape(p)}</p>"
                for p in re.split(r"\n{2,}", own) if p.strip()
            )
            body_html = paras.replace("\n", "<br>")
        else:
            body_html = "<i>(no body — sent-items export has attachments only)</i>"
        if quoted:
            q_paras = "".join(
                f"<p>{html.escape(p)}</p>"
                for p in re.split(r"\n{2,}", quoted) if p.strip()
            ).replace("\n", "<br>")
            q_open = " open" if (open_quote and team) else ""
            q_label = ("client request in the quoted history below"
                       if (open_quote and team) else "quoted history in this email")
            body_html += (f"<details class='quoted'{q_open}><summary>{q_label}</summary>"
                          f"<div class='qbody'>{q_paras}</div></details>")
        att_links = []
        for a in m.get("attachments", []):
            label = "sent in response" if team else "came with request"
            icon = "&#128206;"
            att_links.append(
                f'<a class="att {"team" if team else "client"}" href="{file_href(a["path"])}" '
                f'target="_blank">{icon} {html.escape(a["name"])}</a>'
                f'<span class="attlabel">({label})</span>'
            )
        rec_badge = ('<span class="badge" style="background:#7a5af5">RECOVERED FROM ARCHIVE'
                     '</span> ' if recovered else "")
        return f"""
  <div class="msg {'team' if team else 'client'}{' recovered' if recovered else ''}">
    <div class="msghead">{rec_badge}<span class="who">{who}</span>
      <span class="mfrom">{html.escape(m.get('from') or '')}</span>
      <span class="mdate">{html.escape(m.get('date') or '')}</span>
      <span class="msubj">{html.escape(m.get('subject') or '')}</span></div>
    <div class="mbody">{body_html}</div>
    <div class="atts">{''.join(att_links)}</div>
  </div>"""

    # ---- Section 1: threads whose COIs have request context, side by side
    claimed = set()
    thread_cards = []
    for tkey, msgs in threads.items():
        card_recs, seen_h = [], set()
        for m in msgs:
            for a in m.get("attachments", []):
                rec = graded_by_path.get(a["path"])
                if (rec and rec["hash"] in gradeable_hashes
                        and rec["hash"] not in claimed
                        and rec["hash"] not in seen_h):
                    card_recs.append(rec)
                    seen_h.add(rec["hash"])
        if not card_recs:
            continue
        claimed.update(seen_h)
        worst = min(order[r["verdict"]] for r in card_recs)
        thread_cards.append((worst, tkey, card_recs))
    thread_cards.sort(key=lambda t: (t[0], t[1]))

    section1_cards = []
    for worst, tkey, card_recs in thread_cards:
        # context = union of ALL threads the card's records belong to (a COI
        # can sit in a body-less sent thread while its request lives in the
        # matching inbox thread)
        tkeys = set()
        for rec in card_recs:
            tkeys |= rec_tkeys(rec)
        seen_dirs, union_msgs = set(), []
        for k in sorted(tkeys):
            for m in threads[k]:
                if m.get("dir") not in seen_dirs:
                    seen_dirs.add(m.get("dir"))
                    union_msgs.append(m)
        union_msgs.sort(key=lambda m: m.get("date") or "")
        anchors = [d for d in (_parse_dt(m.get("date")) for m in union_msgs) if d]
        for rec in card_recs:
            rd = _parse_dt(rec.get("message_date"))
            if rd:
                anchors.append(rd)
        recovered = recover_archive_msgs(tkeys, seen_dirs, anchors, by_fuzz)

        has_inbound = any(not is_team_message(m) and (m.get("body") or "").strip()
                          for m in union_msgs) or bool(recovered)
        # if the only request source is quoted history, open those quotes
        open_quotes = not has_inbound

        timeline_msgs = sorted(
            [(m, False) for m in union_msgs] + [(m, True) for m in recovered],
            key=lambda t: t[0].get("date") or "")
        timeline = "".join(msg_html(m, recovered=r, open_quote=open_quotes)
                           for m, r in timeline_msgs)

        # role per COI: DELIVERED if it ever traveled on a team message
        card_paths = {r["path"] for r in card_recs}
        roles, final_path = {}, None
        for m in union_msgs:
            for a in m.get("attachments", []):
                if a["path"] in card_paths:
                    if is_team_message(m):
                        roles[a["path"]] = "DELIVERED COI"
                        final_path = a["path"]
                    else:
                        roles.setdefault(a["path"],
                                         "CLIENT-PROVIDED COI (reference/old cert)")
        coi_col = "".join(
            coi_block(rec,
                      role_label=roles.get(rec["path"], "DELIVERED COI"),
                      is_final=(rec["path"] == final_path))
            for rec in card_recs)

        clients = sorted({r["client"] for r in card_recs})
        verdict_name = ["incorrect", "questionable", "correct"][worst]
        vcol = VERDICT_COLORS[verdict_name]
        n_msgs = len(timeline_msgs)
        section1_cards.append(f"""
<div class="card" data-client="{clients[0]}" data-verdict="{verdict_name}">
  <div class="cardhead threadhead">
    <span class="badge verdict" style="background:{vcol}">worst: {verdict_name.upper()}</span>
    <span class="client">{', '.join(clients)}</span>
    <b class="tsubj">{html.escape(tkey or '(no subject)')}</b>
    <span class="fdate">{n_msgs} message(s), {len(card_recs)} COI(s)</span>
  </div>
  <div class="pair">
    <div class="reqcol"><div class="collabel">REQUEST / EMAIL THREAD</div>{timeline}</div>
    <div class="coicol"><div class="collabel">DELIVERED COI — your grading</div>{coi_col}</div>
  </div>
</div>""")

    # safety net: gradeable records that never got claimed by a thread card
    for rec in sorted((r for r in graded["records"]
                       if r["hash"] in gradeable_hashes and r["hash"] not in claimed),
                      key=lambda r: order[r["verdict"]]):
        claimed.add(rec["hash"])
        excerpt = rec.get("request_excerpt") or ""
        req_html = (f"<div class='msg client'><div class='mbody'>"
                    f"<p>{html.escape(excerpt)}</p></div></div>" if excerpt else
                    "<div class='msg client'><div class='mbody'><i>(request text "
                    "unavailable)</i></div></div>")
        section1_cards.append(f"""
<div class="card" data-client="{rec['client']}" data-verdict="{rec['verdict']}">
  <div class="cardhead threadhead">
    <span class="badge" style="background:#8e8e93">NO THREAD LINK</span>
    <span class="client">{rec['client']}</span></div>
  <div class="pair">
    <div class="reqcol"><div class="collabel">REQUEST / EMAIL THREAD</div>{req_html}</div>
    <div class="coicol"><div class="collabel">DELIVERED COI — your grading</div>{coi_block(rec)}</div>
  </div>
</div>""")

    # ---- Section 2: no recoverable request — template quality check only
    noreq_recs = sorted((r for r in graded["records"]
                         if r["hash"] not in gradeable_hashes),
                        key=lambda r: (order[r["verdict"]], r["client"], r["filename"]))
    section2_cards = []
    for rec in noreq_recs:
        sent_line = ""
        if rec.get("message_date") or rec.get("threads"):
            subj = (rec.get("threads") or [""])[0]
            sent_line = (f"<span class='fdate'>sent {html.escape(rec.get('message_date') or '?')}"
                         + (f" · subject: {html.escape(subj)}" if subj else "")
                         + "</span>")
        section2_cards.append(f"""
<div class="card noreq" data-client="{rec['client']}" data-verdict="{rec['verdict']}">
  <div class="cardhead threadhead">
    <span class="badge" style="background:#8e8e93">NO REQUEST ON FILE</span>
    <span class="client">{rec['client']}</span>
    {sent_line}</div>
  {coi_block(rec, template_check=True)}
</div>""")

    # ---- sanity: every record rendered exactly once
    all_hashes = {r["hash"] for r in graded["records"]}
    assert rendered_hashes == all_hashes, (
        f"render mismatch: {len(rendered_hashes)} rendered vs {len(all_hashes)} records")
    n1, n2 = len(gradeable_hashes), len(all_hashes) - len(gradeable_hashes)

    counts = graded["counts"]
    all_clients = sorted({r["client"] for r in graded["records"]})
    s1_hashes_js = json.dumps(sorted(gradeable_hashes))
    s2_hashes_js = json.dumps(sorted(all_hashes - gradeable_hashes))
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>COI Training Review — request + delivery</title>
<style>
 body {{ font-family: -apple-system, Helvetica, sans-serif; margin: 0; background: #f2f2f4; }}
 header {{ position: sticky; top: 0; background: #1c1c1e; color: #fff; padding: 10px 16px; z-index: 5;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
 select, button {{ font-size: 13px; padding: 4px 8px; }}
 .progress {{ margin-left: auto; font-size: 13px; }}
 .sechead {{ margin: 26px 16px 4px 16px; }}
 .sechead h2 {{ margin: 0 0 2px 0; font-size: 17px; }}
 .sechead .sub {{ font-size: 12.5px; color: #666; }}
 .secprog {{ font-weight: 600; color: #1a7f37; }}
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
 .pair {{ display: grid; grid-template-columns: minmax(340px, 5fr) minmax(430px, 7fr);
          gap: 16px; margin-top: 10px; align-items: start; }}
 @media (max-width: 1100px) {{ .pair {{ grid-template-columns: 1fr; }} }}
 .collabel {{ font-size: 10.5px; font-weight: 700; color: #8e8e93; letter-spacing: .06em;
              margin-bottom: 4px; }}
 .reqcol {{ min-width: 0; }} .coicol {{ min-width: 0; }}
 .msg {{ margin: 10px 0 10px 0; padding: 8px 12px; border-radius: 8px; }}
 .msg.client {{ background: #eef3fb; border-left: 4px solid #2e7dd1; margin-right: 18px; }}
 .msg.team {{ background: #eefaf0; border-left: 4px solid #1a7f37; margin-left: 18px; }}
 .msg.recovered {{ outline: 2px dashed #7a5af5aa; }}
 .msghead {{ font-size: 11.5px; color: #555; display: flex; gap: 10px; flex-wrap: wrap; }}
 .who {{ font-weight: 700; }}
 .msg.client .who {{ color: #2e7dd1; }} .msg.team .who {{ color: #1a7f37; }}
 .mbody {{ font-size: 12.5px; margin: 6px 0; max-height: 340px; overflow-y: auto; }}
 .mbody p {{ margin: 0 0 8px 0; line-height: 1.45; }}
 .quoted summary {{ font-size: 11.5px; color: #8e8e93; cursor: pointer; margin-top: 4px; }}
 .qbody {{ border-left: 3px solid #d0d0d5; padding-left: 10px; margin-top: 6px; color: #555;
           font-size: 12px; max-height: 320px; overflow-y: auto; }}
 .qbody p {{ margin: 0 0 8px 0; line-height: 1.4; }}
 .atts {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
 .att {{ font-size: 12px; text-decoration: none; background: #fff; border: 1px solid #c9c9ce;
         border-radius: 5px; padding: 3px 8px; color: #1c1c1e; }}
 .attlabel {{ font-size: 10.5px; color: #8e8e93; margin-right: 8px; }}
 .coigrade {{ border: 1px solid #d8d8dd; border-radius: 8px; padding: 10px; margin-top: 10px; background: #fff; }}
 .zones {{ display: flex; gap: 12px; margin: 10px 0; flex-wrap: wrap; }}
 .zone img {{ max-width: 900px; width: 100%; border: 1px solid #d0d0d5; display: block; }}
 .zone {{ max-width: 900px; width: 100%; }}
 .zlabel {{ font-size: 10px; color: #8e8e93; text-transform: uppercase; margin-bottom: 2px; }}
 .problems li {{ font-size: 12.5px; margin: 2px 0; }}
 .sev-FAIL {{ color: #c62828; }} .sev-WARN {{ color: #b58105; }} .sev-INFO {{ color: #666; }} .sev-OK {{ color: #1a7f37; }}
 .decide {{ display: flex; gap: 16px; align-items: center; margin-top: 8px; font-size: 13px; flex-wrap: wrap; }}
 .decide .q {{ font-weight: 600; }}
 .decide .note {{ flex: 1; min-width: 220px; padding: 4px 6px; font-size: 12.5px; }}
 .decide .legacy {{ font-size: 11.5px; color: #8e8e93; font-style: italic; }}
 details summary {{ font-size: 12.5px; color: #444; cursor: pointer; }}
 .coigrade.done {{ outline: 3px solid #1a7f3733; }}
</style></head><body>
<header>
 <b>COI Training Review</b>
 <span>{len(section1_cards)} paired cards / {len(all_hashes)} unique COIs — {counts['incorrect']} incorrect / {counts['questionable']} questionable / {counts['correct']} correct</span>
 <select id="fclient" onchange="filter()"><option value="">all clients</option>
  {''.join(f'<option>{c}</option>' for c in all_clients)}</select>
 <select id="fverdict" onchange="filter()"><option value="">all verdicts</option>
  <option>incorrect</option><option>questionable</option><option>correct</option></select>
 <button onclick="exportDecisions()">Export decisions JSON</button>
 <span class="progress" id="progress"></span>
</header>
<div class="sechead"><h2>Section 1 — Delivery review: request paired with delivered COI <span class="secprog" id="prog1"></span></h2>
<div class="sub">The client's request email (full thread where there is one) on the left, what we delivered on the right. Judge the delivery decision: Agree / Disagree.</div></div>
{''.join(section1_cards)}
<div class="sechead"><h2>Section 2 — No request on file — template quality check only <span class="secprog" id="prog2"></span></h2>
<div class="sub">The Sent-Items export kept no bodies for these and no matching inbound email could be recovered from the archive, so the delivery decision can't be judged. One question instead: does the certificate itself meet current template standards?</div></div>
{''.join(section2_cards)}
<script>
const S1 = {s1_hashes_js};
const S2 = {s2_hashes_js};
const store = JSON.parse(localStorage.getItem('coi_decisions') || '{{}}');
function persist() {{
  localStorage.setItem('coi_decisions', JSON.stringify(store));
  const c1 = S1.filter(h => store[h] && store[h].decision).length;
  const c2 = S2.filter(h => store[h] && store[h].decision).length;
  document.getElementById('prog1').textContent = '— ' + c1 + ' of ' + S1.length + ' graded';
  document.getElementById('prog2').textContent = '— ' + c2 + ' of ' + S2.length + ' checked';
  document.getElementById('progress').textContent =
    'S1: ' + c1 + '/' + S1.length + ' · S2: ' + c2 + '/' + S2.length;
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
  if (!d) return;
  if (d.decision) {{
    el.classList.add('done');
    const r = el.querySelector('input[value="' + d.decision + '"]');
    if (r) {{ r.checked = true; }}
    else {{
      // decision saved on the old page for a COI now in the other section —
      // keep it (same key, same export), just show what it was
      const s = document.createElement('span');
      s.className = 'legacy';
      s.textContent = 'saved decision from previous page: ' + d.decision;
      el.querySelector('.decide').appendChild(s);
    }}
  }}
  if (d.note) el.querySelector('.note').value = d.note;
}});
persist();
</script></body></html>"""

    with open(OUT_PATH, "w") as f:
        f.write(page)
    print(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)/1e6:.1f} MB, "
          f"section 1: {len(section1_cards)} cards / {n1} COIs, "
          f"section 2: {len(section2_cards)} cards / {n2} COIs)")


if __name__ == "__main__":
    main()
