# Pipeline CI/CD — To-Do API

## Tabla de contenido
1. [Descripción general](#1-descripción-general)
2. [Trigger y condiciones](#2-trigger-y-condiciones)
3. [Etapas del pipeline](#3-etapas-del-pipeline)
   - [Etapa 1 — Lint & Seguridad](#etapa-1--lint--seguridad)
   - [Etapa 2 — Tests unitarios](#etapa-2--tests-unitarios)
   - [Etapa 3 — Build de imagen Docker](#etapa-3--build-de-imagen-docker)
   - [Etapa 4 — Deploy a producción](#etapa-4--deploy-a-producción)
4. [Artefactos generados](#4-artefactos-generados)
5. [Variables y secretos](#5-variables-y-secretos)
6. [Reporte de build](#6-reporte-de-build)
7. [Cómo ejecutar el pipeline manualmente](#7-cómo-ejecutar-el-pipeline-manualmente)

---

## 1. Descripción general

El pipeline de integración y despliegue continuo (CI/CD) del proyecto está implementado con **GitHub Actions** en el archivo `.github/workflows/ci-cd.yml`. Su objetivo es garantizar que cada cambio que llegue a las ramas principales pase por verificaciones automáticas antes de ser desplegado, eliminando errores manuales y acelerando el ciclo de entrega.

**Flujo de extremo a extremo:**

```
Desarrollador hace push / abre PR
        │
        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Lint &      │────▶│  2. Tests        │────▶│  3. Build       │────▶│  4. Deploy      │
│     Seguridad   │     │     Unitarios    │     │     Docker      │     │     (main only) │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
   flake8, pip-audit       pytest, cov≥80%        GHCR, SHA tag           docker-compose up
```

Cada etapa depende de la anterior (`needs:`). Si una falla, las siguientes no se ejecutan.

---

## 2. Trigger y condiciones

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
```

| Evento | Ramas afectadas | Etapas que corren |
|--------|----------------|-------------------|
| `push` a `develop` | develop | Lint, Tests, Build |
| `push` a `main` | main | Lint, Tests, Build, Deploy |
| `pull_request` a `main` | main | Lint, Tests |

El deploy **solo se activa** en push directo a `main`, nunca en PRs ni en `develop`.

---

## 3. Etapas del pipeline

### Etapa 1 — Lint & Seguridad

**Objetivo:** detectar errores de estilo y vulnerabilidades en dependencias antes de ejecutar los tests.

**Herramientas:**
- `flake8`: analiza el código Python en busca de errores de sintaxis, variables no usadas, líneas demasiado largas (máx. 120 caracteres), etc.
- `pip-audit`: escanea las dependencias declaradas en `requirements.txt` contra la base de datos de vulnerabilidades conocidas (CVE).

**Comando flake8:**
```bash
flake8 src/ --max-line-length=120 --exclude=__pycache__
```

**Comando pip-audit:**
```bash
pip-audit -r requirements.txt --output=json > audit-report.json
```

**Artefacto generado:** `audit-report.json` (subido a GitHub Actions artifacts).

**Comportamiento ante fallos:**
- Si `flake8` encuentra errores de sintaxis o estilo crítico → pipeline se detiene.
- Si `pip-audit` encuentra vulnerabilidades → el reporte se guarda pero el pipeline continúa (el flag `|| true` evita el bloqueo; en producción real se recomienda bloquear).

---

### Etapa 2 — Tests unitarios

**Objetivo:** verificar que todos los endpoints de la API funcionan correctamente y que la cobertura de código supera el umbral mínimo del 80%.

**Herramientas:**
- `pytest`: ejecuta los 24 tests definidos en `tests/test_api.py`.
- `pytest-cov`: mide la cobertura de código sobre el módulo `src/`.

**Comando:**
```bash
python -m pytest tests/ -v \
  --cov=src \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  --junitxml=test-results.xml
```

**Parámetros clave:**
| Parámetro | Propósito |
|-----------|-----------|
| `--cov-fail-under=80` | Falla el pipeline si la cobertura es menor al 80% |
| `--junitxml=test-results.xml` | Genera reporte compatible con GitHub Actions |
| `--cov-report=xml` | Genera reporte de cobertura en formato XML estándar |

**Resultado actual:** 24/24 tests PASSED · 93% de cobertura.

**Artefactos generados:** `test-results.xml`, `coverage.xml`.

---

### Etapa 3 — Build de imagen Docker

**Objetivo:** construir la imagen Docker de la API, etiquetarla con el SHA del commit y subirla al GitHub Container Registry (GHCR).

**Solo se ejecuta** en eventos `push` (no en PRs).

**Proceso:**
1. Login al registro `ghcr.io` con el token automático `GITHUB_TOKEN`.
2. Extraer metadata para generar los tags automáticamente:
   - `sha-<commit_short>` — identifica el commit exacto
   - `main` o `develop` — rama actual
   - `latest` — solo cuando se hace push a `main`
3. Ejecutar `docker build` con el Dockerfile multi-stage.
4. Hacer `docker push` al GHCR.
5. Generar un resumen de build en el Step Summary de GitHub Actions.

**Tags generados (ejemplo):**
```
ghcr.io/carramirezcu-svg/proyecto-final-/todo-api:latest
ghcr.io/carramirezcu-svg/proyecto-final-/todo-api:main
ghcr.io/carramirezcu-svg/proyecto-final-/todo-api:sha-a1b2c3d
```

**Artefacto generado:** imagen Docker versionada en GHCR con digest SHA256.

---

### Etapa 4 — Deploy a producción

**Objetivo:** actualizar el contenedor en ejecución con la nueva imagen.

**Solo se ejecuta** en push a `main` y con el entorno `production` configurado en GitHub.

**Estrategia de deploy:**
```bash
docker-compose pull && docker-compose up -d
```

Este comando descarga la nueva imagen (con el tag `latest` actualizado) y reinicia los contenedores sin tiempo de inactividad para los demás servicios (Prometheus, Grafana).

**Notificación:** al finalizar, escribe un resumen en el Step Summary de GitHub Actions con la imagen desplegada y el commit.

---

## 4. Artefactos generados

| Artefacto | Etapa | Descripción | Retención |
|-----------|-------|-------------|-----------|
| `audit-report.json` | Lint & Seguridad | Resultado del escaneo de vulnerabilidades | 90 días (default GitHub) |
| `test-results.xml` | Tests | Reporte JUnit con resultados de cada test | 90 días |
| `coverage.xml` | Tests | Cobertura de código en formato Cobertura XML | 90 días |
| Imagen Docker | Build | Imagen versionada con SHA en GHCR | Indefinida (GHCR) |

---

## 5. Variables y secretos

| Variable/Secreto | Tipo | Descripción |
|-----------------|------|-------------|
| `GITHUB_TOKEN` | Secreto automático | Provisto por GitHub Actions; se usa para login en GHCR y push de imagen. No requiere configuración manual. |
| `IMAGE_NAME` | Variable de entorno (env:) | Nombre base de la imagen: `todo-api` |
| `REGISTRY` | Variable de entorno (env:) | Registro de contenedores: `ghcr.io` |

No se requieren secretos adicionales para el pipeline base. Para deploy en servidor externo vía SSH se necesitaría agregar `SSH_PRIVATE_KEY` y `SERVER_HOST` como secretos del repositorio en Settings → Secrets.

---

## 6. Reporte de build

Al finalizar la etapa de Build, GitHub Actions genera automáticamente un resumen visible en la pestaña **Summary** del workflow con información como:

```
## Build Report
| Campo   | Valor                                               |
|---------|-----------------------------------------------------|
| Imagen  | ghcr.io/carramirezcu-svg/proyecto-final-/todo-api:sha-a1b2c3d |
| Digest  | sha256:abc123...                                    |
| Commit  | a1b2c3d4e5f6...                                     |
| Rama    | main                                                |
```

---

## 7. Cómo ejecutar el pipeline manualmente

Desde la interfaz de GitHub:
1. Ir a **Actions** → **CI/CD Pipeline — To-Do API**
2. Clic en **Run workflow**
3. Seleccionar la rama y confirmar

Desde la terminal (requiere GitHub CLI):
```bash
gh workflow run ci-cd.yml --ref main
```

Para ver el estado del último run:
```bash
gh run list --workflow=ci-cd.yml
```
