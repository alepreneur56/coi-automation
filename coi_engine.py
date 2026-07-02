"""
coi_engine.py
-------------
COI PDF Edit Engine for USI Insurance Services — Alejandro Bello
Takes a parsed JSON request and produces finished COI PDFs.

Usage:
    from coi_engine import process_request
    output_files = process_request(request_json, templates_dir, output_dir)
"""

import fitz  # PyMuPDF
import json
import os
import re
from datetime import date
from copy import deepcopy


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Certificate holder box (same across all ACORD 25 templates)
HOLDER_BOX_X0    = 19.0
HOLDER_BOX_X1    = 306.5
HOLDER_BOX_Y0    = 664.7
HOLDER_BOX_Y1    = 748.0
HOLDER_BOX_H     = HOLDER_BOX_Y1 - HOLDER_BOX_Y0
HOLDER_TEXT_X    = HOLDER_BOX_X0 + 8      # 27.0
HOLDER_SAFE_RIGHT = HOLDER_BOX_X1 - 2.0   # 304.5
HOLDER_MAX_WIDTH  = HOLDER_SAFE_RIGHT - HOLDER_TEXT_X  # 277.5 pts

# Description of operations safe boundaries
DESC_TEXT_X      = 21.5
DESC_SAFE_RIGHT  = 591.0
DESC_MAX_WIDTH   = DESC_SAFE_RIGHT - DESC_TEXT_X  # 569.5 pts

# Date field
DATE_X = 522.0
DATE_Y = 44.0

# Font
FONT_NAME = "hebo"  # Helvetica-Bold — base14, always clean
FONT_SIZES = [9, 8, 7.5, 7, 6.5, 6, 5.5, 5]


# ---------------------------------------------------------------------------
# TEXT UTILITIES
# ---------------------------------------------------------------------------

# Unicode punctuation -> Latin-1-safe equivalents. Helvetica-Bold (base14)
# only covers Latin-1; smart quotes / em dashes from email clients (or the
# AI parser) would otherwise render as garbage glyphs on the COI.
_UNICODE_REPLACEMENTS = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "―": "-", "−": "-",
    "…": "...",
    " ": " ", " ": " ", " ": " ",
    "•": "-",
}


def sanitize_text(text):
    """Make text safe for base-14 Helvetica insertion: normalize smart
    punctuation, keep Latin-1 (accented) letters, strip anything else."""
    if not text:
        return text
    for bad, good in _UNICODE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    # Transliterate remaining non-Latin-1 chars where possible, drop the rest
    out = []
    for chr_ in text:
        if ord(chr_) <= 0xFF:
            out.append(chr_)
        else:
            import unicodedata
            decomposed = unicodedata.normalize("NFKD", chr_)
            kept = "".join(c for c in decomposed if ord(c) <= 0xFF)
            out.append(kept)
    return "".join(out)


def _hard_split_word(word, fontsize, max_width, fontname=FONT_NAME):
    """Split a single overlong word into chunks that each fit max_width."""
    chunks = []
    current = ""
    for chr_ in word:
        if fitz.get_text_length(current + chr_, fontname=fontname, fontsize=fontsize) <= max_width:
            current += chr_
        else:
            if current:
                chunks.append(current)
            current = chr_
    if current:
        chunks.append(current)
    return chunks or [word]


def wrap_text(text, fontsize, max_width, fontname=FONT_NAME):
    """Word-wrap text to fit within max_width at given font size. Words too
    long for a whole line are hard-split so nothing can cross a box border."""
    words = []
    for word in text.split(' '):
        if word and fitz.get_text_length(word, fontname=fontname, fontsize=fontsize) > max_width:
            words.extend(_hard_split_word(word, fontsize, max_width, fontname))
        else:
            words.append(word)
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if fitz.get_text_length(test, fontname=fontname, fontsize=fontsize) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def find_optimal_font(entity_lines, address_lines, max_width=HOLDER_MAX_WIDTH, box_h=HOLDER_BOX_H):
    """
    Find the largest font size where all entity lines (wrapped) + address lines
    (also wrapped) fit within the certificate holder box height.
    Returns (font_size, line_height, all_display_lines).
    """
    def _wrapped_all(fs):
        wrapped = []
        for e in entity_lines:
            wrapped.extend(wrap_text(e, fs, max_width))
        for a in address_lines:
            wrapped.extend(wrap_text(a, fs, max_width))
        return wrapped

    for fs in FONT_SIZES:
        lh = fs * 1.35
        all_lines = _wrapped_all(fs)
        if len(all_lines) * lh <= box_h:
            return fs, lh, all_lines
    # Fallback — minimum font, may be tight
    fs = FONT_SIZES[-1]
    lh = fs * 1.35
    return fs, lh, _wrapped_all(fs)


def split_into_cois(entity_lines, address_lines, max_width=HOLDER_MAX_WIDTH, box_h=HOLDER_BOX_H):
    """
    Find the largest font that keeps COI count to minimum (prefer ≤ 2).
    Returns list of (font_size, line_height, lines_for_this_coi) tuples.
    """
    best = None
    for fs in FONT_SIZES:
        lh = fs * 1.35
        wrapped = []
        for e in entity_lines:
            wrapped.extend(wrap_text(e, fs, max_width))
        wrapped_addr = []
        for a in address_lines:
            wrapped_addr.extend(wrap_text(a, fs, max_width))
        max_entity_lines = int(box_h / lh) - len(wrapped_addr)
        if max_entity_lines < 1:
            continue
        num_cois = -(-len(wrapped) // max_entity_lines)  # ceiling division
        best = (fs, lh, wrapped, wrapped_addr, max_entity_lines, num_cois)
        if num_cois <= 2:
            break

    if best is None:
        raise ValueError("Cannot fit entities even at minimum font size.")

    fs, lh, all_wrapped, wrapped_addr, max_entity_lines, num_cois = best
    chunks = []
    for i in range(0, len(all_wrapped), max_entity_lines):
        chunk_lines = all_wrapped[i:i + max_entity_lines] + wrapped_addr
        chunks.append((fs, lh, chunk_lines))
    return chunks


def clean_filename(text):
    """Convert text to a safe filename component (capped length)."""
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text or "")
    words = text.strip().split()[:3]
    return ''.join(w.capitalize() for w in words)[:40] or "Client"


# ---------------------------------------------------------------------------
# PDF SPAN FINDERS
# ---------------------------------------------------------------------------

def find_project_span(page):
    """Find the 'Project name & Address ( If Applicable)' span."""
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    if "Project name & Address" in span["text"]:
                        return span
    return None


def find_boilerplate_lines(page, proj_span):
    """Find the boilerplate LINES below the project placeholder (and above
    the bottom of the description box). Returns (lines, dropped_lines) where
    each entry is a dict carrying its spans in reading order.

    Line-level (not span-level) handling matters: several templates store
    'Certificate Holder' as its own span (left cyan by the template builder),
    with the rest of the sentence in sibling spans on the same line. Any
    redact-and-reinsert that operates on single spans loses the siblings.

    Two template quirks this handles:
      - Span bboxes carry big ascender/descender padding, so adjacent lines
        overlap vertically. Inclusion is decided by BASELINE (y0 + size),
        never raw bbox y0 (305 Power's first boilerplate line overlaps the
        project placeholder's bbox).
      - Some templates contain hidden orphan spans painted over with white
        during template building (invisible in render, present in the text
        layer). Visible paragraph lines sit on a regular line-spacing grid;
        off-grid lines are dropped so hidden junk is never re-inserted.
    """
    proj_baseline = proj_span["bbox"][1] + proj_span["size"]
    lines = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            y0 = min(s["bbox"][1] for s in spans)
            size = max(s["size"] for s in spans)
            baseline = y0 + size
            if not (baseline > proj_baseline + 1.0 and y0 < 652):
                continue
            spans.sort(key=lambda s: s["bbox"][0])
            lines.append({
                "spans": spans,
                "x0": min(s["bbox"][0] for s in spans),
                "y0": y0,
                "y1": max(s["bbox"][3] for s in spans),
                "size": size,
                "text": "".join(s["text"] for s in spans),
            })
    lines.sort(key=lambda l: l["y0"])

    # Grid filter: drop off-grid (hidden orphan) lines. Anchor on the LAST
    # line — the bottom of the paragraph never overlaps anything.
    dropped = []
    if len(lines) >= 3:
        deltas = [
            b["y0"] - a["y0"] for a, b in zip(lines, lines[1:])
            if b["y0"] - a["y0"] > 3.0
        ]
        if deltas:
            deltas.sort()
            spacing = deltas[len(deltas) // 2]
            anchor = lines[-1]["y0"]
            kept = []
            for l in lines:
                k = round((anchor - l["y0"]) / spacing)
                if abs((anchor - l["y0"]) - k * spacing) <= 1.5:
                    kept.append(l)
                else:
                    dropped.append(l)
            lines = kept
    return lines, dropped


# ---------------------------------------------------------------------------
# CORE COI BUILDER
# ---------------------------------------------------------------------------

def build_single_coi(
    template_path,
    output_path,
    holder_lines,
    font_size,
    line_height,
    project_text=None,       # None = delete placeholder, str = insert this text
    multiple_holders=False,  # True = edit boilerplate to say "Certificate Holders"
    today_str=None,
):
    """
    Build one COI PDF from a template.

    Args:
        template_path:     Path to the source template PDF
        output_path:       Where to save the finished PDF
        holder_lines:      List of strings to insert in the cert holder box
        font_size:         Font size to use for holder lines
        line_height:       Line height (font_size * 1.35)
        project_text:      Text for desc of operations project line (None to delete)
        multiple_holders:  If True, change "Certificate Holder" to "Certificate Holders"
        today_str:         Date string MM/DD/YYYY (defaults to today)
    """
    if today_str is None:
        today_str = date.today().strftime("%m/%d/%Y")

    # Open and scrub the template in memory to fix any broken xref objects
    _raw = fitz.open(template_path)
    doc = fitz.open("pdf", _raw.tobytes(garbage=3, deflate=True))
    _raw.close()
    page = doc[0]

    # --- Locate key spans ---
    proj_span = find_project_span(page)
    if proj_span is None:
        raise ValueError(f"Could not find 'Project name & Address' in {template_path}")

    px0, py0, px1, py1 = proj_span["bbox"]
    desc_font_size = proj_span["size"]
    desc_lh = desc_font_size * 1.35

    # Build project lines (wrapped if needed)
    project_lines = []
    push_down = 0

    if project_text:
        project_lines = wrap_text(project_text, desc_font_size, DESC_MAX_WIDTH)
        extra_lines = max(0, len(project_lines) - 1)
        push_down = extra_lines * desc_lh

    # The boilerplate below the project line gets rebuilt (redact + re-insert)
    # in ONE unified pass when any of these apply:
    #   - project text wraps -> everything below shifts down (push_down)
    #   - multiple holders  -> 'Certificate Holder' becomes plural
    #   - template has non-black boilerplate text (cyan spans left over from
    #     template building) -> normalize to black
    # One pass avoids the old double redact/re-insert collision when a
    # multi-holder request also had wrapping project text.
    boilerplate_lines, dropped_lines = find_boilerplate_lines(page, proj_span)
    if dropped_lines:
        print(f"  [engine] dropped {len(dropped_lines)} hidden off-grid line(s): "
              f"{[l['text'][:40] for l in dropped_lines]}")
    has_nonblack = any(
        s.get("color", 0) != 0 for l in boilerplate_lines for s in l["spans"]
    )
    rebuild_boilerplate = bool(boilerplate_lines) and (
        push_down > 0 or multiple_holders or has_nonblack
    )

    # Overflow guard: pushing the boilerplate down must never spill past the
    # bottom of the description box (the CERTIFICATE HOLDER / CANCELLATION
    # headers start at y≈653.8). If the shifted block would overflow, regrid
    # the project + boilerplate lines with tighter spacing so the last
    # baseline stays inside the box.
    # Last allowed baseline: the DoO bottom border band starts at y≈651.4;
    # 9pt descenders reach ~2pt below baseline, so 649.0 keeps clear of it.
    DESC_LAST_BASELINE = 649.0
    regrid_lh = None  # None = keep template spacing
    if rebuild_boilerplate and push_down > 0 and boilerplate_lines:
        first_baseline = py0 + desc_font_size
        n_total = len(project_lines) + len(boilerplate_lines)
        last_baseline = (
            boilerplate_lines[-1]["y0"] + boilerplate_lines[-1]["size"] + push_down
        )
        if last_baseline > DESC_LAST_BASELINE and n_total > 1:
            regrid_lh = (DESC_LAST_BASELINE - first_baseline) / (n_total - 1)
            regrid_lh = max(regrid_lh, desc_font_size * 1.03)
            print(f"  [engine] compressed DoO line spacing to {regrid_lh:.2f}pt "
                  f"to keep {n_total} lines inside the box")

    # --- REDACTIONS ---
    # 1. Certificate holder box
    page.add_redact_annot(
        fitz.Rect(HOLDER_BOX_X0, HOLDER_BOX_Y0, HOLDER_BOX_X1, HOLDER_BOX_Y1),
        fill=(1, 1, 1)
    )
    # 2. Date field — tight to value area only; preserves label and box borders
    #    Box borders: top y≈23.5-24.6, bottom y≈47.6-48.7, sides x≈509-510.1 / 592.8-593.9
    #    Label "DATE (MM/DD/YYYY)" lives at y≈24.9-33.16 — leave it alone
    page.add_redact_annot(
        fitz.Rect(510.5, 34.0, 592.5, 47.0),
        fill=(1, 1, 1)
    )
    # 3. Project name placeholder — tight bounds, never touch borders OR neighboring spans.
    #    Some templates (e.g. 305 Power Corp) have spans whose bboxes overlap vertically
    #    due to ascender/descender padding. We must clamp the redaction y-range so it
    #    never extends into the span directly above or below.
    above_y1 = None  # bottom edge of the nearest span above project
    below_y0 = None  # top edge of the nearest span below project
    for _b in page.get_text("dict")["blocks"]:
        if _b.get("type") != 0:
            continue
        for _line in _b["lines"]:
            for _sp in _line["spans"]:
                _sy0, _sy1 = _sp["bbox"][1], _sp["bbox"][3]
                # Skip the project span itself
                if abs(_sy0 - py0) < 0.1 and abs(_sy1 - py1) < 0.1:
                    continue
                # Span sits above the project (its bottom is above project's top)
                if _sy1 <= py0 + 0.5 and _sy1 > 540:
                    if above_y1 is None or _sy1 > above_y1:
                        above_y1 = _sy1
                # Span sits below the project (its top is below project's bottom)
                # We accept any span whose top is greater than project's top — even if its
                # bbox overlaps ours due to padding — and clamp to its top y0.
                if _sy0 > py0 + 0.5 and _sy0 < 660:
                    if below_y0 is None or _sy0 < below_y0:
                        below_y0 = _sy0

    redact_top = py0 - 0.3
    if above_y1 is not None and redact_top < above_y1 + 0.3:
        redact_top = above_y1 + 0.3

    redact_bottom = py1 + 0.3
    if below_y0 is not None and redact_bottom > below_y0 - 0.3:
        redact_bottom = below_y0 - 0.3

    page.add_redact_annot(
        fitz.Rect(px0 - 0.5, redact_top, DESC_SAFE_RIGHT, redact_bottom),
        fill=(1, 1, 1)
    )
    # 4. Boilerplate area (unified rebuild: push-down / plural / color fix)
    if rebuild_boilerplate:
        bp_y0 = min(l["y0"] for l in boilerplate_lines) - 0.3
        bp_y1 = max(l["y1"] for l in boilerplate_lines) + 0.3
        page.add_redact_annot(
            fitz.Rect(DESC_TEXT_X - 0.5, bp_y0, DESC_SAFE_RIGHT, bp_y1),
            fill=(1, 1, 1)
        )

    page.apply_redactions()

    # --- INSERTIONS ---

    # Certificate holder lines
    padding_top = 6
    for i, line in enumerate(holder_lines):
        y = HOLDER_BOX_Y0 + padding_top + (i * line_height) + font_size
        page.insert_text(
            (HOLDER_TEXT_X, y),
            line,
            fontsize=font_size,
            fontname=FONT_NAME,
            color=(0, 0, 0)
        )

    # Project lines
    proj_lh = regrid_lh if regrid_lh else desc_lh
    for i, line in enumerate(project_lines):
        y = py0 + desc_font_size + (i * proj_lh)
        page.insert_text(
            (DESC_TEXT_X, y),
            line,
            fontsize=desc_font_size,
            fontname=FONT_NAME,
            color=(0, 0, 0)
        )

    # Re-insert the rebuilt boilerplate: shifted down if the project text
    # wrapped, pluralized on the 'Certificate Holder' line for multi-holder
    # COIs, and always in black (normalizes stray cyan template spans).
    if rebuild_boilerplate:
        for j, bline in enumerate(boilerplate_lines):
            if regrid_lh:
                # Compressed grid: baseline follows the project lines
                baseline = (
                    py0 + desc_font_size
                    + (len(project_lines) + j) * regrid_lh
                )
            else:
                baseline = bline["y0"] + bline["size"] + push_down

            pluralize = (
                multiple_holders
                and "Certificate Holder" in bline["text"]
                and "Certificate Holders" not in bline["text"]
            )
            if pluralize:
                # Whole-line re-insert: the plural adds width, so sibling
                # spans can't stay at their original x positions.
                new_text = bline["text"].replace(
                    "Certificate Holder", "Certificate Holders"
                )
                page.insert_text(
                    (bline["x0"], baseline),
                    new_text,
                    fontsize=bline["size"],
                    fontname=FONT_NAME,
                    color=(0, 0, 0)
                )
            else:
                # Span-by-span at original x positions — best fidelity.
                for span in bline["spans"]:
                    page.insert_text(
                        (span["bbox"][0], baseline),
                        span["text"],
                        fontsize=span["size"],
                        fontname=FONT_NAME,
                        color=(0, 0, 0)
                    )

    # Date
    page.insert_text(
        (DATE_X, DATE_Y),
        today_str,
        fontsize=9,
        fontname=FONT_NAME,
        color=(0, 0, 0)
    )

    doc.save(output_path, garbage=3, deflate=True)
    doc.close()


# ---------------------------------------------------------------------------
# PROJECT TEXT BUILDER
# ---------------------------------------------------------------------------

def build_project_text(project_name=None, project_address=None, project_unit=None, is_permit=False):
    """
    Format the project line for Description of Operations.
    Returns None if nothing to insert (placeholder will be deleted).

    Handles unit/suite/apartment numbers when the unit is the JOB SITE
    (cert holder office unit numbers go in cert_holder.address_line_2,
    not here).
    """
    # Normalize empty strings to None; sanitize for base-14 font safety
    def _norm(v):
        if isinstance(v, str) and v.strip():
            return sanitize_text(v.strip())
        return None
    project_name = _norm(project_name)
    project_address = _norm(project_address)
    project_unit = _norm(project_unit)

    if is_permit and project_address:
        return f"Permit - {project_address}"

    # Build the address-side fragment, optionally prefixed with the unit
    if project_unit and project_address:
        addr_frag = f"Unit {project_unit} at {project_address}"
    elif project_unit:
        addr_frag = f"Unit {project_unit}"
    elif project_address:
        addr_frag = project_address
    else:
        addr_frag = None

    # Combine with project name based on what's present
    if project_name and addr_frag:
        return f"Project Name & Address: {project_name} - {addr_frag}"
    if project_name:
        return f"Project Name: {project_name}"
    if project_unit:
        # Unit (with or without address) but no project name → "Project: Unit X..."
        return f"Project: {addr_frag}"
    if project_address:
        return f"Project Address: {project_address}"
    return None


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def process_request(request_json, templates_dir, output_dir):
    """
    Process a COI request JSON and produce finished PDFs.

    Args:
        request_json:   Dict from the AI parser (Phase 3 output)
        templates_dir:  Directory containing template PDFs
        output_dir:     Directory to save finished PDFs

    Returns:
        List of output file paths produced
    """
    os.makedirs(output_dir, exist_ok=True)
    today_str = date.today().strftime("%m/%d/%Y")
    today_file = date.today().strftime("%m%d%Y")

    req = request_json
    template_filename = req["template_filename"]
    template_path = os.path.join(templates_dir, template_filename)
    client_short = clean_filename(req.get("client_canonical_name", "Client"))

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    output_files = []

    # --- BATCH REQUEST (multiple individual COIs) ---
    if req.get("request_type") == "batch":
        batch_items = req.get("batch_cois", [])
        for item in batch_items:
            ch = item["certificate_holder"]
            holder_name = sanitize_text(ch["name"])
            addr1 = sanitize_text(ch.get("address_line_1", ""))
            addr2 = sanitize_text(ch.get("address_line_2"))
            city_state_zip = ", ".join(filter(None, [ch.get("city"), ch.get("state"), ch.get("zip")]))
            city_state_zip = sanitize_text(city_state_zip)

            address_lines = [l for l in [addr1, addr2, city_state_zip] if l]
            entity_lines = [holder_name]

            fs, lh, all_lines = find_optimal_font(entity_lines, address_lines)

            project_text = build_project_text(
                project_name=item.get("project_name"),
                project_address=item.get("project_address"),
                project_unit=item.get("project_unit"),
                is_permit=item.get("is_permit", False)
            )

            holder_short = clean_filename(holder_name)
            filename = item.get("output_filename") or f"{client_short}_{holder_short}_{today_file}.pdf"
            out_path = os.path.join(output_dir, filename)

            build_single_coi(
                template_path=template_path,
                output_path=out_path,
                holder_lines=all_lines,
                font_size=fs,
                line_height=lh,
                project_text=project_text,
                multiple_holders=False,  # individual COIs = singular
                today_str=today_str,
            )
            output_files.append(out_path)
            print(f"  [batch] Produced: {filename}")

        return output_files

    # --- SINGLE OR MULTI-ENTITY REQUEST ---
    ch = req.get("certificate_holder", {})
    holder_name = sanitize_text(ch.get("name", ""))
    addr1 = sanitize_text(ch.get("address_line_1", ""))
    addr2 = sanitize_text(ch.get("address_line_2"))
    city_state_zip = ", ".join(filter(None, [ch.get("city"), ch.get("state"), ch.get("zip")]))
    city_state_zip = sanitize_text(city_state_zip)
    address_lines = [l for l in [addr1, addr2, city_state_zip] if l]

    # Use certificate_holder_lines if present (multi-entity), else just the name
    all_entities = req.get("certificate_holder_lines")
    if all_entities:
        all_entities = [sanitize_text(l) for l in all_entities if l]
        # Strip address lines from entity list (they're added back per-COI)
        entity_lines = [l for l in all_entities if l not in address_lines]
    else:
        entity_lines = [holder_name] if holder_name else []

    multiple_holders = len(entity_lines) > 1

    project_text = build_project_text(
        project_name=req.get("project_name"),
        project_address=req.get("project_address"),
        project_unit=req.get("project_unit"),
        is_permit=req.get("is_permit", False)
    )

    holder_short = clean_filename(holder_name)

    # Determine if splitting is needed
    # First try to fit in one COI
    fs, lh, single_coi_lines = find_optimal_font(entity_lines, address_lines)
    total_height = len(single_coi_lines) * lh

    if total_height <= HOLDER_BOX_H:
        # Fits in one COI
        filename = f"{client_short}_{holder_short}_{today_file}.pdf"
        out_path = os.path.join(output_dir, filename)
        build_single_coi(
            template_path=template_path,
            output_path=out_path,
            holder_lines=single_coi_lines,
            font_size=fs,
            line_height=lh,
            project_text=project_text,
            multiple_holders=multiple_holders,
            today_str=today_str,
        )
        output_files.append(out_path)
        print(f"  [single] Produced: {filename}  ({len(single_coi_lines)} lines @ {fs}pt)")

    else:
        # Needs splitting
        chunks = split_into_cois(entity_lines, address_lines)
        total_splits = len(chunks)
        for idx, (chunk_fs, chunk_lh, chunk_lines) in enumerate(chunks):
            split_num = idx + 1
            filename = f"{client_short}_{holder_short}_{split_num}of{total_splits}_{today_file}.pdf"
            out_path = os.path.join(output_dir, filename)
            build_single_coi(
                template_path=template_path,
                output_path=out_path,
                holder_lines=chunk_lines,
                font_size=chunk_fs,
                line_height=chunk_lh,
                project_text=project_text,
                multiple_holders=multiple_holders,
                today_str=today_str,
            )
            output_files.append(out_path)
            print(f"  [split {split_num}/{total_splits}] Produced: {filename}  ({len(chunk_lines)} lines @ {chunk_fs}pt)")

    return output_files


# ---------------------------------------------------------------------------
# QUICK TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    templates_dir = "/mnt/user-data/uploads"
    output_dir = "/home/claude/coi_output"

    # Test 1 — simple single holder
    test1 = {
        "status": "ready",
        "client_canonical_name": "Rolando's HVAC LLC",
        "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
        "certificate_holder": {
            "name": "Miami Dade County",
            "address_line_1": "111 NW 1st St",
            "address_line_2": None,
            "city": "Miami",
            "state": "FL",
            "zip": "33128"
        },
        "project_name": None,
        "project_address": None,
    }

    # Test 2 — multi-entity (6 holders, shared address)
    test2 = {
        "status": "ready",
        "client_canonical_name": "Rolando's HVAC LLC",
        "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
        "certificate_holder": {
            "name": "Brickell Tower Condominium Association",
            "address_line_1": "1234 SW 55th Street",
            "address_line_2": None,
            "city": "Miami",
            "state": "FL",
            "zip": "33175"
        },
        "certificate_holder_lines": [
            "Brickell Tower Condominium Association",
            "Coconut Grove Residences HOA",
            "Coral Gables Villas LLC",
            "Downtown Miami Lofts Association",
            "Edgewater Bay Condominium Inc",
            "Flagler Street Partners LLC",
            "1234 SW 55th Street",
            "Miami, FL 33175",
        ],
        "project_name": None,
        "project_address": None,
    }

    # Test 3 — batch request
    test3 = {
        "status": "ready",
        "request_type": "batch",
        "client_canonical_name": "Rolando's HVAC LLC",
        "template_filename": "Rolando_s_HVAC_COI_Template.pdf",
        "batch_cois": [
            {
                "index": 1,
                "certificate_holder": {
                    "name": "Miami Dade County",
                    "address_line_1": "111 NW 1st St",
                    "address_line_2": None,
                    "city": "Miami", "state": "FL", "zip": "33128"
                },
                "project_name": None, "project_address": None,
            },
            {
                "index": 2,
                "certificate_holder": {
                    "name": "Bengoa Construction Inc",
                    "address_line_1": "2200 N Dixie Hwy",
                    "address_line_2": None,
                    "city": "Hollywood", "state": "FL", "zip": "33020"
                },
                "project_name": None, "project_address": None,
            },
            {
                "index": 3,
                "certificate_holder": {
                    "name": "City of Coral Gables",
                    "address_line_1": "405 Brickell Ave",
                    "address_line_2": None,
                    "city": "Miami", "state": "FL", "zip": "33131"
                },
                "project_name": None, "project_address": None,
            },
        ]
    }

    print("=" * 60)
    print("TEST 1 — Simple single holder")
    print("=" * 60)
    files = process_request(test1, templates_dir, output_dir)
    print(f"Output: {files}\n")

    print("=" * 60)
    print("TEST 2 — Multi-entity (6 holders, shared address)")
    print("=" * 60)
    files = process_request(test2, templates_dir, output_dir)
    print(f"Output: {files}\n")

    print("=" * 60)
    print("TEST 3 — Batch (3 individual COIs)")
    print("=" * 60)
    files = process_request(test3, templates_dir, output_dir)
    print(f"Output: {files}\n")
