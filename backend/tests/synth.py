"""Audio sintético para tests: batería, bajo y una "voz" con vibrato."""

from pathlib import Path

import numpy as np
import soundfile as sf


def make_song(seconds: float = 8.0, sr: int = 48000, bpm: float = 95.0, channels: int = 2) -> np.ndarray:
    rng = np.random.default_rng(7)
    t = np.arange(int(seconds * sr)) / sr
    beat = 60.0 / bpm
    mix = np.zeros_like(t)

    for i, start in enumerate(np.arange(0, seconds, beat / 2)):
        n0 = int(start * sr)
        n = min(len(t) - n0, int(0.12 * sr))
        env = np.exp(-np.linspace(0, 8, n))
        if i % 4 == 0:  # bombo
            mix[n0 : n0 + n] += 0.6 * np.sin(2 * np.pi * 55 * t[:n] * (1 + 2 * env)) * env
        elif i % 4 == 2:  # caja
            mix[n0 : n0 + n] += 0.3 * rng.standard_normal(n) * env
        else:  # hi-hat
            mix[n0 : n0 + n] += 0.08 * rng.standard_normal(n) * env**3

    notes = [110.0, 110.0, 130.81, 98.0]
    idx = (t // (beat * 4)).astype(int) % len(notes)
    mix += 0.25 * np.sin(2 * np.pi * np.array(notes)[idx] * t)

    vib = 1 + 0.01 * np.sin(2 * np.pi * 5.5 * t)
    mix += 0.2 * np.sin(2 * np.pi * 440 * vib * t) * (np.sin(2 * np.pi * t / (beat * 2)) > 0)

    mix = 0.8 * mix / np.max(np.abs(mix))
    stereo = np.stack([mix, 0.9 * mix], axis=1) if channels == 2 else mix[:, None]
    return stereo.astype(np.float32)


def write_song(path: Path, seconds: float = 8.0, sr: int = 48000, channels: int = 2, subtype: str = "PCM_24") -> Path:
    sf.write(str(path), make_song(seconds, sr, channels=channels), sr, subtype=subtype)
    return path
