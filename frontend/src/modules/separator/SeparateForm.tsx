import { useState } from "react";
import { api, type ModelsResponse, type Song } from "../../shared/api";

interface Props {
  song: Song;
  models: ModelsResponse;
  busy: boolean;
  onSubmitted: () => void;
  onError: (message: string) => void;
}

export default function SeparateForm({ song, models, busy, onSubmitted, onError }: Props) {
  const [modelId, setModelId] = useState(models.default);
  const [fixResidual, setFixResidual] = useState(true);
  const [drumSplit, setDrumSplit] = useState(false);
  const [sending, setSending] = useState(false);

  const model = models.models.find((m) => m.id === modelId) ?? models.models[0];
  const hasDrums = model.stems.includes("Drums");

  const submit = async () => {
    setSending(true);
    try {
      await api.separate(song.id, { model: modelId, fix_residual: fixResidual, drum_split: hasDrums && drumSplit });
      onSubmitted();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="separate-form panel">
      <h3>Separar en stems</h3>
      <div className="model-grid" role="radiogroup" aria-label="Modelo">
        {models.models.map((m) => (
          <label key={m.id} className={`model-card ${m.id === modelId ? "selected" : ""}`}>
            <input type="radio" name="model" value={m.id} checked={m.id === modelId} onChange={() => setModelId(m.id)} />
            <span className="model-label">{m.label}</span>
            <span className="model-desc dim">{m.description}</span>
            <span className="model-stems">
              {m.stems.map((s) => (
                <span key={s} className="badge">
                  {s}
                </span>
              ))}
            </span>
            {m.vram_note && <span className="model-note faint">{m.vram_note}</span>}
          </label>
        ))}
      </div>

      <div className="options">
        <label className="check">
          <input type="checkbox" checked={fixResidual} onChange={(e) => setFixResidual(e.target.checked)} />
          <span>
            Suma exacta con la original
            <span className="faint option-help">
              Los modelos no reconstruyen el 100 % de la canción; la diferencia se agrega a «{model.residual_stem}» para
              que los stems sumen exactamente la original en el DAW.
            </span>
          </span>
        </label>
        <label className={`check ${hasDrums ? "" : "check-disabled"}`}>
          <input
            type="checkbox"
            checked={hasDrums && drumSplit}
            disabled={!hasDrums}
            onChange={(e) => setDrumSplit(e.target.checked)}
          />
          <span>
            Dividir la batería en piezas <span className="badge badge-warn">experimental</span>
            <span className="faint option-help">
              {hasDrums
                ? `${models.drum_model.stems.join(", ")}. Calidad variable; el stem completo de batería siempre queda disponible.`
                : "Solo disponible con modelos que separan la batería."}
            </span>
          </span>
        </label>
      </div>

      <div className="form-actions">
        <button className="btn btn-primary" onClick={submit} disabled={sending}>
          {sending ? "Enviando…" : "Separar"}
        </button>
        {busy && <span className="faint">Hay un trabajo en curso; los nuevos esperan en cola (uno a la vez en la GPU).</span>}
      </div>
    </section>
  );
}
