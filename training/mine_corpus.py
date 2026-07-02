"""
mine_corpus.py — A3 step 1: mine the extracted Outlook archive for COI threads.

Walks the Migrated_From_TestAccount archive (Inbox / Sent Items / Deleted
Items), parses every message.txt, filters COI-related traffic, fingerprints
every PDF attachment (ACORD 25 delivered COI for one of our clients vs
requirements doc vs other), groups messages into threads, and writes a
corpus index JSON for the grading step.

Usage: .venv/bin/python training/mine_corpus.py
Output: training/corpus_index.json
"""

import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

ARCHIVE = ("/Users/alepreneur/Documents/Migrated_From_TestAccount_2026-05-03/"
           "Microsoft Outlook Copy/Extracted/IPM_SUBTREE")
FOLDERS = ["Inbox", "Deleted Items"]
SENT_FOLDER = "Sent Items"

# ACORD 25 insured box region (page 1, PDF points) — generous bounds
INSURED_CLIP = fitz.Rect(15, 95, 320, 200)
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus_index.json")

# Our 8 clients — canonical names + loose match tokens for the INSURED box
CLIENT_TOKENS = {
    "305_power_corp": ["305 power"],
    "rolandos_hvac": ["rolando"],
    "emp3_solutions": ["emp 3", "emp3"],
    "central_comfort_ac": ["central comfort"],
    "gd_mechanical": ["g & d mechanical", "g&d mechanical", "g  d mechanical"],
    "absolute_air_solutions": ["absolute air"],
    "ajf_roofing": ["ajf roofing"],
    "apogee_hvac": ["apogee"],
}

COI_PATTERNS = re.compile(
    r"\b(coi|certificate of insurance|cert(ificate)? holder|acord|"
    r"certificado de seguro|insurance certificate|liability insurance)\b",
    re.I,
)


def parse_message(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception:
        return None
    head, _, rest = raw.partition("----- Transport Headers -----")
    body = rest.partition("----- Body -----")[2].strip() if "----- Body -----" in rest else ""
    meta = {}
    for line in head.strip().splitlines():
        k, _, v = line.partition(":")
        meta[k.strip().lower()] = v.strip()
    return {
        "subject": meta.get("subject", ""),
        "from": meta.get("from", ""),
        "date": meta.get("date", ""),
        "body": body[:8000],
    }


def normalize_subject(subject):
    s = re.sub(r"^\s*((re|fw|fwd|rv|rv:|automatic reply)[:\s]+)+", "", subject or "", flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def fingerprint_pdf(path):
    """Classify a PDF: acord_coi (+ which client insured), requirements,
    scanned (image-only), or other."""
    try:
        doc = fitz.open(path)
        page1 = doc[0]
        text = ""
        for i, page in enumerate(doc):
            if i >= 3:
                break
            text += page.get_text()
        insured_text = page1.get_text(clip=INSURED_CLIP)
        page_count = doc.page_count
        doc.close()
    except Exception as e:
        return {"kind": "unreadable", "error": str(e)[:100]}

    tl = text.lower()
    if len(text.strip()) < 40:
        return {"kind": "scanned_pdf", "page_count": page_count}
    if "certificate of liability insurance" in tl:
        client = None
        # Prefer the INSURED box region; fall back to the full page text
        insured_low = insured_text.lower()
        for cid, tokens in CLIENT_TOKENS.items():
            if any(t in insured_low for t in tokens):
                client = cid
                break
        if client is None:
            for cid, tokens in CLIENT_TOKENS.items():
                if any(t in tl for t in tokens):
                    client = cid
                    break
        m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text[:600])
        # A readable insured-name line for reporting (skip ACORD labels)
        insured_name = None
        for line in insured_text.splitlines():
            l = line.strip()
            if (l and not l.isdigit() and "INSURED" not in l.upper()
                    and "INSURER" not in l.upper() and "NAIC" not in l.upper()
                    and ":" not in l and len(l) > 3):
                insured_name = l
                break
        return {
            "kind": "acord_coi",
            "client": client,
            "insured_name": insured_name,
            "issue_date": m.group(1) if m else None,
            "page_count": page_count,
        }
    if re.search(r"insurance requirement|minimum insurance|shall maintain|"
                 r"additional insured.*required|exhibit.*insurance", tl):
        return {"kind": "requirements_doc", "page_count": page_count}
    return {"kind": "other_pdf", "page_count": page_count}


SENT_DIR_RE = re.compile(r"^NEW_(\d{4}-\d{2}-\d{2})_(\d{6})_(.*)_(\d+)$")


def parse_sent_folder_name(entry):
    """Sent Items folders: NEW_YYYY-MM-DD_HHMMSS_<subject-fragment>_<id>.
    No message body was exported for sent mail — subject + timestamp only."""
    m = SENT_DIR_RE.match(entry)
    if not m:
        return None
    date, hms, subject = m.group(1), m.group(2), m.group(3)
    return {
        "subject": subject,
        "from": "Alejandro Bello (sent)",
        "date": f"{date} {hms[:2]}:{hms[2:4]}:{hms[4:6]}",
        "body": "",
    }


def main():
    def collect_attachments(mdir):
        att_dir = os.path.join(mdir, "attachments")
        atts = []
        if os.path.isdir(att_dir):
            for a in sorted(os.listdir(att_dir)):
                ap = os.path.join(att_dir, a)
                if os.path.isfile(ap):
                    atts.append({"name": a, "path": ap,
                                 "is_pdf": a.lower().endswith(".pdf")})
        return atts

    messages = []
    for folder in FOLDERS:
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
            msg["attachments"] = collect_attachments(mdir)
            messages.append(msg)

    # Sent Items: no message.txt — subject/date come from the folder name
    sent_base = os.path.join(ARCHIVE, SENT_FOLDER)
    if os.path.isdir(sent_base):
        for entry in sorted(os.listdir(sent_base)):
            mdir = os.path.join(sent_base, entry)
            if not os.path.isdir(mdir):
                continue
            msg = parse_sent_folder_name(entry)
            if msg is None:
                continue
            msg["folder"] = SENT_FOLDER
            msg["dir"] = mdir
            msg["attachments"] = collect_attachments(mdir)
            messages.append(msg)

    print(f"parsed messages: {len(messages)}")

    # COI relevance: subject/body pattern OR any ACORD PDF attachment
    pdf_cache = {}
    coi_msgs = []
    for msg in messages:
        relevant = bool(COI_PATTERNS.search(msg["subject"] or "")) or bool(
            COI_PATTERNS.search(msg["body"] or "")
        )
        for att in msg["attachments"]:
            if att["is_pdf"]:
                fp = pdf_cache.get(att["path"])
                if fp is None:
                    fp = fingerprint_pdf(att["path"])
                    pdf_cache[att["path"]] = fp
                att["fingerprint"] = fp
                if fp["kind"] == "acord_coi":
                    relevant = True
        if relevant:
            coi_msgs.append(msg)

    print(f"COI-related messages: {len(coi_msgs)}")
    print(f"PDFs fingerprinted: {len(pdf_cache)}")

    kinds = {}
    for fp in pdf_cache.values():
        kinds[fp["kind"]] = kinds.get(fp["kind"], 0) + 1
    print(f"PDF kinds: {kinds}")

    delivered = [
        (p, fp) for p, fp in pdf_cache.items()
        if fp["kind"] == "acord_coi" and fp.get("client")
    ]
    print(f"ACORD COIs for OUR clients: {len(delivered)}")

    # Thread grouping by normalized subject
    threads = {}
    for msg in coi_msgs:
        key = normalize_subject(msg["subject"])
        threads.setdefault(key, []).append(msg)
    for key in threads:
        threads[key].sort(key=lambda m: m["date"])

    print(f"threads: {len(threads)}")

    with open(OUT_PATH, "w") as f:
        json.dump(
            {
                "generated": datetime.now().isoformat(),
                "message_count": len(messages),
                "coi_message_count": len(coi_msgs),
                "thread_count": len(threads),
                "threads": threads,
            },
            f, indent=1,
        )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
