"""
Tests unitarios para la To-Do API.
Cubren: index, health, CRUD completo de tasks, casos de error.
"""
import json
import pytest


# ── /index ────────────────────────────────────────────────────────────────────
def test_index_returns_200(client):
    res = client.get("/")
    assert res.status_code == 200


def test_index_returns_api_name(client):
    data = res = client.get("/").get_json()
    assert data["name"] == "To-Do API"


# ── /health ───────────────────────────────────────────────────────────────────
def test_health_returns_200(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_health_status_healthy(client):
    data = client.get("/health").get_json()
    assert data["status"] == "healthy"


def test_health_has_uptime(client):
    data = client.get("/health").get_json()
    assert "uptime_seconds" in data


# ── /metrics ──────────────────────────────────────────────────────────────────
def test_metrics_returns_200(client):
    res = client.get("/metrics")
    assert res.status_code == 200


def test_metrics_content_type(client):
    res = client.get("/metrics")
    assert "text/plain" in res.content_type


# ── GET /tasks (lista vacía) ──────────────────────────────────────────────────
def test_list_tasks_empty(client):
    res = client.get("/tasks")
    assert res.status_code == 200
    assert res.get_json() == []


# ── POST /tasks ───────────────────────────────────────────────────────────────
def test_create_task_returns_201(client):
    res = client.post("/tasks", json={"title": "Comprar leche"})
    assert res.status_code == 201


def test_create_task_persists_title(client):
    client.post("/tasks", json={"title": "Estudiar DevOps"})
    tasks = client.get("/tasks").get_json()
    assert any(t["title"] == "Estudiar DevOps" for t in tasks)


def test_create_task_with_description(client):
    res = client.post("/tasks", json={"title": "Tarea", "description": "Detalle"})
    data = res.get_json()
    assert data["description"] == "Detalle"


def test_create_task_without_title_returns_400(client):
    res = client.post("/tasks", json={"description": "Sin titulo"})
    assert res.status_code == 400


def test_create_task_no_body_returns_400(client):
    res = client.post("/tasks", content_type="application/json", data="")
    assert res.status_code == 400


def test_create_task_default_completed_false(client):
    res = client.post("/tasks", json={"title": "Nueva"})
    data = res.get_json()
    assert data["completed"] in (0, False)


# ── GET /tasks/<id> ───────────────────────────────────────────────────────────
def test_get_task_returns_correct_title(client):
    created = client.post("/tasks", json={"title": "Buscar trabajo"}).get_json()
    res = client.get(f"/tasks/{created['id']}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "Buscar trabajo"


def test_get_task_not_found_returns_404(client):
    res = client.get("/tasks/99999")
    assert res.status_code == 404


# ── PUT /tasks/<id> ───────────────────────────────────────────────────────────
def test_update_task_title(client):
    created = client.post("/tasks", json={"title": "Viejo titulo"}).get_json()
    res = client.put(f"/tasks/{created['id']}", json={"title": "Nuevo titulo"})
    assert res.status_code == 200
    assert res.get_json()["title"] == "Nuevo titulo"


def test_update_task_completed(client):
    created = client.post("/tasks", json={"title": "Pendiente"}).get_json()
    res = client.put(f"/tasks/{created['id']}", json={"completed": 1})
    assert res.get_json()["completed"] in (1, True)


def test_update_task_not_found(client):
    res = client.put("/tasks/99999", json={"title": "x"})
    assert res.status_code == 404


def test_update_task_no_body_returns_400(client):
    created = client.post("/tasks", json={"title": "task"}).get_json()
    res = client.put(f"/tasks/{created['id']}", content_type="application/json", data="")
    assert res.status_code == 400


# ── DELETE /tasks/<id> ────────────────────────────────────────────────────────
def test_delete_task_returns_200(client):
    created = client.post("/tasks", json={"title": "Borrar"}).get_json()
    res = client.delete(f"/tasks/{created['id']}")
    assert res.status_code == 200


def test_delete_task_actually_removed(client):
    created = client.post("/tasks", json={"title": "Temporal"}).get_json()
    client.delete(f"/tasks/{created['id']}")
    res = client.get(f"/tasks/{created['id']}")
    assert res.status_code == 404


def test_delete_task_not_found(client):
    res = client.delete("/tasks/99999")
    assert res.status_code == 404


# ── Flujo completo ────────────────────────────────────────────────────────────
def test_full_crud_flow(client):
    # Create
    created = client.post("/tasks", json={"title": "Flujo", "description": "desc"}).get_json()
    task_id = created["id"]
    assert task_id is not None

    # Read
    assert client.get(f"/tasks/{task_id}").status_code == 200

    # Update
    updated = client.put(f"/tasks/{task_id}", json={"completed": 1}).get_json()
    assert updated["completed"] in (1, True)

    # List contains task
    tasks = client.get("/tasks").get_json()
    assert any(t["id"] == task_id for t in tasks)

    # Delete
    assert client.delete(f"/tasks/{task_id}").status_code == 200

    # Confirm gone
    assert client.get(f"/tasks/{task_id}").status_code == 404
