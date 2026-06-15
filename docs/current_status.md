# Current status

Fecha base: 2026-06-14

## Resumen ejecutivo

- modelo actual: `foundation`
- fase actual: `Fase 1`
- escenario activo: `basic`
- configuracion activa: [configs/base.toml](/E:/agente-doom/configs/base.toml:1) + [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- flujo principal: `make train`
- flujo recomendado inicial: `make train-from-scratch`

## En que estamos

Foco actual:
- estabilizar entrenamiento de `basic`
- validar que pipeline, checkpoints, reportes y evaluacion funcionen de punta a punta
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

## Bloqueos o riesgos actuales

- falta validar corrida real larga de entrenamiento sobre `basic`
- falta registrar resultados empiricos en `experiment_log.md`
- falta definir criterio numerico exacto de salida de `basic`

## Siguiente accion recomendada

1. correr `make check`
2. correr `make train-from-scratch`
3. observar bloques de consola y TensorBoard
4. registrar resultado en [experiment_log.md](/E:/agente-doom/Docs/experiment_log.md:1)
5. decidir si ajustar `configs/scenarios/basic.toml`

## Cuando actualizar este archivo

Actualiza este archivo si cambia cualquiera de estos puntos:

- fase actual
- escenario activo
- foco principal
- bloqueo principal
- siguiente accion recomendada
