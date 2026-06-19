# Implementation checkpoint

Fecha base: 2026-06-17

## Objetivo de este archivo

Este documento deja checkpoint consolidado de lo que ya fue implementado en el repo.

Sirve para:

- retomar trabajo sin releer todo historial
- validar que ya existe antes de tocar algo
- ubicar siguiente punto operativo rapido

## Estado general

- modelo actual: `foundation`
- escenario activo actual: `basic`
- flujo principal: `make train`
- flujo recomendado para primera corrida limpia: `make train-from-scratch`
- fase actual de entrenamiento: `Fase 1`
- fase actual de storage: `Fase 2`

## Ya implementado

### Configuracion

- se elimino `configs/training_profiles.toml`
- se usa:
  - [configs/base.toml](/E:/agente-doom/configs/base.toml:1)
  - [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- la arquitectura ya permite agregar nuevos escenarios por archivo TOML

### CLI publica

Comandos visibles:

- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-checkpoints`
- `list-runs`
- `sync-artifacts`

Comandos retirados del flujo publico:

- `sweep`
- `list-scenarios`
- `list-profiles`

### Makefile

Comandos principales disponibles:

- `make setup`
- `make bootstrap`
- `make check`
- `make train`
- `make train-from-scratch`
- `make train-latest`
- `make evaluate`
- `make evaluate-last`
- `make play`
- `make inspect`
- `make list-runs`
- `make list-checkpoints`
- `make sync-artifacts RUN_ID=<run_id>`
- `make sync-local-only LIMIT=20`
- `make sync-failed LIMIT=20`
- `make sync-dry-run RUN_ID=<run_id>`
- `make tensorboard`

### Observabilidad

- TensorBoard operativo por corrida
- consola de entrenamiento mejorada con bloques visuales
- resumenes visuales para:
  - inicio de entrenamiento
  - reward shaping
  - resume
  - evaluacion
  - best model
  - checkpoint
  - acciones recientes
  - resultado final

### Cancelacion controlada

- `Ctrl+C` ya no debe dejar en rojo los targets largos de `make` por cancelacion voluntaria
- aplica a:
  - `train`
  - `train-from-scratch`
  - `train-latest`
  - `evaluate`
  - `evaluate-last`
  - `tensorboard`
- errores reales siguen fallando como error

### Storage local fase 1

- checkpoint canonico: `artifacts/checkpoints/`
- checkpoints automaticos: `artifacts/checkpoints/auto/`
- snapshot historico por corrida: `artifacts/runs/<run_id>/`
- reporte por corrida: `artifacts/runs/<run_id>/report.json`
- indice local resumido: `artifacts/reports/index.json`

### Compatibilidad Windows

- lectura JSON tolerante a BOM UTF-8
- evita fallo de `make list-runs` con archivos legacy

### Persistencia remota y arquitectura hibrida

- `alembic` operativo
- schema inicial creado con:
  - `training_runs`
  - `run_artifacts`
  - `sync_events`
- `Neon / PostgreSQL` validado como store remoto de metadata
- `AWS S3` validado como store remoto principal de artefactos
- `MinIO` local soportado como backend de prueba
- selector de backend remoto:
  - `AGENTE_DOOM_STORAGE_BACKEND=minio|s3`
- `TrainingRunRepository` guarda metadata final de corrida en DB
- `ArtifactSyncService` sincroniza artefactos pesados sin romper entrenamiento si falla nube
- `list-runs` ya puede leer desde DB con fallback local

### Sync remoto ya validado

- `report.json`:
  - queda local
  - se indexa por DB
- `checkpoint final`:
  - local
  - remoto
- `best checkpoint`:
  - solo se registra y sincroniza si la corrida realmente genero uno nuevo
- `video`:
  - local
  - remoto

### Resincronizacion manual implementada

- comando CLI:
  - `sync-artifacts --run-id <run_id>`
  - `sync-artifacts --all-local-only --limit <n>`
  - `sync-artifacts --all-failed --limit <n>`
  - `sync-artifacts --run-id <run_id> --dry-run`
- targets `make`:
  - `make sync-artifacts RUN_ID=<run_id>`
  - `make sync-local-only LIMIT=20`
  - `make sync-failed LIMIT=20`
  - `make sync-dry-run RUN_ID=<run_id>`
- soporta resincronizar corridas existentes sin reentrenar
- `dry-run` muestra candidatos sin subir ni tocar DB
- audita reintentos en `sync_events`
- si una corrida mezcla subidas exitosas y fallidas, estado final queda `failed`
- si no hay candidatos de sync, se informa claramente y no se muta estado

### Infra local auxiliar

- `docker-compose.yml` para `MinIO` local
- targets:
  - `make minio-up`
  - `make minio-down`
  - `make minio-logs`

### Tests

- tests reorganizados por paquetes:
  - `tests/cli`
  - `tests/configuration`
  - `tests/envs`
  - `tests/persistence`
  - `tests/services`
  - `tests/storage`
  - `tests/utils`
- `make check` pasa

## Operacion recomendada hoy

1. `make setup`
2. `make check`
3. `make train-from-scratch`
4. `make tensorboard`
5. validar en `Neon`
6. validar en `S3`
7. `make list-runs`
8. `make list-checkpoints`
9. `make evaluate`

## Siguiente paso recomendado

- correr primera corrida real larga sobre `basic`
- observar reward, actions, comportamiento visual y sync remoto
- registrar resultados en [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)
- decidir si ajustar preset de `basic`
- luego definir migracion de corridas viejas, descarga remota y restauracion desde `S3`
