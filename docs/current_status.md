# Current status

Fecha base: 2026-06-17

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

## En que estamos

Foco actual:
- estabilizar entrenamiento de `basic`
- validar corrida larga limpia de `basic` despues de limpieza total de artefactos de prueba
- validar que pipeline, checkpoints, reportes, evaluacion y sync remoto funcionen de punta a punta
- validar experiencia de consola y observabilidad para lectura rapida
- dejar criterios claros para pasar a la siguiente fase

## Ya implementado

- modelo renombrado a `foundation`
- config separada en `base.toml` + `configs/scenarios/*.toml`
- escenario activo reducido a `basic`
- `Makefile` con entrenamiento directo
- `Makefile` con cancelacion limpia para `Ctrl+C` en comandos largos
- documentacion estructurada por fases y por estado
- almacenamiento definido por fases en `Docs/storage_roadmap.md`
- salida de consola del entrenamiento mejorada con bloques visuales
- lectura JSON tolerante a BOM para reportes legacy de Windows
- schema inicial de `PostgreSQL` con:
  - `training_runs`
  - `run_artifacts`
  - `sync_events`
- persistencia de corridas en `Neon`
- lectura de `list-runs` desde `PostgreSQL` con fallback a JSON local
- sync remoto de checkpoints finales y videos a `AWS S3`
- backend `MinIO` local opcional para pruebas
- selector de backend remoto por `AGENTE_DOOM_STORAGE_BACKEND=minio|s3`

## Bloqueos o riesgos actuales

- falta validar corrida real larga de entrenamiento sobre `basic` con estado limpio
- falta registrar resultados empiricos en `experiment_log.md`
- falta definir criterio numerico exacto de salida de `basic`
- falta comando manual para resincronizar corridas `local_only` o `failed`
- falta descarga o reanudacion desde artefactos remotos

## Siguiente accion recomendada

1. correr `make check`
2. correr `make train-from-scratch`
3. observar bloques de consola, TensorBoard y sync remoto
4. validar en `Neon`:
   - `training_runs`
   - `run_artifacts`
   - `sync_events`
5. validar objetos en `AWS S3`
6. registrar resultado en [experiment_log.md](/E:/agente-doom/Docs/experiment_log.md:1)
7. decidir si ajustar `configs/scenarios/basic.toml`

## Cuando actualizar este archivo

Actualiza este archivo si cambia cualquiera de estos puntos:

- fase actual de entrenamiento
- fase actual de storage
- escenario activo
- foco principal
- bloqueo principal
- siguiente accion recomendada
