# Insure Chill — установка киоска

«Застрахуй свой чилл»: экран + планшет оператора.

## Требования

- Windows 10/11
- Python 3.10+ (`runtime\python` в пакете или системный)

## Сборка пакета

```powershell
.\scripts\build_install_package.ps1
.\scripts\build_install_package.ps1 -IncludePython
.\scripts\build_install_package.ps1 -Offline
```

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
