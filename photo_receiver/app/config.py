from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = "0.0.0.0"
    port: int = 8767
    public_base_url: str = "http://127.0.0.1:8767"
    data_dir: Path = Path("data")
    chunk_size: int = 262144
    upload_api_key: str | None = None
    max_upload_bytes: int = 20 * 1024 * 1024


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "uploads").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "parts").mkdir(parents=True, exist_ok=True)
