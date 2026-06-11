from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8766
    leaderboard_reset_hour: int = 0
    game_duration_sec: int = 60
    joystick_deadzone: float = 0.35


settings = Settings()
