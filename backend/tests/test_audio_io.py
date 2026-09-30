import numpy as np
import soundfile as sf

from app import audio_io


def test_conform_recorta_rellena_y_ajusta_canales():
    stereo = np.ones((100, 2), dtype=np.float32)
    assert audio_io.conform(stereo, 80, 2).shape == (80, 2)
    padded = audio_io.conform(stereo, 120, 2)
    assert padded.shape == (120, 2) and np.all(padded[100:] == 0)
    assert audio_io.conform(stereo, 100, 1).shape == (100, 1)
    assert audio_io.conform(np.ones((100, 1), dtype=np.float32), 100, 2).shape == (100, 2)


def test_null_test():
    rng = np.random.default_rng(0)
    original = rng.standard_normal((1000, 2)).astype(np.float32) * 0.1
    assert audio_io.null_test_db(original, [original * 0.5, original * 0.5]) < -120
    assert abs(audio_io.null_test_db(original, [original * 0.9]) - (-20)) < 0.1


def test_wav24_se_guarda_en_24_bit(tmp_path):
    path = tmp_path / "x.wav"
    audio_io.write_wav24(path, np.zeros((10, 2), dtype=np.float32), 44100)
    info = sf.info(str(path))
    assert info.subtype == "PCM_24" and info.samplerate == 44100


def test_decode_conserva_frecuencia_y_canales(tmp_path, song_wav):
    info = audio_io.decode_to_wav(song_wav, tmp_path / "source.wav")
    assert (info.sample_rate, info.channels) == (48000, 2)
    assert info.frames == sf.info(str(song_wav)).frames
