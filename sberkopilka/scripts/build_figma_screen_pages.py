#!/usr/bin/env python3
"""Генерирует web/figma-screens/*.html из _context/*.txt (React+Tailwind CDN → 672×672)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "web" / "assets" / "figma" / "_context"
OUT = ROOT / "web" / "figma-screens"
SHARED = "/static/assets/figma/shared"

LEADERBOARD_HIDDEN_NODES = [
    "25:2224",
    "25:2226", "25:2227", "25:2229", "25:2230",
    "25:2232", "25:2233", "25:2235", "25:2236",
    "25:2238", "25:2239", "25:2241", "25:2242",
    "25:2244", "25:2245", "25:2247", "25:2248",
]


def leaderboard_hidden_css() -> str:
    rules = []
    for node_id in LEADERBOARD_HIDDEN_NODES:
        rules.append(
            f'[data-node-id="{node_id}"],[data-node-id="{node_id}"] *'
        )
    return ",\n    ".join(rules) + " {\n      display: none !important;\n      visibility: hidden !important;\n    }"

SCREENS = [
    "start",
    "onboarding_1",
    "onboarding_2",
    "onboarding_3",
    "error",
    "result_score",
    "result_record",
    "leaderboard",
    "game",
    "game-bg",
]

URL_RE = re.compile(
    r'"http://localhost:3845/assets/([a-f0-9]+)\.(png|svg|jpg|jpeg)"',
    re.I,
)


def fix_assets(code: str) -> str:
    return URL_RE.sub(
        lambda m: f'"{SHARED}/{m.group(1)}.{m.group(2).lower()}"',
        code,
    )


def strip_export(code: str) -> str:
    code = re.sub(r"export\s+default\s+function\s+\w+\s*\(\)\s*\{", "function Screen() {", code)
    code = re.sub(r"export\s+default\s+function\s+\w+\s*\{", "function Screen() {", code)
    return code


FONT_CLASS_MAP = {
    "font-['SB_Sans_Display_BETA2:Extended_Semibold']": "kop-font-display",
    'font-["SB_Sans_Display_BETA2:Extended_Semibold"]': "kop-font-display",
    "font-['SB_Sans_Text:Medium']": "kop-font-text-medium",
    'font-["SB_Sans_Text:Medium"]': "kop-font-text-medium",
    "font-['SB_Sans_Text:Semibold']": "kop-font-text-semibold",
    'font-["SB_Sans_Text:Semibold"]': "kop-font-text-semibold",
}


def normalize_figma_code(code: str) -> str:
    for old, new in FONT_CLASS_MAP.items():
        code = code.replace(old, new)
    code = code.replace("opacity-31", "opacity-[0.31]")
    return code


def wrap_page(component_js: str, title: str) -> str:
    lb_hidden = ""
    if title == "leaderboard":
        lb_hidden = f"\n    {leaderboard_hidden_css()}"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <script src="/static/vendor/tailwindcdn.min.js"></script>
  <script>
    tailwind.config = {{
      theme: {{ extend: {{}} }}
    }};
  </script>
  <link rel="stylesheet" href="/static/css/figma-fonts.css" />
  <link rel="stylesheet" href="/static/css/figma-animations.css?v=2" />
  <style>
    html, body {{ margin: 0; padding: 0; background: linear-gradient(180deg, #ecfffe 0%, #9effa8 100%); }}
    #capture {{
      width: 672px;
      height: 672px;
      overflow: hidden;
      position: relative;
    }}{lb_hidden}
  </style>
</head>
<body>
  <div id="capture"><div id="root" class="w-[672px] h-[672px]"></div></div>
  <script src="/static/js/figma-screen-boot.js"></script>
  <script crossorigin src="/static/vendor/react.production.min.js"></script>
  <script crossorigin src="/static/vendor/react-dom.production.min.js"></script>
  <script src="/static/vendor/babel.min.js"></script>
  <script type="text/babel" data-presets="react">
{component_js}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(Screen));
  </script>
</body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in SCREENS:
        src = CTX / f"{name}.txt"
        if not src.exists() or "export default" not in src.read_text(encoding="utf-8", errors="replace"):
            print(f"skip {name}: no JSX")
            continue
        raw = src.read_text(encoding="utf-8", errors="replace")
        code = normalize_figma_code(strip_export(fix_assets(raw)))
        html = wrap_page(code, name)
        out = OUT / f"{name}.html"
        out.write_text(html, encoding="utf-8")
        print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
