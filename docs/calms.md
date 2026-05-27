# Marco CALMS — To-Do API

## Tabla de contenido
1. [¿Qué es CALMS?](#1-qué-es-calms)
2. [Culture — Cultura](#2-culture--cultura)
3. [Automation — Automatización](#3-automation--automatización)
4. [Lean — Lean](#4-lean--lean)
5. [Measurement — Medición](#5-measurement--medición)
6. [Sharing — Compartir](#6-sharing--compartir)
7. [Resumen de implementación](#7-resumen-de-implementación)

---

## 1. ¿Qué es CALMS?

CALMS es el marco conceptual que define los principios fundamentales de DevOps. No es una herramienta ni un proceso, sino una **filosofía** que guía cómo los equipos deben trabajar para lograr entregas de software rápidas, confiables y sostenibles.

El acrónimo fue popularizado por Damon Edwards y John Willis como una forma de evaluar si una organización está adoptando DevOps de manera genuina o solo usando las herramientas sin cambiar la cultura subyacente.

| Letra | Principio | Pregunta clave |
|-------|-----------|----------------|
| **C** | Culture (Cultura) | ¿El equipo comparte responsabilidad? |
| **A** | Automation (Automatización) | ¿Qué procesos manuales podemos eliminar? |
| **L** | Lean | ¿Estamos eliminando desperdicio? |
| **M** | Measurement (Medición) | ¿Sabemos con datos si mejoramos? |
| **S** | Sharing (Compartir) | ¿El conocimiento fluye dentro del equipo? |

---

## 2. Culture — Cultura

### Definición

La cultura DevOps rompe los silos tradicionales entre los equipos de desarrollo (que quieren cambiar cosas rápido) y operaciones (que quieren estabilidad). El objetivo es que ambos compartan responsabilidad sobre el ciclo de vida completo del software: desde el código hasta la producción.

### Aplicación en este proyecto

**Responsabilidad compartida del pipeline:**
En este proyecto, quien escribe el código también escribe los tests, define el Dockerfile y configura el pipeline de CI/CD. No existe un equipo separado de "QA" o "infraestructura" que reciba el código y lo valide por separado. Esto refleja el principio de "you build it, you run it" de Amazon.

**Calidad como parte del desarrollo:**
Los tests no son una tarea opcional que se hace al final. Son parte del ciclo de desarrollo: cada endpoint tiene sus tests asociados, y el pipeline rechaza el código que no alcanza el 80% de cobertura. La calidad está integrada, no agregada.

**Feedback rápido:**
El pipeline da retroalimentación en minutos. Si se rompe un test o hay un error de lint, el desarrollador lo sabe antes de hacer merge, no después de un deploy fallido en producción.

**Evidencia en el repositorio:**
- Tests junto al código (`tests/`)
- Dockerfile junto al código
- Pipeline junto al código (`.github/workflows/`)
- Documentación junto al código (`docs/`)

Todo en el mismo repositorio, visible y modificable por cualquier miembro del equipo.

---

## 3. Automation — Automatización

### Definición

La automatización en DevOps elimina las tareas manuales repetitivas y propensas a error. Cada paso que se puede automatizar debe automatizarse. El objetivo es que el camino desde el código hasta producción no requiera intervención humana para las tareas rutinarias.

### Qué se automatizó en este proyecto

**Verificación de calidad del código:**
```
Antes: el desarrollador recuerda (o no) correr flake8 localmente
Ahora: flake8 corre automáticamente en cada push y PR
```

**Auditoría de seguridad de dependencias:**
```
Antes: nadie revisa si flask==3.0.0 tiene vulnerabilidades conocidas
Ahora: pip-audit escanea requirements.txt en cada ejecución del pipeline
```

**Ejecución de tests:**
```
Antes: "acordarse" de correr pytest antes de hacer merge
Ahora: pytest corre con cobertura en cada push; el merge está bloqueado si falla
```

**Construcción de la imagen Docker:**
```
Antes: docker build manual en la máquina del desarrollador
Ahora: la imagen se construye automáticamente con el tag correcto en cada push a main/develop
```

**Versionado de la imagen:**
```
Antes: tags manuales como "imagen-final", "imagen-v2", "imagen-nueva-de-verdad"
Ahora: tag automático con SHA del commit (sha-a1b2c3d) y latest en main
```

**Publicación en el registro:**
```
Antes: docker push manual con credenciales locales
Ahora: push automático a GHCR con GITHUB_TOKEN sin credenciales manuales
```

**Deploy:**
```
Antes: SSH al servidor, pull manual, restart manual
Ahora: docker-compose pull && docker-compose up -d en cada merge a main
```

### Herramientas de automatización

| Herramienta | Tarea automatizada |
|-------------|-------------------|
| GitHub Actions | Orquestación del pipeline completo |
| flake8 | Análisis estático de código |
| pip-audit | Auditoría de dependencias |
| pytest + pytest-cov | Tests + cobertura |
| docker/build-push-action | Build y push de imagen |
| docker/metadata-action | Generación automática de tags |

---

## 4. Lean — Lean

### Definición

Lean proviene de la manufactura japonesa (Toyota Production System) y en DevOps se traduce en eliminar desperdicio, reducir el trabajo en progreso y acortar los ciclos de entrega. Un pipeline Lean entrega valor al cliente en el menor tiempo posible, sin pasos innecesarios.

### Tipos de desperdicio eliminados

**Espera entre etapas:**
El pipeline corre automáticamente. No hay que esperar a que alguien "tenga tiempo" de revisar el código ni de hacer el deploy. El tiempo entre un commit y el deploy en producción es de aproximadamente 3 minutos.

**Trabajo repetitivo:**
Antes de CI/CD, cada desarrollador repetía manualmente los mismos pasos: instalar dependencias, correr tests, construir imagen, hacer push, conectarse al servidor, hacer deploy. Ahora esos pasos se ejecutan una vez en el pipeline y nunca se repiten manualmente.

**Defectos que escapan a producción:**
Cada defecto que llega a producción es costoso: hay que detectarlo, reproducirlo, corregirlo, hacer un nuevo deploy. El pipeline detecta errores antes del merge, reduciendo el costo de cada defecto.

**Dependencias externas en tests:**
Los tests unitarios usan una base de datos SQLite en memoria (`:memory:`). Esto elimina la dependencia de un servidor de base de datos externo para correr los tests, lo que hace que sean más rápidos y sin infraestructura adicional.

### Métricas Lean del proyecto

| Indicador | Valor |
|-----------|-------|
| Tiempo de pipeline completo | ~3 minutos |
| Tiempo de feedback ante un test roto | < 2 minutos (etapa de tests) |
| Reducción de tamaño de imagen (multi-stage vs single-stage) | ~50% |
| Tests sin dependencias externas | 100% (in-memory DB) |
| Pasos manuales en el deploy | 0 |

### Dockerfile multi-stage como ejemplo de Lean

```dockerfile
# Etapa builder: instala todas las dependencias
FROM python:3.11-slim AS builder
RUN pip install --prefix=/install -r requirements.txt

# Etapa runtime: copia solo lo necesario
FROM python:3.11-slim
COPY --from=builder /install /usr/local
COPY src/app.py .
```

La imagen final no incluye compiladores, headers de desarrollo ni archivos de build. Solo tiene lo necesario para ejecutar la aplicación. Esto es eliminar desperdicio aplicado a los contenedores.

---

## 5. Measurement — Medición

### Definición

"Si no puedes medirlo, no puedes mejorarlo." En DevOps, la medición continua es lo que permite saber si los cambios que hacemos realmente mejoran el sistema. Sin métricas, las decisiones se toman por intuición; con métricas, se toman con datos.

### ¿Qué se mide en este proyecto?

#### Calidad del código (en el pipeline)

| Métrica | Herramienta | Umbral | Dónde se ve |
|---------|------------|--------|-------------|
| Cobertura de tests | pytest-cov | ≥ 80% (enforced) | `coverage.xml`, terminal |
| Tests pasando | pytest | 100% | `test-results.xml`, GitHub Actions |
| Errores de estilo | flake8 | 0 errores críticos | Log del pipeline |
| Vulnerabilidades | pip-audit | Reporte visible | `audit-report.json` |

#### Comportamiento en producción (runtime)

| Métrica | Tipo Prometheus | Qué mide |
|---------|----------------|---------|
| `http_requests_total` | Counter | Volumen de tráfico por endpoint y método |
| `http_request_duration_seconds` | Histogram | Latencia de respuesta (p50, p95, p99) |
| `tasks_total` | Gauge | Tamaño actual de los datos |
| `/health` HTTP 200/503 | — | Disponibilidad del servicio |

#### Disponibilidad del servicio

El endpoint `/health` responde HTTP 200 cuando la API y la base de datos funcionan, y HTTP 503 cuando hay un problema. Este valor puede ser scrapeado por Prometheus para calcular el **uptime** del servicio:

```promql
# Disponibilidad en los últimos 24 horas (% de tiempo con /health = 200)
avg_over_time(up{job="todo_api"}[24h]) * 100
```

#### Tasa de errores

```promql
# Porcentaje de requests que terminan en error 5xx
rate(http_requests_total{status=~"5.."}[5m])
/
rate(http_requests_total[5m])
* 100
```

#### Latencia (SLO recomendado)

Un SLO (Service Level Objective) de latencia podría definirse como: "El 95% de las requests a `/tasks` deben responder en menos de 200ms."

```promql
# Verificar SLO de latencia p95 < 200ms
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{endpoint="/tasks"}[5m])
) < 0.2
```

### Por qué la medición continua importa

Sin métricas, una degradación de rendimiento del 20% podría pasar desapercibida durante semanas. Con Prometheus y Grafana, ese deterioro es visible en minutos y puede correlacionarse con el deploy que lo causó.

---

## 6. Sharing — Compartir

### Definición

Sharing en CALMS va más allá de documentar. Es la práctica de hacer que el conocimiento, las herramientas, las configuraciones y los aprendizajes sean accesibles para todos los miembros del equipo y para el futuro. Incluye transparencia, documentación viva y cultura de no guardar conocimiento en silos.

### Cómo se aplica en este proyecto

**Infrastructure as Code (IaC):**
Toda la infraestructura está definida en archivos dentro del repositorio. Cualquier miembro del equipo puede levantar exactamente el mismo entorno con un solo comando:
```bash
docker-compose up --build
```
No hay configuraciones secretas en la cabeza de alguien ni en un servidor que "solo Juan sabe cómo configurar".

**Pipeline visible y auditable:**
El archivo `.github/workflows/ci-cd.yml` es el contrato del equipo con el proceso de entrega. Cualquiera puede leerlo, entenderlo y proponer mejoras mediante un PR. El historial de ejecuciones en GitHub Actions es público para el equipo y muestra exactamente qué pasó en cada build.

**Documentación junto al código:**
La documentación no está en una wiki externa que se desactualiza. Está en `docs/` dentro del mismo repositorio, versionada con el código. Cuando cambia el pipeline, el PR que lo cambia también debe actualizar la documentación correspondiente.

**Convención de commits compartida:**
La convención de Conventional Commits hace que el historial de git sea legible para cualquier persona del equipo, no solo para quien escribió el código. Un desarrollador nuevo puede entender qué cambió y por qué leyendo el historial.

**Logs estructurados en JSON:**
Los logs en JSON no requieren que alguien "sepa parsear" el formato particular de la aplicación. Cualquier herramienta estándar (jq, Loki, ELK, CloudWatch) puede ingerirlos y filtrarlos sin configuración especial.

**Configuración externalizada:**
Los parámetros de configuración (puerto, ruta de la DB) se pasan como variables de entorno, documentadas en el `docker-compose.yml` y el `Dockerfile`. No hay "magia" que solo el desarrollador original conoce.

### Cultura de Sharing vs. cultura de silos

| Cultura de silos ❌ | Cultura de Sharing ✅ |
|--------------------|----------------------|
| "Solo yo sé cómo hacer el deploy" | Deploy automatizado, cualquiera puede triggerearlo |
| Documentación en Word compartido en email | `docs/` versionado en el repo |
| Configuración del servidor guardada en la mente | `docker-compose.yml` y variables de entorno |
| "La imagen está en mi máquina" | Imagen en GHCR, accesible por todo el equipo |
| Tests que solo corren en la máquina del dev | Tests en CI, reproducibles en cualquier entorno |

---

## 7. Resumen de implementación

| Principio | Evidencia en el proyecto |
|-----------|------------------------|
| **Culture** | Tests obligatorios, calidad integrada, pipeline bloqueante, responsabilidad del desarrollador sobre su código en producción |
| **Automation** | Pipeline de 4 etapas, deploy automático, build y push de imagen sin intervención manual, tags versionados automáticamente |
| **Lean** | Pipeline en ~3 minutos, tests sin dependencias externas, imagen multi-stage, 0 pasos manuales en deploy |
| **Measurement** | 3 métricas Prometheus, /health con DB check, cobertura enforced al 80%, reportes de build en cada pipeline |
| **Sharing** | IaC en el repo, docs/ versionadas, commits convencionales, logs en JSON estándar, configuración en variables de entorno |
