"""Catálogo de modelos de separación que ofrece la app (todos vía audio-separator)."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SeparationModel:
    id: str
    label: str
    filename: str
    description: str
    stems: list[str]
    # Stem que absorbe el residuo para que la suma sea idéntica a la original ("" = sin corrección).
    residual_stem: str
    experimental: bool = False
    vram_note: str = ""
    kind: str = "song"

    def public(self) -> dict:
        d = asdict(self)
        d.pop("filename")
        return d


MODELS: dict[str, SeparationModel] = {
    m.id: m
    for m in [
        SeparationModel(
            id="demucs_4",
            label="Demucs 4 pistas",
            filename="htdemucs_ft.yaml",
            description="Voz, batería, bajo y otros. El más equilibrado para producir.",
            stems=["Vocals", "Drums", "Bass", "Other"],
            residual_stem="Other",
        ),
        SeparationModel(
            id="demucs_6",
            label="Demucs 6 pistas",
            filename="htdemucs_6s.yaml",
            description="Agrega guitarra y piano. El piano puede salir con artefactos.",
            stems=["Vocals", "Drums", "Bass", "Guitar", "Piano", "Other"],
            residual_stem="Other",
        ),
        SeparationModel(
            id="roformer_vocals",
            label="RoFormer voz",
            filename="model_bs_roformer_ep_317_sdr_12.9755.ckpt",
            description="Voz e instrumental. Las voces más limpias; ideal para acapellas.",
            stems=["Vocals", "Instrumental"],
            residual_stem="Instrumental",
            vram_note="Usa más memoria de GPU; si falla se reintenta con Demucs.",
        ),
    ]
}

DRUM_MODEL = SeparationModel(
    id="drumsep",
    label="Dividir batería (experimental)",
    filename="MDX23C-DrumSep-aufr33-jarredou.ckpt",
    description="Divide el stem de batería en kick, snare, toms, hi-hat, ride y crash. Calidad variable.",
    stems=["Kick", "Snare", "Toms", "HiHat", "Ride", "Crash"],
    residual_stem="",  # sin corrección: el stem completo de batería siempre queda disponible
    experimental=True,
    kind="drum_part",
)

FALLBACK_MODEL_ID = "demucs_4"

# Nombres que devuelve audio-separator -> nombres de la app.
STEM_ALIASES = {
    "vocals": "Vocals",
    "vocal": "Vocals",
    "drums": "Drums",
    "bass": "Bass",
    "other": "Other",
    "guitar": "Guitar",
    "piano": "Piano",
    "instrumental": "Instrumental",
    "no vocals": "Instrumental",
    "kick": "Kick",
    "snare": "Snare",
    "toms": "Toms",
    "tom": "Toms",
    "hh": "HiHat",
    "hihat": "HiHat",
    "hi-hat": "HiHat",
    "ride": "Ride",
    "crash": "Crash",
    "cymbals": "Cymbals",
}


def canonical_stem(name: str) -> str:
    key = name.strip().lower()
    return STEM_ALIASES.get(key, name.strip().title().replace(" ", ""))
