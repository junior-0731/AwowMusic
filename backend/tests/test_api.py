import io
import zipfile

import soundfile as sf


def upload(client, path):
    with path.open("rb") as f:
        r = client.post("/api/songs", files={"file": (path.name, f, "audio/wav")})
    assert r.status_code == 201, r.text
    return r.json()


def separate(client, song_id, **body):
    r = client.post(f"/api/songs/{song_id}/separate", json={"model": "demucs_4", **body})
    assert r.status_code == 202, r.text
    client.app.state.jobs.wait_idle()
    return client.get(f"/api/jobs/{r.json()['id']}").json()


def test_health_y_modelos(client):
    assert client.get("/api/health").json()["status"] == "ok"
    models = client.get("/api/models").json()
    assert {m["id"] for m in models["models"]} == {"demucs_4", "demucs_6", "roformer_vocals"}
    assert "filename" not in models["models"][0]


def test_subir_cancion(client, song_wav):
    song = upload(client, song_wav)
    assert song["title"] == "Mi Canción"
    assert (song["sample_rate"], song["channels"]) == (48000, 2)
    assert client.get(f"/api/songs/{song['id']}/preview").headers["content-type"] == "audio/mpeg"
    assert [s["id"] for s in client.get("/api/songs").json()] == [song["id"]]


def test_rechaza_formato_y_archivo_danado(client, tmp_path):
    bad = tmp_path / "notas.txt"
    bad.write_text("hola")
    assert client.post("/api/songs", files={"file": (bad.name, bad.open("rb"))}).status_code == 415
    broken = tmp_path / "rota.mp3"
    broken.write_bytes(b"esto no es audio" * 100)
    r = client.post("/api/songs", files={"file": (broken.name, broken.open("rb"))})
    assert r.status_code == 422 and "dañado" in r.json()["detail"]
    assert client.get("/api/songs").json() == []


def test_separacion_lista_para_daw(client, song_wav, settings):
    song = upload(client, song_wav)
    job = separate(client, song["id"])
    assert job["status"] == "done", job
    result = job["result"]
    # El backend falso deja un error de ~-40 dB; la corrección de residuo lo lleva a nulo.
    assert result["null_test_raw_db"] > -45
    assert result["null_test_db"] < -90 and result["null_test_passed"]

    seps = client.get(f"/api/songs/{song['id']}/separations").json()
    stems = seps[0]["stems"]
    assert [s["name"] for s in stems] == ["Vocals", "Drums", "Bass", "Other"]
    original = sf.info(str(song_wav))
    for s in stems:
        info = sf.info(str(settings.data_dir / s["wav_path"]))
        assert info.subtype == "PCM_24"
        assert (info.samplerate, info.channels, info.frames) == (original.samplerate, original.channels, original.frames)


def test_sin_correccion_de_residuo(client, song_wav):
    song = upload(client, song_wav)
    result = separate(client, song["id"], fix_residual=False)["result"]
    assert not result["residual_fixed"] and not result["null_test_passed"]


def test_nombres_de_descarga_y_zip(client, song_wav):
    song = upload(client, song_wav)
    job = separate(client, song["id"])
    client.patch(f"/api/songs/{song['id']}", json={"title": "Mi Canción", "bpm": 95, "musical_key": "Am"})
    stem = client.get(f"/api/songs/{song['id']}/separations").json()[0]["stems"][0]

    r = client.get(f"/api/stems/{stem['id']}/download")
    assert r.status_code == 200
    assert 'filename="MiCancion_Vocals_95BPM_Am.wav"' in r.headers["content-disposition"]

    r = client.get(f"/api/separations/{job['id']}/zip")
    assert 'filename="MiCancion_95BPM_Am.zip"' in r.headers["content-disposition"]
    names = sorted(zipfile.ZipFile(io.BytesIO(r.content)).namelist())
    assert names == sorted(f"MiCancion_95BPM_Am/MiCancion_{n}_95BPM_Am.wav" for n in ["Vocals", "Drums", "Bass", "Other"])


def test_division_de_bateria_experimental(client, song_wav, backend):
    song = upload(client, song_wav)
    job = separate(client, song["id"], drum_split=True)
    assert backend.calls == ["demucs_4", "drumsep"]
    assert job["result"]["drum_split"]["stems"] == ["Kick", "Snare", "Toms", "HiHat", "Ride", "Crash"]
    stems = client.get(f"/api/songs/{song['id']}/separations").json()[0]["stems"]
    parts = [s for s in stems if s["kind"] == "drum_part"]
    assert len(parts) == 6 and all(s["experimental"] for s in parts)

    names = zipfile.ZipFile(io.BytesIO(client.get(f"/api/separations/{job['id']}/zip").content)).namelist()
    assert "MiCancion/Bateria_Experimental/MiCancion_Kick.wav" in names


def test_fallback_a_demucs_si_no_hay_memoria(client, song_wav, backend):
    from app.separation.engine import GpuOutOfMemory

    original = backend.separate

    def oom_for_roformer(audio, out_dir, model, sr):
        if model.id == "roformer_vocals":
            raise GpuOutOfMemory("CUDA out of memory")
        return original(audio, out_dir, model, sr)

    backend.separate = oom_for_roformer
    song = upload(client, song_wav)
    job = separate(client, song["id"], model="roformer_vocals")
    assert job["status"] == "done"
    assert job["result"]["model"] == "demucs_4"
    assert "memoria" in job["result"]["warnings"][0]


def test_borrar_cancion(client, song_wav, settings):
    song = upload(client, song_wav)
    separate(client, song["id"])
    assert client.delete(f"/api/songs/{song['id']}").status_code == 204
    assert client.get(f"/api/songs/{song['id']}").status_code == 404
    assert not (settings.songs_dir / song["id"]).exists()
