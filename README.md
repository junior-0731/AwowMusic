# AwowMusic

Herramienta de ideación musical que alimenta a tu DAW. Separa canciones en stems, analiza, mezcla ideas y genera patrones, y todo sale en **WAV 24-bit y MIDI** listo para arrastrar a FL Studio o Ableton. Corre 100 % local en tu PC con GPU NVIDIA: sin servidores y sin subir canciones a la nube.

> Estado: **Fase 1 — Separador listo para DAW** ✅. Mezclador (Fase 3) y generador de beats (Fase 4) en camino. Ver el [plan de trabajo](Estudio%20Musical%20—%20Plan%20de%20trabajo.md).

## Qué hace hoy

- **Separación de stems** con tres modelos (vía [audio-separator](https://github.com/nomadkaraoke/python-audio-separator)):
  - Demucs 4 pistas: voz, batería, bajo y otros.
  - Demucs 6 pistas: agrega guitarra y piano.
  - BS-RoFormer: voz e instrumental, las voces más limpias.
- **Stems listos para el DAW**: WAV PCM 24-bit con la misma frecuencia (44,1/48 kHz), canales y duración que la original, arrancando en 0 ms.
- **Suma exacta**: los modelos no reconstruyen el 100 % de la canción (Demucs deja ~-20 dB de residuo). La app agrega esa diferencia a «Other» o «Instrumental» y comprueba con una prueba de nulidad que los stems guardados suman la original (normalmente < -110 dB).
- **División de batería (experimental)**: kick, snare, toms, hi-hat, ride y crash con MDX23C DrumSep.
- **Reproductor multipista** sincronizado con forma de onda, volumen, mute y solo por pista, más la original para comparar.
- **Descargas** individuales y en ZIP con nombres seguros para cualquier DAW: `MiCancion_Vocals_95BPM_Am.wav`.
- **Cola de trabajos** en SQLite: un trabajo a la vez en la GPU. Si la memoria no alcanza, reintenta con Demucs automáticamente.

## Requisitos

- Windows 10/11
- GPU NVIDIA con driver ≥ 580 (probado en RTX 4070 Laptop, 8 GB). Sin GPU funciona en CPU, mucho más lento.
- Python 3.12, Node.js 20+ y ffmpeg. `setup.bat` los instala con winget si faltan.

## Instalación y uso

```bat
setup.bat      :: crea el entorno, instala PyTorch CUDA 13.0 y las dependencias (~3 GB la primera vez)
iniciar.bat    :: levanta backend y frontend y abre http://localhost:5173
```

La primera separación con cada modelo descarga sus pesos a `backend/data/models/`.

## Arquitectura

```
backend/            FastAPI + PyTorch (Python 3.12)
  app/
    main.py         rutas de la API
    jobs.py         cola de trabajos (un hilo, uno a la vez en GPU)
    db.py           SQLite con migraciones (canciones, trabajos, stems)
    audio_io.py     ffmpeg/soundfile: decodificar, WAV 24-bit, MP3 de vista previa, prueba de nulidad
    separation/     catálogo de modelos y motor de separación + post-proceso
    export/         nombres de archivo y ZIP
  tests/            pytest (audio sintético; `-m gpu` para pruebas reales en GPU)
  data/             audio, modelos y base de datos (fuera de git)
frontend/           React + Vite + TypeScript
  src/modules/      separator/, mixer/, beats/
  src/shared/       cliente de API, reproductor multipista, forma de onda
```

| Capa | Tecnología |
| --- | --- |
| API | FastAPI, Uvicorn |
| Separación | audio-separator (Demucs v4, BS-RoFormer, MDX23C DrumSep), PyTorch 2.14 + CUDA 13.0 |
| Audio | soundfile, ffmpeg, numpy |
| Datos | SQLite |
| Interfaz | React 19, Vite, TypeScript, Web Audio API |

## Estándar de exportación

| Tipo | Formato |
| --- | --- |
| Stems | WAV PCM 24-bit, misma frecuencia y duración que la original, desde 0 ms |
| Vista previa | MP3 192 kbps, solo dentro de la app |
| Nombres | `Titulo_Pista_BPM_Tonalidad.wav`, sin tildes ni espacios |

## Desarrollo

```bat
cd backend
.venv\Scripts\python -m pytest              :: tests rápidos (motor de separación simulado)
.venv\Scripts\python -m pytest -m gpu -s    :: separación real en GPU con todos los modelos

cd frontend
npm run dev          :: interfaz con recarga en caliente
npm run typecheck
```

Documentación interactiva de la API en http://127.0.0.1:8000/docs mientras el backend corre.

## Notas

- **Smart App Control de Windows** bloquea la DLL de numba 0.67, así que queda fijado numba 0.66 (y numpy 2.4). Ver `backend/requirements.txt`.
- Los stems de canciones comerciales son para estudiar y practicar. Lo que publiques, hazlo con tus propios samples o con material con licencia.
