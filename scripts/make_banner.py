#!/usr/bin/env python3
"""Headline banner for the top of an agent video.

Usage: make_banner.py "LINE ONE" "LINE TWO ENDING IN THE QUESTION?" OUT.png
1080x200 RGBA, rounded black bar (alpha 200) x 24..1056, full height, DejaVuSans-Bold 46 px,
line 1 white at y=32, line 2 yellow (255,214,0) at y=104, 2 px black stroke.
The font shrinks if a line would be wider than 1000 px. Text is upper-cased.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 4:
    sys.exit(__doc__)
l1, l2, out = sys.argv[1].upper(), sys.argv[2].upper(), sys.argv[3]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
im = Image.new("RGBA", (1080, 200), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle([24, 0, 1056, 199], radius=28, fill=(0, 0, 0, 200))

def fit(text, size=46):
    while size > 28:
        f = ImageFont.truetype(FONT, size)
        w = d.textbbox((0, 0), text, font=f, stroke_width=2)[2]
        if w <= 1000:
            return f, w
        size -= 2
    f = ImageFont.truetype(FONT, size)
    return f, d.textbbox((0, 0), text, font=f, stroke_width=2)[2]

for text, y, color in ((l1, 32, (255, 255, 255, 255)), (l2, 104, (255, 214, 0, 255))):
    f, w = fit(text)
    d.text(((1080 - w) // 2, y), text, font=f, fill=color, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    if w > 1000:
        print(f"warning: line too long even at small size: {text}", file=sys.stderr)
im.save(out)
print(f"banner written: {out}")
