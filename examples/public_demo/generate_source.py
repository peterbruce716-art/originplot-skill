from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw


def generate(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "synthetic_line.csv"
    png_path = output_dir / "synthetic_line_reference.png"
    rows = [(x, 0.55 * x + 12.0 * math.sin(x / 12.0)) for x in range(0, 101, 2)]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["x", "response"])
        writer.writerows((x, f"{y:.6f}") for x, y in rows)

    width, height = 720, 440
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    frame = (80, 45, 680, 370)
    draw.rectangle(frame, outline="black", width=2)
    values = [y for _, y in rows]
    ymin, ymax = min(values), max(values)
    points = []
    for x, y in rows:
        px = frame[0] + (frame[2] - frame[0]) * x / 100.0
        py = frame[3] - (frame[3] - frame[1]) * (y - ymin) / (ymax - ymin)
        points.append((px, py))
    draw.line(points, fill=(31, 78, 157), width=3)
    draw.text((330, 395), "x", fill="black")
    draw.text((18, 190), "response", fill="black")
    draw.text((92, 58), "Synthetic line", fill="black")
    image.save(png_path)
    return {"csv": str(csv_path), "reference_png": str(png_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = generate(args.output_dir)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
