"""
mine_wording_discrepancies.py — evidence gathering for Alex.

Alex suspects some delivered COIs name a property-management company (and/or
its affiliates) as an Additional Insured in the Description of Operations
boilerplate, while the Certificate Holder box only lists the condo/HOA name
— i.e. the AI grant on the COI is broader (or just different) than what's
printed in the holder box, and nobody would notice without reading both
boxes side by side.

This script does NOT judge whether a hit is a real problem — it just finds
every COI in the training corpus where the DoO's Additional-Insured sentence
names a capitalized entity that doesn't also appear in the holder box, and
lays out the evidence (DoO sentence + holder box text + a rough severity
guess) so Alex can read them and decide.

Inputs:
  training/graded_cois.json  — corpus index (fields: path, holder_text, and
                                the PDFs themselves still live on disk)

For each record: re-extract the DoO text straight from the PDF (fitz), via
the same label-anchored region detection grade_cois.py uses (handles ACORD
101 continuation pages, non-standard layouts, etc.) rather than trusting the
possibly-stale desc_text already in the JSON — cross-checked against it.

Output: training/wording_discrepancy_report.md

Usage:
    .venv/bin/python training/mine_wording_discrepancies.py
"""

import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

fitz.TOOLS.mupdf_display_errors(False)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADED_PATH = os.path.join(BASE, "training", "graded_cois.json")
OUT_PATH = os.path.join(BASE, "training", "wording_discrepancy_report.md")

# Reuse grade_cois.py's label-anchored region detection instead of building a
# second, parallel DoO-locating heuristic.
_spec = importlib.util.spec_from_file_location(
    "grade_cois", os.path.join(BASE, "training", "grade_cois.py")
)
grade_cois = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grade_cois)


# ---------------------------------------------------------------------------
# Sentence splitting + AI-grant sentence detection
# ---------------------------------------------------------------------------

# Patterns that mark a sentence as an Additional-Insured grant sentence.
AI_GRANT_PATTERNS = [
    re.compile(r"\band its\b", re.I),
    re.compile(r"\bits affiliates\b", re.I),
    re.compile(r"\bits officers\b", re.I),
    re.compile(r"\bare\s+(?:named\s+as\s+|listed\s+as\s+|included\s+as\s+)?additional\s+insureds?\b", re.I),
    re.compile(r"\bis\s+(?:named\s+as\s+|listed\s+as\s+|included\s+as\s+)?additional\s+insureds?\b", re.I),
]

# Sentence splitter tuned for DoO boilerplate: split on '.' followed by
# whitespace+capital, but NOT on abbreviations we see constantly in this
# corpus (Inc., LLC., Ave., etc.) or on decimal-looking things.
_ABBREV = r"(?<!\bInc)(?<!\bLLC)(?<!\bCorp)(?<!\bCo)(?<!\bLtd)(?<!\bNo)(?<!\bAve)(?<!\bBlvd)(?<!\bSt)(?<!\bDr)"
_SENT_SPLIT_RE = re.compile(_ABBREV + r"\.(?=\s+[A-Z])")


def split_sentences(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = _SENT_SPLIT_RE.split(text)
    # Re-attach the period that was consumed by the split lookahead/lookbehind
    sentences = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        if not p.endswith("."):
            p += "."
        sentences.append(p)
    return sentences


# ---------------------------------------------------------------------------
# Capitalized entity-name extraction
# ---------------------------------------------------------------------------

# Words that are capitalized in boilerplate for reasons OTHER than being an
# entity name — skip these as candidate "named entity" tokens.
_STOPWORDS = {
    "Additional", "Insured", "Insureds", "Certificate", "Holder", "Holders",
    "General", "Liability", "Commercial", "Auto", "Umbrella", "Excess",
    "Workers", "Compensation", "Employers", "Waiver", "Subrogation",
    "Blanket", "Primary", "Non-contributory", "Noncontributory", "Named",
    "Description", "Operations", "Coverage", "Policy", "Policies", "Form",
    "Acord", "Warning", "Applies", "Basis", "Required", "Written", "Contract",
    "With", "Regards", "Regard", "To", "The", "A", "An", "In", "On", "For",
    "Of", "And", "Is", "Are", "As", "Its", "Their", "This", "That", "Per",
    "See", "Attached", "Descriptions", "Board", "Directors", "Officers",
    "Agents", "Employees", "Architects", "Engineers", "Members", "Managers",
    "Respective", "Successors", "Assigns", "Status", "Endorsement",
    "Automatic", "Provides", "Include", "Includes", "License", "Number",
    "Contractor", "Project", "Name", "Address", "Applicable", "If",
    "Con't", "Cont", "Continued", "Remarks", "Additional Remarks",
}

# Suffix words that unambiguously END an entity name wherever they appear
# (legal-form suffixes). Deliberately excludes words like "Management",
# "Group", "Properties", "Partners", "Holdings" — those are common mid-name
# words too (e.g. "Atrium Management Company"), so treating them as hard
# terminators causes false splits; they're left to the max-run-length /
# stopword cutoffs instead.
_ENTITY_SUFFIX_WORDS = {
    "LLC", "L.L.C.", "INC", "INC.", "INCORPORATED", "CORP", "CORP.",
    "CORPORATION", "CO", "CO.", "COMPANY", "LTD", "LTD.", "LP", "L.P.",
    "LLP", "PLLC", "ASSOCIATION", "HOA", "CONDOMINIUM", "CONDO", "TRUST", "LC",
}
_ENTITY_SUFFIX_RE = re.compile(
    r"\b(LLC|L\.L\.C\.|Inc\.?|Incorporated|Corp\.?|Corporation|Co\.?|Company|"
    r"Ltd\.?|LP|L\.P\.|LLP|PLLC|Association|HOA|Condominium|Condo|Realty|"
    r"Properties|Property Management|Management|Group|Partners|Holdings|"
    r"Trust|LC)\b",
    re.I,
)
# A token that ends a run outright: a code/license-number-looking token
# (mixes letters+digits, or is a bare number/hash), or obvious noise like
# "#CCC-1331111" fragments that leak in from license lines.
_CODE_TOKEN_RE = re.compile(r"^[A-Z]*\d+[A-Z0-9\-]*$|^#")
_CONNECTORS = {"of", "the", "and", "&"}


def extract_candidate_entities(sentence):
    """Pull out short runs of capitalized words that look like a single named
    entity. Word-by-word (not one big greedy regex) so that two adjacent but
    distinct entity mentions (e.g. 'Atrium Development Group' immediately
    followed by 'Atrium Management Company' with no separator in the source
    PDF text) don't get glued into one unmatchable blob: a run is cut short
    as soon as it hits a recognized entity suffix (the suffix ends the run),
    a code/license-number token, or a stopword that isn't a connector."""
    tokens = re.findall(r"[A-Za-z0-9&.,'#\-]+", sentence)
    candidates = []
    run = []

    def flush():
        if not run:
            return
        words = [w.strip(".,'") for w in run]
        # Trim leading/trailing boilerplate stopwords (e.g. "Project Ocala
        # Industrial" -> "Ocala Industrial") so a stray label word doesn't
        # taint an otherwise-real entity mention, and so a run that's ONLY
        # boilerplate on the edges but nothing but stopwords in the middle
        # gets caught by the all-stopwords check below.
        while words and (words[0] in _STOPWORDS or words[0].lower() in _CONNECTORS):
            words = words[1:]
        while words and (words[-1] in _STOPWORDS or words[-1].lower() in _CONNECTORS):
            words = words[:-1]
        if not words:
            return
        text = " ".join(words)
        if len(text) < 3:
            return
        if all(w in _STOPWORDS or w.lower() in _CONNECTORS for w in words):
            return
        has_suffix = bool(_ENTITY_SUFFIX_RE.search(text))
        multiword_titlecase = len([w for w in words if w and w[0].isupper()]) >= 2
        if has_suffix or multiword_titlecase:
            candidates.append(text)

    MAX_RUN_WORDS = 6
    for tok in tokens:
        bare = tok.strip(".,'#\-")
        is_cap = bool(re.match(r"[A-Z]", tok))
        is_connector = tok.lower() in _CONNECTORS
        is_code = bool(_CODE_TOKEN_RE.match(bare)) or tok.startswith("#")
        is_suffix = bare.upper().rstrip(".") in _ENTITY_SUFFIX_WORDS

        if is_code:
            flush()
            run = []
            continue
        if len(run) >= MAX_RUN_WORDS:
            flush()
            run = []
        if is_cap or (is_connector and run):
            run.append(tok)
            if is_suffix:
                # Suffix token ends the run (e.g. "...Group" shouldn't keep
                # absorbing the next capitalized word from an unrelated
                # adjacent sentence fragment).
                flush()
                run = []
            continue
        # Lowercase, non-connector word (or a stray uppercase STOPWORD that
        # signals we've drifted into boilerplate) -> break the run.
        if bare in _STOPWORDS:
            flush()
            run = []
            continue
        flush()
        run = []
    flush()

    # Dedupe, preserve order
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def norm_for_match(s):
    """Normalize for substring comparison against the holder box: lowercase,
    strip punctuation/whitespace differences."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def entity_in_holder(entity, holder_text):
    """True if this entity (or a close variant of it) appears in the holder
    box text. Compares normalized full strings AND normalized individual
    significant words, since holder box text is often wrapped/truncated —
    and, because entity extraction from unpunctuated PDF text sometimes
    glues two adjacent entity mentions together (e.g. 'Atrium Development
    Group Atrium Management' when the source has no separator), also
    accepts a strong majority-of-significant-words match rather than
    requiring the whole candidate as one contiguous substring."""
    en = norm_for_match(entity)
    hn = norm_for_match(holder_text)
    if not en:
        return True  # nothing to check
    if en in hn:
        return True
    # Also try matching just the first "core" word (e.g. "Presidential" from
    # "Presidential Place Condominium Association, Inc.") in case the holder
    # box has the same entity abbreviated/truncated.
    first_word = re.sub(r"[^a-z0-9]", "", entity.split()[0].lower()) if entity.split() else ""
    if len(first_word) >= 4 and first_word in hn:
        return True
    # Majority-of-significant-words match: guards against over-glued
    # multi-entity candidates where every individual entity IS present in
    # the holder box, just not as one contiguous run.
    sig_words = [
        re.sub(r"[^a-z0-9]", "", w.lower())
        for w in entity.split()
        if len(w) >= 4 and w.strip(".,'").upper() not in _ENTITY_SUFFIX_WORDS
    ]
    sig_words = [w for w in sig_words if w]
    if len(sig_words) >= 2:
        found = sum(1 for w in sig_words if w in hn)
        if found / len(sig_words) >= 0.8:
            return True
    return False


# ---------------------------------------------------------------------------
# Severity guess
# ---------------------------------------------------------------------------

_PM_HINTS = re.compile(
    r"\b(Property Management|Realty|Management (?:Company|Group|LLC|Inc)|"
    r"Management & |Management and )\b", re.I
)
_AFFILIATE_HINTS = re.compile(r"\bits affiliates\b|\band its\b", re.I)


def guess_severity(sentence, entity, holder_text):
    """Rough triage, not a verdict. Evidence-gathering only. Both hint
    checks are scoped to the flagged ENTITY text itself, not the whole
    sentence — a PM-sounding word elsewhere in the sentence (e.g. attached
    to a different, already-matched entity) shouldn't inflate severity for
    an unrelated leftover fragment like a project address."""
    reasons = []
    if _AFFILIATE_HINTS.search(entity):
        reasons.append("grants AI status to an open-ended 'affiliates' class")
    if _PM_HINTS.search(entity):
        reasons.append("names a property-management/realty company, not the holder entity")
    if not holder_text.strip():
        reasons.append("holder box is empty — nothing to cross-check against")
        return "HIGH", reasons
    if reasons:
        return "HIGH", reasons
    # Named a specific company/condo-like entity that's just absent from the box
    if _ENTITY_SUFFIX_RE.search(entity):
        reasons.append("named corporate entity not found anywhere in the holder box")
        return "MEDIUM", reasons
    reasons.append("capitalized multi-word phrase not found in the holder box (may be a false positive)")
    return "LOW", reasons


# ---------------------------------------------------------------------------
# Main mining pass
# ---------------------------------------------------------------------------

def get_doo_text(record):
    """Fresh fitz extraction from the PDF on disk, using grade_cois.py's
    label-anchored region detector. Falls back to the JSON's cached
    desc_text if the PDF can't be opened/re-extracted."""
    path = record.get("path")
    if path and os.path.exists(path):
        try:
            fields = grade_cois.extract_fields(path)
            fresh = fields.get("desc_text", "")
            if fresh:
                return fresh, "fitz (fresh)"
        except Exception as e:
            print(f"  [warn] fitz re-extract failed for {path}: {e}")
    return record.get("desc_text", ""), "cached desc_text"


def mine(records):
    hits = []
    for rec in records:
        doo_text, source = get_doo_text(rec)
        if not doo_text:
            continue
        holder_text = rec.get("holder_text", "") or ""

        for sentence in split_sentences(doo_text):
            if not any(p.search(sentence) for p in AI_GRANT_PATTERNS):
                continue
            entities = extract_candidate_entities(sentence)
            if not entities:
                continue
            missing_entities = [e for e in entities if not entity_in_holder(e, holder_text)]
            if not missing_entities:
                continue
            severity, reasons = "LOW", []
            picked_entity = None
            for e in missing_entities:
                sev, why = guess_severity(sentence, e, holder_text)
                if picked_entity is None or _sev_rank(sev) > _sev_rank(severity):
                    severity, reasons, picked_entity = sev, why, e
            hits.append({
                "path": rec.get("path"),
                "filename": rec.get("filename"),
                "client": rec.get("client"),
                "message_date": rec.get("message_date"),
                "doo_sentence": sentence,
                "missing_entities": missing_entities,
                "holder_text": holder_text,
                "severity": severity,
                "reasons": reasons,
                "doo_source": source,
            })
    return hits


def _sev_rank(sev):
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(sev, 0)


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(hits, out_path, total_records):
    hits_sorted = sorted(hits, key=lambda h: -_sev_rank(h["severity"]))
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for h in hits:
        counts[h["severity"]] += 1

    lines = []
    lines.append("# Wording Discrepancy Mining Report")
    lines.append("")
    lines.append(
        "Evidence-gathering only — no judgment calls made. Each hit below is a "
        "COI where the Description of Operations Additional-Insured sentence "
        "names a capitalized entity that does not appear in the Certificate "
        "Holder box (e.g. a property-management company, an 'and its "
        "affiliates' style open grant, or an entity the holder box doesn't "
        "list at all)."
    )
    lines.append("")
    lines.append(f"- Corpus scanned: **{total_records}** graded COIs (`training/graded_cois.json`)")
    lines.append(f"- Total discrepancy hits: **{len(hits)}**")
    lines.append(f"  - HIGH: {counts['HIGH']}   MEDIUM: {counts['MEDIUM']}   LOW: {counts['LOW']}")
    lines.append("")
    lines.append(
        "Severity is a rough triage signal, not a verdict:\n"
        "- **HIGH** — open-ended 'and its affiliates'/'its affiliates' grant, a "
        "named property-management/realty company, or an empty holder box "
        "with nothing to cross-check against.\n"
        "- **MEDIUM** — a specific named corporate entity (has an LLC/Inc/Corp/"
        "Association-type suffix) that isn't anywhere in the holder box.\n"
        "- **LOW** — a capitalized multi-word phrase flagged as a possible "
        "entity name but without a corporate suffix; more likely to be a "
        "false positive (worth a quick human glance, not a str8-to-top item)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, h in enumerate(hits_sorted, 1):
        lines.append(f"## {i}. [{h['severity']}] {h['filename']}")
        lines.append("")
        lines.append(f"- **Client:** {h.get('client') or '(unknown)'}")
        lines.append(f"- **Message date:** {h.get('message_date') or '(unknown)'}")
        lines.append(f"- **Path:** `{h['path']}`")
        lines.append(f"- **DoO extraction source:** {h['doo_source']}")
        lines.append(f"- **Entities named in DoO but absent from holder box:** "
                      f"{', '.join(h['missing_entities'])}")
        lines.append(f"- **Why flagged:** {'; '.join(h['reasons'])}")
        lines.append("")
        lines.append("**DoO sentence:**")
        lines.append("```")
        lines.append(h["doo_sentence"])
        lines.append("```")
        lines.append("")
        lines.append("**Holder box:**")
        lines.append("```")
        lines.append(h["holder_text"] or "(empty)")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(out_path, "w") as fh:
        fh.write("\n".join(lines))

    return counts


def main():
    with open(GRADED_PATH) as f:
        data = json.load(f)
    records = data["records"]
    print(f"Loaded {len(records)} graded COI records.")

    hits = mine(records)
    counts = write_report(hits, OUT_PATH, len(records))

    print(f"\nDiscrepancy hits: {len(hits)}")
    print(f"  HIGH: {counts['HIGH']}   MEDIUM: {counts['MEDIUM']}   LOW: {counts['LOW']}")
    print(f"Report written to: {OUT_PATH}")


if __name__ == "__main__":
    main()
