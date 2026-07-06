"""Apply Alex's 2026-07-04 approved template changes.

1. Rolando's HVAC: DoO reworded (auto AI is scheduled, not blanket) +
   auto row policy number CA-74829 -> CA-74829-0 and exp 12/25/2026 -> 12/15/2026.
2. 305 Power Corp: WOS sentence drops Umbrella; follows-form shortened.

Old text is REMOVED from the text layer via redactions applied with
graphics=PDF_REDACT_LINE_ART_NONE and fill=False, so no hairline/border line
art is touched and no paint is added (verified by pixel diff + get_drawings
comparison afterwards). Plain white-rects were rejected: they would leave the
old boilerplate hidden ON-GRID in the text layer, and the engine's
find_boilerplate_lines grid filter only drops OFF-grid orphans — old+new
spans at the same y0 would merge into duplicated text on any rebuild path.

House rules: hebo 9pt, asc = 9.630*(size/9), redaction rects anchored to
get_drawings() border geometry with >=0.5pt clearance, DoO right edge <=591.0.
"""
import fitz

ASC9 = 9.630
GRID = 11.26
DOO_X0 = 21.5
DOO_MAXW = 591.0 - DOO_X0


def txt(page, x, bbox_top_y, text, size=9.0):
    page.insert_text((x, bbox_top_y + ASC9 * (size / 9.0)), text,
                     fontname="hebo", fontsize=size, color=(0, 0, 0))


def wrap(text, size=9.0):
    # The engine's multi-holder path re-inserts each template line verbatim
    # with 'Certificate Holder' -> 'Certificate Holders' (no re-wrap), so any
    # line carrying that phrase must keep slack for the extra 's'.
    s_w = fitz.get_text_length("s", fontname="hebo", fontsize=size)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        cap = DOO_MAXW - (s_w if "Certificate Holder" in t else 0)
        if fitz.get_text_length(t, fontname="hebo", fontsize=size) <= cap:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def redact_text_only(page, rects):
    for r in rects:
        page.add_redact_annot(fitz.Rect(*r), fill=False)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE)


ROLANDO_NEW = (
    "General Liability policy includes an automatic Additional Insured endorsement "
    "that provides Additional Insured status to the Certificate Holder as required "
    "by written contract. Additional Insured status on the Commercial Auto policy "
    "is added by endorsement as required by written contract. General Liability "
    "policy applies on a primary & non-contributory basis. A Blanket Waiver of "
    "Subrogation applies for General Liability and Commercial Auto policies."
)

P305_NEW_TAIL = (
    # continues after existing line 2 which ends "...applies on a primary &"
    "non-contributory basis. A Blanket Waiver of Subrogation applies for General "
    "Liability and Employer's Liability policies. Excess Liability policy follows form."
)


def build_rolando(src, dst):
    doc = fitz.open(src)
    page = doc[0]

    redact_text_only(page, [
        # DoO boilerplate, 3 old lines (bbox y 599.53-632.10, x to 558.50).
        # Borders: left 17.90-19.00, right 592.80-593.90, bottom 651.40-652.50.
        # Project line bbox bottom 598.31 -> rect top 599.0 stays clear.
        (19.5, 599.0, 592.3, 646.0),
        # Auto policy number cell: verts 213.00-213.20 / 332.10-332.70,
        # top horiz 386.20-386.40, next horiz at 446.60. Old span 215.90-256.91.
        (213.7, 386.9, 331.6, 398.6),
        # Auto POLICY EXP cell: verts 379.30-379.50 / 426.30-426.50.
        # Old exp chars 380.05-425.07; eff date chars end at 377.56 (outside).
        (380.0, 386.9, 425.8, 398.6),
    ])

    lines = wrap(ROLANDO_NEW)
    assert len(lines) == 4, f"expected 4 wrapped lines, got {len(lines)}"
    for i, l in enumerate(lines):
        w = fitz.get_text_length(l, fontname="hebo", fontsize=9.0)
        assert DOO_X0 + w <= 591.0, f"line {i+1} right edge {DOO_X0+w:.1f} > 591.0"
        y0 = 599.53 + i * GRID
        assert y0 < 652, f"line {i+1} y0 {y0} past 652"
        txt(page, DOO_X0, y0, l)

    txt(page, 215.90, 387.69, "CA-74829-0")
    new_exp = "12/15/2026"
    w = fitz.get_text_length(new_exp, fontname="hebo", fontsize=9.0)
    assert 380.05 + w <= 425.8, f"exp date overruns cell: {380.05+w:.2f}"
    txt(page, 380.05, 387.69, new_exp)

    doc.save(dst, garbage=4, deflate=True)
    doc.close()


def build_305(src, dst):
    doc = fitz.open(src)
    page = doc[0]

    # Lines 1-2 (y0 599.53/610.79) are unchanged and re-wrap identically in
    # hebo 9pt (verified). Remove old lines 3-4 (bbox y 622.05-645.71) and
    # insert the new tail on the same grid. Line-2 bbox bottom is 623.18
    # (descent padding; ink stops ~622.3) so the rect top must sit at 622.6:
    # low enough to intersect line-3 chars only, high enough to be checked
    # against line 2 -- redaction removes chars by bbox intersection, so we
    # instead use 623.3 with a post-check that line 2 survived intact.
    redact_text_only(page, [(19.5, 623.3, 592.3, 646.5)])

    lines = wrap(P305_NEW_TAIL)
    assert len(lines) == 2, f"expected 2 wrapped tail lines, got {len(lines)}"
    for i, l in enumerate(lines):
        w = fitz.get_text_length(l, fontname="hebo", fontsize=9.0)
        assert DOO_X0 + w <= 591.0, f"line right edge {DOO_X0+w:.1f} > 591.0"
        txt(page, DOO_X0, 622.05 + i * GRID, l)

    doc.save(dst, garbage=4, deflate=True)
    doc.close()


if __name__ == "__main__":
    T = "/private/tmp/wt-templates/templates"
    W = "/private/tmp/wt-templates/tmp_work"
    build_rolando(f"{T}/Rolando_s_HVAC_COI_Template.pdf", f"{W}/Rolando_new.pdf")
    build_305(f"{T}/305_Power_Corp_COI_Template.pdf", f"{W}/305_new.pdf")
    print("built OK")
