"""Biblioteca en SQLite: canciones, trabajos y stems."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Cada entrada es una migración; el índice + 1 es la versión (PRAGMA user_version).
MIGRATIONS: list[str] = [
    """
    CREATE TABLE songs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        sample_rate INTEGER NOT NULL,
        channels INTEGER NOT NULL,
        frames INTEGER NOT NULL,
        duration REAL NOT NULL,
        bpm REAL,
        musical_key TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE jobs (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        song_id TEXT REFERENCES songs(id) ON DELETE CASCADE,
        status TEXT NOT NULL,
        progress REAL NOT NULL DEFAULT 0,
        message TEXT NOT NULL DEFAULT '',
        params TEXT NOT NULL DEFAULT '{}',
        result TEXT,
        error TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    );
    CREATE INDEX idx_jobs_status ON jobs(status, created_at);
    CREATE TABLE stems (
        id TEXT PRIMARY KEY,
        song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
        job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        model TEXT NOT NULL,
        experimental INTEGER NOT NULL DEFAULT 0,
        wav_path TEXT NOT NULL,
        preview_path TEXT NOT NULL,
        peak REAL NOT NULL DEFAULT 0,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE INDEX idx_stems_song ON stems(song_id);
    """,
]

SONG_FIELDS = ("title", "bpm", "musical_key")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for key in ("params", "result"):
        if key in d and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    if "experimental" in d:
        d["experimental"] = bool(d["experimental"])
    return d


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _migrate(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            for i, sql in enumerate(MIGRATIONS[version:], start=version + 1):
                conn.executescript(sql)
                conn.execute(f"PRAGMA user_version = {i}")

    # --- Canciones -------------------------------------------------------

    def create_song(self, **fields: Any) -> dict[str, Any]:
        song = {"id": new_id(), "bpm": None, "musical_key": None, "created_at": now(), **fields}
        cols = ", ".join(song)
        marks = ", ".join(f":{k}" for k in song)
        with self.connect() as conn:
            conn.execute(f"INSERT INTO songs ({cols}) VALUES ({marks})", song)
        return song

    def get_song(self, song_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _row(conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone())

    def list_songs(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM songs ORDER BY created_at DESC").fetchall()
        return [_row(r) for r in rows]  # type: ignore[misc]

    def update_song(self, song_id: str, **fields: Any) -> dict[str, Any] | None:
        fields = {k: v for k, v in fields.items() if k in SONG_FIELDS}
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            with self.connect() as conn:
                conn.execute(f"UPDATE songs SET {sets} WHERE id = :id", {**fields, "id": song_id})
        return self.get_song(song_id)

    def delete_song(self, song_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))

    # --- Trabajos --------------------------------------------------------

    def create_job(self, type: str, song_id: str | None, params: dict[str, Any]) -> dict[str, Any]:
        job = {
            "id": new_id(),
            "type": type,
            "song_id": song_id,
            "status": "pending",
            "progress": 0.0,
            "message": "En cola",
            "params": json.dumps(params),
            "created_at": now(),
        }
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO jobs (id, type, song_id, status, progress, message, params, created_at) "
                "VALUES (:id, :type, :song_id, :status, :progress, :message, :params, :created_at)",
                job,
            )
        return self.get_job(job["id"])  # type: ignore[return-value]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _row(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def list_jobs(self, song_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM jobs WHERE 1 = 1", []
        if song_id:
            sql += " AND song_id = ?"
            args.append(song_id)
        if status:
            sql += " AND status = ?"
            args.append(status)
        with self.connect() as conn:
            rows = conn.execute(sql + " ORDER BY created_at DESC", args).fetchall()
        return [_row(r) for r in rows]  # type: ignore[misc]

    def update_job(self, job_id: str, **fields: Any) -> None:
        if "result" in fields and fields["result"] is not None:
            fields["result"] = json.dumps(fields["result"])
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        with self.connect() as conn:
            conn.execute(f"UPDATE jobs SET {sets} WHERE id = :id", {**fields, "id": job_id})

    def delete_job(self, job_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    # --- Stems -----------------------------------------------------------

    def create_stem(self, **fields: Any) -> dict[str, Any]:
        stem = {"id": new_id(), "created_at": now(), "experimental": False, **fields}
        cols = ", ".join(stem)
        marks = ", ".join(f":{k}" for k in stem)
        with self.connect() as conn:
            conn.execute(f"INSERT INTO stems ({cols}) VALUES ({marks})", stem)
        return stem

    def get_stem(self, stem_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return _row(conn.execute("SELECT * FROM stems WHERE id = ?", (stem_id,)).fetchone())

    def list_stems(self, song_id: str | None = None, job_id: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM stems WHERE 1 = 1", []
        if song_id:
            sql += " AND song_id = ?"
            args.append(song_id)
        if job_id:
            sql += " AND job_id = ?"
            args.append(job_id)
        with self.connect() as conn:
            rows = conn.execute(sql + " ORDER BY created_at, position", args).fetchall()
        return [_row(r) for r in rows]  # type: ignore[misc]
