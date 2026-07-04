# Estado actual

Documento consolidado del estado vivo del repo y del checkpoint de implementacion.

Sirve para responder dos preguntas sin saltar entre varios archivos:

- en que estamos hoy
- que ya existe realmente en codigo y operacion

Fecha base: 2026-07-03

## Resumen ejecutivo

- modelo actual: `foundation`
- fase actual de entrenamiento: `Fase 3`
- fase actual de storage: `Fase 2`
- escenario baseline oficial: `basic`
- escenario activo oficial: `defend_the_line`
- configuracion baseline: [configs/base.toml](/E:/agente-doom/configs/base.toml:1) + [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- configuracion activa: [configs/scenarios/defend_the_line.toml](/E:/agente-doom/configs/scenarios/defend_the_line.toml:1)
- siguiente escenario sugerido: `basic_audio` como siguiente integracion de Fase 3
- flujo principal: `make train`
- flujo recomendado inicial: `make train-from-scratch`
- metadata remota activa: `Neon / PostgreSQL`
- object storage remoto activo: `AWS S3`
- handoff remoto activo: `hydrate-workspace` + `workspace_state.json`

## Foco actual

- consolidar flujo oficial de entrenamiento, promotion y handoff multi-PC
- dejar storage remoto mas legible para el equipo entre varias corridas
- terminar de alinear documentacion con `manifest`, `promoted` y `hydrate`
- cerrar administrativamente `defend_the_line` y preparar apertura del siguiente escenario del curriculum especializado

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

- baseline larga de `basic` ya cerrada como referencia oficial
- checkpoint promovido disponible para continuidad y transferencia
- `defend_the_center` ya incorporado al catalogo local con config propia
- validacion inicial de `defend_the_center` completada por transferencia desde `basic`
- corrida inicial validada: `doom_foundation_agent__defend_the_center__20260623T025602580980Z`
- corrida de mejora validada: `doom_foundation_agent__defend_the_center__20260625T025825622091Z`
- `health_gathering` ya incorporado al catalogo local con config propia
- piloto inicial validado: `doom_foundation_agent__health_gathering__20260625T113629214351Z`
- corrida de mejora validada: `doom_foundation_agent__health_gathering__20260626T014540629370Z`
- `take_cover` ya incorporado al catalogo local con config propia
- piloto inicial validado: `doom_foundation_agent__take_cover__20260630T011932555138Z`
- corrida de mejora validada: `doom_foundation_agent__take_cover__20260703T140745071243Z`
- `defend_the_line` ya incorporado al catalogo local con config propia
- checkpoint oficial promovido de `defend_the_center`:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- metricas oficiales offline de `50` episodios para `best_model.zip` promovido:
  - `mean_reward = 9.90`
  - `std_reward = 1.38`
  - `mean_episode_length = 634.12`
- checkpoint oficial promovido de `health_gathering`:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- metricas oficiales offline de `50` episodios para `best_model.zip` promovido:
  - `mean_reward = 1580.28`
  - `std_reward = 736.36`
  - `mean_episode_length = 1581.04`
- checkpoint oficial promovido de `take_cover`:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__take_cover_promoted.zip`
- metricas oficiales offline de `50` episodios para checkpoint promovido:
  - `mean_reward = 331.90`
  - `std_reward = 178.23`
  - `mean_episode_length = 331.90`
- corridas validadas de `defend_the_line`:
  - `doom_foundation_agent__defend_the_line__20260703T195759636148Z`
  - `doom_foundation_agent__defend_the_line__20260703T231100240178Z`
- checkpoint oficial promovido de `defend_the_line`:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_line_promoted.zip`
- metricas oficiales offline de `50` episodios para `best_model.zip` promovido:
  - `mean_reward = 27.06`
  - `std_reward = 7.43`
  - `mean_episode_length = 1026.78`
- auto-checkpoints sirven como soporte local, no como fuente oficial de verdad para handoff

## Bloqueos o riesgos actuales

- falta definir politica operativa simple de limpieza y retencion de artefactos
- auto-checkpoints siguen fuera del handoff oficial
- falta preparar formalmente el siguiente escenario de Fase 3 con config y protocolo inicial

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
6. preparar siguiente escenario de Fase 3 con revision previa de compatibilidad de `action_space`
