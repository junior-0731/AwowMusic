import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { formatDuration } from "./api";
import Waveform from "./Waveform";

export interface PlayerTrack {
  id: string;
  name: string;
  url: string;
  /** Pista de referencia (la original): arranca silenciada para comparar. */
  reference?: boolean;
  experimental?: boolean;
  downloadUrl?: string;
}

interface TrackState {
  volume: number;
  muted: boolean;
  solo: boolean;
}

let sharedContext: AudioContext | null = null;
function audioContext(): AudioContext {
  sharedContext ??= new AudioContext();
  return sharedContext;
}

/**
 * Reproductor multipista sincronizado. Cada pista es un AudioBufferSourceNode que arranca
 * en el mismo instante del reloj de audio, así no hay desfase entre stems.
 */
export default function MultitrackPlayer({ tracks }: { tracks: PlayerTrack[] }) {
  const [buffers, setBuffers] = useState<Map<string, AudioBuffer>>(new Map());
  const [loadError, setLoadError] = useState<string | null>(null);
  const [state, setState] = useState<Record<string, TrackState>>({});
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);

  const gains = useRef(new Map<string, GainNode>());
  const sources = useRef<AudioBufferSourceNode[]>([]);
  const clock = useRef({ startedAt: 0, offset: 0 });
  const raf = useRef(0);

  const trackKey = tracks.map((t) => t.id).join("|");
  const duration = useMemo(() => Math.max(0, ...[...buffers.values()].map((b) => b.duration)), [buffers]);
  const loaded = buffers.size === tracks.length && tracks.length > 0;

  // Carga y decodifica todas las pistas.
  useEffect(() => {
    let cancelled = false;
    setBuffers(new Map());
    setLoadError(null);
    setState(Object.fromEntries(tracks.map((t) => [t.id, { volume: 1, muted: !!t.reference, solo: false }])));
    const ctx = audioContext();
    Promise.all(
      tracks.map(async (t) => {
        const res = await fetch(t.url);
        if (!res.ok) throw new Error(`No se pudo cargar ${t.name}`);
        return [t.id, await ctx.decodeAudioData(await res.arrayBuffer())] as const;
      }),
    )
      .then((entries) => !cancelled && setBuffers(new Map(entries)))
      .catch((e: Error) => !cancelled && setLoadError(e.message));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackKey]);

  const anySolo = Object.values(state).some((s) => s.solo);
  const effectiveGain = useCallback(
    (id: string) => {
      const s = state[id];
      if (!s) return 0;
      if (anySolo) return s.solo ? s.volume : 0;
      return s.muted ? 0 : s.volume;
    },
    [state, anySolo],
  );

  // Aplica volumen, mute y solo en vivo, sin cortar la reproducción.
  useEffect(() => {
    const ctx = audioContext();
    for (const [id, gain] of gains.current) gain.gain.setTargetAtTime(effectiveGain(id), ctx.currentTime, 0.01);
  }, [effectiveGain]);

  const currentTime = useCallback(() => {
    const { startedAt, offset } = clock.current;
    return offset + (audioContext().currentTime - startedAt);
  }, []);

  const stopSources = useCallback(() => {
    for (const s of sources.current) {
      s.onended = null;
      try {
        s.stop();
      } catch {
        // ya estaba detenida
      }
      s.disconnect();
    }
    sources.current = [];
    cancelAnimationFrame(raf.current);
  }, []);

  const start = useCallback(
    async (offset: number) => {
      const ctx = audioContext();
      if (ctx.state === "suspended") await ctx.resume();
      stopSources();
      const when = ctx.currentTime + 0.05;
      for (const t of tracks) {
        const buffer = buffers.get(t.id);
        if (!buffer) continue;
        let gain = gains.current.get(t.id);
        if (!gain) {
          gain = ctx.createGain();
          gain.connect(ctx.destination);
          gains.current.set(t.id, gain);
        }
        gain.gain.value = effectiveGain(t.id);
        const src = ctx.createBufferSource();
        src.buffer = buffer;
        src.connect(gain);
        src.start(when, offset);
        sources.current.push(src);
      }
      clock.current = { startedAt: when, offset };
      setPlaying(true);
      const tick = () => {
        const t = currentTime();
        if (t >= duration) {
          stopSources();
          setPlaying(false);
          setPosition(0);
          clock.current.offset = 0;
          return;
        }
        setPosition(Math.max(offset, t));
        raf.current = requestAnimationFrame(tick);
      };
      raf.current = requestAnimationFrame(tick);
    },
    [buffers, tracks, duration, effectiveGain, stopSources, currentTime],
  );

  const pause = useCallback(() => {
    const t = currentTime();
    stopSources();
    clock.current.offset = t;
    setPosition(t);
    setPlaying(false);
  }, [currentTime, stopSources]);

  const toggle = () => (playing ? pause() : start(position));

  const seek = (fraction: number) => {
    const t = Math.min(duration, Math.max(0, fraction * duration));
    setPosition(t);
    clock.current.offset = t;
    if (playing) void start(t);
  };

  const stop = () => {
    stopSources();
    setPlaying(false);
    setPosition(0);
    clock.current.offset = 0;
  };

  // Limpieza al desmontar o al cambiar de pistas.
  useEffect(() => {
    const gainMap = gains.current;
    return () => {
      stopSources();
      for (const g of gainMap.values()) g.disconnect();
      gainMap.clear();
      setPlaying(false);
      setPosition(0);
      clock.current = { startedAt: 0, offset: 0 };
    };
  }, [trackKey, stopSources]);

  const update = (id: string, patch: Partial<TrackState>) =>
    setState((s) => ({ ...s, [id]: { ...s[id], ...patch } }));

  if (loadError) return <div className="alert alert-error">{loadError}</div>;

  const progress = duration ? position / duration : 0;

  return (
    <div className="player">
      <div className="transport">
        <button className="btn btn-go transport-play" onClick={toggle} disabled={!loaded} aria-label={playing ? "Pausa" : "Reproducir"}>
          {playing ? "❚❚" : "▶"}
        </button>
        <button className="btn btn-sm" onClick={stop} disabled={!loaded}>
          ■ Detener
        </button>
        <span className="mono time">
          {formatDuration(position)} / {formatDuration(duration)}
        </span>
        {!loaded && <span className="faint">Cargando pistas…</span>}
        {anySolo && (
          <button className="btn btn-sm btn-ghost" onClick={() => setState((s) => Object.fromEntries(Object.entries(s).map(([k, v]) => [k, { ...v, solo: false }])))}>
            Quitar solos
          </button>
        )}
      </div>

      <div className="tracks">
        {tracks.map((t) => {
          const s = state[t.id] ?? { volume: 1, muted: false, solo: false };
          const audible = effectiveGain(t.id) > 0;
          return (
            <div key={t.id} className={`track ${audible ? "" : "track-silent"} ${t.reference ? "track-ref" : ""}`}>
              <div className="track-head">
                <div className="track-name" title={t.name}>
                  {t.name}
                  {t.experimental && <span className="badge badge-warn">exp.</span>}
                </div>
                <div className="track-controls">
                  <button className="icon-btn mute" aria-pressed={s.muted} onClick={() => update(t.id, { muted: !s.muted })} title="Silenciar">
                    M
                  </button>
                  <button className="icon-btn solo" aria-pressed={s.solo} onClick={() => update(t.id, { solo: !s.solo })} title="Solo">
                    S
                  </button>
                  <input
                    type="range"
                    min={0}
                    max={1.5}
                    step={0.01}
                    value={s.volume}
                    onChange={(e) => update(t.id, { volume: Number(e.target.value) })}
                    onDoubleClick={() => update(t.id, { volume: 1 })}
                    aria-label={`Volumen de ${t.name}`}
                    title={`${Math.round(s.volume * 100)} % (doble clic: 100 %)`}
                  />
                  {t.downloadUrl && (
                    <a className="icon-btn" href={t.downloadUrl} download title="Descargar WAV 24-bit">
                      ⤓
                    </a>
                  )}
                </div>
              </div>
              <Waveform buffer={buffers.get(t.id)} progress={progress} onSeek={seek} reference={t.reference} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
