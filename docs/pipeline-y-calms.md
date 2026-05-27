# Documentación DevOps — To-Do API

## Tabla de contenido
1. [Pipeline CI/CD](#pipeline-cicd)
2. [Estrategia de Branching](#estrategia-de-branching)
3. [Observabilidad](#observabilidad)
4. [Marco CALMS](#marco-calms)

---

## Pipeline CI/CD

### Flujo general

```
Push/PR → Lint & Seguridad → Tests (+ cobertura) → Build Docker → Deploy
```

### Etapas

| Etapa | Trigger | Herramientas | Artefacto generado |
|-------|---------|-------------|-------------------|
| **Lint & Seguridad** | Todo push/PR | flake8, pip-audit | `audit-report.json` |
| **Tests unitarios** | Todo push/PR | pytest, pytest-cov | `test-results.xml`, `coverage.xml` |
| **Build imagen** | Push a main/develop | Docker, GHCR | Imagen versionada con SHA |
| **Deploy** | Push a main | docker-compose / SSH | Contenedor actualizado en prod |

### Reglas de protección
- `main`: requiere PR aprobado + CI verde antes de merge
- `develop`: CI verde obligatorio
- No se permite push directo a `main`

---

## Estrategia de Branching

Se usa **GitHub Flow simplificado**:

```
main (producción estable)
 └── develop (integración continua)
      ├── feature/nombre-feature
      ├── fix/descripcion-bug
      └── hotfix/urgente
```

### Convención de commits (Conventional Commits)

```
feat: agregar endpoint de búsqueda
fix: corregir query de actualización de tarea
docs: actualizar README con instrucciones Docker
test: agregar tests para /health
ci: agregar etapa de auditoría de dependencias
```

---

## Observabilidad

### Endpoints de operaciones

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Estado de la API y la base de datos |
| `GET /metrics` | Métricas en formato Prometheus |

### Métricas expuestas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `http_requests_total` | Counter | Total de requests por método, endpoint y status |
| `http_request_duration_seconds` | Histogram | Latencia de cada request |
| `tasks_total` | Gauge | Número actual de tareas en la DB |

### Logs estructurados

Todos los logs se emiten en JSON con campos:
- `timestamp` (ISO 8601 UTC)
- `level` (INFO, ERROR, etc.)
- `message`
- `logger`

Ejemplo:
```json
{"timestamp": "2026-05-27T05:00:00+00:00", "level": "INFO", "message": "Task created id=3", "logger": "todo_api"}
```

### Stack de monitoreo

```
API → /metrics → Prometheus (scrape cada 15s) → Grafana (dashboards)
```

Accesos locales:
- **Grafana**: http://localhost:3000 (admin / admin123)
- **Prometheus**: http://localhost:9090

---

## Marco CALMS

### Culture (Cultura)
El proyecto adopta una cultura de **responsabilidad compartida**: quien escribe el código también escribe los tests, el Dockerfile y el pipeline. La calidad es responsabilidad del equipo, no de un departamento separado.

### Automation (Automatización)
Todo el ciclo de vida está automatizado mediante GitHub Actions:
- Lint automático en cada PR
- Tests con reporte de cobertura en cada push
- Build y push de imagen versionada automáticamente
- Deploy sin intervención manual en merges a `main`

### Lean (Lean)
Se eliminó desperdicio evitando pasos manuales y promoviendo feedback rápido:
- Pipeline completo corre en ~3 minutos
- Tests unitarios con in-memory DB: sin dependencias externas
- Multi-stage Dockerfile reduce imagen final (~50% menos que single-stage)

### Measurement (Medición)
Métricas clave rastreadas:
- **Cobertura de tests**: mínimo 80% (enforced en pipeline)
- **Latencia de endpoints**: via `http_request_duration_seconds`
- **Tasa de errores**: via `http_requests_total{status=~"5.."}`
- **Disponibilidad**: via `/health` + Prometheus alerting

### Sharing (Compartir)
- Toda la configuración de infraestructura está en el repositorio (Infrastructure as Code)
- Documentación junto al código (`docs/`)
- Pipeline visible y auditable por todos los miembros del equipo
- Logs estructurados en JSON permiten integración con cualquier sistema de log aggregation (ELK, Loki, CloudWatch)
