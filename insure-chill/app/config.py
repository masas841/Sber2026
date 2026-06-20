from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8768
    game_duration_sec: int = 59
    hit_padding_px: int = 10
    data_dir: Path = Path("data")
    play_log_file: str = "data/plays.jsonl"
    play_log_tz: str = "Europe/Moscow"

    # Диагностика: периодически отправлять хвост логов киоска на photo_receiver.
    log_upload_enabled: bool = True
    log_upload_url: str | None = None
    log_upload_api_key: str | None = None
    # bearer | x-api-key
    log_upload_auth: str = "bearer"
    log_upload_kiosk_id: str = ""
    log_upload_interval_sec: float = 60.0
    log_upload_timeout_sec: float = 30.0
    log_upload_max_bytes: int = 512 * 1024
    log_upload_initial_tail_bytes: int = 256 * 1024
    log_upload_paths: str = "data/srv_out.log;data/srv_err.log;server.log;data/plays.jsonl"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
