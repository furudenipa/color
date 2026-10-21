"""Render the article's three OKLCH palettes: python generate_oklch.py.

Out-of-sRGB colors are mapped by reducing chroma at constant L/h.
"""
import json
import math

import numpy as np

from generate import ROOT, render

# OKLab transforms: linear sRGB -> LMS -> OKLab.
RGB_TO_LMS = np.array([
    [.4122214708, .5363325363, .0514459929],
    [.2119034982, .6806995451, .1073969566],
    [.0883024619, .2817188376, .6299787005],
])
LMS_TO_LAB = np.array([
    [.2104542553, .7936177850, -.0040720468],
    [1.9779984951, -2.4285922050, .4505937099],
    [.0259040371, .7827717662, -.8086757660],
])
LMS_TO_RGB = np.linalg.inv(RGB_TO_LMS)
LAB_TO_LMS = np.linalg.inv(LMS_TO_LAB)


def linear_rgb(lightness, chroma, hue):
    angle = math.radians(hue)
    lab = np.array([lightness, chroma * math.cos(angle), chroma * math.sin(angle)])
    return LMS_TO_RGB @ ((LAB_TO_LMS @ lab) ** 3)


def in_gamut(rgb):
    return bool(np.all(rgb >= -1e-10) and np.all(rgb <= 1 + 1e-10))


def mapped(lightness, chroma, hue):
    """Reduce chroma to fit sRGB, preserving lightness and hue."""
    actual = chroma
    if not in_gamut(linear_rgb(lightness, chroma, hue)):
        low, high = 0., chroma
        for _ in range(50):
            middle = (low + high) / 2
            if in_gamut(linear_rgb(lightness, middle, hue)):
                low = middle
            else:
                high = middle
        actual = low
    linear = np.clip(linear_rgb(lightness, actual, hue), 0, 1)
    srgb = np.where(linear <= .0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - .055)
    code = '#' + ''.join(f'{math.floor(float(value) * 255 + .5):02X}' for value in srgb)
    return code, actual


def main():
    config = json.loads((ROOT / "data" / "oklch.json").read_text())
    count = config["count"]
    if not isinstance(count, int) or not 1 <= count <= 10:
        raise ValueError("count must be an integer from 1 to 10")
    palettes = []
    for row in config["palettes"]:
        L, C = row["L"], row["C"]
        if not 0 <= L <= 1 or C < 0:
            raise ValueError("Expected 0 <= L <= 1 and C >= 0")
        colors, marks = [], []
        for index in range(count):
            hue = (config["hue_start"] + 360 * index / count) % 360
            code, actual = mapped(L, C, hue)
            colors.append(code)
            marks.append(actual < C - 1e-8)
        palettes.append({
            "id": "oklch", "name": f"L {L:.2f} / C {C:.2f}",
            "colors": colors, "marks": marks,
        })
    render(palettes, "oklch-article", notes=(
        "* Chroma reduced to fit sRGB; L and hue preserved.",
        f"{count} hues / step {360 / count:g}°",
    ))


if __name__ == "__main__":
    main()
