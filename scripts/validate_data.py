from pathlib import Path


def validate_dataset() -> None:
    images = list(Path("datasets/raw/images").glob("*.jpg"))
    labels = list(Path("datasets/raw/labels").glob("*.txt"))
    if not images:
        raise ValueError("No images found.")
    if len(images) != len(labels):
        raise ValueError("Image/label count mismatch.")
    for label in labels:
        parts = label.read_text().strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid label format in {label}")
    print(f"Validation passed: {len(images)} samples")


if __name__ == "__main__":
    validate_dataset()
