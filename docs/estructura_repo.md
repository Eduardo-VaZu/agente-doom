# Estructura del repo

Este documento explica que hace cada zona importante del proyecto.

No reemplaza leer el codigo, pero te da un mapa para no perderte.

## Vision general

El repo hace cinco cosas principales:

1. define configuraciones de entrenamiento
2. crea entornos de ViZDoom
3. entrena y evalua el modelo
4. guarda metadata y artefactos por corrida
5. sincroniza y mueve corridas entre PCs usando `Neon + S3`

## Carpetas raiz

### [configs](/E:/agente-doom/configs)

Fuente de verdad para perfiles y escenarios.

- [base.toml](/E:/agente-doom/configs/base.toml:1):
  defaults compartidos
- [scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1):
  overrides del escenario `basic`

### [data/scenarios](/E:/agente-doom/data/scenarios)

Archivos reales del escenario ViZDoom.

- `basic.cfg`
- `basic.wad`

### [src](/E:/agente-doom/src)

Codigo principal del proyecto.

### [tests](/E:/agente-doom/tests)

Tests por capa:

- `configuration`
- `services`
- `storage`
- `persistence`
- `utils`
- `cli`

### [docs](/E:/agente-doom/docs)

Documentacion operativa, roadmap y referencias.

## Estructura de `src/doom_agent`

### [cli](/E:/agente-doom/src/doom_agent/cli)

Define argumentos y entrada publica del proyecto.

- [main.py](/E:/agente-doom/src/doom_agent/cli/main.py:1):
  parser central y despacho de comandos
- [train.py](/E:/agente-doom/src/doom_agent/cli/train.py:1):
  argumentos de entrenamiento
- [evaluate.py](/E:/agente-doom/src/doom_agent/cli/evaluate.py:1):
  argumentos de evaluacion
- [sync.py](/E:/agente-doom/src/doom_agent/cli/sync.py:1):
  argumentos de resincronizacion
- [promote.py](/E:/agente-doom/src/doom_agent/cli/promote.py:1):
  argumentos de promotion
- [hydrate.py](/E:/agente-doom/src/doom_agent/cli/hydrate.py:1):
  argumentos de hidratacion multi-PC
- [runs.py](/E:/agente-doom/src/doom_agent/cli/runs.py:1):
  argumentos de inspeccion de corridas

### [config](/E:/agente-doom/src/doom_agent/config)

Carga y materializa perfiles de entrenamiento.

- [profiles.py](/E:/agente-doom/src/doom_agent/config/profiles.py:1):
  carga catalogo TOML y resuelve perfiles
- [schema.py](/E:/agente-doom/src/doom_agent/config/schema.py:1):
  dataclasses/config objects del proyecto

### [envs](/E:/agente-doom/src/doom_agent/envs)

Construccion del entorno ViZDoom y reward shaping.

- [doom_env.py](/E:/agente-doom/src/doom_agent/envs/doom_env.py:1):
  wrapper principal del entorno
- [reward.py](/E:/agente-doom/src/doom_agent/envs/reward.py:1):
  logica de ajuste de recompensa

### [models](/E:/agente-doom/src/doom_agent/models)

Extensiones o configuraciones del modelo recurrente.

- [recurrent_ppo.py](/E:/agente-doom/src/doom_agent/models/recurrent_ppo.py:1):
  personalizaciones del extractor/modelo

### [services](/E:/agente-doom/src/doom_agent/services)

Aqui vive la logica de aplicacion.

Archivos clave:

- [trainer.py](/E:/agente-doom/src/doom_agent/services/trainer.py:1):
  orquesta entrenamiento completo, reportes, DB, sync y handoff
- [training_support.py](/E:/agente-doom/src/doom_agent/services/training_support.py:1):
  callbacks de entrenamiento, evaluacion periodica y best model
- [resume.py](/E:/agente-doom/src/doom_agent/services/resume.py:1):
  decide desde que checkpoint reanudar
- [evaluator.py](/E:/agente-doom/src/doom_agent/services/evaluator.py:1):
  evaluacion offline o interactiva
- [promoter.py](/E:/agente-doom/src/doom_agent/services/promoter.py:1):
  reevaluar y promover checkpoint oficial
- [sync.py](/E:/agente-doom/src/doom_agent/services/sync.py:1):
  subir artefactos locales a `S3`
- [workspace_handoff.py](/E:/agente-doom/src/doom_agent/services/workspace_handoff.py:1):
  publicar/hidratar alias y soporte minimo entre PCs
- [run_inspection.py](/E:/agente-doom/src/doom_agent/services/run_inspection.py:1):
  resumen consolidado de una corrida
- [early_stopping.py](/E:/agente-doom/src/doom_agent/services/early_stopping.py:1):
  politica de parada temprana

### [storage](/E:/agente-doom/src/doom_agent/storage)

Define paths locales y backend remoto.

- [local.py](/E:/agente-doom/src/doom_agent/storage/local.py:1):
  rutas por corrida dentro de `artifacts`
- [s3.py](/E:/agente-doom/src/doom_agent/storage/s3.py:1):
  cliente de object storage remoto
- [config.py](/E:/agente-doom/src/doom_agent/storage/config.py:1):
  variables de entorno y settings S3
- [remote.py](/E:/agente-doom/src/doom_agent/storage/remote.py:1):
  tipos comunes y construccion de object keys

### [persistence](/E:/agente-doom/src/doom_agent/persistence)

Todo lo relacionado a `Neon / PostgreSQL`.

- [models.py](/E:/agente-doom/src/doom_agent/persistence/models.py:1):
  tablas ORM
- [session.py](/E:/agente-doom/src/doom_agent/persistence/session.py:1):
  fabrica de sesiones
- [config.py](/E:/agente-doom/src/doom_agent/persistence/config.py:1):
  lectura de `DATABASE_URL`
- [repositories/run_repository.py](/E:/agente-doom/src/doom_agent/persistence/repositories/run_repository.py:1):
  acceso principal a corridas, artefactos y eventos de sync

### [utils](/E:/agente-doom/src/doom_agent/utils)

Helpers estructurales del proyecto.

- [checkpoints.py](/E:/agente-doom/src/doom_agent/utils/checkpoints.py:1):
  resolver, copiar, guardar y leer metadata de checkpoints
- [reports.py](/E:/agente-doom/src/doom_agent/utils/reports.py:1):
  construir y guardar `report.json`
- [manifests.py](/E:/agente-doom/src/doom_agent/utils/manifests.py:1):
  construir y guardar `manifest.json`
- [console.py](/E:/agente-doom/src/doom_agent/utils/console.py:1):
  bloques visuales en consola
- [filesystem.py](/E:/agente-doom/src/doom_agent/utils/filesystem.py:1):
  helpers de IO y JSON
- [formatting.py](/E:/agente-doom/src/doom_agent/utils/formatting.py:1):
  formato corto de rutas/texto para consola

### [shared](/E:/agente-doom/src/doom_agent/shared)

Tipos y contratos compartidos.

- [contracts.py](/E:/agente-doom/src/doom_agent/shared/contracts.py:1):
  payloads JSON, reportes, manifests y summaries
- [env.py](/E:/agente-doom/src/doom_agent/shared/env.py:1):
  carga de `.env`

## Flujo de punta a punta

1. CLI recibe comando
2. `config` resuelve perfil
3. `envs` crea entorno de entrenamiento o evaluacion
4. `services/trainer.py` o `services/evaluator.py` ejecutan la accion principal
5. `utils/checkpoints.py`, `utils/reports.py` y `utils/manifests.py` guardan artefactos locales
6. `persistence/repositories/run_repository.py` registra metadata en DB
7. `services/sync.py` sube artefactos a `S3`
8. `services/workspace_handoff.py` publica alias oficiales para continuidad entre PCs

## Archivos raiz importantes

- [src/cli.py](/E:/agente-doom/src/cli.py:1):
  wrapper principal para CLI
- [src/train.py](/E:/agente-doom/src/train.py:1):
  compat wrapper legado de entrenamiento
- [src/evaluate.py](/E:/agente-doom/src/evaluate.py:1):
  compat wrapper legado de evaluacion
- [Makefile](/E:/agente-doom/Makefile:1):
  interfaz operativa recomendada
- [README.md](/E:/agente-doom/README.md:1):
  entrada general

## Si quieres entender rapido el proyecto

Lee en este orden:

1. [docs/comandos_principales.md](/E:/agente-doom/docs/comandos_principales.md:1)
2. [README.md](/E:/agente-doom/README.md:1)
3. [src/doom_agent/cli/main.py](/E:/agente-doom/src/doom_agent/cli/main.py:1)
4. [src/doom_agent/services/trainer.py](/E:/agente-doom/src/doom_agent/services/trainer.py:1)
5. [src/doom_agent/services/evaluator.py](/E:/agente-doom/src/doom_agent/services/evaluator.py:1)
6. [src/doom_agent/services/sync.py](/E:/agente-doom/src/doom_agent/services/sync.py:1)
7. [src/doom_agent/services/workspace_handoff.py](/E:/agente-doom/src/doom_agent/services/workspace_handoff.py:1)
