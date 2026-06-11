# GIGAvibe — установка киоска (только портрет)

Киоск: селфи → портрет 9:16 → QR. Видео-генерация не используется.

## Требования

- Windows 10/11
- **Python** — либо уже в пакете (`runtime\python`), либо установите 3.10+ с python.org
- NVIDIA GPU + драйвер CUDA (для профиля гостя / InsightFace)
- Ключ AITunnel (`AITUNNEL_API_KEY` в `.env`)

## Сборка пакета (на машине разработчика)

```powershell
# Только код (~27 MB), Python ставится на площадке
.\scripts\build_install_package.ps1

# С Python внутри (~80–100 MB), pip при установке нужен интернет
.\scripts\build_install_package.ps1 -IncludePython

# Полностью офлайн: Python + pip-колёса + модели улыбки/buffalo_l (~500+ MB)
.\scripts\build_install_package.ps1 -Offline
```

## Установка на площадке

**С Python в комплекте (рекомендуется):**

```powershell
cd C:\gigavibe
.\install\install.ps1
```

**Офлайн-пакет (без интернета на площадке):**

```powershell
.\install\install.ps1 -Offline
```

**Без bundled Python** — нужен системный Python 3.10+ в PATH.

## Настройка

1. Отредактируйте `.env` (шаблон: `install\.env.kiosk.example`).
2. `PUBLIC_BASE_URL` — URL для QR (LAN IP или `https://домен:8765`).
3. `AITUNNEL_API_KEY` — ключ API.

## Запуск

```powershell
.\run-kiosk.ps1
```

Или двойной клик: `install\start-gigavibe.cmd`

Киоск: `http://127.0.0.1:8765` · health: `/api/health`

## HTTPS (опционально)

См. `scripts\issue_letsencrypt.ps1` и `USE_HTTPS` в `.env`.
