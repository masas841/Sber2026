# Сервер выгрузки фото — Greathearted Inna

Дата: 2026-06-07

## Назначение

VPS для **приёма файлов с QR-стендов** и **раздачи по ссылке** на домене `sberfest2026.ru`.

**Клиенты домена:**
- **ГИГАвайб** (FARM) — портрет после генерации, QR на `/outputs/{job_id}.jpg`
- **Улыбкометр** — интерактив улыбки, загрузка результата и QR на тот же домен

| Поле | Значение |
|------|----------|
| **Имя** | Greathearted Inna |
| **IP** | `45.67.59.125` |
| **Домен** | `sberfest2026.ru` |
| **SSH** | `root` / пароль ниже |
| **Сервис** | `photo-receiver` → `127.0.0.1:8767` (только localhost) |
| **Публичный вход** | nginx `:80` / `:443` → proxy на photo-receiver |

```bash
ssh root@45.67.59.125
# Пароль: Q*8ZIDoRV%Fh
```

## DNS и SSL

A-запись: `sberfest2026.ru` → `45.67.59.125` (Beget).

**HTTPS активен** с 2026-06-07, сертификат Let's Encrypt до 2026-09-05.

```bash
curl https://sberfest2026.ru/api/health
```

## Текущее состояние сервера

| Компонент | Статус |
|-----------|--------|
| nginx `:80` / `:443` | работает, HTTP→HTTPS redirect |
| photo-receiver | `127.0.0.1:8767`, `PUBLIC_BASE_URL=https://sberfest2026.ru` |
| ufw | 22, 80, 443; **8767 закрыт** снаружи |
| HTTPS | **работает** |

## API photo_receiver

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | статус |
| POST | `/api/uploads/init` | начать/возобновить загрузку |
| PATCH | `/api/uploads/{id}` | chunk + заголовок `X-Upload-Offset` |
| GET | `/api/uploads/{id}/status` | прогресс докачки |
| POST | `/api/receive` | простой multipart (legacy) |
| GET | `/p/{filename}` | страница просмотра и скачивания (QR) |
| GET | `/outputs/{filename}` | файл (inline); `?download=1` — скачивание |

Очередь и состояние частичных загрузок — SQLite `data/queue.db`.

## Улыбкометр (интерактив улыбки)

Тот же домен и API `photo_receiver`:

```
OUTPUT_UPLOAD_URL=https://sberfest2026.ru
QR_PUBLIC_BASE_URL=https://sberfest2026.ru
```

## FARM (киоск ГИГАвайб)

В `remote/farm-nanobanana.env` (после SSL):

```
OUTPUT_UPLOAD_ENABLED=true
OUTPUT_UPLOAD_URL=https://sberfest2026.ru
QR_PUBLIC_BASE_URL=https://sberfest2026.ru
```

QR ведёт на `https://sberfest2026.ru/p/{filename}` — страница с превью и кнопкой «Скачать».

Киоск FARM сам слушает `:8765` (`PUBLIC_BASE_URL=https://sberfest2026.ru:8765`) — это отдельная машина.

Деплой на FARM:

```powershell
cd i:\Cursor\Sber2026\remote
.\deploy-farm.ps1
```

## Деплой photo_receiver

```powershell
cd i:\Cursor\Sber2026\remote
$env:INNA_SSH_PASSWORD='...'
python deploy-photo-receiver-paramiko.py
python setup-inna-ssl.py   # nginx + попытка certbot
```

## Связанные машины

| Роль | Адрес |
|------|--------|
| FARM — ГИГАвайб | `192.168.1.243` · киоск `:8765` |
| Улыбкометр — ПК стенда | upload + QR → `https://sberfest2026.ru` |
| Greathearted Inna — хостинг | `https://sberfest2026.ru` (`45.67.59.125`) |
