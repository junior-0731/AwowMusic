// Cliente tipado de la API del backend (FastAPI en :8000, vía proxy de Vite).

export type JobStatus = "pending" | "running" | "done" | "error" | "cancelled";

export interface Song {
  id: string;
  title: string;
  original_filename: string;
  sample_rate: number;
  channels: number;
  frames: number;
  duration: number;
  bpm: number | null;
  musical_key: string | null;
  created_at: string;
}

export interface Stem {
  id: string;
  song_id: string;
  job_id: string;
  name: string;
  kind: "song" | "drum_part";
  model: string;
  experimental: boolean;
  peak: number;
  position: number;
}

export interface SeparationResult {
  model: string;
  model_label: string;
  stems: string[];
  sample_rate: number;
  residual_fixed: boolean;
  null_test_raw_db: number;
  null_test_db: number;
  null_test_passed: boolean;
  drum_split?: SeparationResult | null;
  warnings: string[];
}

export interface Job<P = Record<string, unknown>, R = unknown> {
  id: string;
  type: string;
  song_id: string | null;
  status: JobStatus;
  progress: number;
  message: string;
  params: P;
  result: R | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface SeparateParams {
  model: string;
  fix_residual: boolean;
  drum_split: boolean;
}

export type Separation = Job<SeparateParams, SeparationResult> & { stems: Stem[] };

export interface SeparationModel {
  id: string;
  label: string;
  description: string;
  stems: string[];
  residual_stem: string;
  experimental: boolean;
  vram_note: string;
  kind: string;
}

export interface ModelsResponse {
  default: string;
  models: SeparationModel[];
  drum_model: SeparationModel;
}

export interface Health {
  status: string;
  version: string;
  ffmpeg: boolean;
  gpu: {
    available: boolean;
    name: string | null;
    vram_gb: number | null;
    torch: string | null;
    cuda: string | null;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function errorFrom(res: Response): Promise<ApiError> {
  let message = `Error ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch {
    // respuesta sin JSON
  }
  return new ApiError(message, res.status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new ApiError("No hay conexión con el backend. ¿Está corriendo iniciar.bat?", 0);
  }
  if (!res.ok) throw await errorFrom(res);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  models: () => request<ModelsResponse>("/api/models"),

  songs: () => request<Song[]>("/api/songs"),
  updateSong: (id: string, patch: Partial<Pick<Song, "title" | "bpm" | "musical_key">>) =>
    request<Song>(`/api/songs/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteSong: (id: string) => request<void>(`/api/songs/${id}`, { method: "DELETE" }),
  separations: (songId: string) => request<Separation[]>(`/api/songs/${songId}/separations`),
  separate: (songId: string, params: SeparateParams) =>
    request<Job>(`/api/songs/${songId}/separate`, { method: "POST", body: JSON.stringify(params) }),
  deleteJob: (id: string) => request<void>(`/api/jobs/${id}`, { method: "DELETE" }),

  /** Sube con XMLHttpRequest para poder mostrar el progreso de la subida. */
  uploadSong(file: File, onProgress: (fraction: number) => void): Promise<Song> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/songs");
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
      xhr.onerror = () => reject(new ApiError("No hay conexión con el backend.", 0));
      xhr.onload = () => {
        let body: { detail?: string } & Partial<Song> = {};
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          // sin JSON
        }
        if (xhr.status === 201) resolve(body as Song);
        else reject(new ApiError(body.detail ?? `Error ${xhr.status}`, xhr.status));
      };
      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    });
  },
};

export const urls = {
  songPreview: (id: string) => `/api/songs/${id}/preview`,
  stemPreview: (id: string) => `/api/stems/${id}/preview`,
  stemDownload: (id: string) => `/api/stems/${id}/download`,
  separationZip: (jobId: string) => `/api/separations/${jobId}/zip`,
};

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
