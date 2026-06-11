# Контекст: развёртывание GIGAvibe на удалённой машине FARM

Дата последнего обновления: 2026-06-02

## 1. Цель

Развернуть и запустить киоск-сервер **GIGAvibe** на удалённой Windows-машине
(`FARM`) в локальной сети, под управлением по SSH. Сервер должен работать на
GPU (CUDA), быть доступен по сети и переживать перезагрузку.

**Текущий production-режим:** `ref_video` — референс-MP4 + **face swap**
(insightface inswapper), опционально **GFPGAN**. Без LTX, без шариков/фестивальной
атмосферы поверх ролика.

## 2. Доступ к удалённой машине

- **Имя:** FARM
- **IP:** `192.168.1.243`
- **Пользователь:** `user` (домен/имя: `farm\user`)
- **Подключение:** `ssh user@192.168.1.243`
- **Аутентификация:** по SSH-ключу (ed25519, комментарий `masas-windows-skud`).

### Как настраивался SSH (скрипты в корне проекта)

- `setup-openssh-server.ps1` — установка OpenSSH Server, служба `sshd`,
  правило firewall (порт 22).
- `setup-ssh-key-auth.ps1` — добавление публичного ключа в `authorized_keys`.
- `force-user-authorized-keys.ps1` — закомментировал секцию
  `Match Group administrators` в `sshd_config` (решило `Permission denied`).

## 3. Конфигурация машины FARM

- **CPU:** AMD Ryzen 7 5800X (8c/16t)
- **GPU:** 2× NVIDIA GeForce RTX 3090 24 GB
  - **GPU0** (`00000000:04:00.0`) — inswapper + buffalo_l (ONNX)
  - **GPU1** (`00000000:06:00.0`) — дисплей + GFPGAN (PyTorch)
- **Драйвер:** 552.44, **CUDA 12.4**
- **ОС:** Windows (build 10.0.22621)
- **Python:** 3.12 + venv `C:\Users\user\gigavibe\.venv`
- **Git:** установлен

## 4. Расположение проекта на FARM

| Путь | Назначение |
|------|------------|
| `C:\Users\user\gigavibe` | Корень проекта |
| `C:\Users\user\gigavibe\.venv` | Виртуальное окружение (обязателен для сервера) |
| `C:\Users\user\gigavibe\remote\` | Скрипты деплоя, `farm-refvideo.env`, `restart-gigavibe.ps1` |
| `C:\Users\user\gigavibe\certs\` | HTTPS (`cert.pem`, `key.pem`) |
| `C:\Users\user\gigavibe\assets\driving\` | Референс-MP4 для face swap |
| `C:\Users\user\gigavibe\models\` | inswapper, insightface buffalo_l, GFPGAN |
| `C:\Users\user\gigavibe\data\outputs\` | Готовые ролики |
| `C:\Users\user\gigavibe\server.log` | Лог (если перенаправлен в задаче) |
| `D:\gigavibe-models\` | LTX / HF cache (эксперименты, не production) |

## 5. Production: ref_video

### 5.1 Пайплайн

1. **Профиль гостя** — insightface (пол, возраст, комплекция), подбор driving MP4.
2. **Face swap** — inswapper по кадрам референс-видео.
3. **GFPGAN** (если `REF_VIDEO_FACE_RESTORE=true`) — постобработка лица.
4. H.264, QR. **Без** `apply_festival_atmosphere` (шарики), **без** фестивальной рамки
   при `REF_VIDEO_SKIP_FESTIVAL_FX=true`.

### 5.2 Две GPU, модели резидентно

Модели **грузятся один раз при старте** и остаются в VRAM между запросами:

| Модель | GPU | Переменная `.env` |
|--------|-----|-------------------|
| buffalo_l + inswapper | `cuda:0` | `REF_VIDEO_SWAP_DEVICE_ID=0` |
| GFPGAN | `cuda:1` | `REF_VIDEO_RESTORE_DEVICE_ID=1` |

- Синглтоны: `RefVideoGenerator._face_app` / `_swapper`, `face_restore._restorer`.
- Прогрев в `app.main` startup: swap + GFPGAN (если restore включён).
- **`CUDA_VISIBLE_DEVICES` не задаётся** — обе карты видны процессу; устройства
  выбираются явно через `device_id` (ONNX) и `torch.device("cuda:1")`.

### 5.3 Тайминги этапов (киоск + API)

- В `pipeline.py` каждый этап пишет время в `job.stage_timings`.
- API `GET /api/jobs/{id}`: `stage_timings`, `elapsed_sec` (в процессе), `total_sec` (в конце).
- UI: зелёная плашка на экране обработки (`#processing-timings`) и на результате.
- Ключи: `guest_profile`, `face_swap`, `face_restore`, `atmosphere`, `overlay`, `music`, `qr`.
- **Кэш статики:** в HTML подставляется `app.js?v=<mtime>` (см. `main.py` → `index()`).

Пример ответа API (done):

```json
{
  "stage_timings": {
    "guest_profile": 0.1,
    "face_swap": 20.6,
    "face_restore": 44.2,
    "qr": 0.0
  },
  "total_sec": 64.9,
  "generation_sec": 20.6
}
```

Типичное время (тест `test_face.jpg`, `IMG_9240.MP4`): swap ~20 с, GFPGAN ~40 с,
всего ~65 с.

## 6. Решённые проблемы

### 6.1 onnxruntime на CPU

- **Фикс:** `torch 2.6.0+cu124`, `numpy<2`, `torch\lib` в `PATH` стартового скрипта.
- **Результат:** `ref_video_onnx_provider: CUDAExecutionProvider`.

### 6.2 HTTPS и камера

- Самоподписанный cert, `USE_HTTPS=true`. Киоск только по **`https://192.168.1.243:8765`**.

### 6.3 Планировщик и SSH

- Задача `GIGAvibe` (ONLOGON) — сервер не падает при закрытии SSH.

### 6.4 .env с BOM

- Писать ASCII без BOM; шаблон `remote/farm-refvideo.env`.

### 6.5 LTX (эксперимент, не production)

- Пробовали LTX-Video + InstantID: нестабильность на 5 с, артефакты, перегруз VRAM.
- Код и модели на `D:\gigavibe-models\` сохранены; production вернули на `ref_video`.
- При повторном включении LTX: `GENERATOR_MODE=ltx`, `LTX_MODEL_DIR=D:\...`,
  кадры `8n+1`, отдельные `ltx_device_id` / InstantID на GPU1.

### 6.6 Тайминги не отображались в киоске

- **Причина:** браузер кэшировал старый `/static/app.js`.
- **Фикс:** cache-bust `?v=mtime` в HTML, блок `#processing-timings`, всегда отдавать
  `stage_timings` в API.

### 6.7 Старый процесс без venv

- Иногда задача поднимала системный `Python312` вместо `.venv` — после деплоя
  перезапускать через `remote/restart-gigavibe.ps1` (kill :8765 + `schtasks /Run`).

## 7. Текущая конфигурация .env на FARM

Шаблон в репозитории: `remote/farm-refvideo.env`.

```
GENERATOR_MODE=ref_video
HOST=0.0.0.0
PORT=8765
PUBLIC_BASE_URL=auto
PRELOAD_MODEL_ON_STARTUP=true
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=30
VIDEO_DURATION_SEC=10
VIDEO_ENCODE_CRF=16
VIDEO_ENCODE_PRESET=slow
REF_VIDEO_NO_UPSCALE=true
REF_VIDEO_USE_SOURCE_FPS=true
REF_VIDEO_FACE_RESTORE=true
REF_VIDEO_RESTORE_EVERY_N=1
REF_VIDEO_RESTORE_INTERPOLATE=true
REF_VIDEO_SWAP_DEVICE_ID=0
REF_VIDEO_RESTORE_DEVICE_ID=1
REF_VIDEO_SKIP_FESTIVAL_FX=true
FESTIVAL_ATMOSPHERE=false
FESTIVAL_FRAME=false
LIVEPORTRAIT_DEVICE_ID=0
KIOSK_TEST_MODE=true
USE_HTTPS=true
SSL_CERTFILE=certs/cert.pem
SSL_KEYFILE=certs/key.pem
```

Отключить GFPGAN (быстрее, только swap): `REF_VIDEO_FACE_RESTORE=false`.

## 8. Стартовый скрипт на FARM

`C:\Users\user\gigavibe\start-gigavibe-gpu.cmd` (копия также в `remote/start-gigavibe-gpu.cmd`):

```bat
@echo off
cd /d C:\Users\user\gigavibe
rem Обе RTX 3090: swap cuda:0, GFPGAN cuda:1
set PATH=C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;%PATH%
set PYTHONUNBUFFERED=1
.venv\Scripts\python.exe -m app.main
```

Задача планировщика должна вызывать **именно этот** `.cmd`, не голый `python -m app.main`.

## 9. Изменения в коде (актуальные модули)

| Файл | Что делает |
|------|------------|
| `app/config.py` | `ref_video_swap/restore_device_id`, `ref_video_skip_festival_fx` |
| `app/generators/ref_video.py` | inswapper, ONNX `device_id`, резидентные модели |
| `app/face_restore.py` | GFPGAN на `cuda:N`, `warmup_model()` |
| `app/pipeline.py` | этапы + `stage_timings`, без фестивальных FX для ref_video |
| `app/main.py` | прогрев моделей, cache-bust статики, API таймингов |
| `web/app.js` | `formatStageTimings`, `#processing-timings`, `#result-timing` |
| `web/index.html` | блоки таймингов |
| `remote/restart-gigavibe.ps1` | kill :8765 + перезапуск задачи |
| `remote/farm-refvideo.env` | эталон `.env` для FARM |

## 10. Скрипты деплоя (`i:\Cursor\Sber2026\remote\`)

- `farm-refvideo.env` — эталон production `.env`.
- `start-gigavibe-gpu.cmd` — запуск с venv и torch DLL.
- `register-gigavibe-task.ps1` — задача `GIGAvibe`.
- `restart-gigavibe.ps1` — перезапуск без ручного kill PID.
- `submit-job.cmd` — тест API с `data/test_face.jpg`.
- `optimize-gigavibe.ps1`, `enable-https.ps1`, `gpu_check.py` — первичная настройка.
- `ltx_preflight.py`, `download_ltx_to_d.py`, `ltx_lab.py` — только для экспериментов LTX.

**Деплой правок на FARM (типовой):**

```powershell
scp gigavibe/app/pipeline.py user@192.168.1.243:C:/Users/user/gigavibe/_deploy_tmp/
# copy в app/, web/ ...
ssh user@192.168.1.243 powershell -File C:/Users/user/gigavibe/remote/restart-gigavibe.ps1
```

## 11. Текущий статус

- **URL киоска:** https://192.168.1.243:8765
- **Режим:** `ref_video`, `RefVideoGenerator`, CUDA ONNX на GPU0
- **Health:** `GET /api/health` → `ref_video_available: true`
- **Задача:** `GIGAvibe` (планировщик)
- **LTX:** не в production; веса/скрипты на D: при необходимости экспериментов
- **Driving:** fallback `IMG_9240.MP4` если файл из `manifest.json` отсутствует

## 12. Частые команды

```powershell
# Health
curl.exe -sk https://192.168.1.243:8765/api/health

# Проверить cache-bust в HTML
curl.exe -sk https://192.168.1.243:8765/ | findstr app.js

# Перезапуск
ssh user@192.168.1.243 powershell -File C:/Users/user/gigavibe/remote/restart-gigavibe.ps1

# Порт / GPU
ssh user@192.168.1.243 "netstat -ano | findstr :8765"
ssh user@192.168.1.243 nvidia-smi

# Тест job (на FARM)
ssh user@192.168.1.243 "cd /d C:\Users\user\gigavibe && curl.exe -k -s -F photo=@data/test_face.jpg https://127.0.0.1:8765/api/jobs"

# Статус job (подставить job_id)
curl.exe -sk https://192.168.1.243:8765/api/jobs/<job_id>
```

## 13. Важные нюансы

- Локальный shell — **PowerShell:** `curl` → `curl.exe`, цепочки через `;`.
- SSH: сложное экранирование — предпочитать `scp` + `.ps1` на удалённой машине.
- Самоподписанный HTTPS: один раз принять cert на киоске и на телефоне гостя (QR).
- После деплоя **обновить страницу киоска** (Ctrl+F5) — иначе старый `app.js`.
- GFPGAN — самый долгий этап (~40 с на полном ролике); для ускорения отключить restore.
- `KIOSK_TEST_MODE=true` — доп. поля в API; тайминги этапов видны всегда при наличии `stage_timings`.

## 14. Checkpoint (бэкап перед новой механикой)

**2026-06-04** — сохранена точка восстановления ref_video-киоска перед переходом к
**генерации красивых картинок по фото пользователя**.

- Папка: `gigavibe/backups/20260604-refvideo-kiosk/`
- Архив: `gigavibe/backups/20260604-refvideo-kiosk.zip`
- Инструкция: `RESTORE.md` в папке бэкапа; указатель — `gigavibe/CHECKPOINT-refvideo-kiosk.md`
- В бэкапе: локальный код, `remote/`, снимок **production** с FARM (`farm-production/`, `farm-production.env`)

## 15. Возможные следующие шаги

- Почистить `assets/driving/manifest.json` под реально существующие MP4.
- Установить cert в доверенные на киоске (без предупреждения браузера).
- Параллельные jobs — сейчас один воркер; при нагрузке нужна очередь/lock.
- Повторный эксперимент LTX только по отдельному решению (отдельная ветка `.env`).

## 15. Оптимизация производительности ref_video (приёмы Rope)

Цель — догнать near-realtime Rope. Итог: **полный ролик 64.9с → ~23.5с**.

### 15.1 GPU-резидентный swap-конвейер (`app/generators/inswapper.py`)

`InswapperEngine` — свой движок inswapper_128 с io-binding (приём Rope):
- кадр заходит в VRAM один раз; кроп лица и вклейка результата — через
  `torch.nn.functional.affine_grid` + `grid_sample` на GPU (без cv2.warpAffine на CPU);
- постоянные ONNX io-binding буферы (img/lat/out) — без numpy↔GPU копий на кадр;
- latent (`emb @ emap`) считается один раз на гостя; emap читается из fp32-модели
  (в fp16 он свёрнут в Constant — см. `_extract_emap`).
- A/B vs CPU-путь: diff mean 0.05, p99=1/255 (эквивалентно); скорость 19.6 мс/кадр
  (51 fps) против 52.7 мс/кадр CPU, ×2.69.
- fp16-модель отброшена: лицо «мыло» (деградация квантизации), используем fp32
  `inswapper_128.onnx` через `INSWAPPER_FAST_MODEL_PATH`.
- `REF_VIDEO_SWAP_ENGINE=inswapper_fast` включает движок (есть ещё `simswap` 512 — качество).

### 15.2 Lean-детекция + threaded-чтение

- `REF_VIDEO_LEAN_DETECT=true` — на кадре зовём только `det_10g` (kps), а не весь
  buffalo_l (5 сетей). Для свопа нужны только 5 точек.
- `REF_VIDEO_THREADED_READ=true` — декодирование MP4 в отдельном потоке-ридере
  (очередь), перекрывает IO с GPU-работой.

### 15.3 Инлайн-restore вместо второго прохода (`restore_frame_with_landmarks`)

Было: GFPGAN отдельным проходом по MP4 (декод→RetinaFace заново→enhance→энкод).
Стало: restore прямо в swap-цикле по тем же kps, что нашёл детектор свопа —
без повторной детекции и без второго прохода по видео.
- `restore_frame_with_landmarks(frame, kps, restorer, weight)` в `app/face_restore.py`
  инъектирует kps в `FaceRestoreHelper.all_landmarks_5`, минуя RetinaFace; вклейка
  через parsenet-маску.
- `REF_VIDEO_INLINE_RESTORE=true` (вкл по умолч.), `REF_VIDEO_INLINE_RESTORE_WEIGHT=0.5`.
- `pipeline.py` при `last_inline_restored` пропускает старый `restore_video_faces`.

### 15.4 Кросс-GPU конвейер + пул restore-воркеров

- swap (GPU0, ONNX) — в главном потоке; restore (GPU1, GFPGAN PyTorch) — в пуле из
  N потоков. Пока GPU0 свопает кадр N+1, воркеры на GPU1 дочищают предыдущие →
  restore (самая дорогая стадия) прячется за swap.
- `REF_VIDEO_RESTORE_WORKERS=2` — число параллельных GFPGAN-экземпляров. Каждый
  воркер получает СВОЙ `new_restorer()` (face_helper не потокобезопасен). ~+1.5 ГБ
  VRAM на воркер.
- Стрейдинг сохранён: `REF_VIDEO_RESTORE_EVERY_N` (restore каждого N-го кадра,
  промежуточные — без restore). Кадры собираются по индексу — порядок сохраняется.

### 15.5 Реальные тайминги (API-прогон, test_from_driving.jpg, IMG_9240.MP4)

| Этап | Было (2-й проход) | Стало (инлайн+конвейер) |
|------|-------------------|--------------------------|
| face_swap | 13.1с | 18.3с (включает restore-перекрытие) |
| face_restore | 19.8с (отдельно) | ~11.6с (спрятан за swap) |
| **total** | **38.4с** | **23.5с** |

swap сам по себе уже на уровне Rope (io-binding+grid_sample). Узкое место
осталось — restore: пул воркеров (15.4) — последний доводящий приём.

### 15.6 Диагностические скрипты

- `scripts/ab_gpu_swap.py` — A/B корректности GPU vs CPU свопа.
- `scripts/profile_swap.py` — по-стадийный профиль (detect/align/infer/paste).
- `scripts/diag_gfpgan.py` — API GFPGANer/FaceRestoreHelper на FARM.
- `scripts/smoke_inline_restore.py` — smoke инлайн-restore по одному кадру.
- `scripts/bench_refvideo.py` — cold/hot бенч полного генератора.

### 15.7 Новые ключи `.env`

```
REF_VIDEO_SWAP_ENGINE=inswapper_fast
INSWAPPER_FAST_MODEL_PATH=C:\Users\user\gigavibe\models\inswapper_128.onnx
REF_VIDEO_LEAN_DETECT=true
REF_VIDEO_THREADED_READ=true
REF_VIDEO_INLINE_RESTORE=true
REF_VIDEO_INLINE_RESTORE_WEIGHT=0.5
REF_VIDEO_RESTORE_WORKERS=2
## 16. Новая механика (в работе)

**Генерация красивых статичных изображений** по селфи пользователя (не видео face swap).  
Переиспользовать: киоск (HTTPS, камера, jobs API, QR), FARM, GPU, `guest_profile`.  
Видео ref_video — восстановить из checkpoint §14.

