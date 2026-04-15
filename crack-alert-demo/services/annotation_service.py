from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _safe_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_bbox(
    draw: ImageDraw.ImageDraw,
    image_size: tuple[int, int],
    location_hint: dict[str, Any],
) -> None:
    width, height = image_size
    x = int((location_hint.get("x", 15) / 100) * width)
    y = int((location_hint.get("y", 15) / 100) * height)
    box_w = int((location_hint.get("width", 35) / 100) * width)
    box_h = int((location_hint.get("height", 20) / 100) * height)
    x2 = min(width - 1, x + max(box_w, 24))
    y2 = min(height - 1, y + max(box_h, 24))
    draw.rectangle((x, y, x2, y2), outline="#ef4444", width=6)


def _draw_region_overlay(
    draw: ImageDraw.ImageDraw,
    image_size: tuple[int, int],
    location_hint: dict[str, Any],
) -> None:
    width, height = image_size
    desc = (location_hint.get("description") or "").lower()
    left, top, right, bottom = 0.25, 0.25, 0.75, 0.75
    if "top" in desc:
        top, bottom = 0.05, 0.40
    elif "bottom" in desc:
        top, bottom = 0.60, 0.95
    if "left" in desc:
        left, right = 0.05, 0.40
    elif "right" in desc:
        left, right = 0.60, 0.95
    overlay = (int(left * width), int(top * height), int(right * width), int(bottom * height))
    draw.rectangle(overlay, outline="#f97316", width=6)


def create_annotation(
    original_path: Path,
    output_path: Path,
    location_hint: dict[str, Any] | None,
    explanation: str,
) -> Path:
    with Image.open(original_path).convert("RGBA") as image:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        mode = (location_hint or {}).get("mode", "none")

        if mode == "bbox":
            _draw_bbox(draw, image.size, location_hint or {})
        elif mode == "region":
            _draw_region_overlay(draw, image.size, location_hint or {})

        label_text = "Approximate analysis only" if mode == "none" else "Possible crack region"
        label_height = 70
        draw.rectangle((0, 0, image.size[0], label_height), fill=(15, 23, 42, 190))
        draw.text((20, 16), label_text, fill="white", font=_safe_font(24))
        draw.text((20, 42), explanation[:110], fill="#dbeafe", font=_safe_font(16))

        annotated = Image.alpha_composite(image, overlay).convert("RGB")
        annotated.save(output_path)
    return output_path
