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

def wrap_text(text, fontsize, max_width, fontname=FONT_NAME):
    """Word-wrap text to fit within max_width at given font size."""
    words = text.split(' ')
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
    fit within the certificate holder box height.
    Returns (font_size, line_height, all_display_lines).
    """
    for fs in FONT_SIZES:
        lh = fs * 1.35
        wrapped = []
        for e in entity_lines:
            wrapped.extend(wrap_text(e, fs, max_width))
        all_lines = wrapped + address_lines
        if len(all_lines) * lh <= box_h:
            return fs, lh, all_lines
    # Fallback — minimum font, may be tight
    fs = FONT_SIZES[-1]
    lh = fs * 1.35
    wrapped = []
    for e in entity_lines:
        wrapped.extend(wrap_text(e, fs, max_width))
    return fs, lh, wrapped + address_lines


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
        max_entity_lines = int(box_h / lh) - len(address_lines)
        if max_entity_lines < 1:
            continue
        num_cois = -(-len(wrapped) // max_entity_lines)  # ceiling division
        best = (fs, lh, wrapped, max_entity_lines, num_cois)
        if num_cois <= 2:
            break

    if best is None:
        raise ValueError("Cannot fit entities even at minimum font size.")

    fs, lh, all_wrapped, max_entity_lines, num_cois = best
    chunks = []
    for i in range(0, len(all_wrapped), max_entity_lines):
        chunk_lines = all_wrapped[i:i + max_entity_lines] + address_lines
        chunks.append((fs, lh, chunk_lines))
    return chunks


def clean_filename(text):
    """Convert text to a safe filename component."""
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    words = text.strip().split()[:3]
    return ''.join(w.capitalize() for w in words)


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


def find_cert_holder_spans_in_boilerplate(page):
    """Find all spans in description of operations that contain 'Certificate Holder'."""
    matches = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    if "Certificate Holder" in span["text"] and 595 < span["bbox"][1] < 645:
                        matches.append(span)
    return matches


def find_boilerplate_spans(page, below_y):
    """Find all boilerplate spans below a given y coordinate."""
    spans = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    if span["bbox"][1] > below_y + 0.5 and span["bbox"][1] < 652:
                        spans.append(span)
    return spans


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

    doc = fitz.open(template_path)
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
    boilerplate_spans = []

    if project_text:
        project_lines = wrap_text(project_text, desc_font_size, DESC_MAX_WIDTH)
        extra_lines = max(0, len(project_lines) - 1)
        push_down = extra_lines * desc_lh
        if push_down > 0:
            boilerplate_spans = find_boilerplate_spans(page, py1)

    # Cert holder boilerplate spans (for plural edit)
    ch_boilerplate_spans = []
    if multiple_holders:
        ch_boilerplate_spans = find_cert_holder_spans_in_boilerplate(page)

    # --- REDACTIONS ---
    # 1. Certificate holder box
    page.add_redact_annot(
        fitz.Rect(HOLDER_BOX_X0, HOLDER_BOX_Y0, HOLDER_BOX_X1, HOLDER_BOX_Y1),
        fill=(1, 1, 1)
    )
    # 2. Date field
    page.add_redact_annot(
        fitz.Rect(510, 28, 592, 48),
        fill=(1, 1, 1)
    )
    # 3. Project name placeholder — tight bounds, never touch borders
    page.add_redact_annot(
        fitz.Rect(px0 - 0.5, py0 - 0.3, DESC_SAFE_RIGHT, py1 + 0.3),
        fill=(1, 1, 1)
    )
    # 4. Boilerplate area (only if project text overflows)
    if push_down > 0:
        bp_y0 = min(s["bbox"][1] for s in boilerplate_spans) - 0.3
        bp_y1 = max(s["bbox"][3] for s in boilerplate_spans) + 0.3
        page.add_redact_annot(
            fitz.Rect(DESC_TEXT_X - 0.5, bp_y0, DESC_SAFE_RIGHT, bp_y1),
            fill=(1, 1, 1)
        )
    # 5. Certificate Holder → Certificate Holders boilerplate spans
    for span in ch_boilerplate_spans:
        cx0, cy0, cx1, cy1 = span["bbox"]
        page.add_redact_annot(
            fitz.Rect(cx0 - 0.5, cy0 - 0.3, DESC_SAFE_RIGHT, cy1 + 0.3),
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
    for i, line in enumerate(project_lines):
        y = py0 + desc_font_size + (i * desc_lh)
        page.insert_text(
            (DESC_TEXT_X, y),
            line,
            fontsize=desc_font_size,
            fontname=FONT_NAME,
            color=(0, 0, 0)
        )

    # Re-insert boilerplate pushed down by overflow
    if push_down > 0:
        for span in boilerplate_spans:
            sy = span["bbox"][1] + push_down + desc_font_size
            page.insert_text(
                (span["bbox"][0], sy),
                span["text"],
                fontsize=span["size"],
                fontname=FONT_NAME,
                color=(0, 0, 0)
            )

    # Re-insert Certificate Holders (plural) boilerplate
    for span in ch_boilerplate_spans:
        cx0, cy0 = span["bbox"][0], span["bbox"][1]
        new_text = span["text"].replace("Certificate Holder", "Certificate Holders")
        page.insert_text(
            (cx0, cy0 + span["size"]),
            new_text,
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

    doc.save(output_path)
    doc.close()


# ---------------------------------------------------------------------------
# PROJECT TEXT BUILDER
# ---------------------------------------------------------------------------

def build_project_text(project_name=None, project_address=None, is_permit=False):
    """
    Format the project line for Description of Operations.
    Returns None if nothing to insert (placeholder will be deleted).
    """
    if is_permit and project_address:
        return f"Permit - {project_address}"
    if project_name and project_address:
        return f"Project Name & Address: {project_name} - {project_address}"
    if project_name:
        return f"Project Name: {project_name}"
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
            holder_name = ch["name"]
            addr1 = ch.get("address_line_1", "")
            addr2 = ch.get("address_line_2")
            city_state_zip = ", ".join(filter(None, [ch.get("city"), ch.get("state"), ch.get("zip")]))

            address_lines = [l for l in [addr1, addr2, city_state_zip] if l]
            entity_lines = [holder_name]

            fs, lh, all_lines = find_optimal_font(entity_lines, address_lines)

            project_text = build_project_text(
                project_name=item.get("project_name"),
                project_address=item.get("project_address"),
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
    holder_name = ch.get("name", "")
    addr1 = ch.get("address_line_1", "")
    addr2 = ch.get("address_line_2")
    city_state_zip = ", ".join(filter(None, [ch.get("city"), ch.get("state"), ch.get("zip")]))
    address_lines = [l for l in [addr1, addr2, city_state_zip] if l]

    # Use certificate_holder_lines if present (multi-entity), else just the name
    all_entities = req.get("certificate_holder_lines")
    if all_entities:
        # Strip address lines from entity list (they're added back per-COI)
        entity_lines = [l for l in all_entities if l not in address_lines]
    else:
        entity_lines = [holder_name] if holder_name else []

    multiple_holders = len(entity_lines) > 1

    project_text = build_project_text(
        project_name=req.get("project_name"),
        project_address=req.get("project_address"),
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
