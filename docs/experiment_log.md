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

### 2026-06-24

- escenario: `defend_the_center`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo primer piloto por transferencia desde checkpoint promovido de `basic`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial del escenario
  - se cerro administrativamente validacion inicial de `defend_the_center`
- comando ejecutado:
  - `make train SCENARIO=defend_the_center RESUME=artifacts\checkpoints\doom_foundation_agent_promoted.zip ALLOW_SCENARIO_RESUME=1 SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\final_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_center__20260623T025602580980Z`
  - `best_model.zip` supero a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 7.98`
    - `std_reward = 1.30`
    - `mean_episode_length = 650.48`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- decision siguiente:
  - decidir si `defend_the_center` recibe segundo tramo de entrenamiento o si se congela como referencia de Fase 2
  - si se extiende, reanudar desde checkpoint promovido del escenario
  - si no se extiende, abrir siguiente escenario del curriculum

### 2026-06-25

- escenario: `defend_the_center`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un segundo tramo de entrenamiento reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` mejorado como nuevo checkpoint oficial del escenario
  - se cerro `defend_the_center` con una referencia final mas fuerte
- comando ejecutado:
  - `make train SCENARIO=defend_the_center RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\final_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_center__20260625T025825622091Z`
  - `best_model.zip` supero a `final_model.zip` y al checkpoint promovido anterior en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 9.90`
    - `std_reward = 1.38`
    - `mean_episode_length = 634.12`
  - sesgo de acciones mejoro respecto al piloto inicial, aunque no desaparecio por completo
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- decision siguiente:
  - congelar `defend_the_center` como referencia fuerte de Fase 2
  - abrir el siguiente escenario del curriculum con config y protocolo inicial

### 2026-06-25

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se incorporo `health_gathering` al catalogo local como siguiente escenario preparado
  - se agregaron assets oficiales `.cfg` y `.wad`
  - se agrego config de escenario y tests minimos del preset de navegacion
- comando ejecutado:
  - integracion local en repo
- resultado observado:
  - `health_gathering` ya existe en `configs/scenarios/` y `data/scenarios/`
  - el preset esperado queda definido como `health_navigation`
  - el escenario queda listo para piloto inicial por transferencia o desde cero
- decision siguiente:
  - correr piloto inicial de `health_gathering`
  - validar `best_model.zip` y `final_model.zip` offline con `50` episodios

### 2026-06-25

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo piloto inicial por transferencia desde `defend_the_center`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial inicial del escenario
- comando ejecutado:
  - `make train SCENARIO=health_gathering RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip ALLOW_SCENARIO_RESUME=1 SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\final_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__health_gathering__20260625T113629214351Z`
  - `best_model.zip` supero ampliamente a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 1539.16`
    - `std_reward = 635.51`
    - `mean_episode_length = 1541.04`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- decision siguiente:
  - decidir si `health_gathering` recibe un ultimo tramo de mejora o si se congela como referencia fuerte de Fase 2

### 2026-06-26

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un tramo adicional de mejora reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` mejorado como nuevo checkpoint oficial del escenario
- comando ejecutado:
  - `make train SCENARIO=health_gathering RESUME=artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\final_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__health_gathering__20260626T014540629370Z`
  - `best_model.zip` supero a `final_model.zip` y al checkpoint promovido anterior en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 1580.28`
    - `std_reward = 736.36`
    - `mean_episode_length = 1581.04`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- decision siguiente:
  - congelar `health_gathering` como referencia fuerte de Fase 2
  - abrir el siguiente escenario del curriculum
