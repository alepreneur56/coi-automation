"""
build_training_library.py — A3 step 4: turn Alex's review decisions into the
few-shot training library for the classifier prompt.

Input: the decisions JSON exported from training/coi_review.html —
  {"<coi sha1 hash>": {"decision": "approve"|"disagree"|"skip", "note": "..."}}
where "approve" means Alex AGREES with our automated verdict in
training/graded_cois.json and "disagree" means the verdict is wrong (his
note explains why).

Pipeline:
  1. Resolve each decided COI to an EFFECTIVE verdict (approve keeps ours,
     disagree inverts correct<->incorrect; disagreed questionables are
     settled by the note or parked in needs_discussion — never guessed).
  2. For effective-CORRECT COIs with a usable client request body in their
     thread (corpus_index.json), build a few-shot example pair: cleaned
     request context + the parsed JSON the classifier should have produced.
     Candidates that cannot be modeled faithfully (truncated holder box,
     batch-shaped requests, non-US addresses) are rejected, not guessed.
  3. Bucket examples into the A3 categories, pick the best 2-4 per bucket
     (diverse clients, clean bodies, benchmark failure patterns), cap 18.
  4. Build negative examples from effective-INCORRECT COIs (max 5).
  5. Write training/library/training_examples.json, TRAINING_LIBRARY.md,
     and PROMPT_INTEGRATION_PLAN.md. Does NOT touch coi_system_prompt.txt.

Usage:
  .venv/bin/python training/build_training_library.py \
      --decisions ~/Downloads/coi_review_decisions.json
  (optional: --out <dir>, default training/library/)

Idempotent — reruns overwrite the three outputs deterministically.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reuse the review page's body cleaning and team detection — one source of truth
from training.build_review import clean_body, is_team_message  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")
IDX_PATH = os.path.join(BASE, "training", "corpus_index.json")
REGISTRY_PATH = os.path.join(BASE, "coi_client_registry.json")
DEFAULT_OUT = os.path.join(BASE, "training", "library")

MAX_TOTAL = 18
MAX_PER_BUCKET = 4
MIN_PER_BUCKET = 2
MAX_NEGATIVES = 5

BUCKETS = [
    "requirements_pdf_attached",
    "reference_coi_attached",
    "complex_endorsements",
    "specific_language",
    "spanish",
    "vague_or_missing_info",
    "body_only_request",
]

# Buckets that map onto the benchmark's top failure patterns get a boost
# (BENCHMARK_REPORT.md: ABSOLUTE RULE violations on attached COIs/requirements,
# address hallucination when no address is given, Spanish + attachment cases).
BENCHMARK_PRIORITY = {
    "requirements_pdf_attached",
    "reference_coi_attached",
    "vague_or_missing_info",
    "spanish",
}


# ---------------------------------------------------------------- decisions

def sentiment(note):
    """Classify a disagree-note on a questionable verdict. Returns
    'positive' (COI was actually fine), 'negative' (actually wrong), or
    'ambiguous' (goes to needs_discussion — we never guess)."""
    t = (note or "").lower()
    pos = re.search(
        r"\b(fine|good|correct|ok|okay|right|accurate|acceptable|valid|"
        r"no (issue|problem)|looks (right|good)|est\S* bien|bien)\b", t)
    neg = re.search(
        r"\b(wrong|incorrect|bad|error|mistake|missing|missed|failed|"
        r"should (have|not|never)|shouldn'?t|mal|equivocad\S*|falta)\b", t)
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return "ambiguous"


def effective_verdict(our_verdict, decision, note):
    """Returns 'correct' | 'incorrect' | 'questionable' | 'needs_discussion'
    | None (skipped / undecided)."""
    if decision == "approve":
        return our_verdict
    if decision == "disagree":
        if our_verdict == "correct":
            return "incorrect"
        if our_verdict == "incorrect":
            return "correct"
        # questionable — the note decides; ambiguous goes to discussion
        s = sentiment(note)
        if s == "positive":
            return "correct"
        if s == "negative":
            return "incorrect"
        return "needs_discussion"
    return None  # skip or malformed


# ---------------------------------------------------------- request finding

JUNK_SUBJECT = re.compile(r"no action required|out of office|automatic reply", re.I)
JUNK_BODY = re.compile(r"congratulations|your business is covered", re.I)
REQUEST_HINT = re.compile(
    r"\b(coi|cois|cert\w*|certificad\w*|certificate\w*|insurance|seguro|"
    r"holder|insured|renew\w*|update\w*)\b", re.I)
STUBS = {"see below", "fyi", "see attached", "please see below", "ver abajo"}
EXTERNAL_BANNER = re.compile(
    r"You don'?t often get email from[^\n]{0,140}\n?"
    r"(\s*Learn why this is important\.?\s*\n?)?", re.I)
REPLY_HEAD = re.compile(r"\bOn [^\n]{8,120}? wrote:\s*", re.I)

SPANISH = re.compile(
    r"\b(necesito|adjunto|por favor|buen[oa]s (d[ií]as|tardes|noches)|"
    r"gracias|certificado|env[ií]ame|hola|direcci[oó]n|p[oó]liza|"
    r"aseguranza|para|puede[ns]?|quiero|hacer|este|esta)\b", re.I)
ENGLISH = re.compile(
    r"\b(the|please|need|can|you|for|send|attached|thanks|thank you|"
    r"good (morning|afternoon)|address|with)\b", re.I)

# A bare 5-digit number is usually a street number; only count a ZIP when it
# is anchored to a state token ("Davie, FL 33330") or a zip keyword.
STATE_ZIP = re.compile(r"\b[A-Z]{2}[,.]?\s+(\d{5})(?:[- ]\d{4})?\b")
KEYWORD_ZIP = re.compile(r"\bzip(?:\s?code)?\W{0,6}(\d{5})\b", re.I)
MANGLED_ZIP = re.compile(r"\b[A-Z]{2}\s+\d{3}\s\d{2}\b")  # "FL 331 31"
CAN_POSTAL = re.compile(r"\b[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d\b")
STREETISH_LINE = re.compile(
    r"^\s*\d{1,6}\s+[\w. ]{2,40}\b(st|street|ave|avenue|rd|road|dr|drive|"
    r"blvd|ct|court|cir|circle|ln|lane|way|hwy|pkwy)\b", re.I | re.M)


def body_zips(text):
    return set(STATE_ZIP.findall(text)) | set(KEYWORD_ZIP.findall(text))
ENDORSEMENT_CODE = re.compile(r"\bC[GA]\s?\d{2}\s?\d{2}\b")
ENDORSEMENT_ASK = re.compile(
    r"(add|include|list|name|agregar|incluir|poner)\w*[^.\n]{0,100}"
    r"(additional insured|asegurado adicional|waiver of subrogation)", re.I)
SPECIFIC_LANGUAGE = re.compile(
    r"must (state|read|say|show|include)|verbiage|exact (language|wording)|"
    r"wording|the following language|as follows:|que diga|special language", re.I)
UNIT_PROJECT = re.compile(r"\b(unit|suite|ste\.?|apt|apartment|apto|project)\b[\s#]*\w", re.I)
REQ_DOC_NAME = re.compile(r"requirement|exhibit|insurance req|sample", re.I)


def detect_language(text):
    sp = len(SPANISH.findall(text))
    en = len(ENGLISH.findall(text))
    return "spanish" if sp >= 2 and sp > en else "english"


def usable_own_body(msg):
    """Cleaned own-words body of a client message, or None if it is a
    forward stub / junk / acknowledgment / not a request."""
    own, _quoted = clean_body(msg.get("body"))
    if not own:
        return None
    own = EXTERNAL_BANNER.sub("", own)
    own = REPLY_HEAD.split(own)[0].strip()  # drop quoted-reply leakage
    if len(own) < 40 or own.lower() in STUBS:
        return None
    if JUNK_SUBJECT.search(msg.get("subject") or "") or JUNK_BODY.search(own):
        return None
    if not REQUEST_HINT.search(own):
        return None
    return own


def strip_signature(body, from_name):
    """Body with the sender's signature block removed — used ONLY for
    address/ZIP analysis (the display body keeps the signature, since the
    classifier sees signatures in production too)."""
    name = re.sub(r"<[^>]*>", "", from_name or "").strip()
    if len(name) >= 5:
        i = body.lower().find(name.lower(), 30)
        if i > 0:
            return body[:i]
    return body


def find_request_message(msgs, before_date=None):
    """First usable client (non-team) message in the thread, preferring
    messages at or before the delivered COI's date."""
    candidates = []
    for m in msgs:
        if is_team_message(m):
            continue
        own = usable_own_body(m)
        if own:
            candidates.append((m, own))
    if not candidates:
        return None, None
    if before_date:
        prior = [(m, o) for m, o in candidates if (m.get("date") or "") <= before_date]
        if prior:
            return prior[0]
    return candidates[0]


# ------------------------------------------------------------ holder parsing

CSZ_RE = re.compile(r"^(.*?)[,]?\s+([A-Z]{2})\.?,?\s+(\d{5})(?:[- ]\d{4})?\s*$")
JUNK_HOLDER_LINE = re.compile(r"^(LIVE CERTIFICATE|SAMPLE|VOID|CERTIFICATE HOLDER)\b", re.I)
STREET_START = re.compile(r"^(\d|p\.?o\.?\s?box)", re.I)
STREET_WORDS = re.compile(
    r"\b(st|street|ave|avenue|rd|road|dr|drive|blvd|ct|court|cir|circle|"
    r"ln|lane|way|hwy|pkwy|ter|pl|suite|ste)\b\.?", re.I)


def parse_holder(holder_text):
    """Parse the graded holder-box text into the schema's certificate_holder
    fields. The full-box crop often stacks a STALE holder block (the
    template's previous holder) above the real one — blocks end at a
    city/state/ZIP line, and the REAL holder is the last complete block.
    Returns dict or None when the text does not parse cleanly (truncated
    crop, non-US address, leftover lines after the last address)."""
    lines = [l.strip() for l in (holder_text or "").splitlines()
             if l.strip() and not JUNK_HOLDER_LINE.match(l.strip())]
    csz_idx = [i for i, l in enumerate(lines) if CSZ_RE.match(l)]
    if not csz_idx:
        return None
    if csz_idx[-1] != len(lines) - 1:
        return None  # text continues after the last address — truncated crop
    end = csz_idx[-1]
    start = (csz_idx[-2] + 1) if len(csz_idx) > 1 else 0
    block = lines[start:end + 1]
    if len(block) < 3:
        return None
    m = CSZ_RE.match(block[-1])
    city, state, zipc = m.group(1).strip().rstrip(","), m.group(2), m.group(3)
    street_i = None
    for i in range(len(block) - 2, 0, -1):
        if STREET_START.match(block[i]):
            street_i = i
            break
    if street_i is None:
        return None
    street = block[street_i]
    line2 = None
    if street_i + 1 < len(block) - 1:
        extra = block[street_i + 1:len(block) - 1]
        if len(extra) == 1:
            line2 = extra[0]
        else:
            return None  # more than one line between street and CSZ — unclear
    names = block[:street_i]
    if not names:
        return None
    # A "name" line that looks like a street address means a stale block bled
    # into this one — refuse to guess.
    for n in names[1:]:
        if STREET_START.match(n) and STREET_WORDS.search(n):
            return None
    return {
        "names": names,
        "holder": {
            "name": names[0],
            "address_line_1": street,
            "address_line_2": line2,
            "city": city,
            "state": state,
            "zip": zipc,
        },
        "all_lines": names + [street] + ([line2] if line2 else [])
                     + [f"{city}, {state} {zipc}"],
    }


def fallback_holder_name(holder_text):
    """Best-effort holder name for vague-request examples where the full
    parse failed: first line after the last complete address block."""
    lines = [l.strip() for l in (holder_text or "").splitlines()
             if l.strip() and not JUNK_HOLDER_LINE.match(l.strip())]
    csz_idx = [i for i, l in enumerate(lines) if CSZ_RE.match(l)]
    if csz_idx and csz_idx[-1] < len(lines) - 1:
        return lines[csz_idx[-1] + 1]
    return lines[0] if lines else None


def name_in_body(name, body):
    tokens = [t for t in re.findall(r"[A-Za-z]{3,}", name or "")
              if t.lower() not in ("the", "llc", "inc", "corp", "and")]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if re.search(re.escape(t), body, re.I))
    return hits / len(tokens) >= 0.6


# ------------------------------------------------------------------ registry

def load_registry():
    with open(REGISTRY_PATH) as f:
        reg = json.load(f)
    out = {}
    for c in reg["clients"]:
        tpl = next((t for t in c["templates"] if t.get("is_default")),
                   c["templates"][0])
        date_now = (tpl.get("editable_fields", {}).get("date", {})
                    .get("current_value") or "MM/DD/YYYY")
        holder_ph = (tpl.get("editable_fields", {}).get("certificate_holder", {})
                     .get("placeholder_text") or "NAME\nADDRESS\nCITY, STATE ZIP")
        out[c["client_id"]] = {
            "canonical_name": c["canonical_name"],
            "template_id": tpl["template_id"],
            "template_filename": tpl["filename"],
            "holder_placeholder": holder_ph,
            "date_placeholder": date_now,
        }
    return out


# ------------------------------------------------------------------ buckets

def classify_attachments(msg):
    """Summarize the client message's attachments and flag insurance content."""
    summary, kinds = [], set()
    for a in msg.get("attachments", []):
        name = a.get("name") or "attachment"
        fp = a.get("fingerprint") or {}
        kind = fp.get("kind")
        if a.get("is_pdf"):
            if kind == "acord_coi":
                who = fp.get("insured_name") or "unknown insured"
                summary.append(f"{name} (ACORD COI, insured: {who})")
                kinds.add("acord_coi")
            elif kind == "requirements_doc":
                summary.append(f"{name} (insurance requirements document)")
                kinds.add("requirements_doc")
            elif kind == "scanned_pdf":
                summary.append(f"{name} (scanned PDF, image-only)")
                kinds.add("scanned_pdf")
            else:
                summary.append(f"{name} (PDF)")
                kinds.add("other_pdf")
            if kind in ("other_pdf", "scanned_pdf") and REQ_DOC_NAME.search(name):
                kinds.add("requirements_doc")
        elif re.search(r"\.(png|jpe?g|gif)$", name, re.I):
            summary.append(f"{name} (image, likely signature graphic)")
        else:
            summary.append(name)
    return summary or ["none"], kinds


def pick_bucket(body, att_kinds, lang, addr_in_body):
    if "requirements_doc" in att_kinds:
        return "requirements_pdf_attached"
    if "acord_coi" in att_kinds:
        return "reference_coi_attached"
    if ENDORSEMENT_CODE.search(body) or ENDORSEMENT_ASK.search(body):
        return "complex_endorsements"
    if SPECIFIC_LANGUAGE.search(body):
        return "specific_language"
    if lang == "spanish":
        return "spanish"
    if not addr_in_body:
        return "vague_or_missing_info"
    return "body_only_request"


# ------------------------------------------------------- expected output JSON

ACK_EN = ("{first},\n\nThanks for the request. Alejandro is reviewing the "
          "requirements and will get back to you shortly.\n\nRegards,")
ACK_ES = ("{first},\n\nGracias por el envío. Alejandro está revisando "
          "los requisitos y te responderá pronto.\n\nSaludos,")
ASK_ADDR_EN = ("{first},\n\nHappy to put this together for you. I tried looking "
               "up the address for {holder} but couldn't find a match. Please "
               "send the address the certificate holder wants on the COI."
               "\n\nRegards,")
ASK_ADDR_ES = ("{first},\n\nCon gusto preparo el COI. Intenté buscar la "
               "dirección de {holder} pero no la encontré. Por favor "
               "envíame la dirección que el certificate holder quiere "
               "en el COI.\n\nSaludos,")
ASK_NAME_EN = ("{first},\n\nHappy to put this together for you. Please send "
               "the entity name and address of who is requesting the COI."
               "\n\nRegards,")
ASK_NAME_ES = ("{first},\n\nCon gusto preparo el COI. Por favor envíame el "
               "nombre y dirección de la entidad que está pidiendo el COI."
               "\n\nSaludos,")


def first_name(from_name):
    name = re.sub(r"<[^>]*>", "", from_name or "").strip().strip('"')
    return name.split()[0] if name else "Hello"


def confidence_note(reginfo, msg, body):
    """Truthful confidence note: does the sender/body actually reference the
    client, or was the client established by the thread context (third-party
    requester, e.g. a county asking on our insured's behalf)?"""
    tokens = [t for t in re.findall(r"[A-Za-z]{4,}", reginfo["canonical_name"])
              if t.lower() not in ("solutions", "services", "roofing", "hvac",
                                   "air", "conditioning", "power", "corp",
                                   "mechanical")] \
        or re.findall(r"[A-Za-z]{3,}", reginfo["canonical_name"])
    haystack = f"{msg.get('from') or ''} {msg.get('subject') or ''} {body}"
    if any(re.search(re.escape(t), haystack, re.I) for t in tokens):
        return (f"Sender and body context match {reginfo['canonical_name']} "
                f"in the registry.")
    return (f"Client is {reginfo['canonical_name']} from the thread context; "
            f"the sender is a third party requesting on our insured's behalf.")


def to_mmddyyyy(date_str):
    try:
        return datetime.strptime((date_str or "")[:10], "%Y-%m-%d").strftime("%m/%d/%Y")
    except ValueError:
        return "MM/DD/YYYY"


def build_expected_output(bucket, reginfo, parsed, msg, body, lang, client_id,
                          vague_holder_name=None):
    """The parsed JSON the classifier should have produced for this request,
    following the OUTPUT FORMAT schema in coi_system_prompt.txt."""
    first = first_name(msg.get("from"))
    date_ins = to_mmddyyyy(msg.get("date"))

    if bucket == "vague_or_missing_info":
        known_name = vague_holder_name and name_in_body(vague_holder_name, body)
        if known_name:
            reply = (ASK_ADDR_ES if lang == "spanish" else ASK_ADDR_EN).format(
                first=first, holder=vague_holder_name)
            summary = (f"Client requests a COI for {reginfo['canonical_name']} "
                       f"with {vague_holder_name} as certificate holder but "
                       f"provided no address, and lookup could not confirm one.")
        else:
            reply = (ASK_NAME_ES if lang == "spanish" else ASK_NAME_EN).format(
                first=first)
            summary = (f"Client asks {reginfo['canonical_name']} for a COI but "
                       f"the request does not identify the certificate holder.")
        return {
            "classification": "coi_request_incomplete",
            "reply_text": reply,
            "original_request_summary": summary,
        }

    holder = parsed["holder"]
    summary = (f"Client requests a COI for {reginfo['canonical_name']} with "
               f"{holder['name']} as certificate holder.")
    complex_review = bucket in ("requirements_pdf_attached",
                                "reference_coi_attached",
                                "complex_endorsements",
                                "specific_language")
    out = {
        "classification": ("coi_complex_review_required" if complex_review
                           else "coi_request_complete"),
        "reply_text": ((ACK_ES if lang == "spanish" else ACK_EN)
                       .format(first=first) if complex_review else None),
        "original_request_summary": summary,
        "status": "ready",
        "client_id": client_id,
        "client_canonical_name": reginfo["canonical_name"],
        "template_id": reginfo["template_id"],
        "template_filename": reginfo["template_filename"],
        "confidence": "high",
        "confidence_notes": confidence_note(reginfo, msg, body),
        "certificate_holder": holder,
        "date_to_insert": date_ins,
        "project_name": None,
        "project_address": None,
        "project_unit": None,
        "is_permit": False,
        "send_completed_coi_to": None,
        "flags": [],
        "edits_to_make": [
            {"field": "certificate_holder", "action": "replace",
             "old_value": reginfo["holder_placeholder"],
             "new_value": "\n".join(parsed["all_lines"])},
            {"field": "date", "action": "replace",
             "old_value": reginfo["date_placeholder"], "new_value": date_ins},
            {"field": "description_of_operations", "action": "replace",
             "old_value": "Project name & Address ( If Applicable)",
             "new_value": ""},
        ],
    }
    if len(parsed["names"]) > 1:
        out["certificate_holder_lines"] = parsed["all_lines"]
    if complex_review:
        reasons = {
            "requirements_pdf_attached":
                "Client attached an insurance requirements document. The "
                "ABSOLUTE RULE routes any attachment with insurance content "
                "to Alejandro for review before anything ships.",
            "reference_coi_attached":
                "Client attached a prior COI as reference. A reference COI is "
                "insurance content, so the ABSOLUTE RULE applies even though "
                "the holder is fully extractable from it.",
            "complex_endorsements":
                "Body asks for additional insured / waiver wording beyond a "
                "plain cert-holder request. In-body requirements route to "
                "review.",
            "specific_language":
                "Body asks for specific certificate wording. Custom language "
                "requests route to review.",
        }
        out["review_summary"] = reasons[bucket]
        out["coverage_analysis"] = {
            "required_coverages": [],
            "required_endorsements": [],
            "special_language": None,
            "notes": "Draft prepared from extracted holder info; "
                     "Alejandro to verify against the attachment/body.",
        }
    return out


TEACHING = {
    "body_only_request":
        "A plain cert-holder request with a complete address in the body is "
        "coi_request_complete. Use the client's address verbatim, never "
        "verify or second-guess it.",
    "requirements_pdf_attached":
        "An attached requirements document triggers the ABSOLUTE RULE: "
        "classification is coi_complex_review_required no matter how clean "
        "the extraction is. Extract the holder for the draft, never ship.",
    "reference_coi_attached":
        "A prior/reference COI attached to the request IS insurance content. "
        "Extract the holder from it, but the classification stays "
        "coi_complex_review_required. (Top benchmark failure: these were "
        "marked ready and would have shipped unreviewed.)",
    "complex_endorsements":
        "When the body asks to add additional insured or waiver wording "
        "beyond the template boilerplate, that is an in-body requirements "
        "request: coi_complex_review_required, never an automatic edit.",
    "specific_language":
        "Requests for exact certificate wording route to Alejandro. "
        "The classifier extracts what it can but does not modify template "
        "language on its own.",
    "spanish":
        "Spanish request: classification logic is unchanged, reply_text is "
        "in Spanish (Saludos, / envíame, never mándame), the JSON stays in "
        "English.",
    "vague_or_missing_info":
        "Holder information is missing from the request: look it up, and if "
        "the lookup cannot confirm a single match, ask. NEVER invent an "
        "address (the benchmark's most dangerous failure was a hallucinated "
        "address shipped at high confidence).",
}


# ------------------------------------------------------------------ selection

def score_candidate(cand):
    s = 0.0
    if cand["bucket"] in BENCHMARK_PRIORITY:
        s += 3
    if 80 <= len(cand["request_context"]["body"]) <= 1200:
        s += 2
    if cand["delivered_by_team"]:
        s += 1
    if (cand["message_date"] or "") >= "2026":
        s += 1
    if UNIT_PROJECT.search(cand["request_context"]["body"]):
        s -= 2  # unit/project fields not modeled here; avoid teaching them wrong
    return s


def select_examples(candidates):
    """2-4 per bucket, 18 total, greedy with client-diversity penalty."""
    by_bucket = {b: [] for b in BUCKETS}
    for c in candidates:
        by_bucket[c["bucket"]].append(c)
    for b in by_bucket:
        by_bucket[b].sort(key=lambda c: (-c["score"], c["hash"]))

    picked, picked_hashes, client_count = [], set(), {}

    def take(bucket):
        best, best_key = None, None
        for c in by_bucket[bucket]:
            if c["hash"] in picked_hashes:
                continue
            key = c["score"] - 1.5 * client_count.get(c["client"], 0)
            if best is None or key > best_key:
                best, best_key = c, key
        if best:
            picked.append(best)
            picked_hashes.add(best["hash"])
            client_count[best["client"]] = client_count.get(best["client"], 0) + 1
        return best

    # breadth first: up to MIN_PER_BUCKET from every bucket
    for _round in range(MIN_PER_BUCKET):
        for b in BUCKETS:
            if len(picked) >= MAX_TOTAL:
                break
            if sum(1 for p in picked if p["bucket"] == b) < len(by_bucket[b]):
                take(b)
    # then fill to MAX_PER_BUCKET / MAX_TOTAL by global merit
    while len(picked) < MAX_TOTAL:
        pool = []
        for b in BUCKETS:
            n_in = sum(1 for p in picked if p["bucket"] == b)
            if n_in >= MAX_PER_BUCKET:
                continue
            pool += [c for c in by_bucket[b] if c["hash"] not in picked_hashes]
        if not pool:
            break
        pool.sort(key=lambda c: (-(c["score"] - 1.5 * client_count.get(c["client"], 0)),
                                 c["hash"]))
        take(pool[0]["bucket"])
    picked.sort(key=lambda c: (BUCKETS.index(c["bucket"]), c["hash"]))
    return picked


# ----------------------------------------------------------------- negatives

P_CODE_LESSON = {
    "P1": "Delete the 'Project name & Address (If Applicable)' placeholder "
          "line whenever no project is provided; it must never appear on a "
          "finished COI.",
    "P4": "Always insert today's date in the date box. A COI must never go "
          "out without an issue date.",
    "P5": "Never ship a COI with an empty certificate holder box.",
    "P6": "When multiple holder entities are listed, the boilerplate must "
          "say 'Certificate Holders' (plural).",
    "P9": "The certificate holder on the COI must be exactly the entity the "
          "client requested.",
}


def build_negatives(records_by_hash, effective, notes):
    negs = []
    for h, ev in sorted(effective.items()):
        if ev != "incorrect":
            continue
        rec = records_by_hash[h]
        note = notes.get(h)
        fails = [p for p in rec["problems"] if p["severity"] == "FAIL"]
        if not note and not fails:
            continue
        own, _ = clean_body(rec.get("request_excerpt"))
        request = own[:800] if own else "(no request text preserved in the archive)"
        wrong = []
        if note:
            wrong.append(f'Alex: "{note}"')
        wrong += [f'{p["code"]}: {p["message"]}' for p in fails]
        lessons = [P_CODE_LESSON[p["code"]] for p in fails if p["code"] in P_CODE_LESSON]
        if note and not lessons:
            lessons = ["Follow Alex's correction above; do not repeat this outcome."]
        negs.append({
            "hash": h,
            "client": rec["client"],
            "filename": rec["filename"],
            "request": request,
            "what_went_wrong": "; ".join(wrong),
            "correct_behavior": " ".join(dict.fromkeys(lessons)),
            "has_note": bool(note),
        })
    # prefer noted ones, then client diversity, deterministic order
    negs.sort(key=lambda n: (not n["has_note"], n["hash"]))
    out, seen_clients = [], {}
    for n in negs:
        if len(out) >= MAX_NEGATIVES:
            break
        if seen_clients.get(n["client"], 0) >= 2 and len(negs) > MAX_NEGATIVES:
            continue
        seen_clients[n["client"]] = seen_clients.get(n["client"], 0) + 1
        out.append(n)
    return out


# ------------------------------------------------------------------- outputs

def render_markdown(payload):
    L = []
    tag = " (SYNTHETIC decisions — regenerate with Alex's real export)" \
        if payload["synthetic"] else ""
    L.append(f"# COI Classifier Training Library{tag}")
    L.append("")
    L.append(f"Generated {payload['generated']} from `{payload['source_decisions']}` "
             f"by `training/build_training_library.py`.")
    L.append("")
    d = payload["decision_stats"]
    L.append(f"Decisions: {d['total']} total — {d['approve']} approve / "
             f"{d['disagree']} disagree / {d['skip']} skip / "
             f"{d['unknown_hashes']} unknown hashes. Effective verdicts: "
             f"{d['effective_correct']} correct, {d['effective_incorrect']} incorrect, "
             f"{d['effective_questionable']} questionable, "
             f"{d['needs_discussion']} needs discussion.")
    L.append("")
    L.append("## Coverage")
    L.append("")
    L.append("| Bucket | Selected | Available |")
    L.append("|---|---|---|")
    for b in BUCKETS:
        cov = payload["coverage"][b]
        L.append(f"| {b} | {cov['selected']} | {cov['available']} |")
    L.append(f"| **total** | **{sum(payload['coverage'][b]['selected'] for b in BUCKETS)}** "
             f"| **{sum(payload['coverage'][b]['available'] for b in BUCKETS)}** |")
    L.append("")
    L.append("Available = effective-correct COIs whose thread carries a usable, "
             "faithfully modelable client request. Truncated holder crops, "
             "batch-shaped requests, and non-US addresses are excluded rather "
             "than guessed.")
    L.append("")

    for b in BUCKETS:
        exs = payload["buckets"].get(b, [])
        L.append(f"## {b} ({len(exs)} example{'s' if len(exs) != 1 else ''})")
        L.append("")
        if not exs:
            L.append("_No usable material in this bucket yet — see Coverage and Gaps._")
            L.append("")
            continue
        for i, ex in enumerate(exs, 1):
            rc = ex["request_context"]
            L.append(f"### {b} — example {i} ({ex['client']}, {ex['message_date'] or 'undated'})")
            L.append("")
            L.append(f"- Subject: {rc['subject']}")
            L.append(f"- From: {rc['from_name']}")
            L.append(f"- Attachments: {'; '.join(rc['attachments_summary'])}")
            if ex.get("alex_note"):
                L.append(f"- Alex's note: {ex['alex_note']}")
            if ex.get("historical_resolution"):
                L.append(f"- Historical resolution: {ex['historical_resolution']}")
            L.append("")
            L.append("Request body (cleaned):")
            L.append("")
            L.append("```")
            L.append(rc["body"])
            L.append("```")
            L.append("")
            L.append("Expected classifier output:")
            L.append("")
            L.append("```json")
            L.append(json.dumps(ex["expected_output"], indent=2, ensure_ascii=False))
            L.append("```")
            L.append("")
            L.append(f"**Teaching point:** {ex['teaching_point']}")
            L.append("")

    L.append(f"## Negative examples ({len(payload['negative_examples'])})")
    L.append("")
    if not payload["negative_examples"]:
        L.append("_None — no effective-incorrect COIs with notes or FAIL findings._")
        L.append("")
    for i, n in enumerate(payload["negative_examples"], 1):
        L.append(f"### negative {i} ({n['client']}, {n['filename']})")
        L.append("")
        L.append("```")
        L.append(n["request"])
        L.append("```")
        L.append("")
        L.append(f"- What went wrong: {n['what_went_wrong']}")
        L.append(f"- Correct behavior: {n['correct_behavior']}")
        L.append("")

    L.append(f"## Needs discussion ({len(payload['needs_discussion'])})")
    L.append("")
    if not payload["needs_discussion"]:
        L.append("_None._")
    for nd in payload["needs_discussion"]:
        L.append(f"- `{nd['hash'][:10]}` {nd['client']} ({nd['filename']}) — our verdict "
                 f"was {nd['our_verdict']}, Alex disagreed"
                 + (f': "{nd["note"]}"' if nd.get("note") else " without a note")
                 + ". Resolve with Alex before using.")
    L.append("")
    return "\n".join(L)


def render_integration_plan(payload):
    n_pos = sum(payload["coverage"][b]["selected"] for b in BUCKETS)
    n_neg = len(payload["negative_examples"])
    gaps = [b for b in BUCKETS if payload["coverage"][b]["selected"] == 0]
    gaps_line = (", ".join(gaps) if gaps else "none")
    tag = ("\n> NOTE: this run used SYNTHETIC decisions "
           "(training/library/synthetic_decisions.json). Regenerate from "
           "Alex's real export before integrating.\n") if payload["synthetic"] else ""
    return f"""# Prompt Integration Plan — few-shot training examples
{tag}
How the {n_pos} positive examples and {n_neg} negative examples in
`training/library/training_examples.json` should be inserted into
`coi_system_prompt.txt`. This plan does NOT modify the prompt; apply it as a
separate, reviewed edit. Empty buckets this run: {gaps_line}.

## Where

Insert ONE new top-level section into `coi_system_prompt.txt`:

- Anchor by SECTION HEADINGS, not line numbers — the prompt is actively
  edited and line numbers drift.
- Place the new section immediately AFTER the `## RULES` section and BEFORE
  `## MULTI-ENTITY CERTIFICATE HOLDER HANDLING`.
- Rationale: at that point every rule the examples exercise has already
  been defined (ABSOLUTE RULE, STEP 0 precedence, ADDRESS LOOKUP, OUTPUT
  FORMAT, RULES), and the examples land before the long PDF-engine
  reference sections. The existing worked examples (ABSOLUTE RULE examples
  1-3, OUTPUT FORMAT examples A-E) stay where they are — the new section
  complements them with real traffic.

## Section skeleton

```markdown
---

## TRAINING EXAMPLES FROM REAL REQUESTS

The following are real historical client requests (bodies cleaned, holder
data verified against the COIs actually delivered and reviewed by
Alejandro). Match their patterns. Dates in these examples are historical;
always use TODAY'S DATE from your input.

### <bucket name in human form, e.g. "Requests with a reference COI attached">

**Example — <client>, <date>**
Subject: ...
Attachments: ...
Body:
<request_context.body>

Correct output:
<expected_output JSON block, verbatim from training_examples.json>

Why: <teaching_point>

### Mistakes to never repeat

These historical requests were mishandled. Never reproduce these outcomes.

- <request one-liner> -> what went wrong: ... -> correct behavior: ...
```

## Framing rules for the edit

1. Copy `expected_output` blocks VERBATIM from training_examples.json —
   they follow the OUTPUT FORMAT schema exactly (including reply_text
   templates and edits_to_make). Do not paraphrase the JSON.
2. Keep bucket order: {", ".join(BUCKETS)}.
   Attachment buckets come first — they target the benchmark's top failure
   (ABSOLUTE RULE violations on reference COIs marked ready-to-ship).
3. Negative examples go in as the terse "Mistakes to never repeat" list
   (request one-liner -> what went wrong -> correct behavior), not as full
   JSON.
4. Do not include Alex's raw notes, file hashes, or historical_resolution
   fields in the prompt — they are provenance, kept in
   training_examples.json only.
5. Token budget: {n_pos} examples plus negatives is roughly 4-6k tokens.
   The system prompt is cached (the launchd service keeps it warm), so the
   cost impact is one cache write per deploy. If trimming is needed, drop
   to 2 per bucket starting from body_only_request — per
   BENCHMARK_REPORT.md that is the lane the classifier already handles
   best (88% on coi_request_complete).
6. After integrating, re-run
   `.venv/bin/python training/benchmark_classifier.py` — results are keyed
   to the prompt hash, so all 26 cases re-run automatically. The number to
   beat is 16/26 (62%) adjacent classification; watch specifically for the
   five ABSOLUTE RULE misses (bench-4, 15, 16, 19, 22) flipping to
   coi_complex_review_required.

## Regenerating this library

```
.venv/bin/python training/build_training_library.py \\
    --decisions <path to Alex's coi_review_decisions.json>
```

All three outputs are overwritten in place (idempotent, deterministic).
"""


# ---------------------------------------------------------------------- main

def build_candidate(rec, tkey, msg, body, reginfo, notes):
    """Build one positive-example candidate, or None if the request cannot
    be modeled faithfully."""
    att_summary, att_kinds = classify_attachments(msg)
    lang = detect_language(body)
    parsed = parse_holder(rec.get("holder_text"))
    analysis_body = strip_signature(body, msg.get("from"))
    zips = body_zips(analysis_body)
    has_addr_noise = bool(CAN_POSTAL.search(analysis_body)
                          or MANGLED_ZIP.search(analysis_body))
    holder_zip = parsed["holder"]["zip"] if parsed else None
    addr_in_body = bool(holder_zip and holder_zip in zips)

    if addr_in_body and len(zips) > 1:
        return None  # multiple addresses in body — batch-shaped, not modeled
    if not addr_in_body and (zips or has_addr_noise):
        # body carries some address we can't reconcile with the delivered
        # holder (mismatched address, mangled ZIP, non-US) — don't guess
        return None

    bucket = pick_bucket(body, att_kinds, lang, addr_in_body)
    vague_name = None
    if bucket == "vague_or_missing_info":
        if STREETISH_LINE.search(analysis_body):
            return None  # a street address IS in the body — not truly vague
        vague_name = (parsed["holder"]["name"] if parsed
                      else fallback_holder_name(rec.get("holder_text")))
        if not vague_name:
            return None
    elif not parsed:
        return None  # complete/complex examples need a clean holder parse

    cand = {
        "hash": rec["hash"],
        "client": rec["client"],
        "thread": tkey,
        "message_date": msg.get("date"),
        "bucket": bucket,
        "delivered_by_team": False,  # filled by caller
        "alex_note": notes.get(rec["hash"]),
        "request_context": {
            "subject": msg.get("subject") or "(no subject)",
            "from_name": msg.get("from") or "(unknown)",
            "body": body[:1500],
            "attachments_summary": att_summary,
        },
        "expected_output": build_expected_output(
            bucket, reginfo, parsed, msg, body, lang, rec["client"],
            vague_holder_name=vague_name),
        "teaching_point": TEACHING[bucket],
    }
    if bucket == "vague_or_missing_info":
        cand["historical_resolution"] = " / ".join(
            l.strip() for l in (rec.get("holder_text") or "").splitlines()
            if len(l.strip()) > 2)  # drop crop-garbage fragments
        cand["teaching_point"] += (
            " (This request was historically resolved to the holder shown in "
            "historical_resolution.)")
    return cand


def main():
    ap = argparse.ArgumentParser(
        description="Build the few-shot training library from review decisions.")
    ap.add_argument("--decisions", required=True,
                    help="coi_review_decisions.json exported from coi_review.html")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="output directory (default training/library/)")
    args = ap.parse_args()

    with open(args.decisions) as f:
        decisions_raw = json.load(f)
    meta = decisions_raw.get("_meta") or {}
    synthetic = bool(meta.get("synthetic")) or "synthetic" in os.path.basename(
        args.decisions).lower()
    decisions = {h: v for h, v in decisions_raw.items()
                 if not h.startswith("_") and isinstance(v, dict)}

    with open(GRADED_PATH) as f:
        graded = json.load(f)
    with open(IDX_PATH) as f:
        idx = json.load(f)
    registry = load_registry()
    records_by_hash = {r["hash"]: r for r in graded["records"]}

    # 1 — effective verdicts
    effective, notes, needs_discussion = {}, {}, []
    stats = {"total": len(decisions), "approve": 0, "disagree": 0, "skip": 0,
             "unknown_hashes": 0, "effective_correct": 0,
             "effective_incorrect": 0, "effective_questionable": 0,
             "needs_discussion": 0}
    for h, d in sorted(decisions.items()):
        rec = records_by_hash.get(h)
        if rec is None:
            stats["unknown_hashes"] += 1
            continue
        decision = (d.get("decision") or "").lower()
        note = (d.get("note") or "").strip() or None
        if decision in ("approve", "disagree", "skip"):
            stats[decision] += 1
        if note:
            notes[h] = note
        ev = effective_verdict(rec["verdict"], decision, note)
        if ev is None:
            continue
        if ev == "needs_discussion":
            stats["needs_discussion"] += 1
            needs_discussion.append({"hash": h, "client": rec["client"],
                                     "filename": rec["filename"],
                                     "our_verdict": rec["verdict"], "note": note})
            continue
        effective[h] = ev
        stats[f"effective_{ev}"] += 1

    # 2 + 3 — positive candidates from effective-correct COIs, one per thread
    candidates, seen_threads = [], set()
    for h in sorted(effective):
        if effective[h] != "correct":
            continue
        rec = records_by_hash[h]
        reginfo = registry.get(rec["client"])
        if not reginfo:
            continue
        for tkey in rec["threads"]:
            if tkey in seen_threads:
                continue
            msgs = idx["threads"].get(tkey, [])
            msg, body = find_request_message(msgs, before_date=rec.get("message_date"))
            if not msg:
                continue
            seen_threads.add(tkey)
            cand = build_candidate(rec, tkey, msg, body, reginfo, notes)
            if not cand:
                continue
            cand["delivered_by_team"] = any(
                is_team_message(m) for m in msgs
                for a in m.get("attachments", []) if a["path"] == rec["path"])
            cand["score"] = score_candidate(cand)
            candidates.append(cand)

    available = {b: sum(1 for c in candidates if c["bucket"] == b) for b in BUCKETS}
    picked = select_examples(candidates)

    # 4 — negatives
    negatives = build_negatives(records_by_hash, effective, notes)

    # 5 — outputs
    coverage = {b: {"available": available[b],
                    "selected": sum(1 for p in picked if p["bucket"] == b)}
                for b in BUCKETS}
    buckets_out = {b: [] for b in BUCKETS}
    for p in picked:
        buckets_out[p["bucket"]].append({k: v for k, v in p.items() if k != "score"})
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source_decisions": os.path.basename(args.decisions),
        "synthetic": synthetic,
        "decision_stats": stats,
        "coverage": coverage,
        "buckets": buckets_out,
        "negative_examples": negatives,
        "needs_discussion": needs_discussion,
    }

    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "training_examples.json")
    md_path = os.path.join(args.out, "TRAINING_LIBRARY.md")
    plan_path = os.path.join(args.out, "PROMPT_INTEGRATION_PLAN.md")
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    with open(md_path, "w") as f:
        f.write(render_markdown(payload))
    with open(plan_path, "w") as f:
        f.write(render_integration_plan(payload))

    print(f"decisions: {stats}")
    print("coverage (selected/available): " + ", ".join(
        f"{b} {coverage[b]['selected']}/{coverage[b]['available']}" for b in BUCKETS))
    print(f"examples: {len(picked)} positive, {len(negatives)} negative, "
          f"{len(needs_discussion)} needs-discussion")
    for p in (json_path, md_path, plan_path):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
