import { formatDuration, type Song } from "../../shared/api";

interface Props {
  songs: Song[] | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function SongList({ songs, selectedId, onSelect }: Props) {
  if (!songs) return <p className="faint list-note">Cargando…</p>;
  if (!songs.length) return <p className="faint list-note">Aún no hay canciones.</p>;
  return (
    <ul className="song-list">
      {songs.map((s) => (
        <li key={s.id}>
          <button className={`song-item ${s.id === selectedId ? "active" : ""}`} onClick={() => onSelect(s.id)}>
            <span className="song-title">{s.title}</span>
            <span className="song-meta mono">
              {formatDuration(s.duration)} · {(s.sample_rate / 1000).toFixed(1)} kHz
              {s.bpm ? ` · ${s.bpm} BPM` : ""}
              {s.musical_key ? ` · ${s.musical_key}` : ""}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
