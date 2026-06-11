# Smile Pay

Отдельный интерактив **«Улыбка»** — оплата улыбкой. Сцена **504×504**, зелёный фон Figma; камера всегда активна, но видна только через радиальную маску.

## Запуск

```powershell
cd smile-pay
.\run.ps1
```

Откройте http://127.0.0.1:8888

## Превью стадий

| URL | Стадия |
|-----|--------|
| `/?stage=idle` | Только зелёный фон |
| `/?stage=face` | Радиальная маска + frame4 |
| `/?stage=line` | Оба лайна на text-path |
| `/?stage=stickers` | Стикеры |
| `/?stage=qr` | QR |
| `/?demo=1` | Автопроигрывание цепочки |
| `/?stage=idle&debug=1` | Overlay bbox для сверки с Figma |

Старые алиасы: `intro`→`idle`, `line_hold`→`face`, `line_expand`→`line`.

## Ассеты Figma

1. Откройте макет «Улыбка» в **Figma Desktop**.
2. Запустите:

```powershell
.\scripts\download_figma_assets.ps1
```

SVG сохраняются в `web/assets/figma/`.

## Шрифт

Положите `SBSansText-Semibold.woff2` в `web/fonts/` (можно скопировать из проекта sberkopilka, если файл есть локально).

## Live-флоу

1. **idle** — зелёный фон, камера скрыта маской
2. **face** — лицо в кадре → радиальная маска + текст frame4
3. **line** — улыбка → нижний лайн, пауза 10 с
4. **stickers** — каскад стикеров
5. **qr** — диссолв к QR → возврат в idle

## Модель MediaPipe

```powershell
.\scripts\download_smile_model.ps1
```

Без локальной модели используется CDN Google (нужен интернет на киоске).

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/capture` | JPEG → `{ session_id, pay_url }` |
| GET | `/pay/{id}` | Демо-страница «оплачено улыбкой» |

```
smile-pay/
  app/main.py          — FastAPI, порт 8888
  web/
    index.html
    css/style.css
    js/smile-stage.js  — сборка сцены и стадий
    js/app.js          — камера / demo / ?stage=
    assets/figma/      — SVG из Figma
```

Стадии: `idle` → `face` → `line` → `stickers` → `qr`.

Подробный контекст для продолжения работы: **[CONTEXT.md](./CONTEXT.md)** (координаты Figma, известные расхождения, TODO).
