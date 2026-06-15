# Implementation checkpoint

Fecha base: 2026-06-14

## Objetivo de este archivo

Este documento deja checkpoint consolidado de lo que ya fue implementado en el repo.

Sirve para:

- retomar trabajo sin releer todo historial
- validar que ya existe antes de tocar algo
- ubicar siguiente punto operativo rapido

## Estado general

- modelo actual: `foundation`
- escenario activo actual: `basic`
- flujo principal: `make train`
- flujo recomendado para primera corrida limpia: `make train-from-scratch`
- fase actual: `Fase 1`

## Ya implementado

### Configuracion

- se elimino `configs/training_profiles.toml`
- se usa:
  - [configs/base.toml](/E:/agente-doom/configs/base.toml:1)
  - [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- la arquitectura ya permite agregar nuevos escenarios por archivo TOML

### CLI publica

Comandos visibles:

- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-checkpoints`
- `list-runs`

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
- `make list-runs`
- `make list-checkpoints`
- `make tensorboard`

### Observabilidad

- TensorBoard operativo por corrida
- consola de entrenamiento mejorada con bloques visuales
- resumenes visuales para:
  - inicio de entrenamiento
  - reward shaping
  - resume
  - evaluacion
  - best model
  - checkpoint
  - acciones recientes
  - resultado final

### Cancelacion controlada

- `Ctrl+C` ya no debe dejar en rojo los targets largos de `make` por cancelacion voluntaria
- aplica a:
  - `train`
  - `train-from-scratch`
  - `train-latest`
  - `evaluate`
  - `evaluate-last`
  - `tensorboard`
- errores reales siguen fallando como error

### Storage local fase 1

- checkpoint canonico: `artifacts/checkpoints/`
- checkpoints automaticos: `artifacts/checkpoints/auto/`
- snapshot historico por corrida: `artifacts/runs/<run_id>/`
- reporte por corrida: `artifacts/runs/<run_id>/report.json`
- indice local resumido: `artifacts/reports/index.json`

### Compatibilidad Windows

- lectura JSON tolerante a BOM UTF-8
- evita fallo de `make list-runs` con archivos legacy

### Tests

- tests reorganizados por paquetes:
  - `tests/cli`
  - `tests/configuration`
  - `tests/envs`
  - `tests/services`
  - `tests/storage`
  - `tests/utils`
- `make check` pasa

## Operacion recomendada hoy

1. `make setup`
2. `make check`
3. `make train-from-scratch`
4. `make tensorboard`
5. `make list-runs`
6. `make list-checkpoints`
7. `make evaluate`

## Siguiente paso recomendado

- correr primera corrida real larga sobre `basic`
- observar reward, actions y comportamiento visual
- registrar resultados en [experiment_log.md](/E:/agente-doom/Docs/experiment_log.md:1)
- decidir si ajustar preset de `basic`
