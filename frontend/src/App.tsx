import { useEffect, useState } from "react";
import BeatsModule from "./modules/beats/BeatsModule";
import MixerModule from "./modules/mixer/MixerModule";
import SeparatorModule from "./modules/separator/SeparatorModule";
import { api, type Health } from "./shared/api";

const TABS = [
  { id: "separator", label: "Separador", Component: SeparatorModule },
  { id: "mixer", label: "Mezclador", Component: MixerModule },
  { id: "beats", label: "Beats", Component: BeatsModule },
] as const;

type TabId = (typeof TABS)[number]["id"];

function readTab(): TabId {
  const hash = window.location.hash.slice(1);
  return TABS.some((t) => t.id === hash) ? (hash as TabId) : "separator";
}

export default function App() {
  const [tab, setTab] = useState<TabId>(readTab);
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let timer: number;
    const check = () =>
      api
        .health()
        .then((h) => {
          setHealth(h);
          setOffline(false);
        })
        .catch(() => {
          setOffline(true);
          timer = window.setTimeout(check, 3000);
        });
    check();
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const onHash = () => setTab(readTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const Active = TABS.find((t) => t.id === tab)!.Component;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          <span>
            Awow<b>Music</b>
          </span>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <a
              key={t.id}
              href={`#${t.id}`}
              role="tab"
              aria-selected={tab === t.id}
              className="tab"
            >
              {t.label}
            </a>
          ))}
        </nav>
        <SystemStatus health={health} offline={offline} />
      </header>
      {offline && (
        <div className="alert alert-error banner">
          No hay conexión con el backend. Ejecuta <b>iniciar.bat</b>; esta página se reconecta sola.
        </div>
      )}
      {health && !health.ffmpeg && (
        <div className="alert alert-warn banner">
          No se encontró <b>ffmpeg</b>: no se pueden subir canciones. Ejecuta setup.bat o instala ffmpeg en el PATH.
        </div>
      )}
      <main className="content">
        <Active />
      </main>
    </div>
  );
}

function SystemStatus({ health, offline }: { health: Health | null; offline: boolean }) {
  if (offline) return <span className="badge badge-bad">Backend desconectado</span>;
  if (!health) return <span className="badge">Conectando…</span>;
  const { gpu } = health;
  if (!gpu.available)
    return (
      <span className="badge badge-warn" title="La separación funcionará en CPU, mucho más lenta.">
        Sin GPU · modo CPU
      </span>
    );
  return (
    <span className="badge badge-ok" title={`PyTorch ${gpu.torch} · CUDA ${gpu.cuda}`}>
      <span className="dot" /> {gpu.name?.replace("NVIDIA GeForce ", "")} · {gpu.vram_gb} GB
    </span>
  );
}
