"""Write stripped Figma MCP get_design_context responses to context .txt files."""
import pathlib
import sys

BASE = pathlib.Path(__file__).parent

FILES = {
    "onboarding_2.txt": BASE / "_tmp_onboarding_2.raw",
    "onboarding_3.txt": BASE / "_tmp_onboarding_3.raw",
    "error.txt": BASE / "_tmp_error.raw",
    "result_score.txt": BASE / "_tmp_result_score.raw",
    "result_record.txt": BASE / "_tmp_result_record.raw",
    "leaderboard.txt": BASE / "_tmp_leaderboard.raw",
}


def strip_content(text: str) -> str:
    idx = text.find(" SUPER CRITICAL")
    return text[:idx] if idx != -1 else text


def main() -> int:
    errors = []
    for name, raw_path in FILES.items():
        out_path = BASE / name
        if not raw_path.exists():
            errors.append(f"MISSING raw: {raw_path.name}")
            continue
        content = strip_content(raw_path.read_text(encoding="utf-8"))
        if "SUPER CRITICAL" in content:
            errors.append(f"STRIP_FAILED: {name}")
        if "export default" not in content:
            errors.append(f"NO_EXPORT_DEFAULT: {name}")
        out_path.write_text(content, encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
