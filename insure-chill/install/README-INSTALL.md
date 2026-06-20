# Insure Chill — установка киоска

«Застрахуй свой чилл»: экран + планшет оператора.

## Требования

- Windows 10/11
- Python в пакете (`runtime\python`). Системный Python 3.10+ тоже поддерживается, но для киосков рекомендуется bundled-пакет.

## Сборка пакета

```powershell
.\scripts\build_install_package.ps1
.\scripts\build_install_package.ps1 -WithoutPython
.\scripts\build_install_package.ps1 -Offline
```

Обычная сборка включает portable Python, чтобы пакет ставился на чистый киоск без системного Python. Флаг `-WithoutPython` нужен только для облегчённой сборки на машине, где Python уже установлен.

## Установка

```powershell
cd C:\insure-chill
.\install\install.ps1
```

## Запуск

```powershell
.\run-kiosk.ps1
```

Или: `install\start-insure-chill.cmd`

Экран: `http://127.0.0.1:8768/` · Планшет: `/control`

## Скачать пакет с FARM

- `https://slash.omelchak.com:8768/install/`
- `https://192.168.1.243:8768/install/`
- Стабильная ссылка: `/install/insure-chill-kiosk-latest.zip`

## Обновление из GitHub

```powershell
.\install\update-from-github.ps1
```

Автообновление при запуске: `AUTO_UPDATE_FROM_GITHUB=true` в `.env`
