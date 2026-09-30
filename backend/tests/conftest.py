from pathlib import Path

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.separation.models import SeparationModel

from .synth import make_song


class FakeBackend:
    """Imita a audio-separator: divide la mezcla en porciones fijas y agrega un pequeño error."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def separate(self, audio: Path, out_dir: Path, model: SeparationModel, sample_rate: int) -> dict[str, Path]:
        self.calls.append(model.id)
        data, sr = sf.read(str(audio), dtype="float32", always_2d=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        share = 1.0 / len(model.stems)
        result = {}
        for name in model.stems:
            # Stem desplazado de largo (como hacen los modelos) y con un error de 1 %.
            stem = data[: len(data) - 100] * share * 0.99
            path = out_dir / f"song_({name.lower()})_{model.filename}.wav"
            sf.write(str(path), stem, sr, subtype="FLOAT")
            result[name] = path
        return result


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data")


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def client(settings: Settings, backend: FakeBackend):
    app = create_app(settings, backend)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def song_wav(tmp_path: Path) -> Path:
    path = tmp_path / "Mi Canción.wav"
    sf.write(str(path), make_song(4.0), 48000, subtype="PCM_24")
    return path
