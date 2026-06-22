# Estado actual

Documento consolidado del estado vivo del repo y del checkpoint de implementacion.

Sirve para responder dos preguntas sin saltar entre varios archivos:

- en que estamos hoy
- que ya existe realmente en codigo y operacion

Fecha base: 2026-06-20

## Resumen ejecutivo

- modelo actual: `foundation`
- fase actual de entrenamiento: `Fase 1`
- fase actual de storage: `Fase 2`
- escenario activo: `basic`
- configuracion activa: [configs/base.toml](/E:/agente-doom/configs/base.toml:1) + [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- flujo principal: `make train`
- flujo recomendado inicial: `make train-from-scratch`
- metadata remota activa: `Neon / PostgreSQL`
- object storage remoto activo: `AWS S3`
- handoff remoto activo: `hydrate-workspace` + `workspace_state.json`

## Foco actual

- estabilizar entrenamiento de `basic`
- consolidar flujo oficial de entrenamiento, promotion y handoff multi-PC
- dejar storage remoto mas legible para el equipo entre varias corridas
- terminar de alinear documentacion con `manifest`, `promoted` y `hydrate`
- decidir siguiente iteracion sana despues del baseline largo de `basic`

## Ya implementado

### Configuracion

- se usa:
  - [configs/base.toml](/E:/agente-doom/configs/base.toml:1)
  - [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- la arquitectura permite agregar escenarios por archivo TOML

### CLI publica

Comandos visibles:

- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-checkpoints`
- `list-runs`
- `inspect-run`
- `promote-checkpoint`
- `sync-artifacts`
- `hydrate-workspace`

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
- `make inspect-run`
- `make promote`
- `make hydrate`
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
- resumenes visuales para inicio, reward shaping, resume, evaluacion, best model, checkpoint, acciones recientes y resultado final
- `inspect-run` para consolidar `report.json` + `manifest.json`

### Storage y persistencia remota

- schema inicial de `PostgreSQL` con:
  - `training_runs`
  - `run_artifacts`
  - `sync_events`
- persistencia de corridas en `Neon`
- lectura de `list-runs` desde `PostgreSQL` con fallback a JSON local
- sync remoto de `report.json`, `manifest.json`, checkpoints finales, best seleccionados y videos a `AWS S3`
- resincronizacion manual con `sync-artifacts` para corridas `local_only` o `failed`
- backend remoto unico: `AWS S3`
- `manifest.json` como inventario estructurado por corrida

### Handoff multi-PC

- `workspace_state.json` publica punteros compartidos `active` y `promoted`
- `promote-checkpoint` fija checkpoint oficial validado offline
- `hydrate-workspace` reconstruye `active` y `promoted` en otra PC
- flujo oficial: `single active training`, una sola PC entrena la linea principal a la vez

### Estado empirico reciente

- baseline larga de `basic` ya corrida
- checkpoint promovido disponible para continuidad y evaluacion oficial
- auto-checkpoints sirven como soporte local, no como fuente oficial de verdad para handoff

## Bloqueos o riesgos actuales

- falta registrar mejor el historial empirico reciente en `experiment_log.md`
- falta definir politica operativa simple de limpieza y retencion de artefactos
- auto-checkpoints siguen fuera del handoff oficial
- falta decidir si `basic` queda congelado como baseline o si abre una `v2`

## Operacion recomendada hoy

1. `make setup`
2. `make check`
3. `make list-runs`
4. `make inspect-run RUN_ID=<run_id>`
5. `make evaluate CHECKPOINT=... EPISODES=50 NO_RENDER=1 JSON=1`
6. `make promote CHECKPOINT=... PROMOTE_EPISODES=50`
7. validar en `Neon`
8. validar en `S3`
9. `make hydrate ONLY=promoted` en otra PC si hace falta

## Siguiente accion recomendada

1. usar `make inspect-run RUN_ID=...` para revisar la corrida principal
2. usar `make evaluate CHECKPOINT=... EPISODES=50 NO_RENDER=1 JSON=1` para comparaciones oficiales
3. usar `make promote CHECKPOINT=... PROMOTE_EPISODES=50` cuando un checkpoint merezca quedar como referencia
4. usar `make hydrate ONLY=promoted` en otra PC si hace falta continuidad
5. registrar resultado en [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)
6. decidir si `basic` queda congelado como baseline o si abre una `v2`
