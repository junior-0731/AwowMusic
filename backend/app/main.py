"""API de AwowMusic (FastAPI)."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from . import audio_io
from .config import Settings
from .db import Database, new_id
from .export.package import build_stems_zip, stem_download_name
from .jobs import JobQueue, UserError
from .separation.engine import AudioSeparatorBackend, SeparationService, SeparatorBackend
from .separation.models import DRUM_MODEL, MODELS
from .system import system_status

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".aif", ".aiff", ".opus", ".wma"}
UPLOAD_CHUNK = 1024 * 1024


class SongUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    bpm: float | None = Field(default=None, ge=20, le=400)
    musical_key: str | None = Field(default=None, max_length=12)


class SeparateRequest(BaseModel):
    model: str
    fix_residual: bool = True
    drum_split: bool = False


def create_app(settings: Settings | None = None, backend: SeparatorBackend | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_dirs()
    db = Database(settings.db_path)
    jobs = JobQueue(db)
    separation = SeparationService(db, settings, backend or AudioSeparatorBackend(settings.models_dir))
    jobs.register("separate", separation.handle)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        jobs.start()
        yield
        jobs.stop()

    app = FastAPI(title="AwowMusic", version="0.1.0", lifespan=lifespan)
    app.state.settings, app.state.db, app.state.jobs = settings, db, jobs
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
    )

    def song_or_404(song_id: str) -> dict[str, Any]:
        song = db.get_song(song_id)
        if not song:
            raise HTTPException(404, "Canción no encontrada")
        return song

    def stem_or_404(stem_id: str) -> dict[str, Any]:
        stem = db.get_stem(stem_id)
        if not stem:
            raise HTTPException(404, "Stem no encontrado")
        return stem

    def data_file(rel: str) -> Path:
        path = settings.data_dir / rel
        if not path.exists():
            raise HTTPException(404, "El archivo ya no existe en disco")
        return path

    # --- Sistema -------------------------------------------------------------

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": app.version, **system_status()}

    @app.get("/api/models")
    def models() -> dict[str, Any]:
        return {
            "default": settings.default_model,
            "models": [m.public() for m in MODELS.values()],
            "drum_model": DRUM_MODEL.public(),
        }

    # --- Canciones -----------------------------------------------------------

    @app.get("/api/songs")
    def list_songs() -> list[dict[str, Any]]:
        return db.list_songs()

    @app.post("/api/songs", status_code=201)
    def upload_song(file: UploadFile = File(...)) -> dict[str, Any]:
        name = Path(file.filename or "cancion")
        ext = name.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise HTTPException(415, f"Formato no soportado ({ext or 'sin extensión'}). Usa WAV, MP3, FLAC, M4A u OGG.")

        song_id = new_id()
        song_dir = settings.songs_dir / song_id
        song_dir.mkdir(parents=True)
        try:
            original = song_dir / f"original{ext}"
            limit = settings.max_upload_mb * 1024 * 1024
            size = 0
            with original.open("wb") as out:
                while chunk := file.file.read(UPLOAD_CHUNK):
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, f"El archivo supera el límite de {settings.max_upload_mb} MB.")
                    out.write(chunk)
            if size == 0:
                raise HTTPException(400, "El archivo está vacío.")
            info = audio_io.decode_to_wav(original, song_dir / "source.wav")
            audio_io.make_preview(song_dir / "source.wav", song_dir / "preview.mp3", settings.preview_bitrate)
        except UserError as e:
            shutil.rmtree(song_dir, ignore_errors=True)
            raise HTTPException(422, str(e)) from e
        except OSError as e:
            shutil.rmtree(song_dir, ignore_errors=True)
            if getattr(e, "errno", None) == 28:
                raise HTTPException(507, "El disco está lleno. Libera espacio e intenta de nuevo.") from e
            raise
        except BaseException:
            shutil.rmtree(song_dir, ignore_errors=True)
            raise

        return db.create_song(
            id=song_id,
            title=name.stem,
            original_filename=name.name,
            sample_rate=info.sample_rate,
            channels=info.channels,
            frames=info.frames,
            duration=round(info.duration, 3),
        )

    @app.get("/api/songs/{song_id}")
    def get_song(song_id: str) -> dict[str, Any]:
        return song_or_404(song_id)

    @app.patch("/api/songs/{song_id}")
    def update_song(song_id: str, body: SongUpdate) -> dict[str, Any]:
        song_or_404(song_id)
        return db.update_song(song_id, **body.model_dump(exclude_unset=True))  # type: ignore[return-value]

    @app.delete("/api/songs/{song_id}", status_code=204)
    def delete_song(song_id: str) -> None:
        song_or_404(song_id)
        if any(j["status"] == "running" for j in db.list_jobs(song_id=song_id)):
            raise HTTPException(409, "La canción se está procesando; espera a que termine.")
        for job in db.list_jobs(song_id=song_id, status="pending"):
            jobs.cancel(job["id"])
        db.delete_song(song_id)
        shutil.rmtree(settings.songs_dir / song_id, ignore_errors=True)

    @app.get("/api/songs/{song_id}/preview")
    def song_preview(song_id: str) -> FileResponse:
        song_or_404(song_id)
        return FileResponse(data_file(f"songs/{song_id}/preview.mp3"), media_type="audio/mpeg")

    @app.post("/api/songs/{song_id}/separate", status_code=202)
    def separate(song_id: str, body: SeparateRequest) -> dict[str, Any]:
        song_or_404(song_id)
        if body.model not in MODELS:
            raise HTTPException(400, f"Modelo desconocido: {body.model}")
        return jobs.submit("separate", song_id, body.model_dump())

    @app.get("/api/songs/{song_id}/separations")
    def separations(song_id: str) -> list[dict[str, Any]]:
        """Separaciones de la canción (trabajos) con sus stems."""
        song_or_404(song_id)
        stems = db.list_stems(song_id=song_id)
        return [
            {**job, "stems": [s for s in stems if s["job_id"] == job["id"]]}
            for job in db.list_jobs(song_id=song_id)
            if job["type"] == "separate"
        ]

    # --- Trabajos ------------------------------------------------------------

    @app.get("/api/jobs")
    def list_jobs(status: str | None = None) -> list[dict[str, Any]]:
        return db.list_jobs(status=status)

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(404, "Trabajo no encontrado")
        return job

    @app.delete("/api/jobs/{job_id}", status_code=204)
    def delete_job(job_id: str) -> None:
        """Cancela un trabajo en cola, o borra uno terminado junto con sus archivos."""
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(404, "Trabajo no encontrado")
        if job["status"] == "running":
            raise HTTPException(409, "El trabajo está en proceso y no se puede detener.")
        if job["status"] == "pending":
            jobs.cancel(job_id)
            return
        db.delete_job(job_id)
        if job["song_id"]:
            shutil.rmtree(settings.songs_dir / job["song_id"] / "separations" / job_id, ignore_errors=True)

    # --- Stems y descargas -----------------------------------------------------

    @app.get("/api/stems/{stem_id}/preview")
    def stem_preview(stem_id: str) -> FileResponse:
        return FileResponse(data_file(stem_or_404(stem_id)["preview_path"]), media_type="audio/mpeg")

    @app.get("/api/stems/{stem_id}/download")
    def stem_download(stem_id: str) -> FileResponse:
        stem = stem_or_404(stem_id)
        song = song_or_404(stem["song_id"])
        return FileResponse(
            data_file(stem["wav_path"]), media_type="audio/wav", filename=stem_download_name(song, stem)
        )

    @app.get("/api/separations/{job_id}/zip")
    def separation_zip(job_id: str, include_drum_parts: bool = True) -> FileResponse:
        job = db.get_job(job_id)
        if not job or job["status"] != "done":
            raise HTTPException(404, "Separación no encontrada o sin terminar")
        song = song_or_404(job["song_id"])
        stems = [s for s in db.list_stems(job_id=job_id) if include_drum_parts or s["kind"] != "drum_part"]
        fd, tmp_name = tempfile.mkstemp(suffix=".zip", dir=settings.work_dir)
        os.close(fd)
        tmp = Path(tmp_name)
        filename = build_stems_zip(song, stems, settings.data_dir, tmp)
        return FileResponse(
            tmp, media_type="application/zip", filename=filename, background=BackgroundTask(tmp.unlink, missing_ok=True)
        )

    return app


def run() -> FastAPI:
    """Punto de entrada de uvicorn: `uvicorn app.main:run --factory`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return create_app()
