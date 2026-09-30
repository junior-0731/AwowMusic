# Estudio Musical — Plan de trabajo

Sep 29, 2026 · @JrDeveloper

La app es una herramienta de ideación que alimenta a tu DAW, no un DAW nuevo: separa, analiza, mezcla ideas y genera patrones, y todo sale en WAV y MIDI listos para FL Studio o Ableton. Se construye en 6 fases; al final de cada una tienes algo que ya puedes usar.

## Visión y principios

- **Libertad total para explorar ritmos.** Es el principio que manda sobre los demás: una biblioteca enorme de géneros y patrones, cualquier compás, cualquier tempo, capas mezclables entre géneros y ningún límite de pistas o compases. La app nunca le dice al usuario qué no puede hacer.
- **El DAW termina la canción.** La mezcla final, los VST y la masterización viven en FL Studio o Ableton. La app no intenta reemplazar eso.
- **Todo lo que sale es estándar.** Audio en WAV 24-bit, notas en MIDI tipo 1, y el BPM y la tonalidad escritos en el nombre del archivo y en el MIDI.
- **Local primero.** Corre en tu laptop (RTX 4070, 8 GB): sin costos de servidor y sin subir canciones a la nube.
- **Tú decides, la IA propone.** La IA es opcional: sugiere, sorprende y abre caminos, pero nunca bloquea, restringe ni reemplaza la edición manual.
- **Cada fase entrega algo usable.** Mejor un separador funcionando esta semana que tres módulos a medias.

Los tres módulos comparten un núcleo: una biblioteca de audio con análisis (BPM, tonalidad, compás) que usan el mezclador y el generador.

## Ajustes a la propuesta

La propuesta del adjunto va en la dirección correcta; estos son los puntos que cambian cómo se implementa.

| Punto de la propuesta | Qué pasa en la práctica | Cómo lo resolvemos |
| --- | --- | --- |
| Exportar Kick.wav, Snare.wav por separado | Demucs entrega la batería completa en una sola pista (drums), no pieza por pieza | Segundo paso opcional con un modelo de separación de batería (tipo DrumSep o LarsNet) sobre drums.wav; calidad variable, se marca como experimental |
| Demucs como único motor | Para voz, los modelos Mel-RoFormer / BS-RoFormer dan voces más limpias que Demucs | Usar la librería audio-separator (la de UVR), que carga Demucs y RoFormer con la misma interfaz; el usuario elige modelo |
| WAV 24-bit 44.1/48 kHz | Correcto. El código actual exporta MP3 320 | Cambiar a WAV 24-bit por defecto, MP3 solo como vista previa en el navegador |
| Music21 “de Stanford” | Music21 viene del MIT. Es potente para teoría musical, pero pesado para escribir MIDI | music21 para acordes y escalas; mido o pretty\_midi para escribir los .mid |
| La IA interpreta el prompt y genera MIDI | Un LLM no debe escribir el MIDI directamente: se equivoca con tiempos y duraciones | El LLM devuelve un JSON de patrón (pasos, instrumentos, velocidades) validado por el backend; el backend lo convierte a MIDI |
| No incluido | Sacar MIDI de las pistas separadas es muy útil para producir | Agregar basic-pitch (Spotify, open source): bajo o melodía separada → MIDI editable |
| Wavesurfer.js en el mezclador | Correcto para ver formas de onda | Wavesurfer.js para visualizar + Tone.js para reproducción sincronizada, efectos y secuenciador |

## Stack y estructura

Backend en Python (donde está la IA de audio) y frontend React en el navegador, todo corriendo en tu laptop. El backend y la interfaz del módulo 1 ya están empezados en esta conversación.

| Capa | Tecnología | Para qué |
| --- | --- | --- |
| API | FastAPI + Uvicorn | Endpoints, cola de trabajos, archivos |
| Separación | audio-separator (Demucs, Mel-RoFormer) sobre PyTorch CUDA | Stems de voz, batería, bajo, otros |
| Análisis | librosa (BPM, beats), essentia o madmom (tonalidad) | Metadatos para mezclar y nombrar archivos |
| Audio → MIDI | basic-pitch | Convertir bajo o melodía en notas |
| MIDI y teoría | mido / pretty\_midi, music21 | Escribir .mid, escalas, acordes |
| Render y efectos | pedalboard (Spotify), soundfile, ffmpeg | Time-stretch, EQ, exportar WAV 24-bit |
| IA de ideas | API de Claude (o un LLM local con Ollama) | Chat que devuelve patrones en JSON |
| Interfaz | React + Vite | Pantallas de los tres módulos |
| Audio en el navegador | Tone.js + Wavesurfer.js | Reproducción sincronizada, secuenciador, formas de onda |
| Datos | SQLite | Biblioteca de canciones, stems, análisis y proyectos |

```
music-studio/
├── backend/
│   ├── app/
│   │   ├── main.py            # rutas FastAPI
│   │   ├── config.py
│   │   ├── jobs.py            # cola y estado de trabajos
│   │   ├── db.py              # SQLite
│   │   ├── separation/        # módulo 1
│   │   ├── analysis/          # BPM, tonalidad, audio→MIDI
│   │   ├── mixer/             # módulo 2: sync, render
│   │   ├── beats/             # módulo 3: patrones, MIDI, asistente IA
│   │   └── export/            # paquete para DAW
│   ├── data/                  # audio y base de datos (fuera de git)
│   └── tests/
├── frontend/
│   └── src/
│       ├── modules/separator/
│       ├── modules/mixer/
│       ├── modules/beats/
│       └── shared/            # reproductor, waveform, api
├── samples/                   # kits de batería propios (WAV)
├── setup.bat
└── iniciar.bat
```

## Fases de desarrollo

Seis fases en orden de dependencia: cada una usa lo que construyó la anterior. Marca las tareas a medida que avances.

### Fase 0 — Base del proyecto

**Entregable:** la app abre en el navegador, detecta la GPU y guarda trabajos. **Terminado cuando:** `setup.bat` instala todo en un PC limpio y `iniciar.bat` levanta backend y frontend.

- [x] Backend FastAPI con cola de trabajos (un trabajo a la vez en GPU)
- [x] Esqueleto React con pestañas de los tres módulos
- [x] `setup.bat`: entorno virtual, PyTorch CUDA 13.0 (cambio: la estable más nueva), dependencias, `npm install`
- [x] `iniciar.bat` que arranca ambos servicios y abre el navegador
- [x] Migrar el estado de trabajos de JSON a SQLite
- [x] Repositorio git con `.gitignore` para `data/`

### Fase 1 — Separador listo para DAW

**Entregable:** subes una canción y descargas stems WAV 24-bit que se alinean perfecto en FL Studio. **Terminado cuando:** los stems suman de nuevo la canción original sin desfase.

- [x] Cambiar el motor a audio-separator con selector de modelo (Demucs 4 pistas, Demucs 6 pistas, RoFormer voz)
- [x] Exportar WAV 24-bit a la frecuencia original (44.1 o 48 kHz), MP3 solo para escuchar en la app
- [x] Reproductor multipista con volumen, mute y solo por pista
- [x] Descarga individual y ZIP con nombres tipo `Cancion_Vocals_95BPM_Am.wav`
- [x] Opción experimental: dividir la batería en kick, snare, hi-hat, toms
- [x] Prueba: sumar stems y comparar contra la original (error < -40 dB)

### Fase 2 — Análisis musical y audio a MIDI

**Entregable:** cada canción de la biblioteca muestra BPM, tonalidad y grilla de compases, y puedes sacar el MIDI del bajo o la melodía. **Terminado cuando:** el BPM coincide con el que detecta FL Studio en 10 canciones de prueba.

- [ ] Detección de BPM y posiciones de beat (librosa)
- [ ] Detección de tonalidad con notación normal y Camelot (8A, 5B…)
- [ ] Corrección manual de BPM y tonalidad en la interfaz
- [ ] basic-pitch: stem de bajo u otros → archivo .mid con tempo incluido
- [ ] Biblioteca con filtros por BPM, tonalidad y tipo de stem

### Fase 3 — Mezclador de dos canciones

**Entregable:** cargas dos canciones (o sus stems), las sincronizas y exportas la mezcla. **Terminado cuando:** puedes poner la voz de A sobre el instrumental de B y exportar un WAV en tempo.

- [ ] Dos decks con forma de onda (Wavesurfer.js) y grilla de beats
- [ ] Sincronía de BPM: ajustar tempo de B al de A sin cambiar el tono (time-stretch)
- [ ] Indicador de compatibilidad de tonalidad y opción de transponer ± semitonos
- [ ] Control por stem en cada deck: voz, batería, bajo, otros
- [ ] EQ de 3 bandas, ganancia y crossfader
- [ ] Render en el backend (pedalboard) a WAV 24-bit: mezcla completa y cada deck por separado

### Fase 4a — Secuenciador libre y biblioteca de ritmos

**Entregable:** un secuenciador sin límites con una biblioteca grande de ritmos para explorar, editar y exportar como MIDI y WAV. **Terminado cuando:** pasas de una cumbia a un drill y a un ritmo en 7/8 en menos de un minuto, lo editas a tu gusto y el .mid abre en FL Studio con el tempo correcto.

- [ ] Motor de patrones sin límites: pistas y compases ilimitados, cada pista con su propia longitud y resolución (hasta 1/64) para polirritmos
- [ ] Cualquier compás (4/4, 3/4, 6/8, 12/8, 5/4, 7/8…) y BPM de 40 a 300, con swing, tresillos y humanización
- [ ] Biblioteca inicial: 40+ géneros y 300+ patrones, cada uno con variaciones (intro, verso, coro, fill, break)
- [ ] Importar el Groove MIDI Dataset y cualquier .mid tuyo al catálogo
- [ ] Explorador con filtros, escucha previa instantánea y carga con un clic
- [ ] Mezclar capas entre géneros y mutar o aleatorizar con bloqueo de pistas
- [ ] Kits de batería desde la carpeta `samples/` y stems separados como samples
- [ ] Piano roll para 808, bajo y percusión melódica
- [ ] Grabación en vivo con el teclado del PC o un controlador MIDI
- [ ] Exportar MIDI (canal 10, mapa General MIDI) y WAV; guardar proyectos y tus propios patrones en la biblioteca

### Fase 4b — Asistente de ideas con IA

**Entregable:** un chat al lado del secuenciador que propone patrones y tú decides qué aplicar. **Terminado cuando:** “reggaetón romántico a 95 BPM” produce un patrón válido que se aplica con un clic y se puede editar.

- [ ] Esquema JSON de patrón (instrumento, paso, velocidad, duración, compás) validado en el backend
- [ ] Prompt de sistema que conoce todo el catálogo y puede cruzar géneros (“cumbia con 808 de trap”, “dembow en 6/8”)
- [ ] Tres propuestas distintas por pedido, y un modo “Sorpréndeme” que sugiere ritmos fuera de lo que sueles usar
- [ ] Vista previa de cada sugerencia antes de aplicarla, y aplicar solo una pista (“solo el hi-hat”)
- [ ] Pedir variaciones sobre el beat actual (“más agresivo”, “agrega un fill al compás 4”, “llévalo a 140”)
- [ ] Sugerencias de progresiones de acordes y melodía en la tonalidad elegida (MIDI)
- [ ] Todo lo que propone la IA queda editable nota por nota; ignorarla nunca limita nada

### Fase 5 — Paquete para DAW y pulido

**Entregable:** botón “Exportar paquete para DAW” que entrega una carpeta lista para arrastrar. **Terminado cuando:** abres el paquete en FL Studio y todo queda alineado en el compás 1.

- [ ] Paquete ZIP con carpetas `Audio/`, `MIDI/`, `Mezcla/` y un `info.txt` con BPM y tonalidad
- [ ] Todos los archivos del paquete arrancan en el mismo punto (compás 1) y con el mismo tempo
- [ ] Manejo de errores y mensajes claros (sin GPU, archivo corrupto, disco lleno)
- [ ] Atajos de teclado en el secuenciador y el mezclador

## Libertad para explorar ritmos

El generador de beats arranca con una biblioteca de 40+ géneros y 300+ patrones, y crece cada vez que guardas o importas uno. Nada queda bloqueado: cualquier ritmo se puede cargar, mezclar con otro, cambiar de compás o de tempo y editar nota por nota.

### Catálogo inicial de ritmos

| Familia | Ritmos incluidos | Compases |
| --- | --- | --- |
| Latino urbano | Reggaetón, dembow dominicano, perreo, moombahton, RKT, mambo urbano, trap latino | 4/4 |
| Colombia y tropical | Cumbia, champeta, vallenato (paseo, son, merengue, puya), porro, bullerengue, currulao, salsa (clave 2-3 y 3-2), merengue, bachata | 4/4, 2/4, 6/8 |
| Hip hop y trap | Boom bap, trap, drill UK y NY, phonk, lo-fi, jersey club, rage | 4/4 con tresillos |
| Electrónica | House, deep house, tech house, techno, drum & bass, jungle, dubstep, UK garage, trance, breakbeat | 4/4 |
| Afro y Caribe | Afrobeats, amapiano, afro house, dancehall, soca, reggae (one drop, steppers, rockers), kuduro | 4/4 |
| Brasil | Samba, bossa nova, funk carioca, baião, forró | 2/4, 4/4 |
| Pop, rock y groove | Pop, rock, funk, disco, R&B, neo soul, gospel shuffle, jazz swing | 4/4, 12/8 |
| Compases impares y polirritmos | Afrocubano 6/8, flamenco (búlería de 12 tiempos), 5/4, 7/8, 9/8, polirritmos 3:2 y 4:3 | Libres |

Cada patrón viene con variaciones (básico, intro, fill, break, salida). Para ampliar variedad rápido se importa el [Groove MIDI Dataset](https://magenta.tensorflow.org/datasets/groove) de Magenta: unas 13 horas de batería real tocada por bateristas en MIDI, con licencia CC BY 4.0.

### Herramientas para explorar

- **Explorador:** filtrar por género, BPM, compás, energía y densidad; escuchar al pasar el cursor; cargar con un clic.
- **Mezclar géneros por capa:** bombo de house, caja de dembow y hi-hat de trap en el mismo beat.
- **Mutar:** cambia un patrón entre 0 % y 100 %, con pistas bloqueadas que no se tocan.
- **Aleatorio con control:** generar a partir de reglas del género elegido o sin reglas.
- **Parecidos a este:** ritmos cercanos al que estás usando, para descubrir sin perder el rumbo.
- **Transformar:** llevar cualquier ritmo a otro compás, a doble o medio tempo, o a tresillos.
- **Tu propia biblioteca:** guardar patrones, importar .mid de otros productores y cargar tus samples.

### Sin límites

- Pistas y compases ilimitados.
- BPM de 40 a 300 y cambios de tempo sin reiniciar.
- Resolución de 1/4 a 1/64 y longitud distinta por pista.
- Ningún género ni combinación prohibida.
- La IA es un botón más, nunca un paso obligatorio.

## Estándar de exportación

Todo archivo que sale de la app cumple estas reglas, para que al arrastrarlo al DAW quede en tempo y alineado sin tocar nada.

| Tipo | Formato | Detalle |
| --- | --- | --- |
| Stems separados | WAV PCM 24-bit | Misma frecuencia y duración que la original, arrancan en 0 ms |
| Mezcla del mezclador | WAV PCM 24-bit, 44.1 kHz | Headroom de -1 dBFS, sin limitador (el mastering se hace en el DAW) |
| Loop de beat | WAV PCM 24-bit | Duración exacta en compases, sin silencio al final |
| Patrones y notas | MIDI tipo 1, 480 PPQ | Tempo y compás en la pista 0; batería en canal 10 con mapa General MIDI |
| Vista previa en la app | MP3 192 kbps | Solo para escuchar en el navegador, nunca en el paquete |

**Nombres de archivo:** `Titulo_Pista_BPM_Tonalidad.wav`, por ejemplo `MiCancion_Vocals_95BPM_Am.wav`. Sin tildes ni espacios, para evitar problemas en cualquier DAW.

**Paquete para DAW:**

```
MiCancion_95BPM_Am/
├── Audio/     # stems WAV
├── MIDI/      # beats, bajo, acordes
├── Mezcla/    # render del mezclador
└── info.txt   # BPM, tonalidad, origen de cada archivo
```

## Cronograma, riesgos y próximo paso

Con unas 10 horas por semana, el separador listo para DAW está a finales de octubre y la app completa a finales de enero de 2027.

&#91;embedded content: cronograma · 6 fases, \~15 semanas\]

La línea punteada marca la primera versión que ya sirve para producir; desde ahí cada fase agrega un módulo sin romper lo anterior.

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Versiones de PyTorch, CUDA y Demucs que no se entienden entre sí | La separación no arranca | Versiones fijas en `setup.bat` y requirements; probar en un entorno limpio |
| 8 GB de VRAM se quedan cortos con modelos RoFormer grandes | Errores de memoria | Procesar por segmentos, un trabajo a la vez, fallback a Demucs |
| Time-stretch con diferencias de BPM mayores al 10 % | Voces con artefactos en el mezclador | Avisar en la interfaz y sugerir mezclar a medio o doble tempo |
| Separación de batería en piezas con calidad irregular | Kicks o snares sucios | Marcarlo como experimental; el stem completo siempre disponible |
| Stems de canciones comerciales | No se pueden publicar sin licencia | Usarlos para estudiar y practicar; lo que publiques, con tus propios samples o material con licencia |
| Poco tiempo al trabajar tiempo completo | El proyecto se estanca a medias | No saltar fases: cada una termina en algo usable |

**Próximo paso (esta semana):** cerrar la Fase 0 y arrancar la Fase 1.

1. Terminar `setup.bat` e `iniciar.bat` y probar la instalación en tu laptop.
2. Separar la primera canción real con Demucs en la RTX 4070 y medir el tiempo.
3. Cambiar la salida de MP3 a WAV 24-bit y probar los stems en FL Studio o Ableton.
