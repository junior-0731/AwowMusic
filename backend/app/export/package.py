"""ZIP de stems con nombres listos para DAW."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from .naming import package_name, stem_filename

DRUM_PARTS_FOLDER = "Bateria_Experimental"


def stem_download_name(song: dict[str, Any], stem: dict[str, Any]) -> str:
    return stem_filename(song["title"], stem["name"], song.get("bpm"), song.get("musical_key"))


def build_stems_zip(song: dict[str, Any], stems: list[dict[str, Any]], data_dir: Path, dest: Path) -> str:
    """Escribe el ZIP en `dest` y devuelve el nombre sugerido de descarga."""
    root = package_name(song["title"], song.get("bpm"), song.get("musical_key"))
    # WAV casi no se comprime: ZIP_STORED es mucho más rápido y el tamaño es similar.
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as zf:
        for stem in stems:
            folder = f"{root}/{DRUM_PARTS_FOLDER}" if stem["kind"] == "drum_part" else root
            zf.write(data_dir / stem["wav_path"], f"{folder}/{stem_download_name(song, stem)}")
    return f"{root}.zip"
