"""Prueba real en GPU: descarga el modelo (una vez) y separa audio sintético.

Ejecutar con:  .venv\Scripts\python -m pytest -m gpu -s
"""

import time

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.config import BACKEND_DIR
from app.main import create_app
from app.separation.engine import AudioSeparatorBackend

from .synth import write_song

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize(
    ("model", "drum_split"), [("demucs_4", False), ("demucs_6", False), ("roformer_vocals", False), ("demucs_4", True)]
)
def test_separacion_real_suma_la_original(settings, tmp_path, model, drum_split):
    backend = AudioSeparatorBackend(BACKEND_DIR / "data" / "models")  # reutiliza modelos ya descargados
    song_path = write_song(tmp_path / "prueba.wav", seconds=20, sr=48000)
    with TestClient(create_app(settings, backend)) as client:
        song = client.post("/api/songs", files={"file": (song_path.name, song_path.open("rb"))}).json()
        start = time.perf_counter()
        job = client.post(f"/api/songs/{song['id']}/separate", json={"model": model, "drum_split": drum_split}).json()
        client.app.state.jobs.wait_idle()
        job = client.get(f"/api/jobs/{job['id']}").json()
        print(f"\n{model}: {time.perf_counter() - start:.1f} s -> {job.get('result') or job.get('error')}")

        assert job["status"] == "done", job["error"]
        assert job["result"]["null_test_db"] < -40
        if drum_split:
            assert job["result"]["drum_split"], job["result"]["warnings"]
        for stem in client.get(f"/api/songs/{song['id']}/separations").json()[0]["stems"]:
            info = sf.info(str(settings.data_dir / stem["wav_path"]))
            assert (info.subtype, info.samplerate, info.frames) == ("PCM_24", 48000, song["frames"])
