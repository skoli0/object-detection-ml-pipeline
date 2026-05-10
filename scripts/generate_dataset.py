from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path("datasets/raw")
IMAGES = ROOT / "images"
LABELS = ROOT / "labels"
PROC = Path("datasets/processed")


def make_sample(idx: int) -> None:
    w, h = 320, 320
    img = Image.new("RGB", (w, h), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)
    x1, y1 = 60 + idx * 3, 120
    x2, y2 = x1 + 160, y1 + 60
    draw.rectangle([x1, y1, x2, y2], outline="white", width=2)
    for x in range(x1 + 5, x2 - 5, 8):
        draw.line([x, y1 + 5, x, y2 - 5], fill="white", width=2)

    img_path = IMAGES / f"sample_{idx}.jpg"
    lbl_path = LABELS / f"sample_{idx}.txt"
    img.save(img_path)

    x_center = ((x1 + x2) / 2) / w
    y_center = ((y1 + y2) / 2) / h
    bw = (x2 - x1) / w
    bh = (y2 - y1) / h
    lbl_path.write_text(f"0 {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n")


def generate() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    LABELS.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    for i in range(12):
        make_sample(i)

    yaml = """path: datasets/raw
train: images
val: images
names:
  0: barcode
"""
    (PROC / "data.yaml").write_text(yaml)
    print("Generated synthetic dataset in datasets/raw")


if __name__ == "__main__":
    generate()
