"""Lectura, escritura y conversión de audio con soundfile y ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from .jobs import UserError

SILENCE_DB = -200.0


@dataclass
class AudioInfo:
    sample_rate: int
    channels: int
    frames: int

    @property
    def duration(self) -> float:
        return self.frames / self.sample_rate


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def _ffmpeg(*args: str) -> None:
    exe = ffmpeg_path()
    if not exe:
        raise UserError("No se encontró ffmpeg. Ejecuta setup.bat o instala ffmpeg y agrégalo al PATH.")
    proc = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise UserError(f"ffmpeg no pudo procesar el audio: {proc.stderr.strip()[-300:] or 'error desconocido'}")


def decode_to_wav(src: Path, dst: Path) -> AudioInfo:
    """Decodifica cualquier formato a WAV float32 conservando frecuencia y canales."""
    try:
        _ffmpeg("-i", str(src), "-vn", "-map", "0:a:0", "-c:a", "pcm_f32le", str(dst))
    except UserError as e:
        raise UserError("El archivo no se pudo leer como audio. ¿Está dañado o no es un formato de audio?") from e
    info = sf.info(str(dst))
    if info.frames == 0:
        raise UserError("El archivo no contiene audio.")
    return AudioInfo(info.samplerate, info.channels, info.frames)


def make_preview(src: Path, dst: Path, bitrate: str = "192k") -> None:
    """MP3 solo para escuchar en el navegador; nunca se descarga ni va al paquete."""
    _ffmpeg("-i", str(src), "-c:a", "libmp3lame", "-b:a", bitrate, str(dst))


def read(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data, sr


def write_wav24(path: Path, data: np.ndarray, sample_rate: int) -> None:
    sf.write(str(path), data, sample_rate, subtype="PCM_24", format="WAV")


def conform(data: np.ndarray, frames: int, channels: int) -> np.ndarray:
    """Ajusta un stem a la duración y canales exactos de la original (arranca en 0, mismo largo)."""
    if data.shape[1] != channels:
        if channels == 1:
            data = data.mean(axis=1, keepdims=True)
        elif data.shape[1] == 1:
            data = np.repeat(data, channels, axis=1)
        else:
            data = data[:, :channels]
    if len(data) > frames:
        data = data[:frames]
    elif len(data) < frames:
        data = np.pad(data, ((0, frames - len(data)), (0, 0)))
    return np.ascontiguousarray(data, dtype=np.float32)


def rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(data, dtype=np.float64))))


def to_db(value: float) -> float:
    return SILENCE_DB if value <= 0 else max(SILENCE_DB, float(20 * np.log10(value)))


def null_test_db(original: np.ndarray, stems: list[np.ndarray]) -> float:
    """Error de la suma de stems contra la original, en dB relativos (más negativo = mejor)."""
    residual = original.astype(np.float64) - np.sum([s.astype(np.float64) for s in stems], axis=0)
    ref = rms(original)
    if ref == 0:
        return SILENCE_DB
    return round(to_db(rms(residual) / ref), 2)


def peak(data: np.ndarray) -> float:
    return float(np.max(np.abs(data))) if data.size else 0.0
