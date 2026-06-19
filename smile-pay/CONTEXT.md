# Smile Pay — контекст проекта (обновлено 2026-06-19)

Отдельный киоск-интерактив **«Улыбка»** (оплата улыбкой). **Не связан с gigavibe** — изменения только в `smile-pay/`.

## Деплой и окружения

| Окружение | URL / путь |
|-----------|------------|
| Локально | `http://127.0.0.1:8888` (`.\run.ps1`, порт **8888**) |
| FARM | `https://slash.omelchak.com:8767` · `https://192.168.1.243:8767` |
| Сервер FARM | `C:\Users\user\smile-pay` |
| Деплой | `.\remote\deploy-smile-pay-farm.ps1` (нужен SSH к 192.168.1.243) |

Киоск-пакет: `install/` · сборка `scripts\build_install_package.ps1` · скачать `/install/smile-pay-kiosk-latest.zip`.

## Макет Figma

- Секция: **«Улыбка»** `128:109`
- Виджет: **круг 504×504** (обрезка в `.shell`)
- Кадры 1/4/5 в макете **515×515** → масштаб **S = 504/515 ≈ 0.978641**
- **Источник координат**: Figma metadata (absolute bbox), не flex-обёртки get_design_context

| Стадия (код) | Figma frame | node-id | Содержимое |
|--------------|-------------|---------|------------|
| `idle` | Frame 3 | `127:513` | MasterGradient + декор + pill «Такой улыбкой…», камера скрыта |
| `face` | Frame 4 | `127:567` | Subtract-кольцо + камера + text-path + звёзды; при удержании улыбки — hold-декор |
| `line` | Frame 1 | `25:2498` | Оба text-path, смещённые стикеры, **15 с** (demo / превью) |
| `stickers` | Frame 5 | `127:597` | Полный набор стикеров |
| `qr` | Frame 6 | `127:713` | MasterGradient + карточка QR **258×321** + caption + декор |

## Live-флоу (актуальный)

1. **idle** — зелёный градиент, камера **активна**, но **скрыта** (clip-path = 0). MediaPipe ищет лицо на скрытом потоке.
2. **face** — лицо найдено и удержано → `revealCamera()`, случайный bottom line, «Улыбнитесь!». Удержание улыбки **3 с** с прогрессом и hold-стикерами (текст нижнего лайна стирается по символам). Пока MediaPipe отдаёт фазу `smile`, `boomerang-recorder.js` копит до **3 с** кадров в память.
3. После успешной улыбки — JPEG-снимок → `POST /api/capture` в фоне (ошибка API не блокирует анимацию).
4. **line** — нижний текст печатается до конца; затем canvas-бумеранг пользователя плавно появляется поверх окна камеры и проигрывает **3 цикла по 3 с**.
5. **stickers** → **qr** через `playPostSmileSequence({ skipLine: true })` (line уже был показан вручную).
6. **qr** — **10 с**, затем переход в idle через **sticker curtain**: стикеры заполняют экран на QR → idle под ними → стикеры разлетаются (`preserveStickerCurtain`, `stickers-in` / `stickers-out`).
7. Цикл снова с **idle** + presence watcher.

**Demo** (`?demo=1`): полная цепочка **с line 15 с**, автоповтор.

**Превью** (`?stage=…`): фиксированная стадия без камеры/детекта.

**Киоск install gate**: `kiosk-install-mode.js` — poll `sberfest2026.ru/api/kiosk-install-mode/smile-pay` каждые 10 с; при `install_off` — Figma standby-экран «До встречи!» (`index.html` + `web/css/kiosk-install-standby.css`, ассеты `web/assets/figma/install-off/`).

**Hourly refresh**: в live `location.reload()` раз в час.

## Детекция и камера

### Пороги (`app.js`)

```javascript
PRESENCE = { minFaceSize: 0.025, holdMs: 180, releaseMs: 1400, detectStride: 6 }
SMILE    = { threshold: 0.21, minFaceSize: 0.07, holdMs: 3000, releaseMs: 1500, detectStride: 4 }
SMILE_HOLD = { requiredMs: 3000 }
```

### MediaPipe (`face-landmarker.js`)

- Локальные assets: `/static/vendor/mediapipe/tasks-vision` + `/static/models/face_landmarker.task` (CDN fallback).
- `minFaceDetectionConfidence / minFacePresenceConfidence / minTrackingConfidence`: **0.05**.
- `getDetectionFrame()`: crop по `--detection-zoom`, без поворота кадра (камера закреплена в нормальном положении).
- Визуальный preview: `scaleX(-1) scale(var(--camera-zoom))`.
- Снимок: горизонтальное зеркалирование через canvas.

### Видео

```javascript
getUserMedia({ video: { facingMode: "user", width: { ideal: 1920 }, height: { ideal: 1080 } } })
```

### CSS zoom (`style.css`)

```css
--camera-zoom: 2;
--detection-zoom: 3;  /* только для MediaPipe, не для preview */
```

### Layout

- `.shell { top: -15px }` — всё приложение поднято на 15px.
- `CAM_WINDOW_OFFSET_Y = -10` в `cam-geometry.js` — внутренняя геометрия кольца (не общий сдвиг shell).

## Тайминги стадий (`smile-stage.js`)

```javascript
STAGE_TIMING = { line: 15000, stickers: 2400, qr: 10000 }
STICKERS_IN_MS = 1250
STICKERS_OUT_MS = 1200
LINE_TYPEWRITER = { delay: 220, duration: 1150 }
```

Переход QR → idle: `setStage("idle", { preserveStickerCurtain: true })` + анимации curtain; dissolve не скрывает стикеры с классами `stickers-in` / `stickers-out`.

## Архитектура слоёв

`.shell` (круг 504×504, overflow:hidden):
- `.camera-slot` — `<video>`, radial mask, видимость на `shell--cam-open`
- `.stage-root` → `.smile-stage`

Внутри `.smile-stage`:
- `.smile-stage__field` — зелёное поле + прорез камеры
- `.smile-stage__master` — MasterGradientWhite (idle/qr)
- `.smile-stage__subtract-wrap` — кольцо (face/line)
- `.smile-stage__decor-layer`, `.smile-stage__copy`, `.smile-stage__qr-slot`

QR-карточка: белый блок 258×321 @ (123, 92), QR **из макета** (`qr-code.png`, node `137:115`), caption «Подключить оплату улыбкой» (`lines.txt` → `[qr_caption]`). QR **не генерируется**.

Bottom lines: случайный `[bottom]` на каждую попытку гостя в `onFaceReady` (`pickBottomLineForAttempt`).

## Структура кода

```
smile-pay/
  app/main.py              FastAPI, play_log, install_routes
  app/play_log.py          логирование прохождений
  web/js/figma-layout.js   координаты, ALL_DECOR, SMILE_HOLD_DECOR
  web/js/smile-stage.js    DOM, стадии, playPostSmileSequence
  web/js/cam-geometry.js   геометрия окна камеры, applyCamVars
  web/js/face-landmarker.js MediaPipe, getDetectionFrame
  web/js/face-presence.js  ожидание лица → revealCamera
  web/js/smile-capture.js  детект улыбки
  web/js/boomerang-recorder.js  запись кадров улыбки и canvas-бумеранг
  web/js/app.js            live / demo / preview, PRESENCE/SMILE
  web/js/kiosk-install-mode.js  poll install_off
  web/css/style.css
  web/css/kiosk-install-standby.css  экран выключенной активности
  web/assets/copy/lines.txt
  web/assets/figma/install-off/ локальные SVG ассеты standby-экрана
  install/                 киоск-пакет, update-from-github
  scripts/download_figma_assets.ps1
  scripts/download_smile_model.ps1
  remote/deploy-smile-pay-farm.ps1
```

## Cache-busting (актуальные версии в index / imports)

| Файл | query |
|------|-------|
| `style.css` | `?v=20260613-detect-zoom-app-y` |
| `app.js` | `?v=20260613-stage-timing` |
| `smile-stage.js` | `?v=20260613-stage-timing` |
| `face-presence.js`, `smile-capture.js` | `?v=20260614-offline-mp` |
| `face-landmarker.js` (в imports) | `?v=20260613-detection-zoom-3` |
| `figma-layout.js` | `?v=20260612-qr-sticker-fill-2` |
| `cam-geometry.js` | `?v=20260613-app-up` |

`index.html` через `FileResponse` **без** `Cache-Control: no-cache` (киоск может держать старый HTML до reload).

## Запуск и превью

```powershell
cd smile-pay
.\scripts\download_figma_assets.ps1   # Figma Desktop открыт
.\scripts\download_smile_model.ps1    # face_landmarker.task
.\run.ps1
```

| URL | Режим |
|-----|-------|
| http://127.0.0.1:8888/ | live |
| `/?stage=idle\|face\|line\|stickers\|qr` | превью стадии |
| `/?demo=1` | автопроигрывание (с line 15 с) |
| `/?debug=1` | bbox overlay |
| `/?nostage=1` | idle без live |

Алиасы: `intro`→idle, `line_hold`→face, `line_expand`→line.

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | статус сервиса |
| GET | `/api/stats` | статистика play_log |
| POST | `/api/capture` | JPEG → `{ session_id, pay_url }` |
| GET | `/pay/{session_id}` | демо «оплачено улыбкой» |
| GET | `/install/…` | киоск-пакет (через install_routes) |

## Известные расхождения / TODO

1. **Text-path** — `web/js/text-paths.js`; SVG в `web/assets/figma/text-path-*.svg`
2. **MasterGradient** — CSS fallback (SVG = плоский rect)
3. **Шрифт** — в рабочей копии `style.css` локально может быть unstaged hunk `SB Sans Display` vs committed `SB Sans Text` stack
4. **Pixel-perfect** — side-by-side `/?stage=…` vs Figma PNG
5. **Анимации** idle/face — не реализованы
6. **Live без line** — после улыбки стадия line не показывается; тайминг line 15 с только в demo
7. **Деплой FARM** — с некоторых сетей SSH/SCP к 192.168.1.243 timeout; нужен `deploy-smile-pay-farm.ps1` с доступной сети после push

## Отладка «дистанции открытия камеры»

Порядок: MediaPipe на **detection canvas** (zoom 3, без поворота) → `faceBounds().size` vs `PRESENCE.minFaceSize` (0.025) → hold **180 ms** → `onFaceReady` → `revealCamera()`.

Если открытие «на той же дистанции», проверить: задеплоена ли версия с `--detection-zoom: 3`, confidence **0.05**, а не только `minFaceSize`. Также версии в `curl` index.html и cache-busting query.

## Недавние коммиты (main)

| Коммит | Содержание |
|--------|------------|
| `d91ba13` | Stage timing: line 15s, QR 10s |
| `cfefd9d` | `--detection-zoom: 3`, shell top -15px |
| `08bcc04` | Fast acquire (holdMs 180), mirror preview, layout |
| `f52e606` | MediaPipe confidence 0.15→0.05 |
| `ff9ec9b` / `1b9cd8b` | Lower detection / face thresholds |
| `a7ed745` | Rotate feed 180° for detection |
| `11a99e7` | 1080p camera input |
| `98313cd` | QR → idle sticker curtain transition |
