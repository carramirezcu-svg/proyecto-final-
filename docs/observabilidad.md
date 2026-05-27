# Observabilidad — To-Do API

## Tabla de contenido
1. [¿Qué es observabilidad y por qué importa?](#1-qué-es-observabilidad-y-por-qué-importa)
2. [Los tres pilares implementados](#2-los-tres-pilares-implementados)
3. [Logs estructurados](#3-logs-estructurados)
4. [Health Check — /health](#4-health-check--health)
5. [Métricas — /metrics](#5-métricas--metrics)
6. [Prometheus](#6-prometheus)
7. [Grafana](#7-grafana)
8. [Cómo levantar el stack completo](#8-cómo-levantar-el-stack-completo)
9. [Consultas útiles en Prometheus](#9-consultas-útiles-en-prometheus)

---

## 1. ¿Qué es observabilidad y por qué importa?

La **observabilidad** es la capacidad de entender el estado interno de un sistema a partir de sus salidas externas. En DevOps, un sistema observable permite responder preguntas como:

- ¿Está la aplicación funcionando ahora mismo?
- ¿Qué tan rápido responde cada endpoint?
- ¿Cuántos errores se están produciendo?
- ¿Qué pasó exactamente cuando falló el request de las 3am?

Sin observabilidad, los equipos operan a ciegas. Con ella, es posible detectar problemas antes de que los usuarios los reporten y diagnosticar incidentes en minutos en lugar de horas.

---

## 2. Los tres pilares implementados

```
┌─────────────────────────────────────────────────────────┐
│                    OBSERVABILIDAD                        │
│                                                         │
│   📋 LOGS          📊 MÉTRICAS         ❤️ HEALTH        │
│   ─────────        ─────────────       ──────────       │
│   ¿Qué pasó?       ¿Cómo está?         ¿Está vivo?      │
│   JSON a stdout    Prometheus format   /health HTTP     │
│   timestamp+level  Counter/Histogram   DB check         │
│   por cada req     /metrics endpoint   uptime           │
└─────────────────────────────────────────────────────────┘
```

| Pilar | Implementación | Endpoint/Salida |
|-------|---------------|-----------------|
| Logs | JSONFormatter en Python logging | stdout del contenedor |
| Métricas | prometheus-client | `GET /metrics` |
| Health | Endpoint dedicado | `GET /health` |

---

## 3. Logs estructurados

### ¿Por qué logs en JSON?

Los logs en texto plano como `INFO: Task created` son difíciles de filtrar y analizar a escala. Los logs en JSON permiten ser ingeridos directamente por herramientas como **Loki**, **ELK Stack** o **CloudWatch** sin transformaciones adicionales.

### Implementación

```python
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log_record)
```

### Campos de cada log

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `timestamp` | ISO 8601 UTC | `"2026-05-27T05:00:00+00:00"` |
| `level` | String | `"INFO"`, `"ERROR"`, `"WARNING"` |
| `message` | String | `"Task created id=3"` |
| `logger` | String | `"todo_api"` |
| `exception` | String (solo si hay error) | Traceback completo |

### Ejemplos de logs reales

```json
{"timestamp": "2026-05-27T05:00:00+00:00", "level": "INFO", "message": "Database initialized", "logger": "todo_api"}
{"timestamp": "2026-05-27T05:00:01+00:00", "level": "INFO", "message": "Task created id=1", "logger": "todo_api"}
{"timestamp": "2026-05-27T05:00:02+00:00", "level": "INFO", "message": "Task updated id=1", "logger": "todo_api"}
{"timestamp": "2026-05-27T05:00:03+00:00", "level": "INFO", "message": "Task deleted id=1", "logger": "todo_api"}
{"timestamp": "2026-05-27T05:00:04+00:00", "level": "ERROR", "message": "Health check DB error: ...", "logger": "todo_api"}
```

### Cómo ver los logs en Docker

```bash
# Logs en tiempo real
docker logs -f todo_api

# Últimas 100 líneas
docker logs --tail=100 todo_api

# Con timestamps de Docker
docker logs -t todo_api

# Filtrar solo errores (requiere jq)
docker logs todo_api 2>&1 | jq 'select(.level == "ERROR")'
```

---

## 4. Health Check — /health

### Propósito

El endpoint `/health` permite verificar que la aplicación **y sus dependencias** están funcionando correctamente. Es usado por:
- Docker `HEALTHCHECK` (cada 30 segundos)
- Kubernetes liveness y readiness probes
- Herramientas de monitoreo externas (UptimeRobot, Pingdom, etc.)

### Implementación

```python
@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")   # verifica que la DB responde
        conn.close()
        db_status = "ok"
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = "error"

    status = "healthy" if db_status == "ok" else "unhealthy"
    code   = 200        if db_status == "ok" else 503
    return jsonify({
        "status":          status,
        "database":        db_status,
        "uptime_seconds":  round(time.time() - APP_START, 2),
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }), code
```

### Respuestas

**Caso normal (HTTP 200):**
```json
{
  "status": "healthy",
  "database": "ok",
  "uptime_seconds": 3672.45,
  "timestamp": "2026-05-27T05:00:00+00:00"
}
```

**Caso de fallo en BD (HTTP 503):**
```json
{
  "status": "unhealthy",
  "database": "error",
  "uptime_seconds": 15.2,
  "timestamp": "2026-05-27T05:00:00+00:00"
}
```

### Cómo consultarlo

```bash
curl http://localhost:5000/health
```

---

## 5. Métricas — /metrics

### Propósito

El endpoint `/metrics` expone métricas en el **formato estándar de Prometheus** (texto plano con etiquetas). Prometheus hace scraping de este endpoint cada 15 segundos para almacenar los datos en su base de datos de series de tiempo.

### Métricas implementadas

#### `http_requests_total` (Counter)
Cuenta el total acumulado de requests HTTP, con etiquetas para método, endpoint y código de estado.

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/tasks",method="GET",status="200"} 142.0
http_requests_total{endpoint="/tasks",method="POST",status="201"} 38.0
http_requests_total{endpoint="/tasks",method="POST",status="400"} 3.0
http_requests_total{endpoint="/health",method="GET",status="200"} 720.0
```

**Usos:** calcular tasa de requests por segundo, detectar picos de tráfico, medir tasa de errores.

#### `http_request_duration_seconds` (Histogram)
Mide la latencia de cada request, agrupada en buckets. Permite calcular percentiles (p50, p95, p99).

```
# HELP http_request_duration_seconds Request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/tasks",method="GET",le="0.005"} 120.0
http_request_duration_seconds_bucket{endpoint="/tasks",method="GET",le="0.01"} 138.0
http_request_duration_seconds_bucket{endpoint="/tasks",method="GET",le="0.025"} 142.0
http_request_duration_seconds_sum{endpoint="/tasks",method="GET"} 0.892
http_request_duration_seconds_count{endpoint="/tasks",method="GET"} 142.0
```

**Usos:** detectar endpoints lentos, identificar degradación de rendimiento, definir SLOs de latencia.

#### `tasks_total` (Gauge)
Refleja el número actual de tareas en la base de datos. Se actualiza en cada request a `/metrics`.

```
# HELP tasks_total Current number of tasks
# TYPE tasks_total gauge
tasks_total 15.0
```

**Usos:** monitorear el crecimiento de datos, crear alertas si supera un umbral.

### Middleware de métricas

Cada request es registrado automáticamente mediante hooks de Flask:

```python
@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - request._start_time
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    return response
```

### Cómo consultarlo

```bash
curl http://localhost:5000/metrics
```

---

## 6. Prometheus

### ¿Qué es?

Prometheus es un sistema de monitoreo y base de datos de series de tiempo diseñado para entornos cloud-native. Hace **scraping** (recolección activa) de los endpoints `/metrics` de las aplicaciones a intervalos configurables.

### Configuración del scrape

Archivo `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s       # cada cuánto recolectar métricas
  evaluation_interval: 15s   # cada cuánto evaluar reglas de alerta

scrape_configs:
  - job_name: "todo_api"
    static_configs:
      - targets: ["api:5000"]  # nombre del servicio en docker-compose
    metrics_path: /metrics
```

**`scrape_interval: 15s`** significa que Prometheus consulta `/metrics` cada 15 segundos y almacena los valores con su timestamp.

### Acceso

```
http://localhost:9090
```

No requiere usuario ni contraseña en la configuración base.

---

## 7. Grafana

### ¿Qué es?

Grafana es una plataforma de visualización que se conecta a Prometheus (y otras fuentes) para crear dashboards interactivos con gráficas, alertas y paneles de estado.

### Configuración automática

El datasource de Prometheus se provisiona automáticamente al levantar el stack, gracias al archivo:

`monitoring/grafana/provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

Esto significa que al abrir Grafana por primera vez, ya estará conectado a Prometheus sin configuración manual.

### Acceso

```
http://localhost:3000
Usuario:    admin
Contraseña: admin123
```

### Dashboards recomendados para importar

Una vez dentro de Grafana, ir a **Dashboards → Import** e ingresar el ID:

| Dashboard | ID | Descripción |
|-----------|-----|-------------|
| Flask / Python app | `9528` | Métricas de Flask con Prometheus |
| Node Exporter Full | `1860` | Métricas del sistema (si se agrega node-exporter) |

---

## 8. Cómo levantar el stack completo

```bash
# Desde la raíz del proyecto
docker-compose up --build
```

Esto levanta tres servicios en red interna:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| API To-Do | http://localhost:5000 | La aplicación Flask |
| Prometheus | http://localhost:9090 | Base de datos de métricas |
| Grafana | http://localhost:3000 | Dashboards de visualización |

**Verificar que todo está funcionando:**

```bash
# API responde
curl http://localhost:5000/health

# Prometheus recibe métricas
curl http://localhost:9090/api/v1/targets

# Ver métricas raw
curl http://localhost:5000/metrics
```

---

## 9. Consultas útiles en Prometheus

Abrir `http://localhost:9090` → pestaña **Graph** y ejecutar:

### Tasa de requests por segundo (últimos 5 minutos)
```promql
rate(http_requests_total[5m])
```

### Tasa de errores 5xx
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

### Latencia promedio por endpoint
```promql
rate(http_request_duration_seconds_sum[5m])
/
rate(http_request_duration_seconds_count[5m])
```

### Percentil 95 de latencia
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Número actual de tareas
```promql
tasks_total
```

### Requests totales agrupados por endpoint
```promql
sum by (endpoint) (http_requests_total)
```
