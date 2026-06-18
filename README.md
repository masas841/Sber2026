# Sber2026

Рабочая папка активностей для фестиваля / киосков Сбер 2026.

## Проекты

| Папка | Описание |
|-------|----------|
| `gigavibe/` | Киоск «ГИГАвайб» — селфи, AI-портрет, QR |
| `sberkopilka/` | ИнвестКопилка |
| `insure-chill/` | «Застрахуй свой чилл» |
| `smile-pay/` | Smile Pay |
| `photo_receiver/` | Приём фото |

## Gigavibe — быстрый старт

```powershell
cd gigavibe
.\run-kiosk.ps1
```

Установка и сборка пакетов:

| Проект | Документация |
|--------|--------------|
| `gigavibe/` | `gigavibe/install/README-INSTALL.md` |
| `sberkopilka/` | `sberkopilka/install/README-INSTALL.md` |
| `insure-chill/` | `insure-chill/install/README-INSTALL.md` |
| `smile-pay/` | `smile-pay/install/README-INSTALL.md` |

Общие скрипты установки: `scripts/kiosk/`

## Секреты

Файлы `.env` не коммитятся. Используйте `.env.example` / `install/.env.kiosk.example` как шаблоны.
