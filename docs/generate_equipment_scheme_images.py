# -*- coding: utf-8 -*-
"""Generate PNG equipment connection schemes from the updated customer TZ."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent / "equipment-schemes"

W, H = 1800, 1100
BG = "#f4fbfb"
INK = "#18354a"
MUTED = "#5e7180"
GREEN = "#21A038"
PINK = "#FF5CAB"
BLUE = "#5ECFFF"
YELLOW = "#FFD54F"
CARD = "#FFFFFF"
LINE = "#2E6F88"
WARN = "#FF8A00"

PAD = 20
ICON_W = 72


def normalize(text: str) -> str:
    """Replace typographic symbols that often fail in Arial on Windows."""
    repl = {
        "\u00d7": "x",
        "\u00b7": " ",
        "\u2022": "-",
        "\u2011": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00ab": '"',
        "\u00bb": '"',
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u202f": " ",
        "\u2009": " ",
        "\u200b": "",
        "\u00ad": "",
        "\u0451": "\u0435",  # ё -> е
        "\u0401": "\u0415",
    }
    for old, new in repl.items():
        text = text.replace(old, new)
    return text.strip()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


F_TITLE = font(46, True)
F_SUB = font(24)
F_BOX = font(26, True)
F_TEXT = font(21)
F_SMALL = font(18)
F_TAG = font(17, True)


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt) -> int:
    return int(draw.textbbox((0, 0), text, font=fnt)[2])


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    text = normalize(text)
    out: list[str] = []
    for paragraph in re.split(r"\n+", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        words = re.split(r"(\s+|-)", paragraph)
        current = ""
        for part in words:
            if not part:
                continue
            trial = current + part
            if text_width(draw, trial, fnt) <= max_width or not current:
                current = trial
            else:
                if current.strip():
                    out.append(current.strip())
                current = part.strip()
        if current.strip():
            out.append(current.strip())
    return out or [""]


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    text: str,
    fnt,
    fill: str,
    line_spacing: int = 6,
) -> int:
    """Draw wrapped text; return bottom y."""
    lines = wrap_lines(draw, text, fnt, w)
    yy = y
    for line in lines:
        draw.text((x, yy), line, font=fnt, fill=fill)
        yy += int(draw.textbbox((0, 0), "Ay", font=fnt)[3]) + line_spacing
    return yy


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=LINE, width=3, radius=24):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(draw: ImageDraw.ImageDraw, xy, text, fnt, fill=INK, spacing=5):
    x, y = xy
    lines = wrap_lines(draw, text, fnt, 200)
    heights = [int(draw.textbbox((0, 0), line, font=fnt)[3]) for line in lines]
    total_h = sum(heights) + spacing * max(0, len(lines) - 1)
    yy = y - total_h / 2
    for line, hh in zip(lines, heights):
        ww = text_width(draw, line, fnt)
        draw.text((x - ww / 2, yy), line, font=fnt, fill=fill)
        yy += hh + spacing


def label(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str, fill=INK, max_w: int = 130):
    """Подпись на линии: центр (cx, cy), текст с переносом в рамке."""
    text = normalize(text)
    if not text:
        return
    lines = wrap_lines(draw, text, F_SMALL, max_w)
    line_h = int(draw.textbbox((0, 0), "Ay", font=F_SMALL)[3])
    pad = 6
    lw = max(text_width(draw, ln, F_SMALL) for ln in lines)
    box_w = lw + pad * 2
    box_h = line_h * len(lines) + pad * 2 + max(0, len(lines) - 1) * 2
    x = int(cx - box_w / 2)
    y = int(cy - box_h / 2)
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=10, fill="#ffffffee", outline="#b8dfe6", width=1)
    yy = y + pad
    for line in lines:
        draw.text((x + (box_w - text_width(draw, line, F_SMALL)) // 2, yy), line, font=F_SMALL, fill=fill)
        yy += line_h + 2


def arrow(draw: ImageDraw.ImageDraw, start, end, text="", color=LINE, width=5, label_t: float = 0.5):
    draw.line([start, end], fill=color, width=width)
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 16
    tip = (ex, ey)
    p1 = (ex - ux * size + px * size * 0.55, ey - uy * size + py * size * 0.55)
    p2 = (ex - ux * size - px * size * 0.55, ey - uy * size - py * size * 0.55)
    draw.polygon([tip, p1, p2], fill=color)
    if text:
        lx = sx + dx * label_t
        ly = sy + dy * label_t
        px, py = -uy, ux
        label(draw, int(lx + px * 30), int(ly + py * 30), text, color)


def dashed_arrow(draw, start, end, text="", color=PINK, width=4, label_t: float = 0.5):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    steps = 16
    for i in range(steps):
        if i % 2 == 0:
            a, b = i / steps, (i + 1) / steps
            draw.line(
                [(sx + dx * a, sy + dy * a), (sx + dx * b, sy + dy * b)],
                fill=color,
                width=width,
            )
    arrow(draw, (ex - dx * 0.06, ey - dy * 0.06), (ex, ey), "", color, width)
    if text:
        length = max((dx * dx + dy * dy) ** 0.5, 1)
        ux, uy = dx / length, dy / length
        lx = sx + dx * label_t
        ly = sy + dy * label_t
        px, py = -uy, ux
        label(draw, int(lx + px * 30), int(ly + py * 30), text, color)


def base(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    title = normalize(title)
    subtitle = normalize(subtitle)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.ellipse((-250, -220, 650, 400), fill="#D4F7DD")
    draw.ellipse((1180, -140, 2050, 470), fill="#DDF7FF")
    draw.ellipse((420, 860, 1420, 1250), fill="#FFE1F0")
    draw.text((70, 48), title, font=F_TITLE, fill=INK)
    sub_bottom = draw_wrapped(draw, 74, 108, W - 148, subtitle, F_SUB, MUTED, 8)
    draw.line((70, max(sub_bottom + 12, 168), 1730, max(sub_bottom + 12, 168)), fill=GREEN, width=4)
    return img, draw


def _line_height(draw, fnt) -> int:
    return int(draw.textbbox((0, 0), "Ay", font=fnt)[3])


def _content_height(draw, title_lines, body_lines, title_font, body_font, body_gap: int) -> int:
    h = 0
    for line in title_lines:
        h += _line_height(draw, title_font) + 4
    if body_lines:
        h += body_gap + sum(_line_height(draw, body_font) + 5 for _ in body_lines)
    return h


def box(draw, x, y, w, h, title, body="", fill=CARD, outline=LINE, icon=None):
    title = normalize(title)
    body = normalize(body)
    rounded(draw, (x, y, x + w, y + h), fill=fill, outline=outline)

    text_x = x + PAD
    text_w = w - PAD * 2
    icon_h = 0
    if icon:
        icon_h = 36 + 8
        draw.rounded_rectangle(
            (x + PAD, y + PAD, x + PAD + ICON_W, y + PAD + 36),
            radius=10,
            fill="#ffffff",
            outline=outline,
            width=2,
        )
        text_center(draw, (x + PAD + ICON_W // 2, y + PAD + 18), icon, F_TAG, outline)
        text_x = x + PAD + ICON_W + 10
        text_w = w - (text_x - x) - PAD

    title_font = F_BOX
    title_lines = wrap_lines(draw, title, title_font, text_w)
    if len(title_lines) > 2:
        title_font = font(22, True)
        title_lines = wrap_lines(draw, title, title_font, text_w)

    body_size = 21
    body_font = F_TEXT
    body_lines = wrap_lines(draw, body, body_font, text_w) if body else []
    inner_h = h - PAD * 2 - icon_h
    while body_lines and _content_height(draw, title_lines, body_lines, title_font, body_font, 6) > inner_h and body_size > 16:
        body_size -= 2
        body_font = font(body_size)
        body_lines = wrap_lines(draw, body, body_font, text_w)
    if not body and len(title_lines) > 2 and _content_height(draw, title_lines, [], title_font, body_font, 0) > inner_h:
        title_font = font(20, True)
        title_lines = wrap_lines(draw, title, title_font, text_w)

    def draw_title_block(start_y: int, center_in_full_box: bool):
        block_h = sum(_line_height(draw, title_font) + 4 for _ in title_lines) - 4
        yy = start_y
        if not body_lines and len(title_lines) > 1:
            yy = start_y + max(0, (inner_h - block_h) // 2)
        for line in title_lines:
            if center_in_full_box:
                tw = text_width(draw, line, title_font)
                draw.text((x + (w - tw) // 2, yy), line, font=title_font, fill=INK)
            else:
                tw = text_width(draw, line, title_font)
                draw.text((text_x + (text_w - tw) // 2, yy), line, font=title_font, fill=INK)
            yy += _line_height(draw, title_font) + 4
        return yy

    yy0 = y + PAD + icon_h
    if body_lines:
        yy = yy0
        for line in title_lines:
            draw.text((text_x, yy), line, font=title_font, fill=INK)
            yy += _line_height(draw, title_font) + 4
        yy += 6
        for line in body_lines:
            draw.text((text_x, yy), line, font=body_font, fill=MUTED)
            yy += _line_height(draw, body_font) + 5
    elif len(title_lines) == 1 and not icon_h:
        line = title_lines[0]
        tw = text_width(draw, line, title_font)
        th = _line_height(draw, title_font)
        draw.text((x + (w - tw) // 2, y + (h - th) // 2), line, font=title_font, fill=INK)
    elif icon_h:
        draw_title_block(yy0, center_in_full_box=False)
    else:
        draw_title_block(y + PAD, center_in_full_box=True)


def footer(draw, notes: list[str]):
    notes = [normalize(n) for n in notes]
    note_w = 1330
    lines: list[str] = []
    for note in notes:
        lines.extend(wrap_lines(draw, "- " + note, F_SMALL, note_w))
    box_h = max(74, 28 + len(lines) * 22)
    top = 1048 - box_h
    rounded(draw, (70, top, 1730, 1048), radius=20, fill="#ffffffee", outline="#b8dfe6")
    draw.text((95, top + 14), "Монтажные примечания:", font=F_TAG, fill=INK)
    yy = top + 14
    for line in lines:
        draw.text((360, yy), line, font=F_SMALL, fill=MUTED)
        yy += 22


def save(img: Image.Image, filename: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / filename)


def gigavibe():
    img, d = base(
        "1. ГИГАвайб - схема подключения",
        "ATX 600x400x200 | LED в габаритах зоны | загрузка в интернет | QR на телефон",
    )
    box(d, 640, 355, 520, 250, "Системный блок ATX", "Генерация ролика\nChrome kiosk\nПитание до 1200 Вт", fill="#F7FFF5", outline=GREEN, icon="PC")
    box(d, 640, 215, 520, 118, "LED экран зоны", "В габаритах зоны\n9:16, превью и QR", fill="#E8FAFF", outline=BLUE)
    box(d, 110, 355, 400, 185, "USB-камера", "Съемка гостя по улыбке\nУровень лица", icon="CAM")
    box(d, 1270, 355, 400, 195, "Интернет / хостинг", "ПК загружает ролик\nссылка в QR", outline=PINK, icon="WEB")
    box(d, 1270, 615, 400, 165, "Смартфон гостя", "Мобильный интернет\nQR -> скачивание", outline=PINK, icon="QR")
    box(d, 110, 640, 400, 150, "Свет зоны", "Ровный свет на лицо\nБез жестких теней", outline=YELLOW, icon="LUX")
    box(d, 640, 640, 520, 160, "ИБП / 220 В", "Отдельная линия\nпитания", fill="#FFF8E1", outline=WARN, icon="220")
    arrow(d, (900, 355), (900, 320), "HDMI", BLUE, label_t=0.42)
    arrow(d, (510, 445), (640, 445), "USB", GREEN)
    dashed_arrow(d, (1160, 445), (1270, 445), "HTTPS", PINK)
    dashed_arrow(d, (1470, 600), (1470, 550), "LTE/5G", PINK)
    dashed_arrow(d, (1470, 615), (1270, 480), "QR", PINK, label_t=0.35)
    arrow(d, (900, 655), (900, 600), "220 В", WARN, label_t=0.55)
    footer(d, ["LED в габаритах зоны", "ПК выгружает ролик в интернет", "гость: QR и моб. интернет"])
    save(img, "01-gigavibe-equipment-scheme.png")


def chill():
    img, d = base(
        "2. Чилл-страховка - схема подключения",
        "Ноутбук 200 Вт | LED в габаритах зоны | Bluetooth-джойстик / тач",
    )
    box(d, 650, 365, 520, 225, "Ноутбук", "Игра fullscreen\nПитание до 200 Вт\nBluetooth включен", fill="#F7FFF5", outline=GREEN, icon="LAP")
    box(d, 650, 215, 520, 118, "LED экран зоны", "В габаритах зоны\n16:9, игра", fill="#E8FAFF", outline=BLUE)
    box(d, 110, 365, 420, 175, "Bluetooth-джойстик", "Прицел и выстрел\nКнопка Start", outline=PINK, icon="BT")
    box(d, 1280, 365, 420, 175, "Тач-управление", "Опционально:\nсенсорный экран", outline=PINK, icon="TOUCH")
    box(d, 650, 665, 520, 160, "Питание 220 В", "Питание ноутбука\nи LED экрана", fill="#FFF8E1", outline=WARN, icon="220")
    dashed_arrow(d, (530, 450), (650, 450), "Bluetooth", PINK)
    dashed_arrow(d, (1280, 450), (1170, 450), "USB touch", PINK)
    arrow(d, (910, 365), (910, 320), "HDMI", BLUE, label_t=0.42)
    arrow(d, (910, 670), (910, 590), "220 В", WARN, label_t=0.55)
    footer(d, ["LED в габаритах зоны", "джойстик спарить заранее", "интернет не нужен"])
    save(img, "02-chill-strahovka-equipment-scheme.png")


def kopilka():
    img, d = base(
        "3. СберКопилка - схема подключения",
        "Ноутбук 200 Вт | LED в габаритах зоны | Bluetooth-джойстик",
    )
    box(d, 650, 365, 520, 225, "Ноутбук", "Pac-Man аркада\nЛокальный топ дня\nПитание до 200 Вт", fill="#F7FFF5", outline=GREEN, icon="LAP")
    box(d, 650, 215, 520, 118, "LED экран зоны", "В габаритах зоны\nлабиринт, топ", fill="#E8FAFF", outline=BLUE)
    box(d, 110, 355, 420, 190, "Bluetooth-джойстик", "Стик / крестовина\nCross - старт", outline=PINK, icon="BT")
    box(d, 110, 640, 420, 155, "Резерв: клавиатура", "Только настройка\nи сервис", outline="#B8DFE6", icon="KEY")
    box(d, 1280, 365, 420, 175, "Без интернета", "Рейтинг хранится\nна ноутбуке", fill="#FFFFFF", outline=GREEN, icon="LOCAL")
    box(d, 650, 665, 520, 160, "Питание 220 В", "Питание ноутбука\nи LED экрана", fill="#FFF8E1", outline=WARN, icon="220")
    dashed_arrow(d, (530, 450), (650, 450), "Bluetooth", PINK)
    arrow(d, (910, 365), (910, 320), "HDMI", BLUE, label_t=0.42)
    arrow(d, (910, 670), (910, 590), "220 В", WARN, label_t=0.55)
    dashed_arrow(d, (530, 715), (650, 560), "USB опц.", "#B8DFE6", width=3)
    footer(d, ["LED в габаритах зоны", "джойстик спарить до открытия", "топ дня локально"])
    save(img, "03-sberkopilka-equipment-scheme.png")


def smile():
    img, d = base(
        "4. Улыбкометр - схема подключения",
        "Ноутбук 200 Вт | LED в габаритах зоны | загрузка в интернет | QR",
    )
    box(d, 650, 365, 520, 225, "Ноутбук", "Оценка улыбки\nЗагрузка в интернет\nПитание до 200 Вт", fill="#F7FFF5", outline=GREEN, icon="LAP")
    box(d, 650, 215, 520, 118, "LED экран зоны", "В габаритах зоны\nшкала и QR", fill="#E8FAFF", outline=BLUE)
    box(d, 110, 365, 400, 175, "USB-камера", "Live preview\nОценка 3 сек.", outline=GREEN, icon="CAM")
    box(d, 1280, 365, 420, 195, "Интернет / хостинг", "ПК загружает улыбку\nссылка в QR", outline=PINK, icon="WEB")
    box(d, 1280, 615, 420, 165, "Смартфон гостя", "Мобильный интернет\nQR -> картинка", outline=PINK, icon="QR")
    box(d, 110, 640, 400, 150, "Свет зоны", "Ровный свет\nна лицо", outline=YELLOW, icon="LUX")
    box(d, 650, 660, 520, 175, "Питание 220 В", "Питание ноутбука\nи LED экрана", fill="#FFF8E1", outline=WARN, icon="220")
    arrow(d, (510, 450), (650, 450), "USB", GREEN)
    arrow(d, (910, 365), (910, 320), "HDMI", BLUE, label_t=0.42)
    dashed_arrow(d, (1170, 450), (1280, 450), "HTTPS", PINK)
    dashed_arrow(d, (1490, 600), (1490, 550), "LTE/5G", PINK)
    dashed_arrow(d, (1490, 615), (1300, 480), "QR", PINK, label_t=0.35)
    arrow(d, (910, 670), (910, 590), "220 В", WARN, label_t=0.55)
    footer(d, ["LED в габаритах зоны", "ПК выгружает в интернет", "гость: QR и моб. интернет"])
    save(img, "04-ulybkometr-equipment-scheme.png")


def overview():
    img, d = base(
        "Общая схема подключения павильона",
        "4 стенда | LED в габаритах зоны | QR через интернет и моб. связь гостя",
    )
    y = 255
    rows = [
        ("ГИГАвайб", "ATX блок\n1200 Вт", "LED в зоне\n+ камера", "интернет\nQR моб."),
        ("Чилл-страховка", "Ноутбук\n200 Вт", "LED в зоне", "BT / тач"),
        ("СберКопилка", "Ноутбук\n200 Вт", "LED в зоне", "BT джойстик"),
        ("Улыбкометр", "Ноутбук\n200 Вт", "LED в зоне\n+ камера", "интернет\nQR моб."),
    ]
    for i, (name, src, screen, io) in enumerate(rows):
        yy = y + i * 168
        box(d, 90, yy, 340, 118, name, "", fill="#ffffff", outline=PINK)
        box(d, 500, yy, 340, 118, src, "", fill="#F7FFF5", outline=GREEN)
        box(d, 910, yy, 340, 118, screen, "", fill="#E8FAFF", outline=BLUE)
        box(d, 1310, yy, 390, 118, io, "", fill="#FFFFFF", outline=LINE)
        arrow(d, (430, yy + 59), (500, yy + 59), "", GREEN, 4)
        arrow(d, (840, yy + 59), (910, yy + 59), "HDMI", BLUE, 4)
        dashed_arrow(d, (1320, yy + 59), (1240, yy + 59), "ввод", PINK, 3)
    footer(d, ["LED в габаритах каждой зоны", "ГИГАвайб и Улыбкометр: выгрузка в интернет", "гость скачивает по QR с моб. интернетом"])
    save(img, "00-overview-equipment-scheme.png")


if __name__ == "__main__":
    overview()
    gigavibe()
    chill()
    kopilka()
    smile()
    print(f"Saved images to {OUT_DIR}")
