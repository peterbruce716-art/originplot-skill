from __future__ import annotations

from pathlib import Path

CANONICAL_ARTIFACTS = ("figure.opju", "figure.png", "figure.pdf", "figure.tif", "figure_spec.json", "verification.json")


def required_artifacts(output_dir: Path) -> dict[str, Path]:
    return {name: output_dir / name for name in CANONICAL_ARTIFACTS}


def artifact_is_nonblank(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    if path.suffix.lower() not in {".png", ".tif", ".tiff"}:
        return True
    try:
        from PIL import Image, ImageStat

        with Image.open(path).convert("RGB") as image:
            stat = ImageStat.Stat(image)
            return image.width > 10 and image.height > 10 and sum(stat.mean) > 15.0
    except Exception:
        return False


def no_demo_watermark(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path).convert("RGB") as image:
            resized = image.resize((160, 120))
            pixels = list(resized.getdata())
        cyan = sum(1 for red, green, blue in pixels if red < 100 and green > 180 and blue > 200 and abs(green - blue) < 70)
        return cyan / max(len(pixels), 1) <= 0.0005
    except Exception:
        return False
