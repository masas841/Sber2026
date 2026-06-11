#!/usr/bin/env python3
"""Генерирует layouts/*.json из координат Figma JSX (672×672)."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "web" / "assets" / "figma" / "layouts"

SHARED = {
    "logo": "dd849ce3e75e01bc98af7d108143446b11e5b96c.svg",
    "bg_start": "eeb09f2d809e30f9e9d5007b9ceecd44d294b462.svg",
    "bg_onb": "4a4721b9a290a272c96378fff4c00989caad9a80.svg",
    "bg_game": "bd338f5b9b0f56d0bb2cc179fb704abde6cb4956.svg",
    "bg_result": "ef20563d31b1b29159550b8fce4618ea743d9ce9.svg",
    "bg_onb3": "c3f209aa64898f1563b9907e96061277c9034904.svg",
    "grass": "1563697d12155680b73c4d623f05f35318b669a6.png",
    "grass_b": "488b182ee2274bda0e42f0406d131ba5de756d0c.png",
    "grass_c": "199c5ba01a61e6cc478ed13de37575b68e5c4776.png",
    "haze": "74d233acd9ce731dee934ef8f8f2bc708144831b.svg",
    "piggy": "ba682dc3889044076820b4f23216dee0a7394771.png",
    "coin": "7cc85e02203da4dade7c18c7254748004b55a994.png",
    "folder": "9c7a52cb0aaebeae10b7379074ad3d6c045c76aa.png",
    "percent": "6d99ba2c1032d9f030f1c9c467ca810c4b25ca62.png",
    "ingot": "21d6bfc9e1e9691021c27e978b057a688e8e32d4.png",
    "trophy": "ad29bb4cc2685b5f9f095888a406efdf1b230267.png",
    "piggy2": "4cb639982a36e9bf5c2aef2c4dbbbfa2831249b3.png",
    "confetti": "fda304959692ab205391cde62c578889f6a6e95d.svg",
    "error_bg": "a323defe5446b134ade9b820d7a5de36e7964b4d.png",
    "ghost_bag": "aa1388805711ad232ced85bc3af05b4dfc2781a6.png",
    "ghost_arrow": "6112e0a30c946f6fd77daed575d1232516cbd114.png",
    "ghost_fomo": "6efb1b5ba282d7b4bbc5f93a8dbe9bfa74283474.png",
    "piggy_front": "25368a0cb54c2145216ed431d5940cbb1767209d.png",
    "squiggle": "f6ea418e105ffb53210064f86e2c3f7a672f8b0e.svg",
    "star": "ec4ff578e09eb81b02098e81b97a174d5fbb8b1b.svg",
    "shadow1": "a40e0eedcff9764cd702a875f13d87d08e61f2a9.svg",
    "shadow2": "9f73fc3a561e0d7cd8e8ac1508128ea9a7c3f9fb.svg",
    "shadow3": "e91cb2d5c1e875eac227ebd44377c931e4499406.svg",
}


def L(file, x, y, w, h, rot=0, ox=0, oy=0):
    if rot and ox == 0 and oy == 0:
        ox = oy = 0.5
        x, y = x + w / 2, y + h / 2
    return {"file": SHARED.get(file, file), "x": x, "y": y, "w": w, "h": h, "rot": rot, "ox": ox, "oy": oy}


def Lc(file, cx, cy, w, h, rot=0):
    """Слой с центром в (cx, cy)."""
    return L(file, cx - w / 2, cy - h / 2, w, h, rot=rot, ox=0.5, oy=0.5)


def T(text, x, y, size, color="#122654", ox=0.5, bold=False, width=None, dynamic=None):
    d = {"text": text, "x": x, "y": y, "size": size, "color": color, "ox": ox, "bold": bold}
    if width:
        d["width"] = width
    if dynamic:
        d["dynamic"] = dynamic
    return d


LAYOUTS = {
    "start": {
        "bgDecor": SHARED["bg_start"],
        "layers": [
            L("bg_start", -48, -134, 727, 882),
            L("grass_b", -284, 244, 899, 502),
            L("grass_c", -284, 244, 899, 502),
            L("haze", -25, 466, 428, 329),
            Lc("grass", 452, 672, 529, 793, rot=157.6),
            L("shadow1", 356, 504, 201, 106),
            L("shadow2", 356, 521, 201, 65),
            L("shadow3", 356, 530, 201, 46),
            Lc("piggy", 418, 421, 346, 346, rot=-172.9),
            Lc("squiggle", 534, 274, 120, 112, rot=82.9),
            Lc("star", 166, 454, 122, 122, rot=-23.1),
            Lc("logo", 336, 74, 258, 25),
        ],
        "texts": [
            T("ИнвестКопилка", 336, 111, 35.5, "#ff64a2", bold=True, width=392),
            T("против", 336, 138, 18, width=199),
            T("монстров-расходов", 336, 150, 35.5, bold=True, width=392),
            T("играть", 336, 582, 37, "#ffffff", bold=True),
        ],
        "hintY": 0.97,
    },
    "onboarding_1": {
        "bgDecor": SHARED["bg_onb"],
        "layers": [
            L("bg_onb", -49, -134, 728, 882),
            Lc("grass", 338, 619, 740, 1110, rot=157.6),
            Lc("folder", 389, 254, 434, 434, rot=31.9),
            Lc("piggy", 204, 336, 376, 376, rot=-23.5),
            Lc("percent", 430, 480, 534, 356, rot=14.6),
            Lc("ingot", 237, 544, 222, 222, rot=165.3),
            Lc("coin", 153, 566, 269, 269, rot=-10.4),
            Lc("coin", 502, 221, 135, 135, rot=102),
            Lc("logo", 336, 74, 258, 25),
        ],
        "texts": [
            T("Собирай капитал", 336, 119, 32.4, bold=True),
            T("Управляй ИнвестКопилкой на экране,\nлови монеты, проценты и активы СберИнвестиций.", 343, 153, 15, width=337),
        ],
    },
    "onboarding_2": {
        "bgDecor": SHARED["bg_game"],
        "layers": [
            L("bg_game", -49, -134, 728, 882),
            Lc("grass", 303, 677, 848, 1272, rot=157.6),
            Lc("ghost_arrow", 386, 329, 363, 356, rot=8.8),
            Lc("ghost_bag", 117, 128, 489, 448, rot=-7.6),
            L("ghost_fomo", 127, 363, 495, 453),
            Lc("logo", 336, 74, 258, 25),
        ],
        "texts": [
            T("Уворачивайся\nот препятствий", 336, 119, 32.4, bold=True),
            T("Импульсивные покупки, инфляция\nи фомо работают против капитала.", 331, 177, 15, width=304),
        ],
    },
    "onboarding_3": {
        "bgDecor": SHARED["bg_onb3"],
        "layers": [
            L("bg_onb3", -49, -134, 728, 882),
            Lc("grass", 338, 619, 740, 1110, rot=157.6),
            Lc("piggy2", 230, 376, 328, 328, rot=-14.8),
            Lc("trophy", 403, 453, 378, 411, rot=17.1),
            Lc("coin", 127, 217, 158, 158, rot=-10.4),
            Lc("coin", 499, 75, 158, 158, rot=102),
            Lc("logo", 336, 74, 258, 25),
        ],
        "texts": [
            T("Ворвись в топ", 336, 127, 32.4, bold=True),
            T("Продержись 1 минуту, набери максимальный\nсчет и займи первое место в инвест-таблице дня.", 336, 161, 15, width=362),
        ],
    },
    "error": {
        "bgDecor": SHARED["bg_start"],
        "layers": [
            L("bg_start", -48, -134, 727, 882),
            L("haze", -25, 466, 428, 329),
            L("error_bg", -15, -134, 1058, 1058),
            L("coin", 78, 228, 172, 172, rot=4.7),
            L("logo", 336, 61, 258, 25, ox=0.5),
        ],
        "texts": [
            T("инвестКопилка ребалансирует портфель", 336, 103, 35.5, "#ff64a2", bold=True, width=392),
            T("Скоро можно будет снова собирать активы.", 336, 206, 17.2, width=280),
        ],
    },
    "result_score": {
        "bgDecor": SHARED["bg_result"],
        "layers": [
            L("bg_result", -70, -114, 728, 883),
            L("grass_b", 33, 137, 968, 541, rot=-171.7),
            L("grass_c", 33, 137, 968, 541, rot=-171.7),
            L("haze", 270, 458, 428, 329),
            L("grass", -267, 169, 628, 941, rot=157.6),
            L("piggy_front", 80, 310, 281, 281, rot=-8.4),
            L("trophy", 164, 336, 310, 253, rot=24.4),
            L("logo", 336, 61, 258, 25, ox=0.5),
        ],
        "texts": [
            T("счёт:", 333, 141, 21.4, "#01d701", bold=True),
            T("000", 333, 162, 49.3, bold=True, dynamic="score"),
        ],
    },
    "result_record": {
        "bgDecor": SHARED["bg_result"],
        "layers": [
            L("bg_result", -70, -114, 728, 883),
            L("grass_b", 33, 137, 968, 541, rot=-171.7),
            L("piggy_front", 80, 310, 281, 281, rot=-8.4),
            L("trophy", 164, 336, 310, 253, rot=24.4),
            L("logo", 336, 61, 258, 25, ox=0.5),
        ],
        "texts": [
            T("Новый рекорд!", 336, 100, 32, "#ff64a2", bold=True),
            T("счёт:", 333, 141, 21.4, "#01d701", bold=True),
            T("000", 333, 162, 49.3, bold=True, dynamic="score"),
        ],
    },
    "leaderboard": {
        "bgDecor": SHARED["bg_result"],
        "layers": [
            L("confetti", 80, 16, 482, 348),
            L("bg_result", -70, -114, 728, 883),
            L("grass_b", -319, 245, 1256, 701, rot=-171.7),
            L("grass_c", -319, 245, 1256, 701, rot=-171.7),
            L("logo", 336, 61, 258, 25, ox=0.5),
        ],
        "texts": [
            T("Ворвись в топ", 336, 127, 32.4, bold=True),
        ],
        "leaderboard": {
            "panelX": 154,
            "panelY": 206,
            "panelW": 364,
            "panelH": 405,
            "rowH": 45.5,
            "nameX": 185,
            "scoreX": 460,
            "firstY": 206,
            "nameColor": "#01d701",
            "scoreColor": "#122654",
            "size": 22.9,
            "currentColor": "#122654",
        },
    },
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, layout in LAYOUTS.items():
        data = {"id": name, "size": [672, 672], **layout}
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote", path.name)


if __name__ == "__main__":
    main()
