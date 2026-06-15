# Storage roadmap

Este documento define como debe evolucionar almacenamiento de entrenamiento del modelo
`foundation`.

## Objetivo general

Separar correctamente:

- artefactos grandes
- metadata operativa
- historico de corridas
- futura persistencia en nube

## Regla principal

No todo debe ir a base de datos.

Convencion correcta:

- checkpoints, videos y artefactos pesados -> filesystem local hoy, object storage despues
- metadata, reportes e indices -> JSON local hoy, DB despues

## Fase 1: Local estable

Estado:
- activa
- implementada para almacenamiento local por corrida

Objetivo:
- trabajar solo en local
- validar pipeline completo sin complejidad de nube

Que se guarda en local:

- checkpoints `.zip`
- metadata `.json`
- reportes `.json`
- TensorBoard logs
- videos

Ubicacion actual:

- `artifacts/checkpoints/`
- `artifacts/checkpoints/auto/`
- `artifacts/runs/<run_id>/checkpoints/`
- `artifacts/runs/<run_id>/videos/`
- `artifacts/runs/<run_id>/tensorboard/`
- `artifacts/runs/<run_id>/report.json`
- `artifacts/reports/`
- `artifacts/tensorboard/`
- `artifacts/videos/`

Entregables de esta fase:

- estructura local consistente
- nombres de artefactos estables
- reportes y metadata reproducibles
- criterio de que artefactos se conservan y cuales se limpian

Acciones sugeridas:

1. mantener todo local por ahora
2. validar que checkpoints y reportes se guarden bien
3. registrar corridas reales en `Docs/experiment_log.md`
4. definir convencion de nombres por `run_id`

Convencion aplicada:

- checkpoint canonico reutilizable vive en `artifacts/checkpoints/`
- snapshot historico por corrida vive en `artifacts/runs/<run_id>/checkpoints/`
- TensorBoard y videos se separan por corrida dentro de `artifacts/runs/<run_id>/`
- `artifacts/reports/index.json` sigue como indice resumido local
- lectura de JSON local ya es tolerante a BOM UTF-8 para compatibilidad con archivos legacy de Windows

## Fase 2: Arquitectura hibrida

Estado:
- pendiente

Objetivo:
- mantener entrenamiento local
- comenzar a mover artefactos grandes a almacenamiento remoto
- dejar metadata en un sistema consultable

Artefactos a mover a object storage:

- checkpoints
- best checkpoints
- videos
- posiblemente logs pesados

Datos a pasar a DB:

- metadata de checkpoints
- reportes de corridas
- indice de experimentos
- referencias a rutas remotas

Arquitectura esperada:

- entrenamiento sigue escribiendo local primero
- luego sincroniza artefactos grandes a nube
- DB guarda metadata y `remote_uri`

Entregables:

- contrato de `artifact store`
- contrato de `run repository`
- primer backend remoto
- primer schema de DB

## Fase 3: Operacion remota estable

Estado:
- pendiente

Objetivo:
- dejar flujo estable para entrenamientos recurrentes
- soportar historial largo y consulta facil

Resultado esperado:

- checkpoints en object storage
- metadata en DB
- corridas listables por escenario, fase y fecha
- posibilidad de reanudar entrenamientos desde artefactos remotos

## Fase 4: Tracking avanzado

Estado:
- pendiente

Objetivo:
- agregar observabilidad y comparacion de experimentos a mayor escala

Opciones futuras:

- MLflow
- Weights & Biases
- dashboard propio

Esto serviria para:

- comparar corridas
- ver metricas historicas
- comparar escenarios y fases
- decidir mejor cuando avanzar de fase

## Distribucion recomendada de almacenamiento

### Local hoy

- checkpoints
- metadata
- reportes
- videos
- TensorBoard

### Hibrido despues

- object storage:
  - checkpoints
  - videos
  - logs grandes

- DB:
  - reportes
  - metadata
  - indices
  - referencias a artefactos

## Siguiente paso operativo

Actualmente:

- seguir en `Fase 1`
- no mover nada a nube todavia
- estabilizar guardado local y entrenamiento en `basic`

Despues:

- preparar contrato de almacenamiento remoto
- preparar schema inicial para metadata
