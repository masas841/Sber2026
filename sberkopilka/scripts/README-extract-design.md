# Извлечение ассетов из PDF

Макет: `docs/design/ИнвестКопилка.pdf`  
Целевой экран: **504 × 672 px**

## Команда

```powershell
cd sberkopilka
python scripts/extract_design_from_pdf.py
```

Опции:

```powershell
python scripts/extract_design_from_pdf.py --pdf "C:\path\file.pdf" --out web/assets/design
python scripts/extract_design_from_pdf.py --no-slices   # без сетки 504×672
```

## Результат (`web/assets/design/`)

| Папка | Содержимое |
|-------|------------|
| `embedded/` | Все встроенные растры как PNG; альфа из PDF (smask / PNG) |
| `screens/` | Авто-вырезка фреймов 3:4 → **504×672**, фон прозрачный |
| `slices/` | Сетка по полотну PDF (504×672 pt), для ручного выбора экранов |
| `manifest.json` | Каталог файлов, размеры, координаты |

URL в игре: `/static/assets/design/...`

## Прозрачность

- **PNG / smask в PDF** — альфа сохраняется.
- **JPEG без маски** — в PDF непрозрачные; для иконок можно доработать в Figma (экспорт PNG) или включить вырезание белого фона в скрипте (`white_to_alpha`).

После извлечения отберите нужные файлы в `web/assets/design/catalog/` и пропишите в `design-manifest.js`.
