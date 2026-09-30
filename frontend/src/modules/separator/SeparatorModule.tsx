import { useCallback, useEffect, useState } from "react";
import { api, type ModelsResponse, type Song } from "../../shared/api";
import SongList from "./SongList";
import SongPanel from "./SongPanel";
import UploadZone from "./UploadZone";

export default function SeparatorModule() {
  const [songs, setSongs] = useState<Song[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const list = await api.songs();
      setSongs(list);
      setSelectedId((id) => (id && list.some((s) => s.id === id) ? id : (list[0]?.id ?? null)));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void reload();
    api.models().then(setModels, (e: Error) => setError(e.message));
  }, [reload]);

  const selected = songs?.find((s) => s.id === selectedId) ?? null;

  return (
    <div className="separator">
      <aside className="sidebar panel">
        <h2 className="sidebar-title">Biblioteca</h2>
        <UploadZone
          onUploaded={(song) => {
            setSongs((list) => [song, ...(list ?? [])]);
            setSelectedId(song.id);
          }}
        />
        {error && <div className="alert alert-error">{error}</div>}
        <SongList songs={songs} selectedId={selectedId} onSelect={setSelectedId} />
      </aside>
      <section className="workspace">
        {selected && models ? (
          <SongPanel
            key={selected.id}
            song={selected}
            models={models}
            onChange={(song) => setSongs((list) => list?.map((s) => (s.id === song.id ? song : s)) ?? null)}
            onDeleted={reload}
          />
        ) : (
          <div className="empty panel">
            <h2>Sube una canción para empezar</h2>
            <p className="dim">
              Arrastra un archivo de audio a la biblioteca. La app lo separa en stems WAV 24-bit que se alinean
              exactamente en tu DAW.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
