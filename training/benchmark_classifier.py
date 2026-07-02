"""
benchmark_classifier.py — A3 step 4: classifier accuracy baseline on real
historical requests.

Replays real client COI requests (mined from the Outlook archive by
mine_corpus.py) through the CURRENT classifier (classifier.py + the live
system prompt) and scores the results against ground truth derived from the
COIs that were actually delivered (graded_cois.json). This produces the
BASELINE score before few-shot training examples are added to the prompt —
rerun the same command after any prompt change to re-score.

Eval-set construction (one case per thread):
  - request message = first non-team message with a real request body
    (team = Alejandro/Jade/Sent Items/"Attached please find" bodies)
  - thread must link to at least one delivered COI in graded_cois.json,
    or carry a team text reply
  - ground truth holder = the delivered COI's holder box, segmented into
    blocks (template placeholder / GAF-cert blocks stripped) and matched
    to the request body by token overlap
  - expected classification: coi_request_complete when the request body
    already carries the holder street number + zip, else
    coi_request_incomplete. coi_complex_review_required is accepted as
    adjacent whenever the request carried a PDF with insurance content
    (the prompt's ABSOLUTE RULE mandates it there); coi_revision_request
    is accepted when the body asks to update/fix an existing COI; and
    coi_request_complete is accepted when the model looked up the right
    holder name AND address on its own.
  - ambiguous threads are skipped and the reason recorded (forwarded-only
    bodies, acknowledgment-only bodies, holder info that lived in images
    or inline HTML that the archive export lost, non-COI asks)

Replay fidelity limits (also noted in BENCHMARK_REPORT.md):
  - text + PDF attachments only; images are NOT sent (production converts
    HEIC/renders scanned PDFs — here scanned PDFs go through as PDFs)
  - thread history is empty (we replay the FIRST message of each thread)
  - sender address is bench@example.com unless the archive captured a real
    address, so registry domain-matching is often unavailable

Usage: .venv/bin/python training/benchmark_classifier.py [--limit N]
           [--fresh] [--dry-run]
  --dry-run  build and print the eval set, no API calls
  --fresh    ignore previous results and re-run every case
  (default: resume — cases already in benchmark_results.json are kept)
Output: training/benchmark_results.json (+ summary printed to stdout)
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import classifier  # noqa: E402  (imports config -> .env)
from training.build_review import clean_body, is_team_message  # noqa: E402
from training.mine_corpus import CLIENT_TOKENS  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX_PATH = os.path.join(BASE, "training", "corpus_index.json")
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")
REGISTRY_PATH = os.path.join(BASE, "coi_client_registry.json")
OUT_PATH = os.path.join(BASE, "training", "benchmark_results.json")

MAX_CASES = 80
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDFS_PER_CASE = 5

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

STOPWORDS = {"the", "of", "a", "an", "and", "for", "at", "in", "on", "de", "la", "el"}

REQUEST_LANG = re.compile(
    r"\b(cois?|certs?|certificates?|certificados?|insur\w*|holders?|acord|"
    r"seguro|waiver|coverage)\b", re.I)

ON_WROTE = re.compile(r"\bOn\s.{5,90}?\bwrote\s*:", re.S)
QUOTE_START = re.compile(r"^\s*(From|De)\s*:", re.I)

# Outlook exports sometimes carry a Word style-definition preamble that the
# generic CSS stripper in build_review misses (multi-line mso blocks).
WORD_PREAMBLE = re.compile(
    r"^\s*\d*\s*DocumentEmail(\s*(true|false|EN-US|X-NONE))*\s*"
    r"/\* Style Definitions \*/.*?\}\s*", re.S)
JUNK_LINE = re.compile(r"^(\d+|true|false|EN-US|X-NONE|DocumentEmail)$")


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOPWORDS}


def overlap(expected_text, got_text):
    """|expected ∩ got| / |expected| over normalized tokens."""
    exp = tokens(expected_text)
    if not exp:
        return 0.0
    return len(exp & tokens(got_text)) / len(exp)


def strip_word_preamble(text):
    text = WORD_PREAMBLE.sub("", text or "")
    lines = [l for l in text.splitlines() if not JUNK_LINE.match(l.strip())]
    return "\n".join(lines).strip()


def request_body(msg):
    """Returns (own_text, quoted_text, replay_body). own = the sender's own
    words; replay_body = own + quoted history (what production would see in
    body.content)."""
    own, quoted = clean_body(msg.get("body"))
    own = strip_word_preamble(own)
    m = ON_WROTE.search(own)
    if m:  # gmail-style quote the build_review splitter doesn't catch
        own, quoted = own[:m.start()].strip(), (own[m.start():] + "\n" + quoted).strip()
    replay = (own + ("\n\n" + quoted if quoted else "")).strip()
    return own, quoted, replay


PHONE = re.compile(r"\(\d{3}\)\s*\d{3}[- ]\d{4}|\b\d{3}[- ]\d{3}[- ]\d{4}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.\w+\b")


def strip_signature(own, from_name, client_id):
    """Best-effort cut of the sender's signature block, so signature
    addresses (the CLIENT's own address, phone blocks) don't read as
    request content. Cuts at the sender's name, the insured's name, or a
    '--' separator — whichever comes first (never at position 0)."""
    cuts = []
    low = own.lower()
    if from_name and "@" not in from_name:
        i = low.find(from_name.lower())
        if i > 0:
            cuts.append(i)
    for token in CLIENT_TOKENS.get(client_id or "", []):
        i = low.find(token)
        if i > 0:
            cuts.append(i)
    m = re.search(r"\n--\s*(\n|$)| -- ", own)
    if m and m.start() > 0:
        cuts.append(m.start())
    return own[:min(cuts)].strip() if cuts else own


# ---------------------------------------------------------------------------
# Ground-truth holder parsing (from graded holder_text)
# ---------------------------------------------------------------------------

STREET_SUFFIX = re.compile(
    r"\b(street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|circle|cir|"
    r"court|ct|lane|ln|way|terrace|ter|place|pl|parkway|pkwy|highway|hwy|"
    r"walk|trail|trl|bend|loop|point|pt)\b\.?", re.I)
ORG_WORD = re.compile(
    r"\b(llc|inc|corp|corporation|association|assn|condominium|management|"
    r"company|county|group|hotel|residences|partners|development|"
    r"construction|realty|services|solutions|department|division|owner|"
    r"city|university|church|school|club)\b", re.I)
CITY_STATE_ZIP = re.compile(r"\b[A-Z]{2}\.?,?\s+\d{5}(-\d{4})?\b|,\s*F[LI]\b")
ADDR_CONT = re.compile(r"^(suite|ste|unit|apt|#|building|bldg|floor|fl)\b", re.I)
HOLDER_JUNK = {"certificate holder", "certificate holders", "live certificate"}


def _is_addr_line(line, prev_was_addr):
    if re.match(r"^P\.?\s?O\.?\s*Box", line, re.I):
        return True
    if prev_was_addr and ADDR_CONT.match(line):
        return True
    if CITY_STATE_ZIP.search(line) and not ORG_WORD.search(line):
        return True
    if re.match(r"^\d", line) and STREET_SUFFIX.search(line) and not ORG_WORD.search(line):
        return True
    return False


def holder_blocks(holder_text):
    """Segment a holder box extraction into candidate (name, addr) blocks.
    The extractions sometimes carry the template placeholder ('ABC Holder 2'),
    an AJF GAF-certification block, or two holders back to back."""
    lines = []
    for raw in (holder_text or "").splitlines():
        l = raw.strip()
        if len(l) <= 2 or l.lower() in HOLDER_JUNK:
            continue
        lines.append(l)

    blocks, cur, prev_addr = [], {"name": [], "addr": []}, False
    for l in lines:
        if _is_addr_line(l, prev_addr):
            cur["addr"].append(l)
            prev_addr = True
        else:
            if cur["addr"]:  # a name line after an address line = new block
                blocks.append(cur)
                cur = {"name": [], "addr": []}
            cur["name"].append(l)
            prev_addr = False
    if cur["name"] or cur["addr"]:
        blocks.append(cur)

    out = []
    for b in blocks:
        name = " ".join(b["name"]) or None
        low = (name or "").lower()
        if "abc holder" in low:           # template placeholder text
            continue
        if low == "gaf" or (low.startswith("gaf") and b["addr"]
                            and "campus" in b["addr"][0].lower()):
            continue                      # AJF GAF certification block
        zm = re.search(r"\b(\d{5})(?:-\d{4})?\s*$", " ".join(b["addr"]))
        sm = re.match(r"^(\d+)", b["addr"][0]) if b["addr"] else None
        out.append({
            "name": name,
            "addr_lines": b["addr"],
            "zip": zm.group(1) if zm else None,
            "street_no": sm.group(1) if sm else None,
        })
    return out


# ---------------------------------------------------------------------------
# Eval-set construction
# ---------------------------------------------------------------------------

INSURANCE_PDF_KINDS = {"acord_coi", "requirements_doc", "scanned_pdf"}
REVISION_LANG = re.compile(r"\b(updated?|fix|revis\w+|renew\w*|correct\w*|actualizad?\w*)\b", re.I)
ACK_ONLY = re.compile(
    r"^\W*(perfecto|perfect|thanks?( you)?|thank you|gracias|great|got it|"
    r"ok(ay)?|received|awesome)[\s\S]{0,40}$", re.I)
CANCEL_ASK = re.compile(r"\bcancel(l\w*)?\b", re.I)
REFERS_ELSEWHERE = re.compile(
    r"\b(attach\w*|adjunto\w*|below|see below|as per the|following|per the)\b", re.I)
SIG_IMAGE = re.compile(r"^(image\d+|Outlook-\w+)\.(png|jpe?g|gif)$", re.I)


def load_registry_names():
    with open(REGISTRY_PATH) as f:
        reg = json.load(f)
    return {c["client_id"]: c["canonical_name"] for c in reg["clients"]}


def rec_delivery_rank(rec, req):
    """0 = delivered from Sent Items; 1 = seen later in the thread;
    2 = attached to the request itself (reference COI — corroborate)."""
    if rec.get("folder") == "Sent Items":
        return 0
    if rec["path"].startswith(req["dir"] + os.sep):
        return 2
    if rec.get("message_date", "") > req["date"]:
        return 1
    return 2


def pick_ground_truth(grecs, req, replay_body):
    """Pick the (record, holder block) pair that best matches the request.
    Returns (client_id, holder_gt_or_None, note)."""
    if not grecs:
        return None, None, "no graded COI in thread"
    vrank = {"correct": 0, "questionable": 1, "incorrect": 2}
    candidates = []
    for rec in grecs:
        rank = rec_delivery_rank(rec, req)
        for blk in holder_blocks(rec.get("holder_text")):
            ov = overlap((blk["name"] or "") + " " + " ".join(blk["addr_lines"]),
                         replay_body)
            candidates.append((-ov, rank, vrank[rec["verdict"]], rec, blk))
    client = grecs[0]["client"]
    if not candidates:
        return client, None, "holder box unparseable on all graded COIs"
    candidates.sort(key=lambda c: c[:3])
    neg_ov, rank, _, rec, blk = candidates[0]
    note = f"from {rec['filename']} (verdict={rec['verdict']}, overlap={-neg_ov:.2f})"
    if rank == 2 and blk["name"] and overlap(blk["name"], replay_body) < 0.3:
        # Best evidence is a COI the CLIENT attached, and its holder isn't
        # what the body asks for (e.g. old cert attached, new holder named
        # in text) — holder ground truth would be wrong. Keep client only.
        return rec["client"], None, "request-attachment COI holder not corroborated by body"
    if -neg_ov < 0.15 and re.search(r"\b\d{5}\b", replay_body):
        # The request names its own holder + address but NO graded COI in the
        # thread matches it — generic subjects ("coi", "request") bucket
        # unrelated conversations together. Holder ground truth unreliable.
        return rec["client"], None, "graded COI does not match this request (subject-bucket collision)"
    return rec["client"], blk, note


def build_eval_set():
    """Returns (cases, skips). Each case carries the replay message dict,
    attachment specs, and ground truth."""
    with open(IDX_PATH) as f:
        idx = json.load(f)
    with open(GRADED_PATH) as f:
        graded = json.load(f)

    thread_to_recs = {}
    for rec in graded["records"]:
        for t in rec.get("threads", []):
            thread_to_recs.setdefault(t, []).append(rec)

    cases, skips = [], []
    for key in sorted(idx["threads"]):
        msgs = idx["threads"][key]
        req = own = quoted = replay = None
        for m in msgs:
            if is_team_message(m):
                continue
            o, q, r = request_body(m)
            if o or q:
                req, own, quoted, replay = m, o, q, r
                break
        if req is None:
            continue  # nothing replayable in this thread at all

        grecs = thread_to_recs.get(key, [])
        team_texts = [m for m in msgs
                      if is_team_message(m) and (m.get("body") or "").strip()
                      and m.get("folder") != "Sent Items" and m["date"] > req["date"]]
        if not grecs and not team_texts:
            continue  # no outcome evidence -> not part of the eval universe

        def skip(reason):
            skips.append({"thread": key, "from": req["from"], "date": req["date"],
                          "reason": reason, "excerpt": own[:160]})

        # --- ambiguity filters -------------------------------------------
        if not own or QUOTE_START.match(own):
            skip("forwarded_thread_only: request text lives only in a quoted/forwarded block")
            continue
        if ACK_ONLY.match(own) and not REQUEST_LANG.search(own):
            skip("acknowledgment_only: first client message is a thank-you, not a request")
            continue

        client_hint = grecs[0]["client"] if grecs else None
        pre_sig = strip_signature(own, req.get("from"), client_hint)
        has_lang = bool(REQUEST_LANG.search(pre_sig)
                        or REQUEST_LANG.search(req["subject"] or ""))
        has_addr_block = bool(re.search(r"\b\d{5}\b", pre_sig)) and bool(
            re.search(r"\b\d{1,6}\s+[A-Za-z]", pre_sig))
        if not has_lang and has_addr_block and PHONE.search(pre_sig) and EMAIL.search(pre_sig):
            has_addr_block = False  # an uncut signature block, not a request
        if not (has_lang or has_addr_block):
            skip("no_request_language: body carries no COI-request signal")
            continue
        if CANCEL_ASK.search(own[:250]) and not re.search(
                r"\b(send|need|issue|provide|request)\w*\b[^.]{0,60}\b(coi|cert)", own, re.I):
            skip("non_coi_request: policy cancellation ask")
            continue

        client_id, holder_gt, gt_note = pick_ground_truth(grecs, req, replay)

        # --- attachments (PDFs only; note image-loss cases) ---------------
        pdfs, content_images = [], []
        for att in req.get("attachments", []):
            if att["is_pdf"]:
                pdfs.append(att)
            elif not SIG_IMAGE.match(att["name"]):
                content_images.append(att["name"])
        pdfs = pdfs[:MAX_PDFS_PER_CASE]

        holder_in_replay = holder_gt is not None and (
            overlap(holder_gt["name"] or " ".join(holder_gt["addr_lines"]), replay) >= 0.3
            or (holder_gt["zip"] and holder_gt["zip"] in replay))
        if (holder_gt is not None and not holder_in_replay and not pdfs
                and REFERS_ELSEWHERE.search(own)):
            skip("holder_info_not_in_replayable_input: request points at content "
                 "(inline image / HTML table) the archive export did not keep")
            continue

        # --- expected classification --------------------------------------
        if holder_gt is not None and holder_gt["addr_lines"]:
            # holder address known -> is it already in the replayed body?
            if holder_gt["zip"]:
                addr_in_body = bool(
                    re.search(r"\b" + holder_gt["zip"] + r"\b", replay)
                    and holder_gt["street_no"]
                    and re.search(r"\b" + holder_gt["street_no"] + r"\b", replay))
            else:  # zip cropped off the graded COI -> street number + name
                street_words = tokens(holder_gt["addr_lines"][0])
                addr_in_body = bool(
                    holder_gt["street_no"]
                    and re.search(r"\b" + holder_gt["street_no"] + r"\b", replay)
                    and len(street_words & tokens(replay)) >= min(2, len(street_words)))
            gt_confidence = "normal"
        elif holder_gt is None and has_lang and has_addr_block:
            # no reliable holder GT, but the request itself carries a full
            # street + zip block -> it was a complete request
            addr_in_body = True
            gt_confidence = "low"
        else:
            addr_in_body = False
            gt_confidence = "low"
        expected_cls = "coi_request_complete" if addr_in_body else "coi_request_incomplete"

        acceptable = {expected_cls}
        att_kinds = sorted({(a.get("fingerprint") or {}).get("kind", "?") for a in pdfs})
        if any(k in INSURANCE_PDF_KINDS for k in att_kinds) or any(
                re.search(r"policy|insur|coi|cert", a["name"], re.I) for a in pdfs):
            acceptable.add("coi_complex_review_required")
        if REVISION_LANG.search(own):
            acceptable.add("coi_revision_request")

        cases.append({
            "thread": key,
            "req_msg": req,
            "own": own,
            "replay_body": replay,
            "pdfs": pdfs,
            "content_images": content_images,
            "expected": {
                "classification": expected_cls,
                "acceptable": sorted(acceptable),
                "client_id": client_id,
                "holder": holder_gt,
                "gt_note": gt_note,
                "gt_confidence": gt_confidence,
                "graded_coi_count": len(grecs),
            },
        })
        if len(cases) >= MAX_CASES:
            break
    return cases, skips


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

def build_replay_message(case, n):
    req = case["req_msg"]
    frm = req.get("from") or ""
    address = frm if "@" in frm else "bench@example.com"
    sent = req["date"].replace(" ", "T") + "Z" if req.get("date") else ""
    return {
        "id": f"bench-{n}",
        "subject": req.get("subject", ""),
        "from": {"emailAddress": {"name": frm, "address": address}},
        "body": {"content": case["replay_body"]},
        "sentDateTime": sent,
        "hasAttachments": bool(case["pdfs"]),
    }


def build_attachments(case):
    atts = []
    for att in case["pdfs"]:
        try:
            if os.path.getsize(att["path"]) > MAX_PDF_BYTES:
                continue
            with open(att["path"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
        except OSError:
            continue
        atts.append({
            "name": att["name"],
            "kind": "pdf",
            "media_type": "application/pdf",
            "contentBytes": b64,
        })
    return {"attachments": atts}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def extract_holders(parsed):
    """All (name, addr_string) candidates the model produced — single,
    multi-entity (certificate_holder_lines), and batch (batch_cois)."""
    out = []

    def one(obj):
        if not isinstance(obj, dict):
            return
        ch = obj.get("certificate_holder") or {}
        name = ch.get("name") or ""
        lines = obj.get("certificate_holder_lines") or []
        if lines:
            name = name + " " + " ".join(str(l) for l in lines)
        addr = " ".join(str(ch.get(k) or "") for k in
                        ("address_line_1", "address_line_2", "city", "state", "zip"))
        if name.strip() or addr.strip():
            out.append((name.strip(), addr.strip()))

    one(parsed)
    for item in (parsed.get("batch_cois") or []):
        one(item)
    return out


def score_case(case, result, canonical_names):
    exp = case["expected"]
    parsed = result.get("parsed") or {}
    got_cls = parsed.get("classification")

    scores = {
        "classification_strict": got_cls == exp["classification"],
        "classification_ok": got_cls in exp["acceptable"],
        "client_ok": None,
        "holder_name_ok": None,
        "holder_name_overlap": None,
        "holder_addr_ok": None,
    }

    # client
    if exp["client_id"]:
        canon = canonical_names.get(exp["client_id"], "")
        got_id = parsed.get("client_id") or ""
        got_name = parsed.get("client_canonical_name") or ""
        scores["client_ok"] = bool(
            got_id == exp["client_id"] or (got_name and overlap(canon, got_name) >= 0.6))

    # holder — scored when GT exists AND either the model produced holder
    # fields or it was expected to (address was right there in the body)
    hg = exp["holder"]
    holders = extract_holders(parsed)
    if hg is not None and (holders or exp["classification"] == "coi_request_complete"):
        if hg["name"]:
            best = max((overlap(hg["name"], n + " " + a) for n, a in holders), default=0.0)
            scores["holder_name_overlap"] = round(best, 3)
            scores["holder_name_ok"] = best >= 0.6
        if hg["addr_lines"]:
            ok = False
            for _, addr in holders:
                st = (not hg["street_no"]) or bool(
                    re.search(r"\b" + re.escape(hg["street_no"]) + r"\b", addr))
                zp = (not hg["zip"]) or hg["zip"] in addr
                if st and zp and (hg["street_no"] or hg["zip"]):
                    ok = True
                    break
            scores["holder_addr_ok"] = ok

    # lookup-success adjacency: a "complete" verdict with the RIGHT holder
    # name and address is a good outcome even when we expected "incomplete"
    if (not scores["classification_ok"] and got_cls == "coi_request_complete"
            and scores["holder_name_ok"] and scores["holder_addr_ok"]):
        scores["classification_ok"] = True
        scores["lookup_success_adjacency"] = True
    return scores


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def pct(num, den):
    return f"{num}/{den} ({100.0 * num / den:.0f}%)" if den else "n/a (0 cases)"


def summarize(results, skips):
    done = [r for r in results if r.get("api_ok")]
    errors = [r for r in results if not r.get("api_ok")]

    def count(key):
        vals = [r["scores"][key] for r in done if r["scores"].get(key) is not None]
        return sum(1 for v in vals if v), len(vals)

    lines = ["", "=" * 70, "BENCHMARK SUMMARY", "=" * 70]
    lines.append(f"cases evaluated: {len(done)}   api/parse errors: {len(errors)}   "
                 f"skipped threads: {len(skips)}")
    for key, label in [("classification_ok", "classification (with acceptable-adjacent)"),
                       ("classification_strict", "classification (strict)"),
                       ("client_ok", "client identification"),
                       ("holder_name_ok", "holder name (overlap >= 0.6)"),
                       ("holder_addr_ok", "holder address (street no + zip)")]:
        n, d = count(key)
        lines.append(f"  {label:45s} {pct(n, d)}")

    lines.append("\nby expected classification:")
    for cls in sorted({r["expected"]["classification"] for r in done}):
        sub = [r for r in done if r["expected"]["classification"] == cls]
        n = sum(1 for r in sub if r["scores"]["classification_ok"])
        lines.append(f"  {cls:30s} {pct(n, len(sub))}")

    lines.append("\nby client:")
    for cid in sorted({r["expected"]["client_id"] or "(unknown)" for r in done}):
        sub = [r for r in done if (r["expected"]["client_id"] or "(unknown)") == cid]
        n = sum(1 for r in sub if r["scores"]["classification_ok"])
        c = [r for r in sub if r["scores"].get("client_ok") is not None]
        cn = sum(1 for r in c if r["scores"]["client_ok"])
        lines.append(f"  {cid:26s} cls {pct(n, len(sub)):14s} client {pct(cn, len(c))}")

    lines.append("\nmisses:")
    for r in done:
        s = r["scores"]
        bad = [k for k in ("classification_ok", "client_ok", "holder_name_ok", "holder_addr_ok")
               if s.get(k) is False]
        if bad:
            lines.append(f"  [{r['case_id']}] {r['thread'][:48]!r} failed: {', '.join(bad)}")
            lines.append(f"      expected {r['expected']['classification']} / "
                         f"{r['expected']['client_id']} — got "
                         f"{(r.get('got') or {}).get('classification')} / "
                         f"{(r.get('got') or {}).get('client_id')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=MAX_CASES)
    ap.add_argument("--fresh", action="store_true",
                    help="re-run every case (default resumes from prior results)")
    ap.add_argument("--dry-run", action="store_true",
                    help="build + print the eval set, no API calls")
    args = ap.parse_args()

    cases, skips = build_eval_set()
    cases = cases[:args.limit]
    canonical_names = load_registry_names()
    prompt_sha = hashlib.sha256(
        classifier.load_system_prompt().encode()).hexdigest()[:16]

    print(f"eval set: {len(cases)} cases, {len(skips)} skipped threads "
          f"(prompt sha256:{prompt_sha})")
    if args.dry_run:
        for i, c in enumerate(cases, 1):
            e = c["expected"]
            h = e["holder"]
            print(f"\n[{i:02d}] {c['thread'][:60]!r}")
            print(f"     expect {e['classification']} (ok: {e['acceptable']}) "
                  f"client={e['client_id']} conf={e['gt_confidence']}")
            print(f"     holder GT: {h['name'] if h else None} | "
                  f"{' / '.join(h['addr_lines']) if h else '-'}")
            print(f"     pdfs={[p['name'] for p in c['pdfs']]} "
                  f"imgs_lost={c['content_images']}")
            print(f"     own[:140]: {c['own'][:140]!r}")
        for s in skips:
            print(f"\nSKIP {s['thread'][:60]!r}: {s['reason']}")
        return

    prior = {}
    if not args.fresh and os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            old = json.load(f)
        if old.get("prompt_sha") == prompt_sha:
            prior = {r["thread"]: r for r in old.get("results", []) if r.get("api_ok")}
            print(f"resuming: {len(prior)} finished cases carried over")

    results = []
    for i, case in enumerate(cases, 1):
        if case["thread"] in prior:
            results.append(prior[case["thread"]])
            continue
        msg = build_replay_message(case, i)
        atts = build_attachments(case)
        print(f"[{i:02d}/{len(cases)}] {case['thread'][:52]!r} "
              f"({len(atts['attachments'])} pdf)...", flush=True)
        res = classifier.classify(msg, [], atts)
        parsed = res.get("parsed") or {}
        scores = score_case(case, res, canonical_names) if res["success"] else {}
        row = {
            "case_id": f"bench-{i}",
            "thread": case["thread"],
            "subject": msg["subject"],
            "from": case["req_msg"]["from"],
            "date": case["req_msg"]["date"],
            "attachments_sent": [a["name"] for a in atts["attachments"]],
            "content_images_lost": case["content_images"],
            "request_excerpt": case["own"][:400],
            "expected": case["expected"],
            "api_ok": res["success"],
            "api_error": res.get("api_error") or res.get("parse_error"),
            "got": {
                "classification": parsed.get("classification"),
                "client_id": parsed.get("client_id"),
                "client_canonical_name": parsed.get("client_canonical_name"),
                "certificate_holder": parsed.get("certificate_holder"),
                "certificate_holder_lines": parsed.get("certificate_holder_lines"),
                "batch_cois": parsed.get("batch_cois"),
                "status": parsed.get("status"),
                "confidence": parsed.get("confidence"),
                "is_permit": parsed.get("is_permit"),
                "flags": parsed.get("flags"),
                "summary": parsed.get("original_request_summary"),
                "reply_text": (parsed.get("reply_text") or "")[:300] or None,
            } if res["success"] else None,
            "scores": scores,
            "diag": {
                "http_status": res.get("http_status"),
                "attempts": res.get("anthropic_attempts"),
                "stop_reason": res.get("stop_reason"),
                "cache_usage": res.get("cache_usage"),
            },
        }
        results.append(row)
        if res["success"]:
            print(f"      -> {parsed.get('classification')} "
                  f"client={parsed.get('client_id')} scores={scores}")
        else:
            print(f"      -> ERROR: {row['api_error']}")
        # incremental save so a crash loses nothing
        with open(OUT_PATH, "w") as f:
            json.dump({
                "generated": datetime.now().isoformat(),
                "model": classifier.config.ANTHROPIC_MODEL,
                "prompt_sha": prompt_sha,
                "case_count": len(cases),
                "results": results,
                "skips": skips,
            }, f, indent=1)

    print(summarize(results, skips))
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    main()
