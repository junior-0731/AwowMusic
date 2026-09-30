import { useCallback, useEffect, useState } from "react";
import { api, formatDuration, type ModelsResponse, type Separation, type Song } from "../../shared/api";
import SeparateForm from "./SeparateForm";
import SeparationCard from "./SeparationCard";

interface Props {
  song: Song;
  models: ModelsResponse;
  onChange: (song: Song) => void;
  onDeleted: () => void;
}

const POLL_MS = 1000;

export default function SongPanel({ song, models, onChange, onDeleted }: Props) {
  const [separations, setSeparations] = useState<Separation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSeparations(await api.separations(song.id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [song.id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Mientras haya trabajos en cola o en proceso, consulta su estado cada segundo.
  const active = separations?.some((s) => s.status === "pending" || s.status === "running");
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [active, load]);

  const remove = async () => {
    if (!window.confirm(`¿Borrar "${song.title}" y todos sus stems? No se puede deshacer.`)) return;
    try {
      await api.deleteSong(song.id);
      onDeleted();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="song-panel">
      <SongHeader song={song} onChange={onChange} onDelete={remove} />
      {error && <div className="alert alert-error">{error}</div>}
      <SeparateForm
        song={song}
        models={models}
        busy={!!active}
        onSubmitted={load}
        onError={setError}
      />
      {separations?.map((s) => (
        <SeparationCard key={s.id} song={song} separation={s} models={models} onDeleted={load} />
      ))}
    </div>
  );
}

function SongHeader({ song, onChange, onDelete }: { song: Song; onChange: (s: Song) => void; onDelete: () => void }) {
  const [title, setTitle] = useState(song.title);
  const [bpm, setBpm] = useState(song.bpm?.toString() ?? "");
  const [key, setKey] = useState(song.musical_key ?? "");
  const [error, setError] = useState<string | null>(null);

  const save = async (patch: Partial<Pick<Song, "title" | "bpm" | "musical_key">>) => {
    try {
      onChange(await api.updateSong(song.id, patch));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveBpm = () => {
    const value = bpm.trim() ? Number(bpm.replace(",", ".")) : null;
    if (value === song.bpm) return;
    if (value !== null && (!Number.isFinite(value) || value < 20 || value > 400)) {
      setError("El BPM debe estar entre 20 y 400.");
      return;
    }
    void save({ bpm: value });
  };

  return (
    <header className="song-header panel">
      <div className="song-header-main">
        <input
          className="title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => title.trim() && title !== song.title && save({ title: title.trim() })}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          aria-label="Título"
        />
        <div className="faint mono song-facts">
          {song.original_filename} · {formatDuration(song.duration)} · {song.sample_rate} Hz ·{" "}
          {song.channels === 1 ? "mono" : "estéreo"}
        </div>
      </div>
      <div className="song-header-fields">
        <label className="field">
          BPM
          <input
            className="input mono small-input"
            inputMode="decimal"
            placeholder="—"
            value={bpm}
            onChange={(e) => setBpm(e.target.value)}
            onBlur={saveBpm}
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
        </label>
        <label className="field">
          Tonalidad
          <input
            className="input mono small-input"
            placeholder="Am"
            maxLength={12}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            onBlur={() => key !== (song.musical_key ?? "") && save({ musical_key: key.trim() || null })}
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
        </label>
        <button className="btn btn-ghost" onClick={onDelete} title="Borrar canción">
          Borrar
        </button>
      </div>
      <p className="faint hint">
        El BPM y la tonalidad se usan en los nombres de archivo (ej. <span className="mono">Cancion_Vocals_95BPM_Am.wav</span>).
        La detección automática llega en la Fase 2.
      </p>
      {error && <div className="alert alert-error">{error}</div>}
    </header>
  );
}
