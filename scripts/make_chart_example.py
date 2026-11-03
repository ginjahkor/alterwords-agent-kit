#!/usr/bin/env python3
"""Animated B-roll for the grid-drop video: two honest bars (7 AM 3,840 MW, 1 PM 476.7 MW), then the four plants at zero.
Frames are 1080x1920 at 25 fps; local time t=0 is video time T0 (8.0 s). Pipe raw RGB to ffmpeg."""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 25
T0 = 8.0            # chart starts at this video time
DUR = 14.5          # until 22.5 s (just before "NISO says")
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
BG = (12, 14, 26)
YEL = (255, 200, 40)
RED = (235, 64, 52)
WHITE = (240, 240, 245)
GREY = (150, 155, 170)

# video times from the word timings (words.tsv)
T_7AM, T_DROP0, T_DROP1 = 9.64, 14.40, 17.30
PLANTS = [("Egbin", 18.00), ("Jebba", 18.82), ("Shiroro", 19.42), ("Kainji", 20.14)]
T_ZERO = 21.62

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def ctext(d, xy, s, font, fill, anchor="mm"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)

base_top, base_y = 520, 1080   # bar area: top of a full bar and the baseline
full_h = base_y - base_top
MAX = 4000.0

out = sys.stdout.buffer
for i in range(int(DUR * FPS)):
    t = T0 + i / FPS
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    ctext(d, (W // 2, 330), "NIGERIA'S POWER, MONDAY OCT 19", F(B, 50), WHITE)
    ctext(d, (W // 2, 395), "Grid generation in megawatts", F(R, 36), GREY)
    d.line([(110, base_y), (970, base_y)], fill=GREY, width=4)

    # bar 1: 7 AM, grows in when I say "7am"
    g1 = ease((t - (T_7AM - 0.6)) / 0.8)
    h1 = int(full_h * 3840 / MAX * g1)
    x1 = (190, 470)
    if h1 > 0:
        d.rectangle([x1[0], base_y - h1, x1[1], base_y], fill=YEL)
        if g1 > 0.5:
            ctext(d, ((x1[0] + x1[1]) // 2, base_y - h1 - 45), "3,840", F(B, 58), YEL)
    ctext(d, ((x1[0] + x1[1]) // 2, base_y + 50), "7 AM", F(B, 44), WHITE)

    # bar 2: 1 PM, starts level with bar 1 and falls to 476.7 while I say the numbers
    x2 = (610, 890)
    if t >= T_DROP0 - 0.8:
        pre = ease((t - (T_DROP0 - 0.8)) / 0.6)
        fall = ease((t - T_DROP0) / (T_DROP1 - T_DROP0))
        val = 3840 - (3840 - 476.7) * fall
        h2 = int(full_h * val / MAX * pre)
        col = tuple(int(YEL[k] + (RED[k] - YEL[k]) * fall) for k in range(3))
        d.rectangle([x2[0], base_y - h2, x2[1], base_y], fill=col)
        if pre > 0.5:
            label = f"{val:,.0f}" if fall < 1 else "477"
            ctext(d, ((x2[0] + x2[1]) // 2, base_y - h2 - 45), label, F(B, 58), col)
    ctext(d, ((x2[0] + x2[1]) // 2, base_y + 50), "1 PM", F(B, 44), WHITE)
    if t >= T_DROP0:
        ctext(d, (W // 2, 1150), "lines trip at 12:40 PM", F(R, 34), GREY)
    if t >= T_DROP1:
        s = 1 + 0.25 * (1 - ease((t - T_DROP1) / 0.35))
        ctext(d, (750, 700), "-88%", F(B, int(110 * s)), RED)

    # the four plants, each when I name it (left column, my window sits bottom right)
    y = 1310
    for name, tp in PLANTS:
        if t >= tp - 0.1:
            a = ease((t - (tp - 0.1)) / 0.3)
            c = tuple(int(BG[k] + (WHITE[k] - BG[k]) * a) for k in range(3))
            r = tuple(int(BG[k] + (RED[k] - BG[k]) * a) for k in range(3))
            d.text((80, y), name, font=F(B, 54), fill=c, anchor="lm")
            d.text((560, y), "0 MW", font=F(B, 54), fill=r, anchor="rm")
        y += 95
    if t >= T_ZERO - 0.1:
        d.text((80, y + 10), "ALL AT ZERO", font=F(B, 60), fill=RED, anchor="lm")
    d.text((80, 1850), "Source: NISO, via Ripples Nigeria", font=F(R, 28), fill=GREY, anchor="lm")
    out.write(img.tobytes())
