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
