# Estado actual

Documento consolidado del estado vivo del repo.

Sirve para responder rapido:

- en que estamos hoy
- que escenarios ya quedaron cerrados
- que escenarios quedaron provisionales
- cual es el siguiente escenario exacto

Fecha base: 2026-07-09

## Resumen ejecutivo

- modelo actual: `foundation`
- fase actual de entrenamiento: `Fase 3`
- fase actual de storage: `Fase 2`
- baseline oficial: `basic`
- ultimo escenario cerrado fuerte: `defend_the_line`
- ultimos escenarios especializados cerrados: `basic_audio`, `basic_notifications`
- escenario siguiente exacto recomendado: `my_way_home`
- estado operativo actual: no hay entrenamiento principal corriendo; toca preparar siguiente integracion
- configuracion baseline: [configs/base.toml](/E:/agente-doom/configs/base.toml:1) + [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- flujo principal: `make train`
- flujo recomendado para escenario nuevo: `make train-from-scratch`
- metadata remota activa: `Neon / PostgreSQL`
- object storage remoto activo: `AWS S3`
- handoff remoto activo: `hydrate-workspace` + `workspace_state.json`

## Foco actual

- dejar documentado cierre real de `basic_audio` y `basic_notifications`
- congelar por ahora escenarios ya entrenados
- preparar integracion del siguiente escenario del curriculum: `my_way_home`
- mantener el flujo de handoff multi-PC legible para otra IA o para otra PC del equipo

## Estado de escenarios

| Escenario | Estado actual | Calidad operativa | Checkpoint oficial | Resultado resumido | Nota |
|---|---|---|---|---|---|
| `basic` | Cerrado oficial | Bueno | `doom_foundation_agent_promoted.zip` | `mean_reward = -11.84`, `std = 11.26` | Baseline fuerte del proyecto. |
| `defend_the_center` | Cerrado oficial | Bueno | `doom_foundation_agent__defend_the_center_promoted.zip` | `mean_reward = 9.90`, `std = 1.38` | Referencia fuerte de Fase 2. |
| `health_gathering` | Cerrado oficial | Bueno | `doom_foundation_agent__health_gathering_promoted.zip` | `mean_reward = 1580.28`, `std = 736.36` | Muy buen resultado para supervivencia. |
| `take_cover` | Cerrado oficial | Bueno | `doom_foundation_agent__take_cover_promoted.zip` | `mean_reward = 331.90`, `std = 178.23` | Referencia pulida de evasion. |
| `defend_the_line` | Cerrado oficial | Bueno | `doom_foundation_agent__defend_the_line_promoted.zip` | `mean_reward = 27.06`, `std = 7.43` | Mejor cierre actual de Fase 3 estable. |
| `basic_audio` | Cerrado provisional | Regular | `doom_foundation_agent__basic_audio_promoted.zip` | `mean_reward = -64.84`, `std = 111.19` | Mejorado respecto al primer intento, pero aun inestable. |
| `basic_notifications` | Cerrado provisional | Regular | `doom_foundation_agent__basic_notifications_promoted.zip` | `mean_reward = -73.60`, `std = 120.65` | Aprendio algo, pero sigue sesgado e inestable. |
| `my_way_home` | Siguiente escenario | Pendiente | No aplica | No entrenado aun | Siguiente candidato exacto. |
| `predict_position` | Futuro | Pendiente | No aplica | No entrenado aun | Conviene despues de `my_way_home`. |
| `health_gathering_supreme` | Futuro | Pendiente | No aplica | No entrenado aun | Version dura de navegacion/supervivencia. |
| `deadly_corridor` | Futuro | Pendiente | No aplica | No entrenado aun | Alta dificultad. |
| `deathmatch` | Futuro | Pendiente | No aplica | No entrenado aun | Dejar al final. |

## Lectura operativa

- `basic`, `defend_the_center`, `health_gathering`, `take_cover` y `defend_the_line` quedaron como referencias oficiales fuertes.
- `basic_audio` y `basic_notifications` ya quedaron integrados y promovidos, pero solo como referencias provisionales.
- no conviene gastar mas ciclos ahora en `basic_audio` y `basic_notifications` con la misma configuracion.
- para presentacion o continuidad del proyecto, la narrativa correcta es:
  - baseline fuerte en `basic`
  - expansion fuerte en Fase 2
  - Fase 3 ya probo escenario frontal estable y dos escenarios sensoriales especializados

## Ya implementado

### Configuracion

- se usa:
  - [configs/base.toml](/E:/agente-doom/configs/base.toml:1)
  - [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- arquitectura por escenario en `configs/scenarios/*.toml`
- modos de observacion especializados ya integrados:
  - `vision`
  - `vision_audio`
  - `vision_notifications`

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

### Storage y handoff

- schema remoto operativo en `PostgreSQL`
- persistencia de corridas en `Neon`
- sync remoto de `report.json`, `manifest.json`, checkpoints elegibles y videos a `AWS S3`
- `workspace_state.json` publica punteros `active` y `promoted`
- `hydrate-workspace` reconstruye continuidad en otra PC
- flujo oficial: una sola PC entrena linea principal a la vez

## Bloqueos o riesgos actuales

- falta integrar `my_way_home` al catalogo local con `.cfg`, `.wad`, TOML y tests minimos
- escenarios sensoriales quedaron usables, pero no fuertes
- auto-checkpoints siguen siendo apoyo local, no fuente oficial de verdad

## Politica recomendada para reentrenar escenarios pasados

Si, se pueden volver a entrenar escenarios ya cerrados, pero no todos merecen eso ahora.

Regla sugerida:

- reentrenar un escenario fuerte solo si hace falta para una demo puntual o una comparacion formal
- reabrir un escenario provisional si cambia la observacion, reward, arquitectura o si aparece una configuracion mejor claramente justificada
- no reabrir `basic_audio` ni `basic_notifications` ahora con la misma config; el retorno esperado es bajo
- si se reabre algo en el futuro:
  - usar nueva corrida
  - reevaluar offline con `50` episodios
  - promover solo si supera checkpoint oficial vigente

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

1. registrar cierre de escenarios sensoriales en [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)
2. mantener congelados checkpoints oficiales actuales
3. preparar `my_way_home` como siguiente escenario exacto
4. agregar config, assets y tests minimos de `my_way_home`
5. correr piloto inicial desde cero o por transferencia solo si action space y observacion son compatibles
