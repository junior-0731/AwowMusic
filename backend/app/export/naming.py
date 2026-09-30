"""Nombres de archivo seguros para cualquier DAW: Titulo_Pista_BPM_Tonalidad.wav."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def ascii_clean(text: str) -> str:
    """Quita tildes y cualquier carácter que no sea ASCII."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def slug(text: str, fallback: str = "Cancion") -> str:
    """'Mi canción (demo)' -> 'MiCancionDemo'. Sin espacios, tildes ni símbolos."""
    words = [w for w in _NON_ALNUM.split(ascii_clean(text)) if w]
    result = "".join(w[:1].upper() + w[1:] for w in words)
    return result[:60] or fallback


def format_bpm(bpm: float | None) -> str | None:
    if not bpm:
        return None
    return f"{round(bpm, 2):g}".replace(".", "p") + "BPM"


def format_key(key: str | None) -> str | None:
    """'A minor' / 'Am' / 'F# m' / 'Bb' -> 'Am', 'Am', 'Fsm', 'Bb'."""
    if not key:
        return None
    k = key.strip()
    k = re.sub(r"\s*(minor|min|menor|m)$", "m", k, flags=re.IGNORECASE)
    k = re.sub(r"\s*(major|maj|mayor)$", "", k, flags=re.IGNORECASE)
    k = k.replace("#", "s").replace("♯", "s").replace("♭", "b")
    return slug(k, fallback="") or None


def stem_filename(title: str, part: str, bpm: float | None = None, key: str | None = None, ext: str = "wav") -> str:
    pieces = [slug(title), slug(part, fallback="Pista"), format_bpm(bpm), format_key(key)]
    return "_".join(p for p in pieces if p) + f".{ext}"


def package_name(title: str, bpm: float | None = None, key: str | None = None) -> str:
    pieces = [slug(title), format_bpm(bpm), format_key(key)]
    return "_".join(p for p in pieces if p)
