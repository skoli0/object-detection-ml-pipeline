"""
Download diverse placeholder images over HTTP and pair each with a YOLO bbox label.

Uses Lorem Flickr (deterministic-ish tags) plus a fixed seed suffix so each batch is new.
Synthetic labels describe a centered "barcode" box compatible with datasets/processed/data.yaml.

Run standalone:
  python scripts/download_web_images.py --count 10
"""

from __future__ import annotations

import argparse
import io
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ROOT = Path("datasets/raw")
IMAGES = ROOT / "images"
LABELS = ROOT / "labels"
PROC = Path("datasets/processed")

# JPEG source: stable dimensions, permissive license for demos.
_LOREM_BASE = (
    "https://loremflickr.com/{w}/{h}/barcode,package,shipping?lock={seed}"
)


def _default_yolo_barcode_box(w: int, h: int) -> str:
    """Normalized YOLO line: single class 0 barcode-like rectangle near center."""
    bw, bh = int(w * 0.42), int(h * 0.22)
    x1, y1 = (w - bw) // 2, (h - bh) // 2
    x2, y2 = x1 + bw, y1 + bh
    xc = ((x1 + x2) / 2) / w
    yc = ((y1 + y2) / 2) / h
    nw = (x2 - x1) / w
    nh = (y2 - y1) / h
    return f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n"


def download_batch(count: int = 8, seed_offset: int = 0, timeout: float = 30.0) -> list[Path]:
    """
    Download ``count`` images into datasets/raw/images/ with matching labels.
    Images are named web_{seed_offset}_{i}.jpg so new batches stack with prior data.
    """
    IMAGES.mkdir(parents=True, exist_ok=True)
    LABELS.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    w, h = 320, 320
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "gatherai-ml-pipeline-demo/1.0")]

    for i in range(count):
        seed = 10_000 + seed_offset + i
        url = _LOREM_BASE.format(w=w, h=h, seed=seed)
        stem = f"web_{seed_offset}_{i:03d}"
        img_path = IMAGES / f"{stem}.jpg"
        lbl_path = LABELS / f"{stem}.txt"
        req = urllib.request.Request(url)
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            img = Image.new("RGB", (w, h), color=(28, 42, seed % 180 + 40))
            img.save(img_path, format="JPEG", quality=92)
        else:
            try:
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                im = im.resize((w, h), Image.Resampling.BILINEAR)
                im.save(img_path, format="JPEG", quality=92)
            except (UnidentifiedImageError, OSError, ValueError):
                img = Image.new("RGB", (w, h), color=(28, 42, seed % 180 + 40))
                img.save(img_path, format="JPEG", quality=92)

        lbl_path.write_text(_default_yolo_barcode_box(w, h))
        written.append(img_path)

    yaml = """path: datasets/raw
train: images
val: images
names:
  0: barcode
"""
    (PROC / "data.yaml").write_text(yaml)
    print(f"Downloaded {len(written)} web images → {IMAGES}")
    return written


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=8, help="Number of image/label pairs")
    parser.add_argument("--seed-offset", type=int, default=0, help="Batch id for filenames / lock param")
    args = parser.parse_args()
    download_batch(count=args.count, seed_offset=args.seed_offset)


if __name__ == "__main__":
    _main()
