# -*- coding: utf-8 -*-
"""Generate context .txt files from embedded Figma MCP payloads."""
import pathlib
import sys

BASE = pathlib.Path(__file__).parent

PAYLOADS = {}

def strip_content(text: str) -> str:
    idx = text.find(" SUPER CRITICAL")
    return text[:idx] if idx != -1 else text


def load_payloads():
    for name in [
        "onboarding_2",
        "onboarding_3",
        "error",
        "result_score",
        "result_record",
        "leaderboard",
    ]:
        raw_path = BASE / f"_tmp_{name}.raw"
        if raw_path.exists():
            PAYLOADS[f"{name}.txt"] = raw_path.read_text(encoding="utf-8")


def main() -> int:
    load_payloads()
    if len(PAYLOADS) != 6:
        missing = 6 - len(PAYLOADS)
        print(f"ERROR: missing {missing} raw payload files", file=sys.stderr)
        return 1
    errors = []
    for name, raw in sorted(PAYLOADS.items()):
        content = strip_content(raw)
        out = BASE / name
        out.write_text(content, encoding="utf-8")
        if "SUPER CRITICAL" in content:
            errors.append(f"STRIP_FAILED: {name}")
        if "export default" not in content:
            errors.append(f"NO_EXPORT_DEFAULT: {name}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
