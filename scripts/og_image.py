"""Render og-image.png (1200x630) from data/stratz.json. Dev-only; needs Pillow.

    pip install pillow
    python scripts/og_image.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MEDALS = ["herald", "guardian", "crusader", "archon", "legend", "ancient", "divine", "immortal"]
FOCUS = {"crusader": "#c9a227", "archon": "#5aa9ff", "legend": "#c77dff"}
POP = 7_000_000


def medal_shares(cum: dict) -> dict:
    out, floor = {}, 0.0
    for m in MEDALS:
        if m == "immortal":
            out[m] = 100 - floor
            break
        top = cum[m][-1]
        out[m] = top - floor
        floor = top
    return out


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    for name in names:
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def main() -> None:
    data = json.loads((ROOT / "data" / "stratz.json").read_text(encoding="utf-8"))
    months = data["months"]
    base = next(m for m in months if m["month"] == "2026-06")
    latest = months[-1]
    bs, ls = medal_shares(base["cumulative"]), medal_shares(latest["cumulative"])

    img = Image.new("RGB", (1200, 630), "#0f1115")
    d = ImageDraw.Draw(img)
    d.text((60, 50), "Dota 2 ranks after the June 2026 MMR change", fill="#e6e8ee", font=font(44, True))
    d.text((60, 110), "Players per bracket, Jun 2026 vs latest, on 7,000,000 ranked accounts", fill="#9aa3b2", font=font(24))

    x = 60
    for m, color in FOCUS.items():
        b, l = round(bs[m] / 100 * POP), round(ls[m] / 100 * POP)
        delta = l - b
        d.rounded_rectangle((x, 190, x + 340, 540), radius=16, fill="#171a21", outline="#2a2f3a")
        d.text((x + 24, 214), m.capitalize(), fill=color, font=font(30, True))
        d.text((x + 24, 270), f"{l:,}", fill="#e6e8ee", font=font(48, True))
        d.text((x + 24, 335), f"{ls[m]:.2f}% of players", fill="#9aa3b2", font=font(22))
        d.text((x + 24, 400), f"{'+' if delta >= 0 else ''}{delta:,}", fill="#4cc38a" if delta >= 0 else "#e5534b", font=font(40, True))
        d.text((x + 24, 455), f"since Jun 2026 ({b:,})", fill="#9aa3b2", font=font(22))
        x += 370

    d.text((60, 580), "Source: Stratz percentiles via Esports Tales", fill="#9aa3b2", font=font(20))
    out = ROOT / "og-image.png"
    img.save(out, optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
