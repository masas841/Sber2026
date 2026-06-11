"""
Восстановление figma-screens/*.html из чистого Figma-экспорта _context/*.txt.
Текст в html был повреждён двойной перекодировкой (mojibake + потеря данных),
поэтому JSX-тело берём заново из context, а head/обёртку — из текущего html.
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = os.path.join(ROOT, "web", "figma-screens")
CTX = os.path.join(ROOT, "web", "assets", "figma", "_context")
SHARED = "/static/assets/figma/shared/"
LOCALHOST = "http://localhost:3845/assets/"

RENDER_TAIL = (
    "\n\nconst root = ReactDOM.createRoot(document.getElementById('root'));\n"
    "root.render(React.createElement(Screen));\n"
    "  </script>\n</body>\n</html>\n"
)


def survey():
    html_pref, ctx_pref = {}, {}
    for p in glob.glob(os.path.join(SCREENS, "*.html")):
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in re.findall(r'"(/static/assets/[^"]+?/)[0-9a-f]{6}', t):
            html_pref[m] = html_pref.get(m, 0) + 1
    for p in glob.glob(os.path.join(CTX, "*.txt")):
        t = open(p, encoding="utf-8").read()
        for m in re.findall(r'"(http://localhost:3845/[^"]+?/)', t):
            ctx_pref[m] = ctx_pref.get(m, 0) + 1
    print("HTML asset prefixes:")
    for k, v in html_pref.items():
        print("  ", k, v)
    print("Context asset prefixes:")
    for k, v in ctx_pref.items():
        print("  ", k, v)


def rebuild():
    fixed = []
    for html_path in glob.glob(os.path.join(SCREENS, "*.html")):
        name = os.path.basename(html_path)[:-5]
        ctx_path = os.path.join(CTX, name + ".txt")
        if not os.path.exists(ctx_path):
            print("skip (no context):", name)
            continue

        html = open(html_path, encoding="utf-8", errors="replace").read()
        ctx = open(ctx_path, encoding="utf-8").read()

        m = re.search(r'(<script type="text/babel"[^>]*>)', html)
        if not m:
            print("skip (no babel tag):", name)
            continue
        head = html[: m.end()]

        body = ctx.replace(LOCALHOST, SHARED)
        body = re.sub(r"export\s+default\s+function\s+\w+\s*\(", "function Screen(", body, count=1)
        body = body.rstrip()

        new = head + "\n" + body + RENDER_TAIL
        with open(html_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        fixed.append(name)
        print("rebuilt:", name)
    print("done:", len(fixed))


if __name__ == "__main__":
    survey()
    print("-" * 40)
    rebuild()
