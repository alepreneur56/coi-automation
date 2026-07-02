"""
grade_cois.py — A3 step 2: grade every delivered COI against the registry,
the locked-in rules, and the request context.

Reads training/corpus_index.json (from mine_corpus.py), dedupes the delivered
COIs by content hash, extracts their fields with PyMuPDF, runs rule checks,
and writes training/graded_cois.json.

Checks per COI:
  P1  placeholder 'Project name & Address ( If Applicable)' left on the COI
  P2  license number missing from Description of Operations
  P3  boilerplate similarity vs the client's template (altered language)
  P4  issue date missing
  P5  certificate holder box empty
  P6  multi-entity holder without plural 'Certificate Holders'
  P7  policy numbers on COI differ from registry (info — may be older term)
  P8  registry carriers missing from COI
  P9  request/holder mismatch (when the thread has the request body)
  P10 text overruns box borders (holder > 304.5, DoO > 591)

Usage: .venv/bin/python training/grade_cois.py
"""

import difflib
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX_PATH = os.path.join(BASE, "training", "corpus_index.json")
OUT_PATH = os.path.join(BASE, "training", "graded_cois.json")

# Fallback clips (our template geometry) — used only if label anchors fail
HOLDER_CLIP = fitz.Rect(19, 664, 307, 749)
DESC_CLIP = fitz.Rect(20, 568, 592, 652)
DATE_CLIP = fitz.Rect(495, 20, 600, 52)


def _spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b["lines"]:
            for sp in line["spans"]:
                out.append(sp)
    return out


def find_label(spans, predicate):
    """First span whose stripped text satisfies predicate. Returns Rect or None."""
    for sp in spans:
        if predicate(sp["text"].strip()):
            return fitz.Rect(sp["bbox"])
    return None


def find_desc_label(spans):
    """The REAL DoO section label. Some layouts also contain 'DESCRIPTION OF
    OPERATIONS below' inside the Workers-Comp box higher up the page — the
    real section label is the one mentioning LOCATIONS / VEHICLES (and it is
    the lowest such span on page 1)."""
    best = None
    for sp in spans:
        t = sp["text"].strip().upper()
        if t.startswith("DESCRIPTION OF OPERATIONS") and "LOCATION" in t:
            r = fitz.Rect(sp["bbox"])
            if best is None or r.y0 > best.y0:
                best = r
    if best is not None:
        return best
    # fallback: startswith match but never the '...below' reference text
    for sp in spans:
        t = sp["text"].strip().upper()
        if t.startswith("DESCRIPTION OF OPERATIONS") and "BELOW" not in t:
            return fitz.Rect(sp["bbox"])
    return None


def detect_regions(page):
    """Anchor the three regions off the ACORD labels so COIs printed with a
    different layout (Epic, carrier portals) are read correctly."""
    spans = _spans(page)
    W, H = page.rect.width, page.rect.height

    ch = find_label(spans, lambda t: t.upper().startswith("CERTIFICATE HOLDER")
                    and t.upper() == t)
    canc = find_label(spans, lambda t: t.upper().startswith("CANCELLATION")
                      and t.upper() == t)
    desc = find_desc_label(spans)
    auth = find_label(spans, lambda t: t.upper().startswith("AUTHORIZED REPRESENTATIVE"))
    date_lbl = find_label(spans, lambda t: "DATE (MM/DD/YYYY)" in t.upper())

    holder_clip = HOLDER_CLIP
    if ch is not None:
        right = canc.x0 - 4 if canc is not None else min(310, W * 0.52)
        bottom = auth.y0 - 2 if (auth is not None and auth.y0 > ch.y1) else H - 40
        holder_clip = fitz.Rect(ch.x0 - 2, ch.y1 + 1, right, min(bottom, ch.y1 + 95))

    desc_clip = DESC_CLIP
    if desc is not None:
        bottom = ch.y0 - 2 if (ch is not None and ch.y0 > desc.y1) else desc.y1 + 90
        desc_clip = fitz.Rect(desc.x0 - 2, desc.y1 + 1, W - 18, bottom)

    date_clip = DATE_CLIP
    if date_lbl is not None and date_lbl.y0 < 120:
        date_clip = fitz.Rect(date_lbl.x0 - 6, date_lbl.y1, date_lbl.x1 + 12, date_lbl.y1 + 22)

    return holder_clip, desc_clip, date_clip

with open(os.path.join(BASE, "coi_client_registry.json")) as f:
    REGISTRY = json.load(f)
CLIENTS = {c["client_id"]: c for c in REGISTRY["clients"]}


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def extract_fields(path):
    doc = fitz.open(path)
    page = doc[0]
    holder_clip, desc_clip, date_clip = detect_regions(page)
    # DoO frequently continues on an ACORD 101 page 2 — include its text
    extra_desc = ""
    if doc.page_count > 1:
        p2 = doc[1].get_text()
        if "ADDITIONAL REMARKS" in p2.upper() or "ACORD 101" in p2.upper():
            extra_desc = "\n" + p2
    fields = {
        "holder_text": page.get_text(clip=holder_clip).strip(),
        "desc_text": (page.get_text(clip=desc_clip).strip() + extra_desc).strip(),
        "date_text": page.get_text(clip=date_clip).strip(),
        "full_text": page.get_text() + extra_desc,
        "overruns": [],
        "anchored": holder_clip is not HOLDER_CLIP,
    }
    # border overruns measured against the DETECTED region edges
    for sp in _spans(page):
        r = fitz.Rect(sp["bbox"])
        t = sp["text"].strip()
        if not t or t.upper() in ("CERTIFICATE HOLDER", "CANCELLATION"):
            continue
        if r.intersects(holder_clip) and r.x1 > holder_clip.x1 + 2:
            fields["overruns"].append(f"holder box: {t[:40]!r} x1={r.x1:.0f}")
        elif r.intersects(desc_clip) and r.x1 > desc_clip.x1 + 2:
            fields["overruns"].append(f"DoO box: {t[:40]!r} x1={r.x1:.0f}")
    doc.close()
    return fields


def grade(path, client_id, request_body):
    problems = []          # (code, severity FAIL|WARN|INFO, message)
    client = CLIENTS.get(client_id)
    fields = extract_fields(path)
    ft_norm = norm(fields["full_text"]).lower()
    desc_norm = norm(fields["desc_text"])

    # P1 placeholder left behind
    if re.search(r"project name & address\s*\(\s*if applicable\s*\)", desc_norm, re.I):
        problems.append(("P1", "FAIL", "placeholder 'Project name & Address (If Applicable)' left on the COI"))

    # P2 license number
    licenses = set()
    for tpl in client.get("templates", []):
        if tpl.get("license_number"):
            licenses.add(tpl["license_number"])
    if client.get("license_number"):
        licenses.add(client["license_number"])
    if licenses and not any(l.lower() in ft_norm for l in licenses):
        problems.append(("P2", "WARN", f"license number {sorted(licenses)} not found in Description of Operations"))

    # P3 boilerplate vs template current_value — sentence containment:
    # what fraction of the template's boilerplate sentences appear on the COI
    # (page-2 ACORD 101 noise and label fragments then don't hurt the score).
    best_ratio = None
    coi_text = norm(fields["desc_text"]).lower()
    for tpl in client.get("templates", []):
        cur = tpl.get("editable_fields", {}).get("description_of_operations", {}).get("current_value")
        if not cur:
            continue
        sentences = []
        for line in cur.splitlines():
            if "License Number" in line or "Project name & Address" in line:
                continue
            for s in re.split(r"(?<=[.!?])\s+", line):
                s = norm(s).lower()
                if len(s) > 25:
                    sentences.append(s)
        if not sentences:
            continue
        found = sum(1 for s in sentences if s[:60] in coi_text)
        ratio = found / len(sentences)
        best_ratio = ratio if best_ratio is None else max(best_ratio, ratio)
    if best_ratio is not None and best_ratio < 0.5:
        problems.append(("P3", "WARN",
                         f"DoO boilerplate does not match the current template language "
                         f"({best_ratio:.0%} of template sentences found)"))

    # P4 issue date
    if not re.search(r"\d{2}/\d{2}/\d{4}", fields["date_text"]):
        problems.append(("P4", "FAIL", "no issue date in the date box"))

    # P5 holder box
    holder_lines = [l.strip() for l in fields["holder_text"].splitlines() if l.strip()]
    if not holder_lines:
        problems.append(("P5", "FAIL", "certificate holder box is empty"))

    # P6 plural rule: >1 entity line before the address lines
    addr_idx = None
    for i, l in enumerate(holder_lines):
        if re.search(r"\d{2,6}\s+\w+.*(st|street|ave|avenue|blvd|dr|drive|rd|road|way|cir|ct|ter|hwy|lane|ln|pkwy|place|pl)\b", l, re.I) \
           or re.search(r",\s*fl\s*,?\s*\d{5}", l, re.I):
            addr_idx = i
            break
    # Only flag when we positively found the address line — no address found
    # usually means unusual formatting, not multiple entities.
    if addr_idx is not None and addr_idx > 1 and "certificate holders" not in ft_norm:
        problems.append(("P6", "WARN", f"{addr_idx} holder entities but boilerplate says 'Certificate Holder' (singular)"))

    # P7 policy numbers vs registry
    reg_policies = set()
    for tpl in client.get("templates", []):
        for pol in tpl.get("policies", []) or []:
            if pol.get("policy_number"):
                reg_policies.add(norm(pol["policy_number"]).lower())
    if reg_policies:
        found = sum(1 for p in reg_policies if p in ft_norm)
        if found == 0:
            problems.append(("P7", "INFO", "no registry policy numbers on this COI (older policy term or different data)"))
        elif found < len(reg_policies):
            problems.append(("P7", "INFO", f"only {found}/{len(reg_policies)} registry policy numbers present"))

    # P8 carriers vs registry
    reg_carriers = set()
    for tpl in client.get("templates", []):
        for c in tpl.get("carriers", []) or []:
            reg_carriers.add(c["name"].lower())
    if reg_carriers:
        missing = [c for c in reg_carriers if c[:18] not in ft_norm]
        if len(missing) == len(reg_carriers):
            problems.append(("P8", "INFO", "none of the registry carriers appear (older program or different data)"))

    # P9 request vs holder match
    if request_body and holder_lines:
        req = norm(request_body).lower()
        holder_first = holder_lines[0].lower()
        tokens = [t for t in re.findall(r"[a-z]{4,}", holder_first)
                  if t not in ("corporation", "company", "condominium", "association", "management")]
        if tokens:
            hits = sum(1 for t in tokens if t in req)
            if hits == 0:
                problems.append(("P9", "WARN", f"holder {holder_lines[0][:40]!r} not found in the request text"))

    # P10 overruns
    for o in fields["overruns"][:3]:
        problems.append(("P10", "WARN", f"text crosses box border: {o}"))

    sev_rank = {"FAIL": 0, "WARN": 1, "INFO": 2}
    problems.sort(key=lambda p: sev_rank[p[1]])

    # Two dimensions:
    #  - verdict: SUBSTANTIVE correctness (wrong/missing content = real error)
    #  - meets_current_standard: matches Alex's locked-in format rules
    #    (old COIs predate the standard — non-compliance is not an error,
    #    but they must not be used as format exemplars for training)
    STANDARD_CODES = {"P2", "P3"}
    substantive = [p for p in problems if p[0] not in STANDARD_CODES]
    verdict = "correct"
    if any(p[1] == "FAIL" for p in substantive):
        verdict = "incorrect"
    elif any(p[1] == "WARN" for p in substantive):
        verdict = "questionable"
    meets_standard = not any(p[0] in STANDARD_CODES or p[0] == "P1" for p in problems)

    return {
        "verdict": verdict,
        "meets_current_standard": meets_standard,
        "problems": [{"code": c, "severity": s, "message": m} for c, s, m in problems],
        "holder_text": fields["holder_text"],
        "desc_text": fields["desc_text"][:600],
        "date_text": fields["date_text"],
    }


def main():
    with open(IDX_PATH) as f:
        idx = json.load(f)

    # Collect delivered COIs (dedupe by content hash), keep thread context
    seen_hashes = {}
    records = []
    for tkey, msgs in idx["threads"].items():
        # request body = first non-team inbound message with a body
        request_body = ""
        for m in msgs:
            if m.get("body") and "attached please find" not in m["body"][:200].lower():
                request_body = m["body"]
                break
        for m in msgs:
            for a in m.get("attachments", []):
                fp = a.get("fingerprint") or {}
                if fp.get("kind") != "acord_coi" or not fp.get("client"):
                    continue
                with open(a["path"], "rb") as fh:
                    h = hashlib.sha1(fh.read()).hexdigest()
                if h in seen_hashes:
                    seen_hashes[h]["threads"].append(tkey)
                    continue
                rec = {
                    "hash": h,
                    "path": a["path"],
                    "filename": a["name"],
                    "client": fp["client"],
                    "insured_name": fp.get("insured_name"),
                    "issue_date": fp.get("issue_date"),
                    "message_date": m.get("date"),
                    "folder": m.get("folder"),
                    "threads": [tkey],
                    "request_excerpt": request_body[:1200],
                }
                seen_hashes[h] = rec
                records.append(rec)

    print(f"unique delivered COIs to grade: {len(records)}")

    counts = {"correct": 0, "questionable": 0, "incorrect": 0}
    for rec in records:
        g = grade(rec["path"], rec["client"], rec["request_excerpt"])
        rec.update(g)
        counts[g["verdict"]] += 1

    print(f"verdicts: {counts}")

    by_client = {}
    for rec in records:
        by_client.setdefault(rec["client"], []).append(rec)
    for cid, recs in sorted(by_client.items()):
        c = {"correct": 0, "questionable": 0, "incorrect": 0}
        for r in recs:
            c[r["verdict"]] += 1
        print(f"  {cid:28s} {len(recs):3d} COIs — {c}")

    with open(OUT_PATH, "w") as f:
        json.dump({"records": records, "counts": counts}, f, indent=1)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
