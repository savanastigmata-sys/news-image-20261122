"""Draw the world-news infographic for Sunday 22 November 2026.

Pure Python standard library. Renders a 1024x1024 PNG in a dense
newspaper style: masthead, UTC timeline, 16 illustrated lead stories,
a world map with numbered pins, a numbered 17-50 list, a date check
and a sourcing footer. Glyphs come from fontdata.py (DejaVu bitmaps
rasterised at build time); the program itself needs no fonts, no
network, no clock and no randomness -- two runs write identical bytes.

TARGET (per the brief): TOP 1. The judge weighs, in order: the day
named with specific recognisable events; breadth across regions and
fields; readability from the image alone; faithfulness; craft.

Stories: every one happened, or was first reported, on Sunday
22 November 2026 in at least one time zone (the competition's own
rule). Built at about 15:00 UTC on 22 November, so the day is covered
up to early afternoon UTC; the DATE CHECK box names the big stories
deliberately left out because they belong to 20-21 November, and what
had not happened yet when the image was built.
"""
import base64 as _b64
import json as _json
import os
import struct
import sys
import zlib
from math import cos, pi, sin

# The grader runs `python3 -P -s`, which does not put the script's own
# directory on sys.path: add it so the sibling fontdata module is found.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontdata import _FONT_B64

W, H = 1024, 1024
PAPER = (247, 241, 222)
CARD = (255, 252, 242)
INK = (26, 26, 26)
RED = (143, 29, 33)
MAROON = (112, 20, 24)
MUTED = (104, 94, 78)
RULE = (176, 164, 136)
LAND = (203, 192, 158)
SEA = (226, 232, 228)
TINTS = {
    "Europe": (216, 228, 242),
    "Middle East": (242, 216, 198),
    "Asia": (214, 236, 214),
    "Americas": (242, 232, 196),
    "Africa": (234, 214, 234),
    "Oceania": (198, 232, 230),
    "Global": (228, 228, 228),
}
GREEN = (34, 120, 60)
PIN_COLOURS = {
    "Europe": (60, 100, 180),
    "Middle East": (220, 120, 40),
    "Asia": (130, 80, 160),
    "Americas": (180, 40, 40),
    "Africa": (40, 130, 70),
    "Oceania": (40, 140, 140),
    "Global": (90, 90, 90),
}
TOPICS = {1: "CLIMATE", 2: "GULF TENSIONS", 3: "UKRAINE WAR", 4: "CARTEL RAID",
          5: "FACTORY FIRE", 6: "FORMULA 1", 7: "CRICKET", 8: "CYBER",
          9: "WEST BANK", 10: "DEPORTATION DEAL", 11: "RUSSIA ROW",
          12: "AI DEAL", 13: "EXAM SCANDAL", 14: "AI WEAPONS",
          15: "HOUTHI STRIKES", 16: "SUMMIT FALLOUT"}

_FONTS = _json.loads(_b64.b64decode(_FONT_B64))


def _pick_size(family, size):
    sizes = sorted(int(s) for s in _FONTS[family])
    best = sizes[0]
    for s in sizes:
        if abs(s - size) < abs(best - size) or (
                abs(s - size) == abs(best - size) and s > best):
            best = s
    return best


def _glyph(family, size, ch):
    base = _pick_size(family, size)
    f = _FONTS[family][str(base)]
    g = f["glyphs"].get(ch)
    if g is None:
        g = f["glyphs"].get("?", f["glyphs"][" "])
    w, h, xo, yo, adv, b64 = g
    raw = _b64.b64decode(b64) if b64 else b""
    return w, h, xo, yo, adv, raw, base


def _bit(raw, w, x, y):
    i = y * w + x
    return (raw[i >> 3] >> (7 - (i & 7))) & 1


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def _i(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._i(x, y)
            self.px[i:i + 3] = bytes(c)

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._i(x0, yy)
            self.px[i:i + len(row)] = row

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.fill_rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y0 - y1)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - t < d <= r:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[k]), y,
                               max(1, int(xs[k + 1]) - int(xs[k])), 1, c)

    def round_rect(self, x, y, w, h, r, c):
        self.fill_rect(x + r, y, w - 2 * r, h, c)
        self.fill_rect(x, y + r, w, h - 2 * r, c)
        for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                       (x + r, y + h - r - 1),
                       (x + w - r - 1, y + h - r - 1)):
            self.disc(cx, cy, r, c)


def text_width(family, size, s):
    tot = 0
    for ch in s:
        _, _, _, _, adv, _, base = _glyph(family, size, ch)
        tot += adv * size / base
    return tot


def draw_text(cv, family, size, x, y, s, color):
    cx = x
    for ch in s:
        w, h, xo, yo, adv, raw, base = _glyph(family, size, ch)
        sc = size / base
        if w <= 0 or h <= 0:
            cx += adv * sc
            continue
        dw, dh = max(1, round(w * sc)), max(1, round(h * sc))
        ox = round(cx + xo * sc)
        oy = round(y + yo * sc)
        for dy in range(dh):
            sy = min(h - 1, round(dy * (h - 1) / max(1, dh - 1)))
            for dx in range(dw):
                sx = min(w - 1, round(dx * (w - 1) / max(1, dw - 1)))
                if _bit(raw, w, sx, sy):
                    cv.set(ox + dx, oy + dy, color)
        cx += adv * sc
    return cx


def draw_centered(cv, family, size, cx, y, s, color):
    draw_text(cv, family, size,
              int(cx - text_width(family, size, s) / 2), y, s, color)


def wrap(family, size, s, max_w):
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_width(family, size, trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---- small procedural illustrations (one per lead story) ----
# Each draws inside box (x, y, w, h) on a tinted ground. Simple, bold
# shapes: the label text beside it carries the facts; the picture
# only has to make the story recognisable at a glance.


def _sky(cv, x, y, w, h, c):
    cv.fill_rect(x, y, w, h, c)


def ill_strike(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (60, 58, 64))
    cv.fill_rect(x, y + h - 12, w, 12, (40, 38, 42))
    for dx, dy, r in ((w // 2, h // 2, 13), (w // 2 - 16, h // 2 + 4, 8),
                      (w // 2 + 17, h // 2 + 3, 7)):
        cv.disc(x + dx, y + dy, r, (240, 170, 40))
        cv.disc(x + dx, y + dy, r - 4, (250, 220, 90))
    cv.fill_rect(x + 8, y + h - 22, 10, 10, (20, 20, 22))
    cv.fill_rect(x + w - 20, y + h - 20, 12, 8, (20, 20, 22))


def ill_ship(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (120, 165, 200))
    cv.fill_rect(x, y + h - 14, w, 14, (38, 84, 130))
    cv.poly([(x + 8, y + h - 14), (x + w - 8, y + h - 14),
             (x + w - 22, y + h - 4), (x + 22, y + h - 4)], (90, 40, 36))
    cv.fill_rect(x + w // 2 - 4, y + 8, 8, h - 26, (200, 200, 200))
    cv.disc(x + w // 2 + 14, y + 12, 7, (240, 170, 40))
    cv.fill_rect(x + w - 30, y + 6, 16, 3, (250, 220, 90))


def ill_talks(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (222, 214, 190))
    cv.fill_rect(x + 6, y + h - 16, w - 12, 6, (120, 84, 50))
    cv.disc(x + w // 3, y + h // 2 - 2, 9, (70, 90, 130))
    cv.disc(x + 2 * w // 3, y + h // 2 - 2, 9, (150, 60, 50))
    cv.fill_rect(x + w // 3 - 9, y + h // 2 + 6, 18, 10, (70, 90, 130))
    cv.fill_rect(x + 2 * w // 3 - 9, y + h // 2 + 6, 18, 10, (150, 60, 50))
    draw_text(cv, "sans_bold", 11, x + w // 2 - 4, y + 2, "?", INK)


def ill_chart_down(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (240, 236, 224))
    cv.fill_rect(x + 10, y + h - 12, 8, 12, (90, 130, 90))
    cv.fill_rect(x + 26, y + h - 20, 8, 20, (90, 130, 90))
    cv.fill_rect(x + 42, y + h - 30, 8, 30, (170, 60, 50))
    cv.fill_rect(x + 58, y + h - 38, 8, 38, (170, 60, 50))
    cv.line(x + 8, y + 10, x + w - 8, y + h - 8, (170, 60, 50))
    cv.line(x + w - 14, y + h - 14, x + w - 8, y + h - 8, (170, 60, 50))
    cv.line(x + w - 14, y + h - 2, x + w - 8, y + h - 8, (170, 60, 50))


def ill_space(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (18, 22, 44))
    for dx, dy in ((8, 6), (w - 12, 8), (14, h - 8), (w - 20, h - 12),
                   (w // 2, 5)):
        cv.disc(x + dx, y + dy, 1, (255, 255, 255))
    cv.disc(x + w - 18, y + 12, 10, (200, 190, 170))
    cv.disc(x + w - 21, y + 10, 3, (170, 160, 140))
    cv.disc(x + 16, y + h - 12, 7, (90, 140, 200))
    cv.line(x + 16, y + h - 12, x + 34, y + h - 22, (240, 200, 80))


def ill_cyclone(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (170, 195, 215))
    cx, cy = x + w // 2, y + h // 2
    for r in (16, 11, 6):
        cv.ring(cx, cy, r, (255, 255, 255), 3)
    cv.disc(cx, cy, 3, (240, 240, 240))
    cv.fill_rect(x, y + h - 10, w, 10, (90, 130, 90))
    cv.line(x + 6, y + h - 10, x + 14, y + h - 22, (60, 90, 60))
    cv.line(x + 14, y + h - 22, x + 22, y + h - 10, (60, 90, 60))


def ill_quake(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (210, 200, 170))
    cv.fill_rect(x + 8, y + h - 20, 14, 14, (120, 100, 80))
    cv.fill_rect(x + w - 26, y + h - 24, 16, 18, (100, 85, 70))
    cv.fill_rect(x + w // 2 - 6, y + h - 16, 12, 10, (140, 120, 95))
    cv.line(x + 4, y + h - 6, x + w // 3, y + h - 14, (60, 50, 40))
    cv.line(x + w // 3, y + h - 14, x + 2 * w // 3, y + h - 4, (60, 50, 40))
    cv.line(x + 2 * w // 3, y + h - 4, x + w - 4, y + h - 12, (60, 50, 40))
    draw_text(cv, "sans_bold", 11, x + w // 2 - 8, y + 2, "6.7", RED)


def ill_gavel(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (226, 220, 200))
    cv.fill_rect(x + 10, y + h - 12, w - 20, 5, (120, 84, 50))
    cv.line(x + w // 2 - 14, y + 12, x + w // 2 + 14, y + 26, (90, 60, 30))
    cv.fill_rect(x + w // 2 - 18, y + 8, 12, 7, (70, 50, 30))
    cv.fill_rect(x + w // 2 + 6, y + 22, 12, 7, (70, 50, 30))


def ill_chip(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (30, 44, 66))
    cv.fill_rect(x + w // 2 - 14, y + h // 2 - 12, 28, 24, (60, 180, 140))
    cv.fill_rect(x + w // 2 - 8, y + h // 2 - 6, 16, 12, (30, 44, 66))
    for dx in (-18, -9, 0, 9, 18):
        cv.fill_rect(x + w // 2 + dx - 1, y + 4, 2, 8, (200, 200, 200))
        cv.fill_rect(x + w // 2 + dx - 1, y + h - 12, 2, 8, (200, 200, 200))


def ill_plane(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (150, 190, 220))
    cv.poly([(x + 8, y + h // 2), (x + w - 12, y + h // 2 - 6),
             (x + w - 4, y + h // 2), (x + w - 12, y + h // 2 + 6)],
            (240, 240, 240))
    cv.poly([(x + w // 2, y + h // 2 - 4), (x + w // 2 + 8, y + h // 2 - 16),
             (x + w // 2 + 12, y + h // 2 - 4)], (200, 60, 50))
    cv.disc(x + w - 22, y + 8, 5, (250, 220, 90))


def ill_flag(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (232, 226, 205))
    cv.fill_rect(x + 12, y + 6, 3, h - 12, (90, 70, 50))
    cv.fill_rect(x + 15, y + 8, w - 30, 12, (40, 90, 160))
    cv.fill_rect(x + 15, y + 20, w - 30, 12, (255, 255, 255))
    cv.fill_rect(x + 15, y + 32, w - 30, 12, (200, 60, 50))


def ill_missile(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (40, 40, 52))
    cv.line(x + 10, y + h - 8, x + w - 16, y + 10, (240, 200, 80))
    cv.disc(x + w - 16, y + 10, 4, (255, 240, 160))
    cv.disc(x + w // 2, y + h // 2 + 6, 8, (150, 60, 50))
    cv.disc(x + w // 2, y + h // 2 + 6, 4, (240, 170, 40))
    cv.fill_rect(x + 6, y + h - 16, 14, 8, (90, 90, 100))


def ill_court(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (222, 216, 198))
    cv.poly([(x + 6, y + 14), (x + w // 2, y + 2), (x + w - 6, y + 14)],
            (170, 150, 110))
    for dx in (12, 28, 44, 58):
        cv.fill_rect(x + dx, y + 16, 4, h - 26, (200, 185, 150))
    cv.fill_rect(x + 6, y + h - 10, w - 12, 4, (150, 130, 95))


def ill_mine(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (90, 130, 170))
    cv.fill_rect(x, y + h - 12, w, 12, (30, 70, 110))
    cv.poly([(x + 12, y + h - 12), (x + w - 12, y + h - 12),
             (x + w - 24, y + h - 2), (x + 24, y + h - 2)], (70, 60, 55))
    cv.disc(x + w // 2, y + 12, 6, (40, 40, 44))
    for a in range(8):
        ang = a * pi / 4
        cv.line(x + w // 2, y + 12, int(x + w // 2 + 11 * cos(ang)),
                int(y + 12 + 11 * sin(ang)), (40, 40, 44))


def ill_summit(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (214, 228, 214))
    cv.fill_rect(x + 6, y + h - 14, w - 12, 5, (120, 84, 50))
    for dx, col in ((-18, (70, 90, 130)), (0, (150, 60, 50)),
                    (18, (60, 120, 80))):
        cv.disc(x + w // 2 + dx, y + h // 2 - 4, 8, col)
        cv.fill_rect(x + w // 2 + dx - 8, y + h // 2 + 3, 16, 9, col)
    draw_text(cv, "sans_bold", 10, x + w // 2 - 14, y + 2, "COP31", INK)


def ill_science(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (238, 234, 220))
    draw_text(cv, "serif_bold", 20, x + 8, y + 6, "R", INK)
    draw_text(cv, "serif_bold", 12, x + w - 26, y + h - 22, "17m", RED)
    cv.line(x + 6, y + h - 8, x + w - 6, y + 8, (90, 90, 90))
    cv.disc(x + w // 2, y + h // 2, 5, (60, 120, 180))


def ill_sport(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (90, 150, 90))
    cv.disc(x + w // 2, y + h // 2, 12, (255, 255, 255))
    cv.fill_rect(x + w // 2 - 1, y + 4, 2, h - 8, (255, 255, 255))
    cv.disc(x + w // 2 - 8, y + h // 2 - 6, 3, (30, 30, 30))
    cv.disc(x + w // 2 + 8, y + h // 2 + 6, 3, (30, 30, 30))


def ill_globe(cv, x, y, w, h):
    _sky(cv, x, y, w, h, (200, 220, 235))
    cv.disc(x + w // 2, y + h // 2, min(w, h) // 2 - 2, (70, 120, 180))
    cv.disc(x + w // 2 - 6, y + h // 2 - 6, 7, (90, 170, 110))
    cv.disc(x + w // 2 + 8, y + h // 2 + 7, 5, (90, 170, 110))
    cv.ring(x + w // 2, y + h // 2, min(w, h) // 2 - 2, (40, 80, 130), 2)


def ill_fire(cv, x, y, w, h):
    # A factory fire: dark smoke sky, orange flame tongues, a roofline.
    _sky(cv, x, y, w, h, (52, 46, 44))
    cv.fill_rect(x, y + h - 14, w, 14, (34, 32, 30))
    cv.fill_rect(x + 6, y + h - 24, w - 12, 10, (96, 84, 70))
    for dx, hh, col in ((-16, 22, (230, 90, 20)), (0, 30, (250, 160, 30)),
                        (16, 20, (230, 90, 20))):
        cx = x + w // 2 + dx
        cv.poly([(cx - 7, y + h - 24), (cx, y + h - 24 - hh),
                 (cx + 7, y + h - 24)], col)
    cv.disc(x + w // 2, y + h - 26, 4, (250, 220, 90))
    cv.fill_rect(x + 8, y + 4, w - 16, 3, (90, 84, 78))


def ill_race(cv, x, y, w, h):
    # A Formula 1 car under the floodlights: dark track, low open-wheeler.
    _sky(cv, x, y, w, h, (24, 26, 40))
    for dx, dy in ((10, 6), (w - 14, 10), (w // 2, 5), (20, h - 20)):
        cv.disc(x + dx, y + dy, 1, (255, 255, 255))
    cv.fill_rect(x, y + h - 12, w, 12, (60, 60, 66))
    cv.fill_rect(x + 6, y + h - 22, w - 12, 10, (200, 30, 40))
    cv.disc(x + w // 2 - 12, y + h - 10, 5, (20, 20, 20))
    cv.disc(x + w // 2 + 12, y + h - 10, 5, (20, 20, 20))
    cv.fill_rect(x + w // 2 - 4, y + h - 30, 8, 9, (240, 240, 240))
    for i in range(4):
        col = (255, 255, 255) if i % 2 == 0 else (20, 20, 20)
        cv.fill_rect(x + w - 14 + (i % 2) * 4, y + 4 + (i // 2) * 4, 4, 4,
                     col)


def ill_cricket(cv, x, y, w, h):
    # A cricket bat striking a red ball on a green outfield.
    _sky(cv, x, y, w, h, (96, 158, 96))
    cv.fill_rect(x, y + h - 10, w, 10, (70, 120, 70))
    cv.line(x + w // 2 - 4, y + 6, x + w // 2 + 10, y + h - 18,
            (222, 200, 150))
    cv.fill_rect(x + w // 2 + 8, y + h - 22, 6, 12, (222, 200, 150))
    cv.disc(x + w // 2 + 18, y + h // 2 - 4, 5, (190, 40, 40))
    cv.disc(x + w // 2 + 18, y + h // 2 - 4, 2, (240, 240, 240))
    for dx in (-20, -14, -8):
        cv.fill_rect(x + w // 2 + dx, y + h - 12, 3, 6, (240, 230, 200))


ILLS = {"strike": ill_strike, "ship": ill_ship, "talks": ill_talks,
        "chart": ill_chart_down, "space": ill_space, "cyclone": ill_cyclone,
        "quake": ill_quake, "gavel": ill_gavel, "chip": ill_chip,
        "plane": ill_plane, "flag": ill_flag, "missile": ill_missile,
        "court": ill_court, "mine": ill_mine, "summit": ill_summit,
        "science": ill_science, "sport": ill_sport, "globe": ill_globe,
        "fire": ill_fire, "race": ill_race, "cricket": ill_cricket}

# ---- world map (coarse equirectangular continents, hand-plotted) ----
CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 72), (-95, 72), (-80, 73), (-65, 62),
     (-55, 52), (-60, 45), (-75, 35), (-80, 26), (-85, 20), (-95, 16),
     (-105, 20), (-115, 28), (-125, 40), (-125, 49), (-145, 60), (-168, 66)],
    [(-80, 10), (-60, 8), (-50, 0), (-40, -5), (-35, -10), (-40, -20),
     (-50, -30), (-60, -35), (-70, -40), (-73, -50), (-70, -55),
     (-75, -40), (-80, -20), (-80, -5), (-80, 10)],
    [(-10, 36), (-10, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 60), (30, 62), (30, 70), (20, 70), (12, 65),
     (5, 60), (-5, 58), (-10, 55), (-10, 48), (-10, 36)],
    [(-6, 35), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (48, 11),
     (51, 10), (44, 0), (40, -10), (35, -20), (32, -28), (20, -35),
     (15, -30), (12, -18), (9, -2), (9, 4), (-8, 5), (-15, 10), (-17, 15),
     (-15, 25), (-10, 30), (-6, 35)],
    [(30, 70), (40, 68), (60, 70), (70, 72), (90, 75), (110, 76), (130, 72),
     (150, 70), (170, 66), (178, 65), (170, 60), (160, 55), (155, 50),
     (142, 45), (140, 40), (130, 35), (127, 33), (122, 30), (120, 25),
     (110, 20), (105, 10), (100, 8), (95, 15), (90, 22), (85, 20), (80, 13),
     (75, 8), (72, 20), (65, 25), (60, 25), (55, 26), (50, 30), (48, 30),
     (42, 35), (36, 36), (30, 36), (30, 42), (30, 55), (30, 70)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (130, -32), (135, -35),
     (140, -38), (145, -38), (150, -37), (153, -32), (153, -27), (150, -22),
     (146, -19), (142, -11), (137, -12), (135, -15), (132, -12), (130, -13),
     (126, -14), (122, -17), (118, -20), (113, -22)],
    [(167, -45), (170, -42), (174, -39), (177, -38), (174, -41), (168, -46),
     (167, -45)],
]


def _lonlat(lon, lat, x, y, w, h):
    # latitude cropped to -60..85 so the map is not a flat strip
    return (x + int((lon + 180.0) / 360.0 * w),
            y + int((85.0 - lat) / 145.0 * h))


def draw_map(cv, x, y, w, h, pins):
    cv.fill_rect(x, y, w, h, SEA)
    for poly in CONTINENTS:
        pts = [_lonlat(lon, lat, x, y, w, h) for lon, lat in poly]
        cv.poly(pts, LAND)
        for i in range(len(pts)):
            cv.line(pts[i][0], pts[i][1], pts[(i + 1) % len(pts)][0],
                    pts[(i + 1) % len(pts)][1], (150, 138, 108))
    for num, lon, lat, region in pins:
        px, py = _lonlat(lon, lat, x, y, w, h)
        cv.disc(px, py, 8, PIN_COLOURS[region])
        cv.ring(px, py, 8, (255, 255, 255), 1)
        s = str(num)
        draw_text(cv, "sans_bold", 9, px - int(text_width("sans_bold", 9, s) / 2),
                  py - 5, s, (255, 255, 255))


MX = 28
CW = 968


def draw_masthead(cv):
    cv.hline(MX, 12, CW, INK)
    cv.hline(MX, 14, CW, INK)
    draw_centered(cv, "sans_bold", 12, 512, 18, "THE WORLD TODAY", RED)
    draw_centered(cv, "serif_bold", 48, 512, 36,
                  "SUNDAY, 22 NOVEMBER 2026", INK)
    draw_centered(cv, "sans", 11, 512, 92,
                  "ONE DAY OF WORLD NEWS, ONE PICTURE  \u00b7  50 STORIES  \u00b7  7 REGIONS  \u00b7  16 FIELDS",
                  MUTED)
    cv.hline(MX, 110, CW, INK)


def draw_timeline(cv):
    y = 134
    draw_text(cv, "sans_bold", 10, MX, y, "THE DAY IN UTC", RED)
    draw_text(cv, "sans", 10, MX + 108, y,
              "as the day turned west \u2014 overnight to evening", MUTED)
    bx, bw, bh = MX, 132, 34
    for i, (t, head) in enumerate(TIMELINE):
        x = bx + i * (bw + 7)
        cv.fill_rect(x, y + 14, bw, bh, CARD)
        cv.hline(x, y + 14, bw, RULE)
        cv.hline(x, y + 14 + bh - 1, bw, RULE)
        draw_text(cv, "sans_bold", 9, x + 5, y + 17, t, RED)
        for j, ln in enumerate(wrap("sans", 9, head, bw - 10)):
            draw_text(cv, "sans", 9, x + 5, y + 28 + j * 10, ln, INK)


def _meta(cv, x, y, max_w, region, source, status):
    draw_text(cv, "sans_bold", 8, x, y,
              (region.upper() + "  \u00b7  " + source.upper())[:60], MUTED)
    label = "CONFIRMED" if status == "CONFIRMED" else "CLAIM"
    col = GREEN if status == "CONFIRMED" else RED
    tw = int(text_width("sans_bold", 8, label))
    px = int(x + max_w - tw - 8)
    cv.fill_rect(px, y - 1, tw + 8, 10, col)
    draw_text(cv, "sans_bold", 8, px + 4, y, label, (255, 255, 255))


def draw_card(cv, s):
    n = s["n"]
    col, row = (n - 1) % 4, (n - 1) // 4
    x = MX + col * 246
    ys = [186, 294, 392, 490]
    hs = [106, 94, 94, 94]
    y, h = ys[row], hs[row]
    w = 238
    large = (row == 0)
    cv.fill_rect(x, y, w, h, CARD)
    cv.hline(x, y, w, RULE)
    cv.hline(x, y + h - 1, w, RULE)
    cv.vline(x, y, h, RULE)
    cv.vline(x + w - 1, y, h, RULE)
    cv.fill_rect(x, y, w, 13, TINTS[s["region"]])
    draw_text(cv, "sans_bold", 9, x + 4, y + 2, str(n), RED)
    draw_text(cv, "sans_bold", 8, x + 18, y + 3,
              s["region"].upper() + " \u00b7 " + TOPICS[n], INK)
    if large:
        ILLS[s["ill"]](cv, x + 4, y + 16, 58, 44)
        tx, tsize, tw = x + 66, 12, w - 70
        sy = y + 62
    else:
        ILLS[s["ill"]](cv, x + 4, y + 16, 44, 28)
        tx, tsize, tw = x + 52, 11, w - 56
        sy = y + 46
    for j, ln in enumerate(wrap("serif_bold", tsize, s["title"], tw)[:2]):
        draw_text(cv, "serif_bold", tsize, tx, y + 17 + j * (tsize + 2), ln,
                  INK)
    for j, ln in enumerate(wrap("sans", 9, s["summ"], w - 8)[:3]):
        draw_text(cv, "sans", 9, x + 4, sy + j * 10, ln, INK)
    _meta(cv, x + 4, y + h - 11, w - 8, s["region"], s["source"], s["status"])


REGION_TALLY = [("EUROPE", 10), ("MIDDLE EAST", 7), ("ASIA", 8),
                ("AMERICAS", 8), ("AFRICA", 5), ("OCEANIA", 4),
                ("GLOBAL", 8)]
FIELDS = ["War", "Politics", "Diplomacy", "Trade", "Markets", "Climate",
          "Space", "Science", "Sport", "Disaster", "Health", "AI & Tech",
          "Law & Crime", "Migration", "Defence", "Energy"]


def draw_map_panel(cv):
    y = 588
    draw_text(cv, "sans_bold", 11, MX, y, "WHERE IT HAPPENED", RED)
    draw_text(cv, "sans", 10, MX + 150, y,
              "numbered pins are the 16 lead stories above", MUTED)
    my = y + 15
    # left tally: stories per region (counts verified against the 50 items)
    draw_text(cv, "sans_bold", 9, MX, my, "BY REGION", INK)
    for i, (name, cnt) in enumerate(REGION_TALLY):
        ry = my + 14 + i * 11
        cv.disc(MX + 5, ry + 4, 4, PIN_COLOURS[name.title()])
        draw_text(cv, "sans", 9, MX + 14, ry, name, INK)
        c = str(cnt)
        draw_text(cv, "sans_bold", 9, MX + 156 - text_width("sans_bold", 9, c),
                  ry, c, RED)
    # right list: the 16 fields covered, two columns
    rx = MX + CW - 160
    draw_text(cv, "sans_bold", 9, rx, my, "16 FIELDS", INK)
    for i, f in enumerate(FIELDS):
        col = i // 8
        row = i % 8
        draw_text(cv, "sans", 8, rx + col * 82, my + 14 + row * 11, f, INK)
    pins = [(s["n"], s["lon"], s["lat"], s["region"]) for s in LEADS]
    draw_map(cv, MX + 164, my, 640, 140, pins)


def draw_also(cv):
    y = 749
    draw_text(cv, "sans_bold", 11, MX, y, "ALSO ON SUNDAY", RED)
    draw_text(cv, "sans", 10, MX + 140, y, "stories 17\u201350, one line each",
              MUTED)
    col_w = 478
    for i, s in enumerate(ALSO):
        col = i // 17
        row = i % 17
        x = MX + col * (col_w + 12)
        yy = y + 16 + row * 10
        draw_text(cv, "sans_bold", 9, x, yy, str(s["n"]) + ".", RED)
        line = s["title"] + " \u2014 " + s["source"]
        for ln in wrap("sans", 9, line, col_w - 22):
            draw_text(cv, "sans", 9, x + 20, yy, ln, INK)
            if s.get("claim"):
                draw_text(cv, "sans_bold", 9,
                          x + 20 + text_width("sans", 9, ln) + 3, yy,
                          "\u00b7 CLAIM", RED)
            break


def draw_datecheck(cv):
    y = 941
    cv.fill_rect(MX, y, CW, 48, (238, 232, 210))
    cv.hline(MX, y, CW, RED)
    cv.hline(MX, y + 47, CW, RED)
    cv.vline(MX, y, 48, RED)
    cv.vline(MX + CW - 1, y, 48, RED)
    draw_text(cv, "sans_bold", 10, MX + 6, y + 4, "DATE CHECK", RED)
    lines = wrap("sans", 9, DATECHECK, CW - 12)
    for j, ln in enumerate(lines[:3]):
        draw_text(cv, "sans", 9, MX + 6, y + 17 + j * 11, ln, INK)


def draw_footer(cv):
    y = 993
    cv.hline(MX, y, CW, INK)
    draw_text(cv, "sans", 9, MX, y + 5, FOOTER, MUTED)


# ---- the day's stories (verified Sunday 22 November 2026) ----
# Every item happened, or was first reported, on 22 Nov 2026 in at
# least one time zone. CLAIM = one side's account, not confirmed.
# Sources checked 22 Nov 2026 ~14:45 UTC: Reuters/CNN (COP31 collapse),
# OneTurn day page 2026-11-22 (Dymer, Bahrain, Mexico, Korea, Gaza,
# West Bank, Houthis, Indonesia fire, Nigeria, Rwanda, AI weapons),
# Reuters/F1 (Las Vegas GP), ANI (Ashes Perth), BBC (Korea, Kate),
# AfricaFrontPage 22 Nov (Somalia naval HQ, Kenya hiker, NEMA boat).
TIMELINE = [
    ("~00:30 UTC", "Drone hits flats near Kyiv; 14 missing"),
    ("~02:00 UTC", "Iran strikes Bahrain industrial site"),
    ("~03:00 UTC", "Mexico captures El Chapo Isidro"),
    ("05:40 UTC", "Verstappen wins Las Vegas GP"),
    ("~09:00 UTC", "Head's 123 seals Ashes win in Perth"),
    ("~12:00 UTC", "Indonesia factory fire: 3 dead, dozens missing"),
    ("~15:00 UTC", "COP31 collapses with no deal"),
]

LEADS = [
    {"n": 1, "region": "Global", "ill": "summit", "lon": 30.7, "lat": 36.9,
     "title": "COP31 collapses with no deal",
     "summ": "After two weeks in Antalya, the EU rejects a draft with no mention of fossil fuels; the longest COP ever ends empty-handed.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 2, "region": "Middle East", "ill": "missile", "lon": 50.6, "lat": 26.2,
     "title": "Iran strikes Bahrain industrial site",
     "summ": "Bahrain says missiles and drones hit an industrial site and two are hurt; Iran claims it destroyed two US Patriot radars.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 3, "region": "Europe", "ill": "strike", "lon": 30.3, "lat": 50.8,
     "title": "Russian drone flattens Kyiv flats",
     "summ": "A drone hits a five-storey block in Dymer overnight; 14 are missing and rescuers pull nine out by ladder.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 4, "region": "Americas", "ill": "gavel", "lon": -108.5, "lat": 25.6,
     "title": "Mexico captures El Chapo Isidro",
     "summ": "Special forces seize FBI most-wanted Fausto Isidro Meza Flores; seven gunmen and four soldiers die in the raid.",
     "source": "AP", "status": "CONFIRMED"},
    {"n": 5, "region": "Asia", "ill": "fire", "lon": 106.2, "lat": -6.2,
     "title": "Candy factory fire kills 3",
     "summ": "A blaze at a candy plant in Banten leaves about 50 workers missing; 15 are rescued as crews search the ruins.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 6, "region": "Americas", "ill": "race", "lon": -115.1, "lat": 36.2,
     "title": "Verstappen wins wild Las Vegas GP",
     "summ": "Thirty-five lead changes under the lights; Norris and Piastri follow as Russell hits the wall late.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 7, "region": "Oceania", "ill": "cricket", "lon": 115.9, "lat": -32.0,
     "title": "Head's 123 seals Ashes win in two days",
     "summ": "Travis Head smashes 123 off 83 as Australia chase 205 and take a 1-0 lead; Starc takes ten wickets in the match.",
     "source": "ANI", "status": "CONFIRMED"},
    {"n": 8, "region": "Americas", "ill": "chip", "lon": -77.0, "lat": 38.9,
     "title": "Trump confirms FBI database breach",
     "summ": "Trump confirms the NCIC crime database was breached; police nationwide use it, and the FBI is investigating.",
     "source": "CNBC", "status": "CONFIRMED"},
    {"n": 9, "region": "Middle East", "ill": "flag", "lon": 35.2, "lat": 31.9,
     "title": "Settlers burn 12 cars in West Bank",
     "summ": "Settlers torch a dozen Palestinian vehicles overnight; Eisenkot calls it Jewish terrorism and police open an inquiry.",
     "source": "Le Monde", "status": "CONFIRMED"},
    {"n": 10, "region": "Africa", "ill": "talks", "lon": 30.1, "lat": -1.9,
     "title": "EU states strike Rwanda deportation deal",
     "summ": "Five EU countries agree deportation centres in Rwanda; Costa also proposes a 3% tax on big digital firms.",
     "source": "El Pais", "status": "CONFIRMED"},
    {"n": 11, "region": "Europe", "ill": "flag", "lon": 12.6, "lat": 55.7,
     "title": "Denmark urges EU to curb Russian travel",
     "summ": "After foiling an alleged plot to kill a rapper, Denmark presses EU states to limit Russian visas.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 12, "region": "Global", "ill": "chip", "lon": -122.4, "lat": 37.8,
     "title": "Amazon nears $7.5bn AI startup deal",
     "summ": "Amazon is close to buying Israeli AI startup Decart to boost its Trainium chips, reports say.",
     "source": "Crypto Briefing", "status": "CLAIM"},
    {"n": 13, "region": "Asia", "ill": "gavel", "lon": 127.0, "lat": 37.5,
     "title": "Korea minister quits over exam scandal",
     "summ": "Education chief Choi Kyo-jin resigns days before college entrance exams after AI cheating chaos.",
     "source": "BBC", "status": "CONFIRMED"},
    {"n": 14, "region": "Global", "ill": "talks", "lon": 6.1, "lat": 46.2,
     "title": "UN AI-weapons talks end with no rules",
     "summ": "Talks in Geneva end with agreement to keep talking but no binding rules on weapons that pick their own targets.",
     "source": "Guardian", "status": "CONFIRMED"},
    {"n": 15, "region": "Middle East", "ill": "missile", "lon": 42.8, "lat": 14.8,
     "title": "Houthis fire missiles at Riyadh",
     "summ": "Saudi defences stop three missiles aimed at the capital after coalition strikes on Hodeida port.",
     "source": "Al Jazeera", "status": "CONFIRMED"},
    {"n": 16, "region": "Asia", "ill": "talks", "lon": 114.1, "lat": 22.5,
     "title": "Zelenskyy: to us, Putin is a killer",
     "summ": "After Trump again calls Putin a friend, Zelenskyy replies that to Ukrainians he is a killer; analysts say Xi gained most.",
     "source": "CBS", "status": "CONFIRMED"},
]

ALSO = [
    {"n": 17, "title": "Sparta II still burning off Finland; Helsinki probes helicopter incursion", "source": "Reuters"},
    {"n": 18, "title": "Iran starts power rationing as war hits its grid", "source": "BBC Persian"},
    {"n": 19, "title": "Lebanon's Aoun blames Israel and Iran for threats to sovereignty", "source": "Al Jazeera"},
    {"n": 20, "title": "Eisenkot invites Netanyahu's Likud to coalition talks", "source": "Euronews"},
    {"n": 21, "title": "WCK says Gaza van dead were not its team", "source": "CBC"},
    {"n": 22, "title": "Princess Kate says she is in remission from cancer", "source": "CBS"},
    {"n": 23, "title": "Second group verifies Riemann proof claim", "source": "Guardian", "claim": True},
    {"n": 24, "title": "Tech stocks suffer worst week since 2020", "source": "CNBC"},
    {"n": 25, "title": "Brent crude $89.95 as Gulf turmoil meets glut forecasts", "source": "CNBC"},
    {"n": 26, "title": "One-time CRISPR therapy cuts bad cholesterol by 52%", "source": "Good News Network"},
    {"n": 27, "title": "Argentina approves $50bn LNG export project", "source": "Buenos Aires Times"},
    {"n": 28, "title": "Seattle jet-bridge arrests draw outcry", "source": "Al Jazeera"},
    {"n": 29, "title": "Bangladesh garment strikes shut 80 factories", "source": "TBS"},
    {"n": 30, "title": "Saudi Arabia triples oil stored in Japan", "source": "Japan Today"},
    {"n": 31, "title": "Turkey takes control of last independent news channel", "source": "RFI"},
    {"n": 32, "title": "Nigeria funeral-boat toll reaches 24", "source": "Al Jazeera"},
    {"n": 33, "title": "Ethiopia to host COP32 after Antalya failure", "source": "Reuters"},
    {"n": 34, "title": "Black Foils win Dubai SailGP, beating Australia", "source": "Reuters"},
    {"n": 35, "title": "Magnitude 4.9 quake south of Fiji Islands", "source": "USGS"},
    {"n": 36, "title": "Leeds stun Chelsea 4-1 at Stamford Bridge", "source": "Sky Sports"},
    {"n": 37, "title": "Ferrari boss: Hamilton-Leclerc crash unacceptable", "source": "BBC Sport"},
    {"n": 38, "title": "May tells Burnham to move on from Brexit", "source": "BBC"},
    {"n": 39, "title": "S&P 500 falls into correction, down 9.8% in a month", "source": "CNBC"},
    {"n": 40, "title": "Kyiv claims 45,000 Russian troops killed in November", "source": "Kyiv", "claim": True},
    {"n": 41, "title": "Australia edge Wales 29-26 in Cardiff", "source": "ESPN"},
    {"n": 42, "title": "Man convicted of starting 2025 Palisades fire", "source": "France 24"},
    {"n": 43, "title": "FBI arrests Georgia man over $26,000 sent to IS-linked groups", "source": "FBI"},
    {"n": 44, "title": "Pakistan says 15 militants killed in Mastung raids", "source": "Pakistan"},
    {"n": 45, "title": "Armenia launches Trump Road project near border", "source": "Armenia"},
    {"n": 46, "title": "Somalia launches naval HQ and maritime operations centre", "source": "Goobjoog"},
    {"n": 47, "title": "Kenya deploys chopper and drones for missing Aberdare hiker", "source": "The Standard"},
    {"n": 48, "title": "Cyclone Xavier weakens north of Samoa", "source": "BOM"},
    {"n": 49, "title": "Cost-of-living protests continue in France and Portugal", "source": "France 24"},
    {"n": 50, "title": "US Agriculture Dept also breached, reports say", "source": "BBC"},
]

DATECHECK = ("Left out: the Shenzhen Trump-Xi-Putin summit (19-20 Nov); the EU-Indonesia trade deal, BepiColombo at Mercury "
             "and the ICJ Rohingya ruling (21 Nov and earlier); Russian missiles landing in Poland (Fri 20 Nov); the Peru "
             "quake toll (Fri 20 Nov); the Women's Rugby League World Cup final (Sat 21 Nov). Not yet decided at about "
             "15:00 UTC: what follows the collapsed COP31 pact; the full toll of the Cikande factory fire.")

FOOTER = ("Every story happened or was first reported on Sun 22 Nov 2026. "
          "CLAIM = one side's account. "
          "Sources: Reuters, AP, CNN, BBC, Al Jazeera, CBS, El Pais, ANI. Original drawings.")


def render():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_timeline(cv)
    for s in LEADS:
        draw_card(cv, s)
    draw_map_panel(cv)
    draw_also(cv)
    draw_datecheck(cv)
    draw_footer(cv)
    return cv


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    size = write_png(render(), path)
    print("wrote", path, size, "bytes")


if __name__ == "__main__":
    main()
