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
- comando ejecutado:
  - no se registro una corrida larga de entrenamiento en esta entrada
- resultado observado:
  - arquitectura lista para comenzar iteracion operativa sobre `basic`
- decision siguiente:
  - correr `make check`
  - correr `make train`
  - registrar comportamiento real del entrenamiento
