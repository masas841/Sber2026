# SberKopilka — установка киоска

ИнвестКопилка: джойстик, лабиринт, таблица лидеров.

## Требования

- Windows 10/11
- Python 3.10+ (`runtime\python` в пакете или системный)

## Сборка пакета (на машине разработчика)

```powershell
# Только код, Python на площадке
.\scripts\build_install_package.ps1

# С Python внутри (~80–100 MB)
.\scripts\build_install_package.ps1 -IncludePython

# Офлайн: Python + pip-колёса
.\scripts\build_install_package.ps1 -Offline
```

## Установка на площадке

```powershell
cd C:\sberkopilka
.\install\install.ps1
```

Офлайн-пакет:

```powershell
.\install\install.ps1 -Offline
```

## Запуск

```powershell
.\run-kiosk.ps1
```

Или: `install\start-sberkopilka.cmd`

Киоск: `http://127.0.0.1:8766` · health: `/api/health`

## Скачать пакет с FARM

- `http://192.168.1.243:8766/install/`
- Стабильная ссылка: `/install/sberkopilka-kiosk-latest.zip`

## Обновление из GitHub

```powershell
.\install\update-from-github.ps1
```

Или автообновление при запуске:

```env
AUTO_UPDATE_FROM_GITHUB=true
```
