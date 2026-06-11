# GIGAvibe — киоск «фестивальный вайб»

Автономное приложение для **одной машины** на площадке: гость подходит к камере → делает селфи по улыбке → получает фестивальный портрет/ролик + QR для скачивания на телефон. Размер задаётся в `.env`: `VIDEO_WIDTH`, `VIDEO_HEIGHT`.

API GigaChat **не используется**.

## Режимы генерации

| Режим | Качество | Время | Железо |
|-------|----------|-------|--------|
| **`ref_video`** | **Референс-ролик как база** + лицо с селфи (face swap) | **30–90 с** | RTX 3060 Ti+ |
| **`liveportrait`** | Селфи + driving → только мимика/голова на **фоне фото** | 15–60 с | RTX 3060 Ti+ |
| **`ltx`** | **LTX-Video** img2vid (diffusers), GGUF на 8GB | 2–6 мин | RTX 3060 Ti 8GB |
| `svd` | Stable Video Diffusion | 1–4 мин | RTX 3060 Ti 8GB |
| `auto` | LTX → SVD → cinematic | — | — |
| `cinematic` | Запасной без нейросети | 5–15 с | CPU |

### Киоск (стенд без ввода)

- Старт: `.\run.ps1` → http://127.0.0.1:8765
- Камера включается сама; **снимок по улыбке** (MediaPipe Face Landmarker). Фоновое видео `assets/fon.mp4` играет непрерывно на всех экранах, поверх него плавно появляются/исчезают UI-слои.
- Один раз скачайте модель улыбки (офлайн на площадке): `.\scripts\download_smile_model.ps1` → `web/models/face_landmarker.task`. WASM по-прежнему с jsDelivr (нужен интернет при первом открытии киоска).
- Загрузка фото с диска отключена.
- Фото/результат отправляются на внешний сервер, если включено `OUTPUT_UPLOAD_ENABLED=true` и задан `OUTPUT_UPLOAD_URL=https://sberfest2026.ru/api/receive`.
- По селфи: **пол**, **возраст** (ребёнок / взрослый / пожилой — InsightFace `genderage`) и **комплекция** (slim / medium / full).
- Референс-ролик из `assets/driving/manifest.json`: **пол × возраст × комплекция** (до 18 вариантов на пол + fallback).

Актуальные параметры камеры и детекта в `.env`:

```env
KIOSK_FACE_DETECT_STRIDE=25
KIOSK_FACE_HOLD_MS=700
KIOSK_FACE_RELEASE_MS=1600
KIOSK_SMILE_DETECT_STRIDE=6
KIOSK_SMILE_HOLD_MS=650
```

Presence теперь считается по миллисекундам, а не по количеству редких проверок MediaPipe, поэтому `detect_stride=25` не даёт задержку входа ~5 секунд. На экране съёмки улыбка и контроль ухода гостя работают через один watcher, чтобы не создавать два MediaPipe-инстанса при появлении камеры. Canvas-превью рисуется через `requestVideoFrameCallback`, то есть по кадрам камеры, а не каждый RAF.

Летающие 3D-спрайты берутся из `assets/img/Asset (1).png` ... `Asset (20).png`, раздаются через `/assets/img/...` и размещаются с safe-зонами, чтобы не перекрывать логотип и подсказку «Улыбайтесь!».

Пороги профиля гостя в `.env`: `GUEST_AGE_CHILD_MAX=15`, `GUEST_AGE_SENIOR_MIN=55` (между — взрослый).

В `manifest.json` для каждой ячейки — **строка или массив** путей; при нескольких файлах выбирается **случайный** существующий:

```json
"medium": [
  "assets/driving/female_adult_medium_01.MP4",
  "assets/driving/female_adult_medium_02.MP4"
]
```

Одна строка `"path.MP4"` тоже работает. Несуществующие пути в массиве пропускаются. Если в ячейке никого нет — fallback `medium` → `default` → общий `default`.

### Ref-video (референс IMG_9240 + селфи гостя)

Режим `ref_video`: каждый кадр берётся из **вашего MP4**, подменяется только **лицо** с фото гостя. Это то, что ожидается от «референсного ролика как базы».

```env
GENERATOR_MODE=ref_video
LIVEPORTRAIT_DRIVING_PATH=assets/driving/IMG_9240.MP4
```

Первый запуск скачает `models/inswapper_128.onnx` (~530 MB). Нужны `insightface` и **`onnxruntime-gpu`** (не ставьте отдельно пакет `onnxruntime` — он перекрывает CUDA). На Windows cuDNN подхватывается из `torch/lib` автоматически.

После swap по умолчанию включён **GFPGAN** (`REF_VIDEO_FACE_RESTORE=true`): чётче лицо, +~0.1–0.3 с на кадр. Первый раз скачается `models/gfpgan/GFPGANv1.4.pth` (~350 MB). Отключить: `REF_VIDEO_FACE_RESTORE=false`.

Ускорение GFPGAN — `REF_VIDEO_RESTORE_EVERY_N` (по умолчанию `1`): полный прогон сети только на каждом N-м кадре (keyframe), а для промежуточных добавляется интерполированный «детальный слой» (residual = `restored − original`) соседних keyframe'ов. `2`–`3` дают ускорение примерно в N раз при почти незаметной потере качества на плавном движении. `REF_VIDEO_RESTORE_INTERPOLATE=true` — линейная интерполяция residual между keyframe'ами (плавнее); `false` — держать residual ближайшего предыдущего keyframe (дешевле).

После генерации в киоске: **«Готово за N с, CUDAExecutionProvider»** (в логах то же). Ориентир на RTX 3060 Ti: **~30–40 с** (150 кадров swap + 5 с видео), на CPU — **~2–3 мин**.

**LivePortrait** (`liveportrait`) для этого не подходит: он всегда рисует поверх **статичного фото** (paste-back на source), driving задаёт только движение губ/головы, не сцену из ролика.

### LivePortrait (оживление портрета на фоне фото)

1. Установите [FFmpeg](https://ffmpeg.org/download.html) (`ffmpeg` и `ffprobe` в PATH).
2. Запустите `download_liveportrait.bat` (git + отдельный `.venv-liveportrait` + веса ~2 GB).
3. В `.env`: `GENERATOR_MODE=liveportrait`, `PRELOAD_MODEL_ON_STARTUP=false`.
4. Driving-ролики: `assets/driving/*.mp4` (копируются из примеров при установке). Свои ролики — **1:1**, лицо в кадре, нейтральное первое выражение.

Тест: `.venv\Scripts\python.exe scripts\test_liveportrait.py`

Первый запуск LTX: скачивание GGUF (~1.3 GB) + компонентов пайплайна (VAE, T5 — несколько GB). Нужен стабильный интернет.

В `.env` для LTX:
```env
GENERATOR_MODE=ltx
LTX_GGUF_REPO_FILE=city96/LTX-Video-gguf/ltx-video-2b-v0.9-Q4_K_S.gguf
LTX_NUM_FRAMES=49
```

## Быстрый старт

```powershell
cd i:\Cursor\Sber2026\gigavibe
.\install-ai.ps1
copy .env.example .env
.\run.ps1
```

**Старт киоска:** `.\run.ps1` → в браузере **http://127.0.0.1:8765**

`run.ps1` ставит `onnxruntime-gpu` и `insightface` без CPU-пакета `onnxruntime` (через `constraints.txt` + `--no-deps`). Предупреждения pip про `gradio`/`pillow` можно игнорировать, если киоск в режиме `ref_video` (gradio нужен только LivePortrait). После запуска: `[GIGAvibe] ref_video ready, ONNX: CUDAExecutionProvider`.

В `.env` оставьте `PUBLIC_BASE_URL=auto` — IP для QR подставится сам (LAN Wi‑Fi).

Проверка: `http://127.0.0.1:8765/api/health` — поле `ref_video_onnx_provider` должно быть `CUDAExecutionProvider`, не `CPUExecutionProvider`.

## QR-код

- В QR зашит URL вида `http://<LAN-IP>:8765/outputs/....mp4` — телефон гостя должен быть в той же сети.
- На экране киоска QR показывается **с того же сервера** (`/api/jobs/.../qr.png` или inline base64), не с чужого IP — иначе картинка не грузилась.

## Брендинг

- Положите PNG-рамку с прозрачностью в `assets/overlay.png` и укажите `BRAND_OVERLAY_PATH` в `.env`.
- Фоновая музыка: `assets/music.mp3` + `BACKGROUND_MUSIC_PATH`.

## Схема на площадке

```
[Веб-камера / планшет] → браузер fullscreen
         ↓
[Этот ПК: FastAPI + генератор]
         ↓
MP4 в data/outputs/ + QR (PUBLIC_BASE_URL)
         ↓
Гость сканирует QR → скачивает видео
```

`PUBLIC_BASE_URL=auto` подставляет LAN IP. Если авто-IP неверный — укажите вручную: `http://192.168.x.x:8765`.

## Структура

```
gigavibe/
  app/
    main.py          # HTTP API + раздача UI
    pipeline.py      # очередь задач
    generators/
      liveportrait.py
      cinematic.py   # офлайн-видео
      ltx.py / svd.py
  web/               # киоск в браузере
  data/outputs/      # готовые MP4
```

## Дальше

- Полноэкранный Chrome в kiosk mode (`--kiosk`)
- Автозапуск через планировщик Windows
- Согласие на обработку фото (экран перед съёмкой)
- TTL-очистка `data/outputs` раз в сутки
