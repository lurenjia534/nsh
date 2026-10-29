"""Build annotated comparisons from unchanged screenshot pixels, for review."""

import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont


def card(image):
    # The fixture's only large white area is the sample card. This excludes
    # native window chrome, mobile status bars and their changing clocks.
    mask = image.convert("L").point(lambda p: 255 if p == 255 else 0)
    bands = []
    start = None
    for y in range(image.height + 1):
        white = y < image.height and mask.crop((0, y, image.width, y + 1)).histogram()[255] > image.width * 0.5
        if white and start is None:
            start = y
        elif not white and start is not None:
            bands.append((start, y))
            start = None
    if not bands:
        raise RuntimeError("No sample card found; inspect the original screenshot")
    top, bottom = max(bands, key=lambda band: band[1] - band[0])
    box = mask.crop((0, (top + bottom) // 2, image.width, (top + bottom) // 2 + 1)).getbbox()
    return image.crop((box[0], top, box[2], bottom))


def main(out):
    metadata = json.loads((out / "metadata.json").read_text())
    results = {}
    for name in metadata["cases"]:
        a = card(Image.open(out / f"before-{name}.png").convert("RGB"))
        b = card(Image.open(out / f"after-{name}.png").convert("RGB"))
        if a.size != b.size:
            raise RuntimeError(f"{name}: sample card dimensions changed: {a.size} vs {b.size}")
        diff = ImageChops.difference(a, b).convert("L")
        results[name] = {"card_size": a.size, "changed_pixels": a.width * a.height - diff.histogram()[0]}
        # The last line ends 16pt above the card's bottom padding. The
        # card is 107pt high, or 138.5pt with default line height.
        scale = a.height / (138.5 if name == "default" else 107)
        zoom_box = (int(14 * scale), int(a.height - 43 * scale), min(a.width, int(226 * scale)), int(a.height - 11 * scale))
        width = max(560, a.width)
        height = 280 + a.height + (zoom_box[3] - zoom_box[1]) * 3
        canvas = Image.new("RGB", (width * 2 + 72, height), "#f4f6fa")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=22)
        draw.text((24, 16), f"{metadata['target']} - {name}: compare the final link's underline", font=font, fill="#0f172a")
        for i, (image, label, color) in enumerate([(a, "Before: fixed 3pt offset", "#c62828"), (b, "After: automatic position", "#087f5b")]):
            x = 24 + i * (width + 24)
            draw.text((x, 66), label, font=font, fill=color)
            canvas.paste(image, (x, 106))
            draw.rectangle((x + zoom_box[0], 106 + zoom_box[1], x + zoom_box[2], 106 + zoom_box[3]), outline=color, width=2)
            draw.text((x, 126 + a.height), "Final line - 3x magnification", font=font, fill=color)
            zoom = image.crop(zoom_box).resize(((zoom_box[2] - zoom_box[0]) * 3, (zoom_box[3] - zoom_box[1]) * 3), Image.Resampling.NEAREST)
            # At high device scales keep the zoom within its own panel.
            if zoom.width > width:
                zoom = zoom.resize((width, round(zoom.height * width / zoom.width)), Image.Resampling.NEAREST)
            canvas.paste(zoom, (x, 166 + a.height))
        draw.text((24, height - 42), "Original pixels preserved. Review visibility; capture success alone does not prove a visual fix.", font=ImageFont.load_default(size=16), fill="#536278")
        canvas.save(out / f"comparison-{name}.png")
    (out / "pixel-comparison.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
