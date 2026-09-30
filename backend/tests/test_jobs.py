import threading

from app.db import Database
from app.jobs import JobQueue, UserError


def test_trabajos_uno_a_la_vez_y_estados(tmp_path):
    db = Database(tmp_path / "t.db")
    q = JobQueue(db)
    running = []
    max_parallel = 0
    lock = threading.Lock()

    def handler(ctx):
        nonlocal max_parallel
        with lock:
            running.append(1)
            max_parallel = max(max_parallel, len(running))
        ctx.progress(0.5, "mitad")
        with lock:
            running.pop()
        if ctx.params.get("fail") == "user":
            raise UserError("mensaje claro")
        if ctx.params.get("fail") == "boom":
            raise RuntimeError("boom")
        return {"ok": True}

    q.register("t", handler)
    q.start()
    ok = q.submit("t", None, {})
    user = q.submit("t", None, {"fail": "user"})
    boom = q.submit("t", None, {"fail": "boom"})
    q.wait_idle()
    q.stop()

    assert max_parallel == 1
    assert db.get_job(ok["id"])["status"] == "done"
    assert db.get_job(ok["id"])["result"] == {"ok": True}
    assert db.get_job(user["id"])["error"] == "mensaje claro"
    assert "boom" in db.get_job(boom["id"])["error"]


def test_al_reiniciar_marca_interrumpidos_y_retoma_pendientes(tmp_path):
    db = Database(tmp_path / "t.db")
    stuck = db.create_job("t", None, {})
    db.update_job(stuck["id"], status="running")
    pending = db.create_job("t", None, {})

    q = JobQueue(db)
    q.register("t", lambda ctx: {})
    q.start()
    q.wait_idle()
    q.stop()

    assert db.get_job(stuck["id"])["status"] == "error"
    assert db.get_job(pending["id"])["status"] == "done"


def test_cancelar_pendiente(tmp_path):
    db = Database(tmp_path / "t.db")
    q = JobQueue(db)
    q.register("t", lambda ctx: {})
    job = q.submit("t", None, {})  # sin start(): queda pendiente
    assert q.cancel(job["id"])
    assert db.get_job(job["id"])["status"] == "cancelled"
