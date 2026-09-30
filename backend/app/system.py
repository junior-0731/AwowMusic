"""Información del sistema: GPU, PyTorch y ffmpeg."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .audio_io import ffmpeg_path


@lru_cache(maxsize=1)
def gpu_info() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"available": False, "name": None, "vram_gb": None, "torch": None, "cuda": None}
    info: dict[str, Any] = {
        "available": torch.cuda.is_available(),
        "name": None,
        "vram_gb": None,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }
    if info["available"]:
        props = torch.cuda.get_device_properties(0)
        info["name"] = props.name
        info["vram_gb"] = round(props.total_memory / 1024**3, 1)
    return info


def system_status() -> dict[str, Any]:
    return {"gpu": gpu_info(), "ffmpeg": ffmpeg_path() is not None}
