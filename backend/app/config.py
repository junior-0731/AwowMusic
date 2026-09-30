"""Configuración de la app. Se puede sobrescribir con variables AWOW_* o backend/.env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AWOW_", env_file=BACKEND_DIR / ".env", extra="ignore")

    data_dir: Path = BACKEND_DIR / "data"
    default_model: str = "demucs_4"
    max_upload_mb: int = 500
    preview_bitrate: str = "192k"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def db_path(self) -> Path:
        return self.data_dir / "awow.db"

    @property
    def songs_dir(self) -> Path:
        return self.data_dir / "songs"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def work_dir(self) -> Path:
        return self.data_dir / "work"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.songs_dir, self.models_dir, self.work_dir):
            d.mkdir(parents=True, exist_ok=True)
