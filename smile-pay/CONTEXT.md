# Smile Pay — контекст проекта (обновлено 2026-06-09, сессия 3)

Отдельный интерактив **«Улыбка»** (оплата улыбкой). **Не связан с gigavibe** — все изменения только в `smile-pay/`.

## Макет Figma

- Секция: **«Улыбка»** `128:109` (выбранный пользователем обновлённый дизайн)
- Виджет: **круг 504×504** (обрезка в `.shell`)
- Кадры 1/4/5 в макете **515×515** → при рендере масштаб **S = 504/515 ≈ 0.978641**
- **Источник координат**: Figma metadata (absolute bbox), не flex-обёртки get_design_context

| Стадия (код) | Figma frame | node-id | Содержимое |
|--------------|-------------|---------|------------|
| `idle` | Frame 3 | `127:513` | MasterGradient + декор + pill «Такой улыбкой… (узнай что)», камера скрыта |
| `face` | Frame 4 | `127:567` | Subtract-кольцо + камера + text-path + 3 звезды |
| `line` | Frame 1 | `25:2498` | Оба text-path, смещённые стикеры, **10 с** |
| `stickers` | Frame 5 | `127:597` | Полный набор стикеров (обновлённые позиции) |
| `qr` | Frame 6 | `127:713` | MasterGradient + карточка QR **258×321** + caption + декор |

## Live-флоу

1. **idle** — зелёный градиент, камера **активна**, но **скрыта** (clip-path = 0)
2. **face** — лицо ≥ ~18% кадра → Subtract + text-path frame4
3. **line** — улыбка (~650 ms) → снимок → раскрытие нижнего лайна → **10 с**
4. **stickers** — каскад стикеров
5. **qr** — диссолв → QR + «Подключить оплату улыбкой» → возврат в idle

Тайминги: `PRESENCE { minFaceSize: 0.18, holdMs: 450 }`, `SMILE.holdMs: 650`,
`STAGE_TIMING { line: 10000, stickers: 2400, qr: 5000 }`.

## Архитектура слоёв

`.shell` (круг, overflow:hidden):
- `.camera-slot` — `<video>`, clip circle(0) → ellipse на cam-open
- `.stage-root` → `.smile-stage` (прозрачный)

Внутри `.smile-stage`:
- `.smile-stage__field` — зелёное поле + прорез камеры на cam-open
- `.smile-stage__master` — MasterGradientWhite (idle/qr)
- `.smile-stage__subtract-wrap` — кольцо (face/line)
- `.smile-stage__decor-layer`, `.smile-stage__copy`, `.smile-stage__qr-slot`

Текст pill внутри повёрнутого `.smile-stage__pill-block` (rotate −5.82°), координаты
текста — **абсолютные относительно блока** из metadata `127:545` / `127:556`.

QR-карточка: белый блок 258×321 @ (123, 92), **QR-код из макета** (`qr-code.png`,
Figma node `137:115`, экспорт `figma_mcp_call.mjs shot 137:115 isolated`) 245×245 @
(129, 97), подпись «Подключить оплату улыбкой» @ y: 342. QR **не генерируется**.

## Структура кода

```
smile-pay/
  web/js/figma-layout.js     ← единый источник координат (обновлён сессия 3)
  web/js/smile-stage.js      DOM, mapBox(), QR caption, стадии
  web/js/app.js              камера, face-presence, smile-capture
  web/css/style.css
  web/assets/figma/          SVG + layout.json
  scripts/download_figma_assets.ps1
```

## Ключевые размеры (metadata → canvas 504)

| Элемент | frame | Координаты |
|---------|-------|------------|
| MasterGradient | 504 | −201, −72, 1205.66×678.61 |
| Subtract | 515→S | −152, −92.69, 807×688.54 |
| Cam ellipse | 515→S | 43.95, 43.96, 414.61² |
| Pill | 504 | 13.34, **200.916**, 477.31×199.54, −5.82° |
| Текст main | 504 | 53, **216.926**, 403.3, 39.316px |
| Текст cta | 504 | 126, **295.728**, 266.55, 25.985px |
| QR card | 504 | 123, **92**, **258×321**, r25 |
| QR image | 504 | 129, 100, 245×245 |
| QR caption | 504 | 149.71, 342, 20.923px |

## Декор по стадиям (figma-layout.js)

- **idle**: sber (37.13, −41.72), smile (320, **287.78**), spring (−10, **305.35**), star-lg (326.54, 113), star-sm (268.34, **103.35**)
- **face**: star-mid-r, star-sm-r, star-tiny-l (frame 515, ×S)
- **line**: звёзды + smile-sm + sber-sm
- **stickers**: 15 элементов — smile @ (334, **306.78**), cl-a top **219.98**, cl-b **11.44**, cl-c **290.98**, cl-d **−20.02**, sber-lg (61.97, −46), star-big (258, **419.8**), …
- **qr**: cluster-tr/tl, smile-qr, spring-qr, star-qr-l/r (новые ассеты)

## Новые ассеты (Frame 6)

| Файл | Figma hash |
|------|------------|
| qr-cluster-tr.svg / qr-cluster-tl.svg | 22f23c2f… |
| qr-code.png | shot node 137:115 (PNG, не SVG) |
| sticker-smile-qr.svg | 93625fba… |
| spring-scribble-qr.svg | 3838156b… (обновлён) |
| mask-subtract.svg | c388cb26… |
| star-tiny.svg / star-small.svg | 0081b1eb… / 794a00b8… |

`download_figma_assets.ps1` пропускает 500-ошибки Figma Desktop и оставляет локальные копии.

## Известные расхождения (TODO)

1. **Text-path** — `web/js/text-paths.js`: полукруги по Ellipse 28798 (nodes `128:111`, `127:512`); SVG в `web/assets/figma/text-path-*.svg`
2. **MasterGradient** — CSS fallback (SVG = плоский rect)
3. **Шрифт** SB Sans — fallback Segoe UI
4. **Pixel-perfect** — side-by-side `/?stage=…` vs Figma PNG
5. **Анимации** idle/face — не реализованы

## Запуск и превью

```powershell
cd smile-pay
.\scripts\download_figma_assets.ps1   # Figma Desktop открыт
.\run.ps1
```

| URL | Стадия |
|-----|--------|
| http://127.0.0.1:8888/ | live |
| `/?stage=idle\|face\|line\|stickers\|qr` | превью |
| `/?demo=1` | автопроигрывание |
| `/?debug=1` | bbox overlay |

Алиасы: `intro`→idle, `line_hold`→face, `line_expand`→line.

## API

- `POST /api/capture` — JPEG → `{ session_id, pay_url }` (QR на экране — из Figma)
- `GET /pay/{session_id}` — демо «оплачено улыбкой»
