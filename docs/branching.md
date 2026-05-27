# Estrategia de Branching — To-Do API

## Tabla de contenido
1. [Modelo de branching](#1-modelo-de-branching)
2. [Descripción de cada rama](#2-descripción-de-cada-rama)
3. [Flujo de trabajo completo](#3-flujo-de-trabajo-completo)
4. [Convención de nombres](#4-convención-de-nombres)
5. [Convención de commits](#5-convención-de-commits)
6. [Reglas de protección de ramas](#6-reglas-de-protección-de-ramas)
7. [Relación con el pipeline CI/CD](#7-relación-con-el-pipeline-cicd)
8. [Ejemplos prácticos](#8-ejemplos-prácticos)

---

## 1. Modelo de branching

El proyecto usa **GitHub Flow con rama de integración**, un modelo ligero diseñado para equipos pequeños con entregas frecuentes. Se compone de dos ramas permanentes y ramas temporales de trabajo.

```
main ──────────────────────────────────────────────────────────▶  (producción estable)
  │                         ↑ merge PR                ↑ merge PR
  └── develop ──────────────┴─────────────────────────┴────────▶  (integración continua)
           │         ↑ merge          ↑ merge
           ├── feature/agregar-health ┘
           ├── feature/observabilidad
           ├── fix/cors-error
           └── hotfix/token-expirado  ──────────────────────────▶  (merge directo a main)
```

---

## 2. Descripción de cada rama

### `main`
- Representa el estado actual de **producción**.
- Todo lo que está en `main` ha pasado por el pipeline completo (lint, tests, build, deploy).
- **Nunca** se hace push directo. Solo recibe merges desde `develop` (vía PR) o desde `hotfix/*` (en emergencias).
- Cada merge a `main` genera automáticamente una imagen Docker con el tag `latest`.

### `develop`
- Rama de **integración continua**. Aquí convergen todas las features antes de ir a producción.
- Se ejecutan las etapas de lint, tests y build en cada push.
- El equipo puede probar el estado integrado antes de hacer release a `main`.

### `feature/*`
- Ramas de trabajo para nuevas funcionalidades.
- Se crean desde `develop` y se fusionan de vuelta a `develop` mediante Pull Request.
- Vida útil corta: se eliminan después del merge.
- Ejemplo: `feature/agregar-paginacion`, `feature/endpoint-filtro`

### `fix/*`
- Corrección de bugs no urgentes encontrados en `develop` o reportados por QA.
- Mismo ciclo que `feature/*`: nace de `develop`, vuelve a `develop`.
- Ejemplo: `fix/error-404-incorrecto`, `fix/validacion-title`

### `hotfix/*`
- Corrección **urgente** de un bug en producción.
- Se crea directamente desde `main`, se corrige y se fusiona tanto a `main` como a `develop` para no perder el fix.
- Ejemplo: `hotfix/crash-al-eliminar-tarea`

---

## 3. Flujo de trabajo completo

### Desarrollo de una nueva feature

```bash
# 1. Actualizar develop local
git checkout develop
git pull origin develop

# 2. Crear rama de feature
git checkout -b feature/nueva-funcionalidad

# 3. Desarrollar, commitear
git add .
git commit -m "feat: agregar filtro de tareas completadas"

# 4. Push de la rama
git push origin feature/nueva-funcionalidad

# 5. Abrir Pull Request en GitHub: feature/... → develop
# 6. Esperar que el CI pase (lint + tests)
# 7. Merge del PR (Squash and Merge recomendado)
# 8. Eliminar la rama remota desde GitHub
```

### Release a producción

```bash
# 1. Desde develop, abrir PR hacia main
# 2. Revisar que todos los tests pasen
# 3. Merge del PR → dispara el pipeline completo + deploy automático
```

### Hotfix de emergencia

```bash
# 1. Crear desde main
git checkout main
git pull origin main
git checkout -b hotfix/descripcion-del-bug

# 2. Corregir, commitear
git commit -m "fix: corregir crash al eliminar tarea con ID inválido"

# 3. Abrir PR a main Y a develop
# 4. Merge en main → deploy automático
# 5. Merge en develop → mantener sincronía
```

---

## 4. Convención de nombres

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Feature | `feature/descripcion-corta` | `feature/agregar-paginacion` |
| Fix | `fix/descripcion-del-bug` | `fix/validacion-title-vacio` |
| Hotfix | `hotfix/descripcion-urgente` | `hotfix/crash-delete-task` |
| Release (opcional) | `release/vX.Y.Z` | `release/v1.2.0` |

**Reglas:**
- Usar guiones (`-`), nunca guiones bajos ni espacios.
- Todo en minúsculas.
- Máximo 50 caracteres en el nombre de la rama.
- Describir QUÉ hace la rama, no quién la hace.

---

## 5. Convención de commits

Se usa el estándar **Conventional Commits** para que el historial sea legible y para facilitar la generación automática de changelogs.

### Formato

```
<tipo>(<scope opcional>): <descripción corta en imperativo>

<cuerpo opcional - explicación del por qué>

<footer opcional - referencias a issues>
```

### Tipos válidos

| Tipo | Cuándo usarlo |
|------|---------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Solo cambios en documentación |
| `test` | Agregar o corregir tests |
| `ci` | Cambios en el pipeline o configuración CI/CD |
| `refactor` | Cambio de código sin nueva funcionalidad ni bug fix |
| `chore` | Tareas de mantenimiento (actualizar dependencias, etc.) |
| `perf` | Mejora de rendimiento |

### Ejemplos

```bash
# Feature nueva
feat: agregar endpoint GET /tasks con filtro por estado

# Bug fix
fix: corregir status 500 cuando el body del PUT es null

# Tests
test: agregar casos de error para endpoint DELETE

# CI/CD
ci: agregar etapa de auditoría de dependencias con pip-audit

# Documentación
docs: agregar guía de branching y convención de commits

# Refactor
refactor(db): extraer lógica de conexión a módulo separado

# Con issue referenciado
fix: corregir query de actualización de tarea

Closes #12
```

### Commits a evitar

```bash
# ❌ Muy vago
git commit -m "fix"
git commit -m "cambios"
git commit -m "wip"

# ✅ Descriptivo y en imperativo
git commit -m "fix: corregir validación de campo title en POST /tasks"
```

---

## 6. Reglas de protección de ramas

Configurar en **GitHub → Settings → Branches → Branch protection rules**:

### Para `main`

| Regla | Configuración |
|-------|--------------|
| Require a pull request before merging | ✅ Activado |
| Require approvals | 1 aprobación mínima |
| Require status checks to pass | ✅ Activado — checks: `lint-and-security`, `test` |
| Require branches to be up to date | ✅ Activado |
| Do not allow bypassing | ✅ Activado |
| Allow force pushes | ❌ Desactivado |
| Allow deletions | ❌ Desactivado |

### Para `develop`

| Regla | Configuración |
|-------|--------------|
| Require status checks to pass | ✅ Activado — checks: `lint-and-security`, `test` |
| Allow force pushes | ❌ Desactivado |

---

## 7. Relación con el pipeline CI/CD

| Rama | Lint & Seguridad | Tests | Build Docker | Deploy |
|------|:----------------:|:-----:|:------------:|:------:|
| `feature/*` (PR a develop) | ✅ | ✅ | ❌ | ❌ |
| `develop` (push) | ✅ | ✅ | ✅ | ❌ |
| `main` (PR desde develop) | ✅ | ✅ | ❌ | ❌ |
| `main` (push/merge) | ✅ | ✅ | ✅ | ✅ |

---

## 8. Ejemplos prácticos

### Ciclo completo de una feature

```
1. git checkout develop && git pull
2. git checkout -b feature/health-endpoint
3. [escribir código + tests]
4. git add . && git commit -m "feat: agregar endpoint /health con estado de BD"
5. git push origin feature/health-endpoint
6. Abrir PR en GitHub → CI corre lint + tests
7. PR aprobado → merge a develop
8. En develop: CI corre lint + tests + build → imagen sha-xxx en GHCR
9. Abrir PR develop → main
10. PR aprobado → merge → CI completo + deploy automático
```

### Historial de commits ejemplo

```
a1b2c3d feat: agregar endpoint /metrics con Prometheus
b2c3d4e test: agregar tests para /health y /metrics  
c3d4e5f ci: configurar GitHub Actions con 4 etapas
d4e5f6a feat: agregar logs estructurados en JSON
e5f6a7b chore: actualizar requirements.txt con prometheus-client
f6a7b8c feat: contenerizar app con Dockerfile multi-stage
```
