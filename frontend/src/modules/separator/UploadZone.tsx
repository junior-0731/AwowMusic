import { useRef, useState } from "react";
import { api, type Song } from "../../shared/api";

const ACCEPT = ".wav,.mp3,.flac,.ogg,.m4a,.aac,.aif,.aiff,.opus,.wma,audio/*";

interface Upload {
  name: string;
  progress: number;
  processing: boolean;
}

export default function UploadZone({ onUploaded }: { onUploaded: (song: Song) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [upload, setUpload] = useState<Upload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length || upload) return;
    setErrors([]);
    for (const file of Array.from(files)) {
      setUpload({ name: file.name, progress: 0, processing: false });
      try {
        const song = await api.uploadSong(file, (p) =>
          setUpload({ name: file.name, progress: p, processing: p >= 1 }),
        );
        onUploaded(song);
      } catch (e) {
        setErrors((list) => [...list, `${file.name}: ${(e as Error).message}`]);
      }
    }
    setUpload(null);
  };

  return (
    <div>
      <button
        type="button"
        className={`dropzone ${dragging ? "dropzone-active" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        disabled={!!upload}
      >
        {upload ? (
          <span className="dropzone-body">
            <span className="dropzone-file">{upload.name}</span>
            <span className="faint">{upload.processing ? "Analizando y preparando…" : `Subiendo ${Math.round(upload.progress * 100)} %`}</span>
            <span className={`progress ${upload.processing ? "indeterminate" : ""}`}>
              <div style={{ width: `${upload.progress * 100}%` }} />
            </span>
          </span>
        ) : (
          <span className="dropzone-body">
            <span className="dropzone-icon">＋</span>
            <b>Subir canción</b>
            <span className="faint">Arrastra o haz clic · WAV, MP3, FLAC, M4A…</span>
          </span>
        )}
      </button>
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => {
          void handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
      {errors.map((err) => (
        <div key={err} className="alert alert-error upload-error">
          {err}
        </div>
      ))}
    </div>
  );
}
