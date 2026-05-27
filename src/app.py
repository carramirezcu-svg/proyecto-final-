from flask import Flask, request, jsonify
import sqlite3
import os
import logging
import json
import time
from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── Logging estructurado ──────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("todo_api")

# ── Métricas Prometheus ───────────────────────────────────────────────────────
REQUEST_COUNT   = Counter("http_requests_total",   "Total HTTP requests",      ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "endpoint"])
TASKS_TOTAL     = Gauge("tasks_total", "Current number of tasks")

app = Flask(__name__)
APP_START = time.time()
DB_PATH = os.environ.get("DB_PATH", "tasks.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed   BOOLEAN DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized")


init_db()


# ── Middleware de métricas ────────────────────────────────────────────────────
@app.before_request
def start_timer():
    request._start_time = time.time()


@app.after_request
def record_metrics(response):
    endpoint = request.path
    latency  = time.time() - getattr(request, "_start_time", time.time())
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(latency)
    logger.info("request handled", extra={})
    return response


# ── Endpoints de operaciones ──────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({"name": "To-Do API", "version": "1.0.0", "endpoints": ["/tasks", "/health", "/metrics"]})


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = "error"

    status = "healthy" if db_status == "ok" else "unhealthy"
    code   = 200        if db_status == "ok" else 503
    return jsonify({
        "status":   status,
        "database": db_status,
        "uptime_seconds": round(time.time() - APP_START, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), code


@app.route("/metrics", methods=["GET"])
def metrics():
    # Actualizar gauge de tareas
    try:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.close()
        TASKS_TOTAL.set(count)
    except Exception:
        pass
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ── CRUD tasks ────────────────────────────────────────────────────────────────
@app.route("/tasks", methods=["GET"])
def list_tasks():
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    logger.info(f"Listed {len(tasks)} tasks")
    return jsonify([dict(t) for t in tasks])


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "El campo 'title' es obligatorio"}), 400

    title       = data["title"]
    description = data.get("description", "")

    conn   = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (title, description),
    )
    task_id = cursor.lastrowid
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    logger.info(f"Task created id={task_id}")
    return jsonify(dict(task)), 201


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if task is None:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(dict(task))


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se enviaron datos"}), 400

    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        conn.close()
        return jsonify({"error": "Tarea no encontrada"}), 404

    title       = data.get("title",       task["title"])
    description = data.get("description", task["description"])
    completed   = data.get("completed",   task["completed"])

    conn.execute(
        "UPDATE tasks SET title=?, description=?, completed=? WHERE id=?",
        (title, description, completed, task_id),
    )
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    logger.info(f"Task updated id={task_id}")
    return jsonify(dict(task))


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        conn.close()
        return jsonify({"error": "Tarea no encontrada"}), 404

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    logger.info(f"Task deleted id={task_id}")
    return jsonify({"message": "Tarea eliminada"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
