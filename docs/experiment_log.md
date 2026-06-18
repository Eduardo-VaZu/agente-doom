# Experiment log

Bitacora cronologica de decisiones y resultados.

## Formato recomendado

Cada entrada debe incluir:

- fecha
- escenario
- fase
- cambio realizado
- comando ejecutado
- resultado observado
- decision siguiente

## Entradas

### 2026-06-14

- escenario: `basic`
- fase: `Fase 1`
- cambio realizado:
  - modelo renombrado a `foundation`
  - config separada en `base.toml` + `configs/scenarios/basic.toml`
  - `Makefile` reactivado con `make train`
  - tests reorganizados por area
  - `Docs/` reorganizado como sistema de referencia + seguimiento
  - storage local por corrida implementado en `artifacts/runs/<run_id>/`
  - consola de entrenamiento mejorada con bloques visuales
  - cancelacion limpia por `Ctrl+C` aplicada a comandos largos de `make`
  - fix de compatibilidad BOM para `make list-runs`
- comando ejecutado:
  - `make check`
  - `make list-runs`
- resultado observado:
  - arquitectura lista para comenzar iteracion operativa sobre `basic`
  - validacion automatica estable
  - operacion diaria mas clara para entrenamiento, evaluacion y seguimiento
- decision siguiente:
  - correr `make train-from-scratch`
  - observar TensorBoard y consola visual
  - registrar comportamiento real del entrenamiento

### 2026-06-16

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se agrego schema remoto en `PostgreSQL`
  - se conecto `Neon`
  - se empezo persistencia de `training_runs` y `run_artifacts`
  - se corrigio copia heredada incorrecta de `best checkpoint`
- comando ejecutado:
  - `alembic upgrade head`
  - corridas cortas de prueba
  - consultas SQL en `Neon`
- resultado observado:
  - metadata de corridas registrada correctamente en DB
  - `best checkpoint` ya no se hereda falsamente si la corrida no evaluo
- decision siguiente:
  - agregar sync remoto de artefactos pesados

### 2026-06-17

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se valido `MinIO` local para object storage
  - se agrego backend `AWS S3`
  - se sincronizan checkpoints finales y videos
  - se registran `sync_events`
  - se limpio historial de pruebas local, `Neon` y bucket
- comando ejecutado:
  - corridas cortas de prueba
  - queries a `training_runs`, `run_artifacts`, `sync_events`
- resultado observado:
  - `Neon + AWS S3` funcionando
  - `storage_backend = s3`
  - `remote_uri = s3://...`
  - corrida nueva marcada como `synced`
- decision siguiente:
  - correr primera corrida larga limpia de `basic`
  - registrar resultado empirico real del entrenamiento
