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
  - `docs/` reorganizado como sistema de referencia + seguimiento
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

### 2026-06-18

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se implemento `sync-artifacts`
  - se agregaron modos `--run-id`, `--all-local-only`, `--all-failed` y `--dry-run`
  - se agregaron targets `make sync-artifacts`, `make sync-local-only`, `make sync-failed` y `make sync-dry-run`
  - se alineo documentacion de storage con resync manual implementado
  - se valido limpieza total de local, `Neon` y bucket `S3`
- comando ejecutado:
  - `make check`
  - `make sync-dry-run RUN_ID=doom_foundation_agent__20260617T040513523127Z`
  - `make sync-local-only LIMIT=20`
  - queries de verificacion en `training_runs` y `run_artifacts`
- resultado observado:
  - `sync-artifacts` operativo y validado
  - sistema limpio responde sin falsos positivos
  - no quedaron corridas, artefactos ni candidatos pendientes de sync
- decision siguiente:
  - correr nueva corrida limpia para repoblar metadata y artefactos reales
  - validar pipeline completo de entrenamiento, persistencia y sync remoto

### 2026-06-20

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se corrio una baseline larga limpia de `basic`
  - se reevaluaron checkpoints automaticos con protocolo offline consistente
  - se agrego `promote-checkpoint` para fijar checkpoint oficial validado
  - se agrego `hydrate-workspace` para continuidad operativa entre PCs
  - se agrego `inspect-run` para consolidar `report.json` + `manifest.json`
  - se paso a usar `report.json` y `manifest.json` dentro del flujo de sync/handoff
  - se elimino `MinIO` del camino operativo principal; backend remoto unico `AWS S3`
- comando ejecutado:
  - `make train-from-scratch SEED=42 TIMESTEPS=1500000`
  - `make evaluate CHECKPOINT=artifacts\\checkpoints\\auto\\doom_foundation_agent_1250000_steps.zip EPISODES=50 NO_RENDER=1 JSON=1`
  - `make evaluate CHECKPOINT=artifacts\\runs\\doom_foundation_agent__20260620T172048583643Z\\checkpoints\\final_model.zip EPISODES=50 NO_RENDER=1 JSON=1`
  - `make promote CHECKPOINT=artifacts\\checkpoints\\auto\\doom_foundation_agent_1250000_steps.zip PROMOTE_EPISODES=50`
- resultado observado:
  - checkpoint auto de `1250000` pasos quedo mejor que `final_model` bajo evaluacion offline de `50` episodios
  - `promoted` quedo apuntando al checkpoint oficialmente preservado
  - `workspace_state.json` y `hydrate-workspace` dejan listo el flujo base entre PCs
  - el repo ya no depende solo del disco local para reconstruir continuidad minima
- decision siguiente:
  - alinear documentacion con el flujo real de `promoted`, `manifest` y `hydrate`
  - definir politica simple de retencion/limpieza de artefactos
  - decidir si `basic` se congela como baseline oficial o si abre iteracion `v2`

### 2026-06-22

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo corrida larga oficial de `basic`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `final_model.zip` como checkpoint oficial del escenario
  - se documento TensorBoard y lectura de metricas para presentacion
- comando ejecutado:
  - `make train-from-scratch`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\best_model.zip --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\final_model.zip --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\final_model.zip --episodes 50`
- resultado observado:
  - `basic` quedo cerrado con checkpoint oficial promovido
  - metricas finales oficiales:
    - `mean_reward = -11.84`
    - `std_reward = 11.26`
    - `mean_episode_length = 13.84`
  - el `final_model.zip` supero al `best_model.zip` cuando se comparo offline con `50` episodios
- decision siguiente:
  - congelar `basic` como baseline oficial
  - abrir `defend_the_center` como primer escenario de transferencia
  - correr piloto inicial desde `doom_foundation_agent_promoted.zip`
