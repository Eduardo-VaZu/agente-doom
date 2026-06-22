# Storage y handoff

Documento consolidado de almacenamiento, sync remoto y continuidad multi-PC.

## Objetivo general

Separar correctamente:

- artefactos grandes
- metadata operativa
- historico de corridas
- continuidad de trabajo entre PCs

## Arquitectura actual

- `Git` guarda codigo
- `Neon / PostgreSQL` guarda metadata e historial operativo
- `AWS S3` guarda artefactos pesados
- `workspace_state.json` publica los punteros compartidos de continuidad

## Regla principal

No todo va a base de datos.

Convencion actual:

- checkpoints, videos y artefactos grandes -> local + `S3`
- metadata de corridas y estados de sync -> `PostgreSQL`
- `report.json` y `manifest.json` -> local + `S3`

## Fase 1: Local estable

Estado:
- completa

Base local por corrida:

- `artifacts/checkpoints/`
- `artifacts/checkpoints/auto/`
- `artifacts/runs/<run_id>/checkpoints/`
- `artifacts/runs/<run_id>/videos/`
- `artifacts/runs/<run_id>/tensorboard/`
- `artifacts/runs/<run_id>/report.json`
- `artifacts/runs/<run_id>/manifest.json`
- `artifacts/reports/`

## Fase 2: Arquitectura hibrida

Estado:
- completa en su base operativa

Implementado hoy:

- `training_runs`, `run_artifacts`, `sync_events` en `PostgreSQL`
- `Neon` como metadata store remoto
- `AWS S3` como object storage remoto principal
- escritura local primero, sync remoto despues
- `list-runs` prefiere DB con fallback local
- `sync-artifacts` resincroniza sin reentrenar

Sync validado para:

- `report.json`
- `manifest.json`
- `final checkpoint`
- `best checkpoint` cuando exista realmente en la corrida
- `video`

Decisiones aplicadas:

- si sync falla, entrenamiento no cae
- `manifest.json` es el inventario estructurado por corrida
- los estados de sync viven en DB
- el backend remoto operativo es solo `S3`

## Handoff multi-PC

### Idea base

- `active`: ultimo checkpoint desde donde debe continuar entrenamiento
- `promoted`: checkpoint oficialmente validado para evaluacion y baseline

### Que actualiza el repo

Al terminar `train`:

- guarda corrida local por `run_id`
- actualiza alias local `active`
- escribe `workspace_state.json`
- si sync remoto sale bien, publica alias `active` + `workspace_state.json`

Al ejecutar `promote-checkpoint`:

- mantiene alias local `promoted`
- actualiza `workspace_state.json`
- publica alias `promoted` + `workspace_state.json` cuando hay storage remoto

Al ejecutar `sync-artifacts`:

- resincroniza artefactos pendientes
- vuelve a publicar `workspace_state.json` y aliases compartidos

### Que hace `hydrate-workspace`

1. descarga `workspace_state.json` desde storage remoto
2. descarga alias oficiales `active` y/o `promoted`
3. reconstruye aliases locales en `artifacts/checkpoints/`
4. intenta restaurar soporte minimo por corrida:
   - `artifacts/runs/<run_id>/report.json`
   - `artifacts/runs/<run_id>/manifest.json`
   - `artifacts/runs/<run_id>/checkpoints/final_model.*`
   - `artifacts/runs/<run_id>/checkpoints/best_model.*`
5. reescribe rutas del `report.json` al filesystem local actual

### Flujo recomendado entre PCs

#### PC A

1. `git pull`
2. `hydrate-workspace`
3. entrenar
4. `sync-artifacts`
5. si corresponde, `promote-checkpoint`

#### PC B

1. `git pull`
2. `hydrate-workspace`
3. continuar desde `active` con `train --resume auto`

### Regla operativa

- una sola PC entrena la linea principal a la vez
- `active` manda para continuidad
- `promoted` manda para evaluacion oficial y baseline estable

## Fase 3: Operacion remota estable

Estado:
- en progreso

Pendiente para considerar esta fase completa:

- migracion de corridas antiguas `local_only`
- descarga o restauracion mas completa desde `S3`
- politica clara para `best checkpoint` y reintentos
- criterio de limpieza o lifecycle para artefactos remotos
- hidratacion ampliada por `run_id` para reconstruir mas historial si el equipo lo necesita

## Siguiente paso operativo

- mantener `Neon + AWS S3` como camino principal
- usar `manifest.json` como inventario de verdad por corrida
- usar `workspace_state.json` para continuidad entre PCs
- definir politica de limpieza y retencion
