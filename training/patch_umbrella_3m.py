"""One-off: Clayton umbrella limits 2,000,000 -> 3,000,000 (each occ + aggregate).

White-rects ONLY the digit runs in the limits value column (x 523.25-564.0),
>=0.5pt clear of row hairlines (446.6-446.8 / 458.7-458.9 / 470.7-470.9),
never touching the $ spans (x1=523.15) or the column borders (516.7-516.9,
592.8-593.9). Re-inserts hebo 9pt at the same x0/bbox_top as the old spans.
"""
import fitz

SRC = "templates/Clayton_Mechanical_COI_Template.pdf"
OUT = "templates/Clayton_Mechanical_COI_Template_NEW.pdf"

ASC = 9.630  # hebo ascender at 9pt

doc = fitz.open(SRC)
page = doc[0]

def white_rect(x0, y0, x1, y1):
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
    shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
    shape.commit()

def txt(x, bbox_top, text, size=9.0):
    page.insert_text((x, bbox_top + ASC * (size / 9.0)), text,
                     fontname="hebo", fontsize=size, color=(0, 0, 0))

# EACH OCCURRENCE row (hairlines 446.8 top / 458.7 bottom)
white_rect(523.25, 447.30, 564.0, 458.20)
# AGGREGATE row (hairlines 458.9 top / 470.7 bottom)
white_rect(523.25, 459.40, 564.0, 470.20)

# Old spans: '2' Arial at x0=523.34; hebo ',000,000' bbox_top 447.61 / 459.61
txt(523.34, 447.61, "3,000,000")
txt(523.34, 459.61, "3,000,000")

doc.save(OUT, garbage=4, deflate=True)
doc.close()

# Verify read-back
doc = fitz.open(OUT)
page = doc[0]
for b in page.get_text("dict")["blocks"]:
    for line in b.get("lines", []):
        for s in line.get("spans", []):
            x0, y0, x1, y1 = s["bbox"]
            if 445 <= y0 <= 475 and x0 > 500:
                print(f"bbox=({x0:.2f},{y0:.2f},{x1:.2f},{y1:.2f}) "
                      f"font={s['font']} text={s['text']!r}")
print("is_repaired:", doc.is_repaired)
doc.close()
