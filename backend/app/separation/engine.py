"""Separación de stems: motor audio-separator + post-proceso listo para DAW.

El post-proceso garantiza el estándar de exportación: WAV 24-bit, misma frecuencia,
canales y duración que la original, arrancando en 0 ms, y que la suma de stems
reconstruye la original (prueba de nulidad).
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .. import audio_io
from ..config import Settings
from ..db import Database
from ..jobs import JobContext, UserError
from .models import DRUM_MODEL, FALLBACK_MODEL_ID, MODELS, SeparationModel, canonical_stem

log = logging.getLogger(__name__)

_STEM_IN_FILENAME = re.compile(r"_\(([^)]+)\)")


class SeparatorBackend(Protocol):
    def separate(self, audio: Path, out_dir: Path, model: SeparationModel, sample_rate: int) -> dict[str, Path]:
        """Separa `audio` y devuelve {nombre de stem: ruta del archivo}."""
        ...


class GpuOutOfMemory(Exception):
    pass


class AudioSeparatorBackend:
    """Carga Demucs y RoFormer con la misma interfaz a través de audio-separator (la librería de UVR)."""

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir

    def separate(self, audio: Path, out_dir: Path, model: SeparationModel, sample_rate: int) -> dict[str, Path]:
        from audio_separator.separator import Separator  # import pesado: solo al separar

        out_dir.mkdir(parents=True, exist_ok=True)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=str(self.models_dir),
            output_dir=str(out_dir),
            output_format="WAV",
            sample_rate=sample_rate,
            # soundfile respeta la profundidad de la entrada (float32), así no se pierde resolución
            # antes del post-proceso a 24-bit.
            use_soundfile=True,
        )
        try:
            separator.load_model(model_filename=model.filename)
            files = separator.separate(str(audio))
        except Exception as e:
            if _is_oom(e):
                raise GpuOutOfMemory(str(e)) from e
            raise
        finally:
            _free_gpu()

        stems: dict[str, Path] = {}
        for f in files:
            path = Path(f)
            if not path.is_absolute():
                path = out_dir / path
            match = _STEM_IN_FILENAME.search(path.stem)
            name = canonical_stem(match.group(1) if match else path.stem)
            stems[name] = path
        return stems


def _is_oom(e: BaseException) -> bool:
    text = f"{type(e).__name__} {e}".lower()
    return "out of memory" in text or "outofmemory" in text


def _free_gpu() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


@dataclass
class StemAudio:
    name: str
    data: np.ndarray


def fix_residual(original: np.ndarray, stems: list[StemAudio], residual_stem: str) -> None:
    """Suma el residuo (original - suma de stems) al stem indicado para que la suma sea exacta."""
    target = next((s for s in stems if s.name == residual_stem), stems[-1])
    residual = original - np.sum([s.data for s in stems], axis=0)
    target.data = (target.data + residual).astype(np.float32)


class SeparationService:
    def __init__(self, db: Database, settings: Settings, backend: SeparatorBackend):
        self.db = db
        self.settings = settings
        self.backend = backend

    def handle(self, ctx: JobContext) -> dict[str, Any]:
        params = ctx.params
        model = MODELS.get(params.get("model", ""))
        if not model:
            raise UserError(f"Modelo desconocido: {params.get('model')}")
        song = self.db.get_song(ctx.job["song_id"])
        if not song:
            raise UserError("La canción ya no existe en la biblioteca.")

        song_dir = self.settings.songs_dir / song["id"]
        source = song_dir / "source.wav"
        if not source.exists():
            raise UserError("No se encontró el audio original de la canción. Vuelve a subirla.")
        out_dir = song_dir / "separations" / ctx.job["id"]
        work_dir = self.settings.work_dir / ctx.job["id"]
        warnings: list[str] = []

        try:
            original, sr = audio_io.read(source)
            ctx.progress(0.05, f"Separando con {model.label} (puede tardar varios minutos)")
            try:
                raw = self.backend.separate(source, work_dir / "main", model, sr)
            except GpuOutOfMemory:
                if model.id == FALLBACK_MODEL_ID:
                    raise UserError(
                        "La GPU se quedó sin memoria. Cierra otros programas que usen la GPU e intenta de nuevo."
                    ) from None
                warnings.append(f"{model.label} no cupo en la memoria de la GPU; se usó Demucs 4 pistas.")
                model = MODELS[FALLBACK_MODEL_ID]
                ctx.progress(0.1, f"Sin memoria de GPU, reintentando con {model.label}")
                raw = self.backend.separate(source, work_dir / "fallback", model, sr)

            ctx.progress(0.75, "Escribiendo WAV 24-bit")
            stems = self._load(raw, model, len(original), original.shape[1])
            fix = bool(params.get("fix_residual", True)) and bool(model.residual_stem)
            report = self._finalize(ctx, song, model, original, sr, stems, out_dir, fix, warnings)

            if params.get("drum_split") and "Drums" in raw:
                ctx.progress(0.85, "Dividiendo la batería (experimental)")
                report["drum_split"] = self._split_drums(ctx, song, out_dir, sr, warnings)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        report["warnings"] = warnings
        return report

    def _load(self, raw: dict[str, Path], model: SeparationModel, frames: int, channels: int) -> list[StemAudio]:
        if not raw:
            raise UserError("El modelo no devolvió ninguna pista.")
        order = {name: i for i, name in enumerate(model.stems)}
        stems = []
        for name, path in sorted(raw.items(), key=lambda kv: order.get(kv[0], len(order))):
            data, _ = audio_io.read(path)
            stems.append(StemAudio(name, audio_io.conform(data, frames, channels)))
        return stems

    def _finalize(
        self,
        ctx: JobContext,
        song: dict[str, Any],
        model: SeparationModel,
        original: np.ndarray,
        sr: int,
        stems: list[StemAudio],
        out_dir: Path,
        fix: bool,
        warnings: list[str],
    ) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        null_before = audio_io.null_test_db(original, [s.data for s in stems])
        if fix:
            fix_residual(original, stems, model.residual_stem)

        written = []
        for i, stem in enumerate(stems):
            p = audio_io.peak(stem.data)
            if p > 1.0:
                warnings.append(
                    f"{stem.name} pasa de 0 dBFS (pico {audio_io.to_db(p):+.1f} dB) y se recorta al guardar en 24-bit."
                )
            wav = out_dir / f"{stem.name}.wav"
            audio_io.write_wav24(wav, stem.data, sr)
            ctx.progress(0.75 + 0.1 * (i + 0.5) / len(stems), f"Vista previa de {stem.name}")
            preview = out_dir / f"{stem.name}.mp3"
            audio_io.make_preview(wav, preview, self.settings.preview_bitrate)
            self.db.create_stem(
                song_id=song["id"],
                job_id=ctx.job["id"],
                name=stem.name,
                kind=model.kind,
                model=model.id,
                experimental=model.experimental,
                wav_path=self._rel(wav),
                preview_path=self._rel(preview),
                peak=round(p, 4),
                position=i if model.kind == "song" else 100 + i,
            )
            written.append(wav)

        # La prueba se hace con los archivos ya guardados, tal como llegan al DAW.
        null_after = audio_io.null_test_db(original, [audio_io.read(w)[0] for w in written])
        return {
            "model": model.id,
            "model_label": model.label,
            "stems": [s.name for s in stems],
            "sample_rate": sr,
            "residual_fixed": fix,
            "null_test_raw_db": null_before,
            "null_test_db": null_after,
            "null_test_passed": bool(null_after < -40),
        }

    def _split_drums(
        self, ctx: JobContext, song: dict[str, Any], out_dir: Path, sr: int, warnings: list[str]
    ) -> dict[str, Any] | None:
        drums_wav = out_dir / "Drums.wav"
        drums, _ = audio_io.read(drums_wav)
        try:
            raw = self.backend.separate(drums_wav, self.settings.work_dir / ctx.job["id"] / "drums", DRUM_MODEL, sr)
        except GpuOutOfMemory:
            warnings.append("No hubo memoria de GPU para dividir la batería; el stem completo sí está disponible.")
            return None
        except Exception as e:  # noqa: BLE001 - la división es opcional, nunca tumba la separación
            log.exception("Falló la división de batería")
            warnings.append(f"No se pudo dividir la batería ({e}); el stem completo sí está disponible.")
            return None
        parts = self._load(raw, DRUM_MODEL, len(drums), drums.shape[1])
        return self._finalize(ctx, song, DRUM_MODEL, drums, sr, parts, out_dir, False, warnings)

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.settings.data_dir).as_posix()
