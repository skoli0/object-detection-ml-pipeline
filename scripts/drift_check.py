import argparse
import json


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reference", required=True)
    p.add_argument("--current", required=True)
    args = p.parse_args()

    with open(args.reference, "r", encoding="utf-8") as f:
        ref = json.load(f)
    with open(args.current, "r", encoding="utf-8") as f:
        cur = json.load(f)

    delta = abs(cur["mean_brightness"] - ref["mean_brightness"])
    print({"delta": delta, "drift": delta > 0.1})


if __name__ == "__main__":
    main()
