# AwowMusic — Estudio Musical

## Objetivo del proyecto

AwowMusic es una **herramienta de ideación musical que alimenta al DAW**, no un DAW nuevo. Separa canciones en stems, analiza BPM/tonalidad/compás, mezcla ideas entre dos canciones y genera patrones rítmicos. Todo sale en **WAV 24-bit y MIDI tipo 1** listos para arrastrar a FL Studio o Ableton (el DAW principal aún no está definido: validar compatibilidad con ambos).

**Finalidad:** uso personal para producir **y** proyecto de portafolio en GitHub. Por eso importan las dos cosas: que funcione bien en la laptop del autor y que el repositorio se vea profesional (README claro, código limpio y tipado, tests).

La especificación completa, fases y criterios de "terminado" están en [Estudio Musical — Plan de trabajo.md](Estudio%20Musical%20—%20Plan%20de%20trabajo.md). Ese documento manda; este archivo resume el contexto y registra las decisiones tomadas encima del plan.

## Principios (del plan)

1. **Libertad total para explorar ritmos** — manda sobre todo: sin límites de pistas, compases, compás o tempo (40–300 BPM). La app nunca dice "no puedes".
2. **El DAW termina la canción** — nada de mastering, VST ni mezcla final aquí.
3. **Todo lo que sale es estándar** — ver "Estándar de exportación" abajo.
4. **Local primero** — corre en la laptop, sin servidor ni subir canciones a la nube.
5. **Tú decides, la IA propone** — la IA es opcional y nunca bloquea la edición manual.
6. **Cada fase entrega algo usable** — no saltar fases, no dejar módulos a medias.

## Decisiones tomadas (2026-09-29)

| Tema | Decisión |
| --- | --- |
| Código previo | Se empieza **desde cero**. Las tareas marcadas `[x]` en el plan no existen en el repo y se rehacen. |
| Alcance actual | **Fase 0 + Fase 1** (base del proyecto y separador listo para DAW). Luego se revisa y se sigue. |
| Estructura | Código en la **raíz del repo**: `backend/`, `frontend/`, `samples/`, `setup.bat`, `iniciar.bat` (no dentro de `music-studio/`). |
| Frontend | **React + Vite + TypeScript**. |
| PyTorch/CUDA | **PyTorch 2.14 + CUDA 13.0 (cu130)**, la estable más nueva, en lugar de 12.1. torchaudio no se usa (dejó de publicarse tras la 2.11). |
| IA (Fase 4b) | **Por decidir.** Diseñar una interfaz de proveedor genérica (Claude API / Ollama) sin acoplarse a ninguno. |
| Git | Commits por tarea; **commit + push a `origin/main` al cerrar cada fase**. |
| Pruebas con audio real | Las hace el autor con sus canciones. Los tests automáticos usan audio sintético generado. |
| DAW de validación | No definido aún: exportes compatibles con FL Studio y Ableton. |

## Interfaz

- Idioma: **español** (textos, mensajes de error, etiquetas).
- Tema **oscuro** estilo DAW, con paleta basada en:
  - `#8C1918` rojo oscuro (acento principal: acciones, grabar, pistas activas)
  - `#06981A` verde (estado OK, reproducir, sincronía, compatibilidad)
  - Fondos casi negros/grises neutros; los dos acentos deben combinar sin saturar (usar variantes más claras/oscuras para hover y texto con buen contraste).
- Definir los colores como variables CSS en un solo lugar.

## Entorno del autor

- Windows 11, laptop con **NVIDIA RTX 4070 Laptop (8 GB VRAM)**, driver 616.
- Python 3.12 (también 3.13/3.14 instalados; el venv usa **3.12**), Node 24, npm 11, ffmpeg 9 en PATH.
- Scripts de arranque en `.bat` (setup e iniciar). Un solo trabajo de GPU a la vez; con 8 GB procesar por segmentos y hacer fallback a Demucs si falta memoria.

## Stack

FastAPI + Uvicorn · audio-separator (Demucs, Mel-/BS-RoFormer) sobre PyTorch CUDA · librosa + essentia/madmom · basic-pitch · mido/pretty_midi + music21 · pedalboard, soundfile, ffmpeg · SQLite · React + Vite + TS · Tone.js + Wavesurfer.js.

## Estándar de exportación

- Stems: WAV PCM 24-bit, misma frecuencia y duración que la original, arrancan en 0 ms.
- Mezcla: WAV 24-bit 44.1 kHz, headroom -1 dBFS, sin limitador.
- MIDI: tipo 1, 480 PPQ, tempo y compás en la pista 0, batería en canal 10 (General MIDI).
- MP3 192 kbps solo para vista previa en el navegador, nunca en descargas ni paquetes.
- Nombres: `Titulo_Pista_BPM_Tonalidad.wav` (ej. `MiCancion_Vocals_95BPM_Am.wav`), sin tildes ni espacios.

## Trampas conocidas del entorno

- `requirements.txt` fija `torch==2.14.0+cu130` con `--extra-index-url`: sin eso, pip reemplaza PyTorch CUDA por la versión de PyPI que solo usa CPU.
- **Smart App Control** está activo en la laptop y bloquea DLL sin reputación (numba 0.67 `_box.pyd`). Por eso numba 0.66 y numpy 2.4.x (numba 0.66 exige numpy < 2.5). Antes de subir versiones con extensiones nativas, verificar que importen.
- librosa 1.0 ya no instala `audioread`, pero audio-separator lo importa: está en requirements.
- Demucs no suma exactamente la original (~-20 dB de residuo). La opción «suma exacta» (activa por defecto) agrega el residuo a Other/Instrumental; la prueba de nulidad se mide sobre los WAV ya guardados.
- Para capturas del frontend con Edge headless, usar un `--user-data-dir` aislado con `--disable-sync --no-first-run`, porque Edge inicia sesión y sincroniza la cuenta del usuario, y borrar ese perfil al terminar.

## Comandos

- Backend: `backend\.venv\Scripts\python -m pytest` (rápido) · `-m gpu -s` (separación real) · servidor: `uvicorn app.main:run --factory`
- Frontend: `npm run dev` · `npm run build` (incluye typecheck)

## Convenciones

- `backend/data/` (audio y base de datos) fuera de git.
- Actualizar las casillas del plan al completar cada tarea.
