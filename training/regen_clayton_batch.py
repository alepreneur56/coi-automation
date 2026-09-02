"""Regenerate the 63 Clayton COIs on the fixed (3M umbrella) template.

- Extracts holder block lines verbatim from each source cert's holder box
  (rect 19,664,306,748; words grouped into lines by y, reading order).
- Rebuilds via coi_engine.build_single_coi (project_text=None, today's date).
- Verifies each output: holder text match, umbrella 3,000,000 x2 (text +
  pixel-identical to template cells), INSR letters A/B/C/D (text + pixel),
  date = today, non-blank render, not is_repaired.
- Writes folder + zip + index xlsx. Does NOT upload or email anything.
"""
import os, sys, zipfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz
from coi_engine import build_single_coi, find_optimal_font

SRC_DIR = "/Users/alepreneur/Desktop/Clayton COIs 2026-27 (existing batch)"
OUT_DIR = "/Users/alepreneur/Desktop/Clayton COIs 2026-27 (REGENERATED 09-01)"
TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "templates", "Clayton_Mechanical_COI_Template.pdf")
TODAY = date.today().strftime("%m/%d/%Y")

HOLDER_RECT = fitz.Rect(19, 664, 306, 748)
# Section y-ranges for INSR LTR letters (letter span y0 must fall in range)
LETTER_CELLS = {"GL": (300, 386), "Auto": (386, 446), "Umb": (446, 483), "WC": (483, 535)}
EXPECTED = {"GL": "A", "Auto": "B", "Umb": "C", "WC": "D"}
# Pixel-compare regions that must be identical to the template render
PIX_REGIONS = {
    "insr_col": fitz.Rect(17.0, 300.0, 37.0, 535.0),
    "umb_limits": fitz.Rect(517.5, 447.0, 592.0, 470.5),
}
ZOOM = fitz.Matrix(150 / 72, 150 / 72)


def holder_lines_of(path):
    doc = fitz.open(path)
    page = doc[0]
    words = [w for w in page.get_text("words")
             if HOLDER_RECT.contains(fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
    doc.close()
    words.sort(key=lambda w: (w[1], w[0]))
    lines, cur, cur_y = [], [], None
    for w in words:
        if cur_y is None or abs(w[1] - cur_y) <= 2.0:
            cur.append(w)
            cur_y = w[1] if cur_y is None else cur_y
        else:
            cur.sort(key=lambda x: x[0])
            lines.append(" ".join(x[4] for x in cur))
            cur, cur_y = [w], w[1]
    if cur:
        cur.sort(key=lambda x: x[0])
        lines.append(" ".join(x[4] for x in cur))
    return lines


def region_pix(page, rect):
    return page.get_pixmap(matrix=ZOOM, clip=rect).samples


def letters_of(page):
    found = {}
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                x0, y0 = s["bbox"][0], s["bbox"][1]
                t = s["text"].strip()
                if x0 < 36 and t and len(t) <= 2:
                    for sec, (a, bnd) in LETTER_CELLS.items():
                        if a <= y0 < bnd:
                            found.setdefault(sec, []).append(t)
    return found


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tdoc = fitz.open(TEMPLATE)
    tpage = tdoc[0]
    ref_pix = {k: region_pix(tpage, r) for k, r in PIX_REGIONS.items()}

    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".pdf"))
    print(f"{len(files)} source certs")
    rows, failures = [], []
    counts = {k: 0 for k in ["holder", "umb3m_text", "umb3m_pix", "letters",
                             "letters_pix", "date", "nonblank", "not_repaired"]}

    for fname in files:
        src = os.path.join(SRC_DIR, fname)
        out = os.path.join(OUT_DIR, fname)
        src_lines = holder_lines_of(src)
        if not src_lines:
            failures.append((fname, "no holder lines extracted from source"))
            continue
        fs, lh, disp_lines = find_optimal_font(src_lines, [])
        build_single_coi(TEMPLATE, out, disp_lines, fs, lh,
                         project_text=None, today_str=TODAY)

        # ---- verify ----
        doc = fitz.open(out)
        page = doc[0]
        errs = []

        # (a) holder text matches source (normalized whitespace)
        new_lines = holder_lines_of(out)
        if " ".join(" ".join(src_lines).split()) == " ".join(" ".join(new_lines).split()):
            counts["holder"] += 1
        else:
            errs.append(f"holder mismatch: src={src_lines!r} new={new_lines!r}")

        # (b) umbrella limits 3,000,000 twice — text layer, visible spans
        vals = []
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    x0, y0 = s["bbox"][0], s["bbox"][1]
                    if 517 <= x0 <= 570 and 446 <= y0 <= 471 and s["text"].strip() not in ("$",):
                        vals.append(s["text"])
        joined = "".join(vals)
        if joined.count("3,000,000") == 2:
            counts["umb3m_text"] += 1
        else:
            errs.append(f"umbrella text spans: {vals!r}")
        if region_pix(page, PIX_REGIONS["umb_limits"]) == ref_pix["umb_limits"]:
            counts["umb3m_pix"] += 1
        else:
            errs.append("umbrella limits cells render differs from fixed template")

        # (c) INSR letters
        found = letters_of(page)
        ok = all(found.get(sec) == [EXPECTED[sec]] for sec in EXPECTED)
        if ok:
            counts["letters"] += 1
        else:
            errs.append(f"letters: {found!r}")
        if region_pix(page, PIX_REGIONS["insr_col"]) == ref_pix["insr_col"]:
            counts["letters_pix"] += 1
        else:
            errs.append("INSR LTR column render differs from fixed template")

        # (d) date
        date_txt = page.get_text(clip=fitz.Rect(509, 33.5, 593, 47.5)).strip()
        if date_txt == TODAY:
            counts["date"] += 1
        else:
            errs.append(f"date reads {date_txt!r}")

        # (e) non-blank, not repaired
        pm = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        dark = sum(1 for i in range(0, len(pm.samples), pm.n) if pm.samples[i] < 128)
        if dark > 2000:
            counts["nonblank"] += 1
        else:
            errs.append(f"render nearly blank ({dark} dark px)")
        if not doc.is_repaired:
            counts["not_repaired"] += 1
        else:
            errs.append("doc.is_repaired = True")
        doc.close()

        rows.append((fname, disp_lines[0], " | ".join(disp_lines), TODAY))
        if errs:
            failures.append((fname, "; ".join(errs)))

    tdoc.close()

    # index xlsx
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clayton COIs 09-01"
    ws.append(["file", "holder line 1", "full holder block", "issue date"])
    for r in rows:
        ws.append(list(r))
    for col, wdt in zip("ABCD", (45, 40, 80, 14)):
        ws.column_dimensions[col].width = wdt
    xlsx = os.path.join(os.path.dirname(OUT_DIR), "Clayton COIs 2026-27 (REGENERATED 09-01) index.xlsx")
    wb.save(xlsx)

    # zip
    zpath = OUT_DIR + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(OUT_DIR)):
            z.write(os.path.join(OUT_DIR, f), arcname=f)

    print(f"generated: {len(rows)}  |  today={TODAY}")
    for k, v in counts.items():
        print(f"  check {k}: {v}/{len(rows)}")
    if failures:
        print("FAILURES:")
        for f, e in failures:
            print(f"  {f}: {e}")
    else:
        print("ALL CHECKS PASSED")
    print("xlsx:", xlsx)
    print("zip:", zpath)


if __name__ == "__main__":
    main()
