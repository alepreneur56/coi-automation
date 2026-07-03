"""
endorsements.py
---------------
A9 — endorsement documentation attachments. Pure Python, no API calls.

Three responsibilities:

1. DETECT which endorsement types a COI request is demanding, from the
   classifier's parsed JSON (coverage_analysis / review_summary) and, when
   present, the extracted text of attached requirements documents.
   Keyword/pattern based and deliberately conservative: a plain cert-holder
   request produces zero demands.

2. DECIDE what to do about each demand against coi_endorsement_registry.json:
     - status "blanket" + PDF on disk (endorsements/<client_id>/)  -> attach
     - status "blanket" + PDF not on file                          -> producer note
     - status "scheduled" (e.g. Rolando's auto AI/WOS/P&NC)        -> flag: a
       carrier endorsement request is needed. NEVER attach. (Hard rule,
       Alex 2026-07-03.)
     - status "none"/"unverified", or nothing on file              -> producer note

3. plan_for_decision(): the single entry point pipeline.decide_action() calls
   when config.ENDORSEMENTS_ENABLED is true. Never raises — any internal
   failure returns None and the COI flow proceeds exactly as before.

The endorsement registry is a SIBLING of coi_client_registry.json on purpose:
the client registry is injected verbatim into every classifier API call, and
endorsement data must not bloat or perturb that prompt.
"""

import base64
import json
import os
import re

import config

ENDORSEMENT_REGISTRY_PATH = os.path.join(config.BASE_DIR, "coi_endorsement_registry.json")

# Canonical endorsement types (match coi_endorsement_registry.json)
TYPES = (
    "additional_insured",
    "waiver_of_subrogation",
    "primary_noncontributory",
    "notice_of_cancellation",
    "per_project_aggregate",
)

# Canonical coverage lines (match the registry). None in a demand = any line.
LINES = ("GL", "Auto", "WC", "Umbrella", "Excess")

_registry_cache = None


def load_endorsement_registry(path=None):
    """Load (and cache) the endorsement registry. Explicit path skips cache."""
    global _registry_cache
    if path:
        with open(path, "r") as f:
            return json.load(f)
    if _registry_cache is None:
        with open(ENDORSEMENT_REGISTRY_PATH, "r") as f:
            _registry_cache = json.load(f)
    return _registry_cache


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

# ISO/NCCI form-number families -> (type, line). Matched case-insensitively
# with flexible spacing ("CG 20 10", "CG2010", "CG 20 10 04 13" all hit).
_FORM_MAP = [
    (r"CG\s*20\s*10", "additional_insured", "GL"),
    (r"CG\s*20\s*37", "additional_insured", "GL"),
    (r"CG\s*20\s*33", "additional_insured", "GL"),
    (r"CG\s*20\s*38", "additional_insured", "GL"),
    (r"CG\s*20\s*01", "primary_noncontributory", "GL"),
    (r"CG\s*24\s*04", "waiver_of_subrogation", "GL"),
    (r"CG\s*24\s*53", "waiver_of_subrogation", "GL"),
    (r"CG\s*25\s*03", "per_project_aggregate", "GL"),
    (r"CG\s*25\s*04", "per_project_aggregate", "GL"),
    (r"CA\s*20\s*48", "additional_insured", "Auto"),
    (r"CA\s*04\s*44", "waiver_of_subrogation", "Auto"),
    (r"WC\s*00\s*03\s*13", "waiver_of_subrogation", "WC"),
    (r"WC\s*04\s*03\s*06", "waiver_of_subrogation", "WC"),
]
_FORM_PATTERNS = [(re.compile(rx, re.IGNORECASE), t, l) for rx, t, l in _FORM_MAP]

# Phrase patterns per type. These run against classifier coverage_analysis
# text and requirements-doc text ONLY (never against a simple request's body,
# which carries no such fields) — that keeps the bread-and-butter path silent.
_PHRASE_MAP = [
    (r"additional\s+insured\s+endorsement", "additional_insured"),
    (r"copy\s+of\s+the\s+(?:blanket\s+)?additional\s+insured", "additional_insured"),
    (r"endorsement\s+naming\s+.{0,60}additional\s+insured", "additional_insured"),
    (r"\bAI\s+endorsement", "additional_insured"),
    (r"waiver\s+of\s+subrogation", "waiver_of_subrogation"),
    (r"subrogation\s+waiver", "waiver_of_subrogation"),
    (r"primary\s*(?:and|&|,)\s*non[\s-]?contributory", "primary_noncontributory"),
    (r"primary\s*(?:and|&|,)\s*noncontributory", "primary_noncontributory"),
    (r"notice\s+of\s+cancellation", "notice_of_cancellation"),
    (r"\b\d{1,3}\s*(?:/\s*\d{1,3}\s*)?days?'?\s+(?:advance\s+|written\s+|prior\s+)*notice\b.{0,60}cancel", "notice_of_cancellation"),
    (r"\b30\s*/\s*10\b.{0,40}(?:notice|cancel)", "notice_of_cancellation"),
    (r"per[\s-]?project\s+(?:general\s+)?aggregate", "per_project_aggregate"),
    (r"per[\s-]?location\s+(?:general\s+)?aggregate", "per_project_aggregate"),
    (r"aggregate\s+(?:limit\s+)?(?:shall\s+)?appl(?:y|ies)\s+(?:on\s+a\s+)?per[\s-]?(?:project|location)", "per_project_aggregate"),
    (r"designated\s+construction\s+project", "per_project_aggregate"),
]
_PHRASE_PATTERNS = [(re.compile(rx, re.IGNORECASE), t) for rx, t in _PHRASE_MAP]

# Line keywords looked for in a window around each phrase match.
_LINE_KEYWORDS = [
    (re.compile(r"\b(?:auto(?:mobile)?|vehicle)\b", re.IGNORECASE), "Auto"),
    (re.compile(r"\b(?:workers'?\s+comp\w*|work\s+comp|employer'?s\s+liability)\b", re.IGNORECASE), "WC"),
    (re.compile(r"\bumbrella\b", re.IGNORECASE), "Umbrella"),
    (re.compile(r"\bexcess\b", re.IGNORECASE), "Excess"),
    (re.compile(r"\b(?:general\s+liability|CGL|commercial\s+general)\b", re.IGNORECASE), "GL"),
]

_LINE_WINDOW = 90  # chars each side of a phrase match to scan for a line


def _infer_line(text, start, end):
    """Which coverage line does this phrase match refer to? Only commit when
    exactly one line keyword appears in the window — otherwise None (any)."""
    lo = max(0, start - _LINE_WINDOW)
    window = text[lo:end + _LINE_WINDOW]
    found = {line for pat, line in _LINE_KEYWORDS if pat.search(window)}
    if len(found) == 1:
        return found.pop()
    return None


def _gather_texts(parsed, requirements_texts=None):
    """Collect (source_label, text) pairs worth scanning. Simple complete
    requests carry none of these fields, so they yield nothing."""
    texts = []
    parsed = parsed or {}
    ca = parsed.get("coverage_analysis") or {}
    for entry in (ca.get("required_endorsements") or []):
        if entry:
            texts.append(("required_endorsements", str(entry)))
    for key in ("special_language", "notes"):
        val = ca.get(key)
        if val and str(val).strip():
            texts.append((f"coverage_analysis.{key}", str(val)))
    rs = parsed.get("review_summary")
    if rs and str(rs).strip():
        texts.append(("review_summary", str(rs)))
    for i, t in enumerate(requirements_texts or []):
        if t and t.strip():
            texts.append((f"requirements_doc[{i}]", t))
    return texts


def detect_demanded_endorsements(parsed, requirements_texts=None):
    """Return a list of demands: {"type", "line" (canonical or None = any),
    "evidence"}. Deduped on (type, line). Conservative: no endorsement
    language anywhere -> empty list."""
    demands = {}

    def add(dtype, line, evidence):
        key = (dtype, line)
        if key not in demands:
            demands[key] = {"type": dtype, "line": line, "evidence": evidence[:200]}

    for source, text in _gather_texts(parsed, requirements_texts):
        for pat, dtype, line in _FORM_PATTERNS:
            m = pat.search(text)
            if m:
                add(dtype, line, f"{source}: form {m.group(0).strip()}")
        for pat, dtype in _PHRASE_PATTERNS:
            m = pat.search(text)
            if m:
                line = _infer_line(text, m.start(), m.end())
                add(dtype, line, f"{source}: \"{m.group(0).strip()}\"")

    return list(demands.values())


def extract_requirements_texts(attachments_result, max_chars=20000):
    """Best-effort local text extraction from the incoming attachments
    (text-layer PDFs via PyMuPDF, plus already-extracted Word/Excel text).
    No API calls. Never raises."""
    texts = []
    if not attachments_result:
        return texts
    for att in (attachments_result.get("attachments") or []):
        try:
            kind = att.get("kind")
            if kind in ("text", "excel"):
                t = att.get("extracted_text") or ""
                if t.strip():
                    texts.append(t[:max_chars])
            elif kind == "pdf" and att.get("contentBytes"):
                import fitz  # PyMuPDF — already a runtime dependency
                pdf_bytes = base64.b64decode(att["contentBytes"])
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                try:
                    t = "".join((page.get_text() or "") for page in doc)
                finally:
                    doc.close()
                if t.strip():
                    texts.append(t[:max_chars])
        except Exception:
            continue  # a bad attachment must never break the pipeline
    return texts


# ---------------------------------------------------------------------------
# Attach decision
# ---------------------------------------------------------------------------

def decide_attachments(client_id, demands, registry=None, endorsements_dir=None):
    """Given a client and detected demands, decide per endorsement entry:
    attach / scheduled-flag / missing-pdf / unavailable.

    Returns a plan dict:
      attach          [{"entry", "path"}]          blanket + PDF on disk
      scheduled_flags [{"type", "description"}]    NEVER attached — producer flag
      notes           [str]                        missing-PDF + unavailable notes
      demands         the input demands (for logging)
    """
    endorsements_dir = endorsements_dir or config.ENDORSEMENTS_DIR
    registry = registry or load_endorsement_registry()

    plan = {"attach": [], "scheduled_flags": [], "notes": [], "demands": demands}
    if not demands:
        return plan

    client = (registry.get("clients") or {}).get(client_id or "")
    if not client:
        plan["notes"].append(
            f"No endorsement inventory on file for client '{client_id}' — "
            f"nothing attached. Demanded: "
            + ", ".join(sorted({d['type'] for d in demands}))
        )
        return plan

    entries = client.get("endorsements") or []
    seen_paths = set()

    for demand in demands:
        matched = [
            e for e in entries
            if e.get("type") == demand["type"]
            and (demand["line"] is None or e.get("line") == demand["line"])
        ]
        if not matched:
            where = demand["line"] or "any line"
            plan["notes"].append(
                f"Demanded {demand['type']} ({where}) but no endorsement of "
                f"that type is on file for {client_id}. Evidence: {demand['evidence']}"
            )
            continue

        for entry in matched:
            status = entry.get("status")
            label = f"{entry.get('endorsement_id')} ({entry.get('type')}, {entry.get('line')})"

            if status == "scheduled":
                # HARD RULE: scheduled endorsements are never auto-attached.
                # A new certificate holder needs a new carrier change
                # endorsement first (e.g. Rolando's HVAC auto AI/WOS/P&NC).
                plan["scheduled_flags"].append({
                    "type": "scheduled_endorsement_carrier_request_needed",
                    "endorsement_id": entry.get("endorsement_id"),
                    "description": (
                        f"{label} is SCHEDULED (per-holder), not blanket — a "
                        f"carrier endorsement request is needed before this "
                        f"holder can be certified with it. Not attached. "
                        f"{entry.get('notes') or ''}"
                    ).strip(),
                })
            elif status == "blanket":
                pdf_name = entry.get("pdf_filename")
                path = (
                    os.path.join(endorsements_dir, client_id, pdf_name)
                    if pdf_name else None
                )
                if path and os.path.isfile(path):
                    if path not in seen_paths:
                        seen_paths.add(path)
                        plan["attach"].append({"entry": entry, "path": path})
                else:
                    plan["notes"].append(
                        f"{label} is blanket on file (form: "
                        f"{entry.get('form_number') or 'unspecified'}) but no "
                        f"PDF is in endorsements/{client_id}/ yet — not attached."
                    )
            else:  # "none", "unverified", anything unknown
                plan["notes"].append(
                    f"{label} demanded but status is '{status}' — not attached. "
                    f"{entry.get('form_title') or ''}"
                )

    return plan


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def plan_for_decision(parsed, attachments_result=None):
    """Called by pipeline.decide_action() when ENDORSEMENTS_ENABLED. Returns
    the extra decision keys, or None when there are no endorsement demands.
    Never raises — the COI flow must not depend on this feature."""
    try:
        requirements_texts = extract_requirements_texts(attachments_result)
        demands = detect_demanded_endorsements(parsed, requirements_texts)
        if not demands:
            return None
        plan = decide_attachments((parsed or {}).get("client_id"), demands)
        return {
            "endorsement_pdf_paths": [a["path"] for a in plan["attach"]],
            "endorsement_flags": plan["scheduled_flags"],
            "endorsement_notes": plan["notes"],
            "endorsement_demands": [
                {"type": d["type"], "line": d["line"]} for d in demands
            ],
        }
    except Exception:
        return None
