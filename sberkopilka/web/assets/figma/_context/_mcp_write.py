# -*- coding: utf-8 -*-
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).parent

NODES = {
    "onboarding_2.txt": "25:1125",
    "onboarding_3.txt": "25:1323",
    "error.txt": "25:1407",
    "result_score.txt": "25:1632",
    "result_record.txt": "25:1944",
    "leaderboard.txt": "25:2181",
}


def strip_content(text: str) -> str:
    idx = text.find(" SUPER CRITICAL")
    return text[:idx] if idx != -1 else text


def main() -> int:
    errors = []
    for name in NODES:
        raw_path = BASE / f"_tmp_{name.replace('.txt', '')}.raw"
        out_path = BASE / name
        if not raw_path.exists():
            errors.append(f"MISSING: {raw_path.name}")
            continue
        raw = raw_path.read_text(encoding="utf-8")
        content = strip_content(raw)
        out_path.write_text(content, encoding="utf-8")
        if "SUPER CRITICAL" in content:
            errors.append(f"STRIP_FAILED: {name}")
        if "export default" not in content:
            errors.append(f"NO_EXPORT_DEFAULT: {name}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
