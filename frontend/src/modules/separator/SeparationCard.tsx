import { useMemo, useState } from "react";
import { api, urls, type ModelsResponse, type Separation, type Song } from "../../shared/api";
import MultitrackPlayer, { type PlayerTrack } from "../../shared/MultitrackPlayer";

interface Props {
  song: Song;
  separation: Separation;
  models: ModelsResponse;
  onDeleted: () => void;
}

const STATUS_LABEL: Record<Separation["status"], string> = {
  pending: "En cola",
  running: "Procesando",
  done: "Listo",
  error: "Error",
  cancelled: "Cancelado",
};

function elapsed(from: string | null, to: string | null): string | null {
  if (!from || !to) return null;
  const s = Math.round((Date.parse(to) - Date.parse(from)) / 1000);
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

export default function SeparationCard({ song, separation: sep, models, onDeleted }: Props) {
  const [error, setError] = useState<string | null>(null);
  const modelLabel = sep.result?.model_label ?? models.models.find((m) => m.id === sep.params.model)?.label ?? sep.params.model;

  const tracks = useMemo<PlayerTrack[]>(
    () => [
      { id: `original-${song.id}`, name: "Original", url: urls.songPreview(song.id), reference: true },
      ...sep.stems.map((s) => ({
        id: s.id,
        name: s.name,
        url: urls.stemPreview(s.id),
        experimental: s.experimental,
        downloadUrl: urls.stemDownload(s.id),
      })),
    ],
    [song.id, sep.stems],
  );

  const remove = async () => {
    const question = sep.status === "pending" ? "¿Cancelar este trabajo?" : "¿Borrar esta separación y sus archivos?";
    if (!window.confirm(question)) return;
    try {
      await api.deleteJob(sep.id);
      onDeleted();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const result = sep.result;
  const running = sep.status === "running";

  return (
    <article className="separation panel">
      <header className="separation-head">
        <div>
          <h3>{modelLabel}</h3>
          <span className="faint">
            {new Date(sep.created_at).toLocaleString("es")}
            {elapsed(sep.started_at, sep.finished_at) && ` · ${elapsed(sep.started_at, sep.finished_at)}`}
          </span>
        </div>
        <div className="separation-actions">
          <span className={`badge ${sep.status === "done" ? "badge-ok" : sep.status === "error" ? "badge-bad" : ""}`}>
            {STATUS_LABEL[sep.status]}
          </span>
          {sep.status === "done" && (
            <a className="btn btn-go btn-sm" href={urls.separationZip(sep.id)} download>
              ⤓ Descargar ZIP
            </a>
          )}
          {!running && (
            <button className="btn btn-ghost btn-sm" onClick={remove}>
              {sep.status === "pending" ? "Cancelar" : "Borrar"}
            </button>
          )}
        </div>
      </header>

      {(sep.status === "pending" || running) && (
        <div className="job-progress">
          <div className={`progress ${running && sep.progress < 0.75 ? "indeterminate" : ""}`}>
            <div style={{ width: `${Math.max(5, sep.progress * 100)}%` }} />
          </div>
          <span className="dim">{sep.message}</span>
        </div>
      )}

      {sep.status === "error" && <div className="alert alert-error">{sep.error}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <>
          <div className="result-facts">
            <span
              className={`badge ${result.null_test_passed ? "badge-ok" : "badge-bad"}`}
              title="Diferencia entre la suma de los stems guardados y la canción original. Menos de -40 dB = sin desfase audible."
            >
              Prueba de suma: {result.null_test_db.toFixed(1)} dB {result.null_test_passed ? "✓" : "✗"}
            </span>
            <span className="badge">WAV 24-bit · {(result.sample_rate / 1000).toFixed(1)} kHz</span>
            {result.residual_fixed && (
              <span className="badge" title={`Error del modelo antes de corregir: ${result.null_test_raw_db.toFixed(1)} dB`}>
                Residuo del modelo: {result.null_test_raw_db.toFixed(1)} dB
              </span>
            )}
            {result.drum_split && <span className="badge badge-warn">Batería dividida (experimental)</span>}
          </div>
          {result.warnings.map((w) => (
            <div key={w} className="alert alert-warn">
              {w}
            </div>
          ))}
        </>
      )}

      {sep.status === "done" && sep.stems.length > 0 && <MultitrackPlayer tracks={tracks} />}
    </article>
  );
}
