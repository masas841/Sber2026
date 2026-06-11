# -*- coding: utf-8 -*-
import pathlib

BASE = pathlib.Path(r"i:\Cursor\Sber2026\sberkopilka\web\assets\figma\_context")

FILES = {
    "result_score.txt": "_tmp_fetch_25_1632.raw",
    "result_record.txt": "_tmp_fetch_25_1944.raw",
    "leaderboard.txt": "_tmp_fetch_25_2181.raw",
}


def strip_content(text: str) -> str:
    for marker in (" SUPER CRITICAL", "SUPER CRITICAL"):
        idx = text.find(marker)
        if idx != -1:
            return text[:idx].rstrip() + "\n"
    return text


def function_part(text: str) -> str:
    lines = text.splitlines()
    idx = next(i for i, line in enumerate(lines) if line.startswith("export default"))
    return "\n".join(lines[idx:]).rstrip() + "\n"


def const_part_existing(path: pathlib.Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    const_lines = [l for l in lines if l.startswith("const ")]
    return "\n".join(const_lines).rstrip() + "\n"


def main() -> None:
    for out_name, raw_name in FILES.items():
        stripped = strip_content((BASE / raw_name).read_text(encoding="utf-8"))
        if "SUPER CRITICAL" in stripped:
            raise SystemExit(f"strip failed: {out_name}")
        const_block = const_part_existing(BASE / out_name)
        fn_block = function_part(stripped)
        if "export default" not in fn_block:
            raise SystemExit(f"no export in fn: {out_name}")
        content = const_block + "\n" + fn_block
        (BASE / out_name).write_text(content, encoding="utf-8")
        print(f"wrote {out_name} size {(BASE / out_name).stat().st_size}")


if __name__ == "__main__":
    main()
