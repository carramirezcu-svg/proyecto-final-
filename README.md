# To-Do API — Semilla para Trabajo Final DevOps

API REST básica de gestión de tareas. **Este es el punto de partida** — su trabajo es construir todo el ecosistema DevOps alrededor.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Info de la API |
| GET | `/tasks` | Listar todas las tareas |
| POST | `/tasks` | Crear tarea (`{"title": "...", "description": "..."}`) |
| GET | `/tasks/<id>` | Obtener una tarea |
| PUT | `/tasks/<id>` | Actualizar tarea |
| DELETE | `/tasks/<id>` | Eliminar tarea |

## Ejecutar

```bash
pip install -r requirements.txt
python src/app.py
```

La API corre en `http://localhost:5000`.

## Qué falta (su trabajo)

TODO lo relacionado con DevOps. Partiendo de esta app, deben implementar:

1. **Tests unitarios** — Mínimo 5, en carpeta `tests/`
2. **Dockerfile** + **docker-compose.yml** — Contenerizar la app
3. **Pipeline CI/CD** — `.github/workflows/ci-cd.yml` con GitHub Actions
4. **Observabilidad** — Logs estructurados, `/health`, `/metrics`, Prometheus/Grafana
5. **Seguridad** — Auditoría de dependencias, linting
6. **Kubernetes** — Manifests en `k8s/` (bonus)
7. **Documentación** — `docs/` con pipeline, branching, observabilidad, CALMS
8. **Artefactos** — Imagen versionada, reportes de build

Lean el documento del trabajo final para los detalles completos de cada requisito.

## Stack

- **Lenguaje:** Python 3.11
- **Framework:** Flask
- **Base de datos:** SQLite (ya incluida, no necesita instalación)
- **Dependencias:** Ver `requirements.txt`

---

*DevOps & Automatización — UNAL Sede Manizales — 2026-1*
