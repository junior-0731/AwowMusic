"""Cola de trabajos: un solo hilo de trabajo, así la GPU procesa un trabajo a la vez."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

from .db import Database, now

log = logging.getLogger(__name__)


class UserError(Exception):
    """Error con un mensaje claro para mostrar en la interfaz."""


class JobContext:
    def __init__(self, db: Database, job: dict[str, Any]):
        self.db = db
        self.job = job

    @property
    def params(self) -> dict[str, Any]:
        return self.job["params"]

    def progress(self, progress: float, message: str) -> None:
        self.db.update_job(self.job["id"], progress=round(max(0.0, min(1.0, progress)), 3), message=message)


Handler = Callable[[JobContext], dict[str, Any]]


class JobQueue:
    def __init__(self, db: Database):
        self.db = db
        self._handlers: dict[str, Handler] = {}
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def register(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    def start(self) -> None:
        # Un trabajo que quedó "running" es porque la app se cerró a mitad de camino.
        for job in self.db.list_jobs(status="running"):
            self.db.update_job(
                job["id"], status="error", error="Interrumpido: la app se cerró durante el proceso.", finished_at=now()
            )
        for job in reversed(self.db.list_jobs(status="pending")):
            self._queue.put(job["id"])
        self._thread = threading.Thread(target=self._worker, name="job-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float | None = 5) -> None:
        if self._thread:
            self._queue.put(None)
            self._thread.join(timeout)
            self._thread = None

    def submit(self, job_type: str, song_id: str | None, params: dict[str, Any]) -> dict[str, Any]:
        if job_type not in self._handlers:
            raise ValueError(f"Tipo de trabajo desconocido: {job_type}")
        job = self.db.create_job(job_type, song_id, params)
        self._queue.put(job["id"])
        return job

    def cancel(self, job_id: str) -> bool:
        """Cancela un trabajo que aún no empezó."""
        job = self.db.get_job(job_id)
        if not job or job["status"] != "pending":
            return False
        self.db.update_job(job_id, status="cancelled", message="Cancelado", finished_at=now())
        return True

    def wait_idle(self) -> None:
        self._queue.join()

    def _worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                if job_id is None:
                    return
                self._run(job_id)
            finally:
                self._queue.task_done()

    def _run(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        if not job or job["status"] != "pending":
            return
        self.db.update_job(job_id, status="running", started_at=now(), message="Iniciando")
        job["status"] = "running"
        try:
            result = self._handlers[job["type"]](JobContext(self.db, job))
            self.db.update_job(
                job_id, status="done", progress=1.0, message="Listo", result=result, finished_at=now()
            )
        except UserError as e:
            self.db.update_job(job_id, status="error", error=str(e), message="Error", finished_at=now())
        except Exception as e:  # noqa: BLE001 - cualquier fallo se reporta en el trabajo
            log.exception("Falló el trabajo %s", job_id)
            self.db.update_job(
                job_id, status="error", error=f"Error inesperado: {e}", message="Error", finished_at=now()
            )
