"""
catalog_requirements.py — A7 groundwork step 1: catalog every insurance-
requirements document in the Outlook archive.

The A3 miner (training/mine_corpus.py) fingerprinted PDFs with a narrow
regex and only inside COI-classified threads, so it found just a handful of
`requirements_doc` PDFs. This script sweeps EVERY PDF attachment in the
archive (Inbox / Sent Items / Deleted Items), applies broader keyword-family
heuristics + filename hints, and catalogs anything that looks like an
insurance-requirements document: contract insurance exhibits, full contracts,
vendor packets, "sample COI + requirements" combos, and scanned (image-only)
candidates that need OCR.

Noise the naive keyword approach hits, handled explicitly:
  - our own issued ACORD certs + endorsement packets (ACORD footer and
    CG-endorsement boilerplate contains "additional insured", "primary and
    non-contributory", "waiver of subrogation") -> boilerplate suppression +
    direction check (a cert that only ever appears in Sent Items is our
    output, not a requirements input);
  - the clients' own carrier policy documents / dec pages / quotes /
    proposals (they contain "insurance requirements", "minimum limits",
    "indemnification" as policy text) -> policy-document markers;
  - carrier application forms (FCCI / supplemental apps) and legal filings.

Usage:
    .venv/bin/python training/a7/catalog_requirements.py [--dump-texts DIR]

Output:
    training/a7/requirements_catalog.json

--dump-texts DIR additionally writes the full extracted text of every
cataloged doc to DIR/<sha1>.txt for manual ground-truth analysis (used to
build parsed_examples.json). Keep DIR outside the repo.
"""

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime

import fitz

fitz.TOOLS.mupdf_display_errors(False)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

ARCHIVE = ("/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/"
           "Microsoft Outlook Copy/Extracted/IPM_SUBTREE")
FOLDERS = ["Inbox", "Sent Items", "Deleted Items"]
CORPUS_INDEX = os.path.join(REPO, "training", "corpus_index.json")
OUT_PATH = os.path.join(HERE, "requirements_catalog.json")

MAX_PAGES_TEXT = 40           # cap text extraction for huge contracts
MAX_EXCERPTS = 10
SCANNED_TEXT_THRESHOLD = 120  # chars of extractable text below which a PDF
                              # is considered image-only (needs OCR)

# Same loose client tokens the A3 miner uses (registry aliases distilled).
CLIENT_TOKENS = {
    "305_power_corp": ["305 power"],
    "rolandos_hvac": ["rolando"],
    "emp3_solutions": ["emp 3", "emp3"],
    "central_comfort_ac": ["central comfort"],
    "gd_mechanical": ["g & d mechanical", "g&d mechanical", "g  d mechanical",
                      "g and d mechanical"],
    "absolute_air_solutions": ["absolute air"],
    "ajf_roofing": ["ajf roofing", "ajf "],
    "apogee_hvac": ["apogee"],
}

# ---------------------------------------------------------------------------
# Keyword families.
# CORE families are requirement-imposing language ("thou shalt carry X") that
# identifies a doc as a requirements source. SUPPORT families corroborate but
# also appear in policy/endorsement boilerplate, so alone they don't qualify.
# ---------------------------------------------------------------------------
CORE_FAMILIES = {
    "insurance_requirements_heading": re.compile(
        r"insurance\s+requirements?|requirements?\s+(?:of|for)\s+insurance|"
        r"minimum\s+insurance", re.I),
    "shall_maintain": re.compile(
        r"(?:shall|must|agrees?\s+to|required\s+to)\s+"
        r"(?:procure(?:\s+and\s+maintain)?|maintain|carry|obtain|provide|keep)"
        r"[^.\n]{0,120}?insurance|insurance[^.\n]{0,80}?"
        r"(?:shall|must)\s+be\s+maintained", re.I),
    "minimum_limits": re.compile(
        r"minimum\s+limits?|limits?\s+(?:of\s+(?:liability|insurance)\s+)?"
        r"(?:not|no)\s+less\s+than|not\s+less\s+than\s+\$|"
        r"at\s+least\s+\$[\d,]+|minimum\s+(?:coverage|amounts?)", re.I),
    "coi_must": re.compile(
        r"certificates?\s+of\s+insurance[^.\n]{0,120}?"
        r"(?:must|shall|required|prior\s+to|before|evidencing|naming)|"
        r"(?:furnish|provide|submit|deliver)[^.\n]{0,60}?"
        r"certificates?\s+of\s+insurance", re.I),
    "exhibit_insurance": re.compile(
        r"exhibit\s+[A-Z0-9][^\n]{0,60}?insurance|"
        r"insurance[^\n]{0,40}?exhibit\s+[A-Z0-9]", re.I),
}

SUPPORT_FAMILIES = {
    "additional_insured_required": re.compile(
        r"(?:shall|must)\s+(?:be\s+)?(?:named?|includ\w+|list\w+|endorsed?)"
        r"[^.\n]{0,80}?additional\s+insured|"
        r"additional\s+insured[^.\n]{0,60}?(?:shall|must|is\s+required)|"
        r"nam\w+\s+as\s+additional\s+insureds?\b", re.I),
    "waiver_subrogation_required": re.compile(
        r"waiver\s+of\s+subrogation[^.\n]{0,60}?"
        r"(?:required|shall|must|in\s+favor)|"
        r"(?:shall|must)[^.\n]{0,80}?waiv\w+\s+(?:of\s+)?"
        r"(?:all\s+)?(?:rights\s+of\s+)?subrogation", re.I),
    "primary_noncontributory_required": re.compile(
        r"primary\s+(?:and|&)\s+non[- ]?contributory|"
        r"primary[^.\n]{0,40}?non[- ]?contribut\w+", re.I),
    "hold_harmless": re.compile(r"hold\s+harmless", re.I),
    "indemnification": re.compile(r"indemnif\w+", re.I),
    "umbrella_excess_required": re.compile(
        r"(?:umbrella|excess)\s+(?:liability|coverage|policy)"
        r"[^.\n]{0,80}?(?:\$[\d,]+|required|shall|must|limits?)|"
        r"(?:shall|must)[^.\n]{0,80}?(?:umbrella|excess\s+liability)", re.I),
    "notice_of_cancellation": re.compile(
        r"(?:thirty|ten|sixty|\b30\b|\b10\b|\b60\b)[^.\n]{0,40}?days?"
        r"[^.\n]{0,60}?(?:written\s+)?notice[^.\n]{0,60}?"
        r"(?:cancel|termination|non[- ]?renewal)|"
        r"notice\s+of\s+cancellation[^.\n]{0,60}?(?:days?|required|shall)",
        re.I),
}

ALL_FAMILIES = {**CORE_FAMILIES, **SUPPORT_FAMILIES}

# Filename hints strong enough to lower the text-evidence bar. Deliberately
# excludes bare "insurance"/"policy"/"contract" — every carrier doc has those.
FILENAME_HINTS = re.compile(
    r"requirement|exhibit|vendor|sample|template|example|subcontract|"
    r"addendum|rpq|rfp|rfq|\bbid\b|packet|checklist|set[- ]?up|setup|"
    r"\breqs?\b|compliance|spec\b", re.I)

ACORD_CERT_MARKER = re.compile(r"certificate\s+of\s+liability\s+insurance", re.I)

CONTRACT_MARKERS = re.compile(
    r"this\s+(?:agreement|contract|subcontract)\s+(?:is\s+)?"
    r"(?:made|entered\s+into|between)|in\s+witness\s+whereof|witnesseth|"
    r"scope\s+of\s+(?:work|services)|terms\s+and\s+conditions|"
    r"governing\s+law|entire\s+agreement", re.I)

VENDOR_MARKERS = re.compile(
    r"vendor\s+(?:application|packet|registration|compliance|approval|"
    r"requirements?|form|set[- ]?up)|w-?9\b|supplier\s+(?:packet|registration)|"
    r"credit\s+application", re.I)

# --- noise detectors -------------------------------------------------------
# Carrier policy documents / dec pages / quotes / proposals (the client's OWN
# insurance paper, not a requester's requirements).
POLICY_DOC_MARKERS = [
    re.compile(r"insuring\s+agreement", re.I),
    re.compile(r"coverage\s+form", re.I),
    re.compile(r"declarations", re.I),
    re.compile(r"(?:total|annual|estimated)\s+premium|premium\s+basis", re.I),
    re.compile(r"this\s+endorsement\s+(?:changes|modifies)\s+the\s+policy", re.I),
    re.compile(r"common\s+policy\s+conditions", re.I),
    re.compile(r"quote\s+(?:number|no\b|proposal)|quotation", re.I),
    re.compile(r"forms?\s+and\s+endorsements?\s+schedule", re.I),
]
POLICY_FILENAME = re.compile(
    r"\bpolicy\b|\bdec\b|quote|proposal|term\s*\d{2}|renewal", re.I)

CARRIER_APP_FILENAME = re.compile(r"\bapp(?:lication)?\b|sup\s*ap", re.I)
CARRIER_APP_TEXT = re.compile(r"applicant", re.I)

LEGAL_FILING = re.compile(
    r"case\s+no\.?|plaintiff|defendant|circuit\s+court|vouch[- ]?in", re.I)

# Boilerplate that must NOT count as requirement language: the ACORD 25
# footer, CG-endorsement wording, and our own description-of-operations
# blanket language. These appear on every cert / endorsement we issue.
OWN_BOILERPLATE = re.compile(
    r"includes?\s+an\s+automatic\s+additional\s+insured\s+endorsement|"
    r"blanket\s+waiver\s+of\s+subrogation\s+applies|"
    r"if\s+the\s+certificate\s+holder\s+is\s+an\s+additional\s+insured|"
    r"policy\(ies\)\s+must\s+(?:have|be\s+endorsed)|"
    r"(?:if|when|as)\s+required\s+by\s+(?:a\s+|executed\s+)?"
    r"(?:written\s+)?contract(?:\s+or\s+agreement)?|"
    r"this\s+endorsement\s+(?:changes|modifies)\s+the\s+policy|"
    r"will\s+not\s+be\s+broader\s+than\s+that\s+which\s+you\s+are\s+required|"
    r"in\s+accordance\s+with\s+the\s+policy\s+provisions", re.I)


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text(path):
    """Return (text, page_count, error)."""
    try:
        doc = fitz.open(path)
        page_count = doc.page_count
        text = ""
        for i, page in enumerate(doc):
            if i >= MAX_PAGES_TEXT:
                break
            text += page.get_text() + "\n"
        doc.close()
        return text, page_count, None
    except Exception as e:
        return "", 0, str(e)[:150]


def sentences(text):
    """Crude sentence-ish splitter good enough for excerpt harvesting."""
    chunks = re.split(r"(?<=[.;:])\s+|\n{2,}", text)
    out = []
    for c in chunks:
        c = re.sub(r"\s+", " ", c).strip()
        if 15 <= len(c) <= 600:
            out.append(c)
    return out


def harvest_excerpts(text):
    """Sentences matching requirement families, boilerplate suppressed."""
    excerpts = []
    seen = set()
    for sent in sentences(text):
        if OWN_BOILERPLATE.search(sent):
            continue
        hits = [name for name, rx in ALL_FAMILIES.items() if rx.search(sent)]
        if not hits:
            continue
        key = sent[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        excerpts.append({"families": hits, "text": sent[:400]})
        if len(excerpts) >= MAX_EXCERPTS:
            break
    return excerpts


def is_policy_doc(text, filename):
    hits = sum(1 for rx in POLICY_DOC_MARKERS if rx.search(text))
    if hits >= 3:
        return True
    if hits >= 2 and POLICY_FILENAME.search(filename):
        return True
    return False


def guess_doc_type(text, core, page_count, filename, is_cert):
    fn = filename.lower()
    if is_cert:
        return "sample_coi_with_requirements"
    if VENDOR_MARKERS.search(text) or "vendor" in fn:
        return "vendor_packet"
    contract_hits = len(CONTRACT_MARKERS.findall(text))
    if (contract_hits >= 2 and page_count >= 5) or \
            (contract_hits >= 1 and page_count >= 12):
        return "full_contract"
    if core:
        return "requirements_exhibit"
    return "unknown"


def infer_client(*texts, thread_info=None):
    blob = " ".join(t.lower() for t in texts if t)
    for cid, tokens in CLIENT_TOKENS.items():
        if any(t in blob for t in tokens):
            return cid
    # Fall back to whichever client's certs dominate the thread (A3 corpus).
    if thread_info and thread_info.get("clients_on_certs"):
        return thread_info["clients_on_certs"][0]
    return None


def parse_message_header(msg_path):
    subject = sender = date = ""
    body_head = ""
    try:
        with open(msg_path, encoding="utf-8", errors="replace") as f:
            raw = f.read(12000)
        head = raw.partition("----- Transport Headers -----")[0]
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            k = k.strip().lower()
            if k == "subject":
                subject = v.strip()
            elif k == "from":
                sender = v.strip()
            elif k == "date":
                date = v.strip()
        if "----- Body -----" in raw:
            body_head = raw.partition("----- Body -----")[2][:3000]
    except Exception:
        pass
    return subject, sender, date, body_head


def normalize_subject(subject):
    s = re.sub(r"^\s*((re|fw|fwd|rv|rv:|automatic reply)[:\s]+)+",
               "", subject or "", flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def load_corpus_threads():
    """Map normalized subject -> thread summary from the A3 corpus index."""
    try:
        with open(CORPUS_INDEX, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        return {}
    out = {}
    for norm_subj, msgs in idx.get("threads", {}).items():
        coi_sent = False
        clients = Counter()
        req_docs = 0
        for m in msgs:
            for a in m.get("attachments", []):
                fp = a.get("fingerprint") or {}
                if fp.get("kind") == "acord_coi":
                    if m.get("folder") == "Sent Items":
                        coi_sent = True
                    if fp.get("client"):
                        clients[fp["client"]] += 1
                elif fp.get("kind") == "requirements_doc":
                    req_docs += 1
        out[norm_subj] = {
            "message_count": len(msgs),
            "coi_sent_from_us": coi_sent,
            "clients_on_certs": [c for c, _ in clients.most_common()],
            "miner_flagged_requirements_docs": req_docs,
        }
    return out


def what_happened(thread_info):
    if thread_info is None:
        return ("thread_not_in_coi_corpus — the A3 miner did not classify "
                "this thread as COI traffic")
    if thread_info["coi_sent_from_us"]:
        return (f"coi_delivered — we sent an ACORD cert in this thread "
                f"({thread_info['message_count']} msgs in thread)")
    return (f"no_coi_sent_found — thread is in the COI corpus but no "
            f"sent cert was fingerprinted "
            f"({thread_info['message_count']} msgs in thread)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-texts", metavar="DIR", default=None,
                    help="also write full extracted text per cataloged doc")
    args = ap.parse_args()
    if args.dump_texts:
        os.makedirs(args.dump_texts, exist_ok=True)

    corpus_threads = load_corpus_threads()

    docs = {}            # sha1 -> catalog record
    pending_certs = {}   # sha1 -> record for certs (direction decided at end)
    total_pdfs = 0
    excluded = Counter()

    for folder in FOLDERS:
        root = os.path.join(ARCHIVE, folder)
        if not os.path.isdir(root):
            continue
        for msg_dir in sorted(os.listdir(root)):
            att_dir = os.path.join(root, msg_dir, "attachments")
            if not os.path.isdir(att_dir):
                continue
            msg_path = os.path.join(root, msg_dir, "message.txt")
            subject, sender, date, body_head = parse_message_header(msg_path)
            if not subject:
                # NEW_* dirs (live-test captures) have no message.txt; the
                # subject is encoded in the dir name:
                # NEW_<date>_<time>_<subject>_<id>  /  <NNNNN>_<subject>
                m = re.match(r"^NEW_(\d{4}-\d{2}-\d{2})_(\d{6})_(.*)_(\d+)$",
                             msg_dir)
                if m:
                    subject = m.group(3)
                    date = date or m.group(1)
                else:
                    subject = re.sub(r"^\d+_", "", msg_dir)
            norm = normalize_subject(subject or msg_dir.split("_", 1)[-1])
            thread_info = corpus_threads.get(norm)

            for fn in sorted(os.listdir(att_dir)):
                if not fn.lower().endswith(".pdf"):
                    continue
                total_pdfs += 1
                path = os.path.join(att_dir, fn)
                digest = sha1_file(path)

                occurrence = {
                    "path": path,
                    "folder": folder,
                    "thread_subject": subject,
                    "message_from": sender,
                    "message_date": date,
                }

                if digest in docs:
                    docs[digest]["occurrences"].append(occurrence)
                    continue
                if digest in pending_certs:
                    pending_certs[digest]["occurrences"].append(occurrence)
                    continue

                text, page_count, err = extract_text(path)
                text_len = len(text.strip())
                filename_hint = bool(FILENAME_HINTS.search(fn))

                # --- scanned / unreadable ---------------------------------
                if err or text_len < SCANNED_TEXT_THRESHOLD:
                    subj_hint = bool(FILENAME_HINTS.search(subject or ""))
                    coi_thread_scan = (
                        thread_info is not None
                        and re.search(r"coi|cert|insur",
                                      f"{fn} {subject}", re.I))
                    if not (filename_hint or subj_hint or coi_thread_scan):
                        excluded["scanned_no_hint"] += 1
                        continue
                    docs[digest] = {
                        "sha1": digest,
                        "filename": fn,
                        "path": path,
                        "page_count": page_count,
                        "doc_type": "unknown",
                        "ocr_needed": True,
                        "read_error": err,
                        "matched_families": [],
                        "filename_hint": filename_hint,
                        "client": infer_client(subject, body_head, path,
                                               thread_info=thread_info),
                        "thread_subject": subject,
                        "what_happened_in_thread": what_happened(thread_info),
                        "thread_info": thread_info,
                        "excerpts": [],
                        "occurrences": [occurrence],
                    }
                    continue

                # --- readable ---------------------------------------------
                core = {n for n, rx in CORE_FAMILIES.items() if rx.search(text)}
                support = {n for n, rx in SUPPORT_FAMILIES.items()
                           if rx.search(text)}
                is_cert = bool(ACORD_CERT_MARKER.search(text))
                excerpts = harvest_excerpts(text)

                if is_cert:
                    # A cert is only a requirements artifact if it carries
                    # real (non-boilerplate) requirement language — e.g. a
                    # sample cert a requester sent showing the language they
                    # need. Direction (received vs only-ever-sent) is decided
                    # after the sweep, since duplicates appear in both boxes.
                    if not excerpts or not (core | support):
                        excluded["plain_acord_cert"] += 1
                        continue
                    rec_type = "sample_coi_with_requirements"
                    target = pending_certs
                else:
                    if is_policy_doc(text, fn):
                        excluded["carrier_policy_doc"] += 1
                        continue
                    if CARRIER_APP_FILENAME.search(fn) and \
                            CARRIER_APP_TEXT.search(text):
                        excluded["carrier_application"] += 1
                        continue
                    if len(LEGAL_FILING.findall(text)) >= 2:
                        excluded["legal_filing"] += 1
                        continue
                    include = (
                        (core and len(core | support) >= 2)
                        or (filename_hint and (core or support))
                    )
                    if not include or not excerpts:
                        excluded["no_requirement_language"] += 1
                        continue
                    rec_type = guess_doc_type(text, core, page_count, fn,
                                              is_cert)
                    target = docs

                target[digest] = {
                    "sha1": digest,
                    "filename": fn,
                    "path": path,
                    "page_count": page_count,
                    "doc_type": rec_type,
                    "ocr_needed": False,
                    "read_error": None,
                    "matched_families": sorted(core | support),
                    "filename_hint": filename_hint,
                    "client": infer_client(subject, body_head, path,
                                           text[:4000],
                                           thread_info=thread_info),
                    "thread_subject": subject,
                    "what_happened_in_thread": what_happened(thread_info),
                    "thread_info": thread_info,
                    "excerpts": excerpts,
                    "occurrences": [occurrence],
                }
                if args.dump_texts:
                    with open(os.path.join(args.dump_texts, digest + ".txt"),
                              "w", encoding="utf-8") as f:
                        f.write(f"# {fn}\n# {path}\n\n{text}")

    # Direction check for certs: keep only certs that were RECEIVED (Inbox /
    # Deleted Items) at least once. A cert that only ever exists in Sent
    # Items is our own output, not a requirements input.
    for digest, rec in pending_certs.items():
        received = any(o["folder"] != "Sent Items"
                       for o in rec["occurrences"])
        sample_hint = re.search(r"sample|template|example",
                                rec["filename"], re.I)
        if received or sample_hint:
            rec["direction"] = "received" if received else "sent_only"
            docs[digest] = rec
        else:
            excluded["issued_cert_sent_only"] += 1

    records = sorted(docs.values(),
                     key=lambda d: (-len(d["matched_families"]),
                                    d["filename"].lower()))
    by_type = Counter(d["doc_type"] for d in records)
    by_client = Counter(d["client"] or "unmatched" for d in records)
    summary = {
        "generated": datetime.now().isoformat(),
        "archive": ARCHIVE,
        "total_pdf_attachments_swept": total_pdfs,
        "unique_docs_cataloged": len(records),
        "excluded": dict(excluded),
        "by_doc_type": dict(by_type),
        "by_client": dict(by_client),
        "ocr_needed_count": sum(1 for d in records if d["ocr_needed"]),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "documents": records}, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_PATH}")
    for d in records:
        fams = ",".join(d["matched_families"]) or (
            "OCR" if d["ocr_needed"] else "-")
        print(f"  [{d['doc_type']:>28}] {d['filename'][:55]:55} "
              f"pages={d['page_count']:>3} client={d['client'] or '-':<20} "
              f"{fams[:70]}")


if __name__ == "__main__":
    main()
