"""Render data/*.json palettes: python generate.py (pip install -r requirements.txt)."""
import json
import re
from pathlib import Path

from PIL import Image, ImageCms, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SIZE, LEFT, PAD, STEP = 112, 270, 32, 180
WIDTH = LEFT + 10 * SIZE + PAD
OUTPUTS = {
    "tableau10": "tableau10",
    "okabe-ito": "okabe-ito",
    "matplotlib-tab20": "matplotlib-tab20",
    "paul-tol": "02-paul-tol",
    "colorbrewer": "03-colorbrewer",
}


def font(size, mono=False):
    """Use macOS fonts, or DejaVu fonts on Linux."""
    names = (
        ["/System/Library/Fonts/Supplemental/Andale Mono.ttf", "DejaVuSansMono.ttf"]
        if mono else
        ["/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise RuntimeError("Install Arial/Andale Mono or DejaVu fonts.")


def render(palettes, stem, notes=()):
    """Render HEX swatches; optional marks identify gamut-mapped colors."""
    rows = []
    for palette in palettes:
        colors = palette["colors"]
        columns = 10 if palette["id"] == "matplotlib-tab20" or len(colors) <= 10 else (len(colors) + 1) // 2
        marks = palette.get("marks", [False] * len(colors))
        if not colors or len(marks) != len(colors):
            raise ValueError("Colors and marks must have matching nonempty lengths.")
        for start in range(0, len(colors), columns):
            rows.append((palette["name"] if start == 0 else "", colors[start:start + columns], marks[start:start + columns]))
    height = PAD * 2 + len(rows) * STEP - 30 + (94 if notes else 0)
    image = Image.new("RGB", (WIDTH, height), "white")
    draw = ImageDraw.Draw(image)
    name_font, hex_font, info_font = font(26), font(20, mono=True), font(21)
    for row_index, (name, colors, marks) in enumerate(rows):
        y = PAD + row_index * STEP
        lines = name.split(" / ") if draw.textlength(name, font=name_font) > LEFT - PAD - 20 else [name]
        for index, line in enumerate(lines):
            if draw.textlength(line, font=name_font) >= LEFT - PAD - 12:
                raise ValueError(f"Label too wide: {line}")
            draw.text((PAD, y + SIZE / 2 + (index - (len(lines) - 1) / 2) * 30), line, font=name_font, fill="#222222", anchor="lm")
        for index, (color, marked) in enumerate(zip(colors, marks)):
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                raise ValueError(f"Invalid HEX: {color}")
            x = LEFT + index * SIZE
            draw.rectangle((x, y, x + SIZE - 1, y + SIZE - 1), fill=color)
            draw.text((x + SIZE / 2, y + SIZE + 14), color, font=hex_font, fill="#333333", anchor="mt")
            if marked:
                draw.text((x + SIZE / 2, y + SIZE + 38), "*", font=info_font, fill="#555555", anchor="mt")
    for index, note in enumerate(notes):
        draw.text((PAD, height - 68 + index * 30), note, font=info_font, fill="#555555")
    output = ROOT / "images" / f"{stem}.png"
    output.parent.mkdir(exist_ok=True)
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    image.save(output, icc_profile=profile)
    with Image.open(output) as saved:
        for row_index, (_, colors, _) in enumerate(rows):
            for index, color in enumerate(colors):
                expected = tuple(bytes.fromhex(color[1:]))
                for offset in (0, SIZE // 2, SIZE - 1):
                    if saved.getpixel((LEFT + index * SIZE + offset, PAD + row_index * STEP + SIZE // 2)) != expected:
                        raise ValueError(f"Swatch mismatch: {color}")
    print(output.relative_to(ROOT))


def main():
    for name, stem in OUTPUTS.items():
        palettes = json.loads((ROOT / "data" / f"{name}.json").read_text())
        render(palettes, stem)


if __name__ == "__main__":
    main()
