# Smile Pay — установка киоска

Оплата улыбкой: камера, детект улыбки (MediaPipe), QR.

## Требования

- Windows 10/11
- Python 3.10+ (`runtime\python` в пакете или системный)
- Для офлайн-работы детекта улыбки нужны `web/vendor/mediapipe` и `web/models/face_landmarker.task`

## Сборка пакета

```powershell
# Код (~15 MB), pip при установке нужен интернет
.\scripts\build_install_package.ps1

# С Python внутри
.\scripts\build_install_package.ps1 -IncludePython

# Офлайн: Python + wheels + MediaPipe vendor + face model
.\scripts\build_install_package.ps1 -Offline
```

## Установка

```powershell
cd C:\smile-pay
.\install\install.ps1
```

Офлайн:

```powershell
.\install\install.ps1 -Offline
```

## Запуск

```powershell
.\run-kiosk.ps1
```

Или: `install\start-smile-pay.cmd`

Киоск: `http://127.0.0.1:8888` · health: `/api/health`

## Скачать пакет с FARM

- `https://slash.omelchak.com:8767/install/`
- `https://192.168.1.243:8767/install/`
- Стабильная ссылка: `/install/smile-pay-kiosk-latest.zip`

## Обновление из GitHub

```powershell
.\install\update-from-github.ps1
```

Автообновление при запуске: `AUTO_UPDATE_FROM_GITHUB=true` в `.env`
