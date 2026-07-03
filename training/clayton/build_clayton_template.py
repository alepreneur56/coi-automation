"""
Build Clayton Mechanical COI template from the bound COI 070126.pdf.

Per COI_TEMPLATE_BUILDING_GUIDE.md:
  STEP 1 white rects (erase), STEP 2 insert text, STEP 3 save.

Changes vs source:
  1. Flatten the 4 FreeText annotations into page content (2 NAIC numbers,
     ANY AUTO X, umbrella ADDL/SUBR X pair), then delete the annotations.
  2. Erase DGO Hotel holder block -> NAME / ADDRESS / STATE, CITY ZIP CODE
     placeholder (exact Rolando template positions).
  3. Erase 07/01/2026 date -> MM/DD/YYYY (Rolando position x=522.0 y0=35.25).
  4. Insert 'Project name & Address ( If Applicable)' line in the DoO gap
     (license y0=577.20 + 11.26 grid = 588.46), required by coi_engine.
"""
import fitz

# clayton_clean_v1.pdf = insert_pdf clean copy of the original COI 070126.pdf,
# whose xref table is too broken for MuPDF to rewrite directly (renders fine,
# any save dies on dangling refs like '36 0 R').
SRC = "/private/tmp/wt-clayton/clayton_clean_v1.pdf"
OUT = "/private/tmp/wt-clayton/templates/Clayton_Mechanical_COI_Template.pdf"

# The source PDF has a dangling xref (36 0 R) that breaks any save — even
# the engine's tobytes scrub. The dangler hangs off the FreeText annots, so
# delete them BEFORE serializing (their values are re-inserted as page
# content in STEP 2a).
_raw = fitz.open(SRC)
_n = 0
while _raw[0].first_annot:
    _raw[0].delete_annot(_raw[0].first_annot)
    _n += 1
print(f"deleted {_n} annotations (pre-scrub)")
doc = fitz.open("pdf", _raw.tobytes(garbage=3, deflate=True))
_raw.close()
page = doc[0]


def asc(size):
    return 9.630 * (size / 9.0)


def white_rect(x0, y0, x1, y1):
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
    shape.commit()


def txt(x, bbox_top_y, text, size=9.0):
    page.insert_text((x, bbox_top_y + asc(size)), text,
                     fontname="hebo", fontsize=size, color=(0, 0, 0))


# ---- STEP 1: white rects ----
# Holder block content (borders: left 17.9-19.0, top 663.6-664.7,
# stray hairline at x68.4 y742.58 -> stop at 740.0). DGO text is y 683.6-726.3.
white_rect(20.0, 666.0, 304.0, 740.0)
# Date value area (box: 509-510.1 / 592.8-593.9 / 23.5-24.6 / 47.6-48.7).
# Same rect the engine uses at issuance on this form family.
white_rect(510.5, 34.0, 592.5, 47.0)

# ---- STEP 2: insert text ----
# 2a. Flattened annotation values (match page-content siblings:
#     NAIC 24112 at x0=543.38 size 9; row X pattern x0=183.50/201.50 size 9)
txt(543.38, 194.25, "19445")            # INSURER C NAIC (National Union)
txt(543.38, 207.75, "42376")            # INSURER D NAIC (Technology Ins)
txt(83.58, 363.20, "X")                 # ANY AUTO checkbox
txt(183.50, 447.61, "X")                # Umbrella ADDL INSR (grid of row Xs)
txt(201.50, 447.61, "X")                # Umbrella SUBR WVD

# 2b. Holder placeholder — exact Rolando template positions
txt(71.90, 678.76, "NAME")
txt(71.90, 690.03, "ADDRESS")
txt(71.90, 701.29, "STATE, CITY ZIP CODE")

# 2c. Date placeholder — Rolando position
txt(522.00, 35.25, "MM/DD/YYYY")

# 2d. Project placeholder line in DoO (license 577.20 + 11.26 line grid)
txt(21.50, 588.46, "Project name & Address ( If Applicable)")

# ---- STEP 3: save ----
doc.save(OUT, garbage=4, deflate=True)
doc.close()
print(f"saved {OUT}")
