import { useEffect, useRef } from "react";

interface Props {
  buffer?: AudioBuffer;
  /** 0..1 */
  progress: number;
  onSeek: (fraction: number) => void;
  reference?: boolean;
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Forma de onda en canvas a partir de los picos del AudioBuffer. */
export default function Waveform({ buffer, progress, onSeek, reference }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = canvas.current;
    if (!el || !buffer) return;

    const draw = () => {
      const width = el.clientWidth;
      const height = el.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      el.width = Math.round(width * dpr);
      el.height = Math.round(height * dpr);
      const g = el.getContext("2d")!;
      g.scale(dpr, dpr);
      g.clearRect(0, 0, width, height);

      const channels = Array.from({ length: buffer.numberOfChannels }, (_, i) => buffer.getChannelData(i));
      const samplesPerPx = Math.max(1, Math.floor(buffer.length / width));
      const mid = height / 2;
      g.fillStyle = reference ? cssVar("--text-faint") : cssVar("--green");
      for (let x = 0; x < width; x++) {
        const start = x * samplesPerPx;
        let peak = 0;
        // Muestreo con salto para que el dibujo sea rápido en canciones largas.
        const step = Math.max(1, Math.floor(samplesPerPx / 64));
        for (let i = start; i < start + samplesPerPx; i += step) {
          for (const data of channels) {
            const v = Math.abs(data[i] ?? 0);
            if (v > peak) peak = v;
          }
        }
        const h = Math.max(1, Math.min(1, peak) * mid * 0.95);
        g.fillRect(x, mid - h, 1, h * 2);
      }
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(el);
    return () => observer.disconnect();
  }, [buffer, reference]);

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    onSeek((e.clientX - rect.left) / rect.width);
  };

  return (
    <div className="waveform" onClick={handleClick}>
      <canvas ref={canvas} />
      <div className="waveform-played" style={{ width: `${progress * 100}%` }} />
      <div className="waveform-cursor" style={{ left: `${progress * 100}%` }} />
    </div>
  );
}
