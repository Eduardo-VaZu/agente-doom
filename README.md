# Agente Doom

Proyecto de ViZDoom con `Gymnasium`, `Stable-Baselines3` y `RecurrentPPO`.

Estado actual:
- entrenamiento activo para modelo `foundation`
- escenario activo actual: `basic`
- evaluacion, inspeccion y reportes historicos disponibles
- arquitectura lista para agregar escenarios uno por uno

## Requisitos

- Windows x64
- Python 3.12
- `py` disponible en PowerShell

## Instalacion

```powershell
cd E:\agente-doom
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Flujo rapido

Entrenar modelo `foundation`:

```powershell
.\.venv\Scripts\python.exe src\cli.py train --scenario basic
```

Evaluar checkpoint resuelto por escenario:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic
```

Inspeccionar metadata:

```powershell
.\.venv\Scripts\python.exe src\cli.py inspect-checkpoint --scenario basic
```

Listar checkpoints y reportes:

```powershell
.\.venv\Scripts\python.exe src\cli.py list-checkpoints --limit 10
.\.venv\Scripts\python.exe src\cli.py list-runs --limit 10
```

## Makefile

Atajos:

```powershell
make help
make setup
make bootstrap
make install
make check
make train
make train-from-scratch
make train-latest
make evaluate SCENARIO=basic
make evaluate-last SCENARIO=basic
make play SCENARIO=basic
make inspect SCENARIO=basic
make list-checkpoints LIMIT=10
make list-runs LIMIT=10
make tensorboard
```

## CLI publica

Comandos disponibles:
- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-checkpoints`
- `list-runs`

Comandos retirados:
- `sweep`
- `list-scenarios`
- `list-profiles`

`src\train.py` se conserva como wrapper legacy del flujo de entrenamiento actual.

## Entrenamiento

Modelo actual:
- identidad: `foundation`
- checkpoint base: `doom_foundation_agent`
- TensorBoard run: `Doom_Foundation_Agent`
- escenario activo hoy: `basic`

Comandos:

```powershell
.\.venv\Scripts\python.exe src\cli.py train --scenario basic
.\.venv\Scripts\python.exe src\cli.py train --scenario basic --from-scratch
.\.venv\Scripts\python.exe src\cli.py train --scenario basic --resume latest
```

## Evaluacion

Evaluar mejor checkpoint del escenario:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic
```

Evaluar checkpoint explicito:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\checkpoints\doom_foundation_agent.zip
```

Elegir variante:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --select best
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --select last
```

Limitar pasos:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --steps 500
```

## Catalogo de escenarios

Los presets siguen en:

```text
configs/base.toml
configs/scenarios/basic.toml
```

Se usan para:
- resolver nombres de checkpoint por escenario
- conservar metadata y compatibilidad historica

Escenario activo hoy:
- `basic`

Escenarios futuros recomendados:
- `defend_the_center`
- `health_gathering`
- `take_cover`
- `deadly_corridor`

La priorizacion detallada vive en [Docs/vizdoom_escenarios_oficiales.md](/E:/agente-doom/Docs/vizdoom_escenarios_oficiales.md:89).

## Artefactos

Salidas historicas:
- `artifacts/checkpoints/`
- `artifacts/checkpoints/auto/`
- `artifacts/runs/<run_id>/`
- `artifacts/reports/`
- `artifacts/tensorboard/`
- `artifacts/videos/`

Convencion local de fase 1:
- `artifacts/checkpoints/` guarda checkpoint canonico para `resume` y `evaluate`
- `artifacts/runs/<run_id>/checkpoints/` guarda snapshot inmutable por corrida
- `artifacts/runs/<run_id>/videos/` guarda videos de esa corrida
- `artifacts/runs/<run_id>/tensorboard/` guarda logs de esa corrida
- `artifacts/runs/<run_id>/report.json` guarda reporte detallado

## Desarrollo

Checks locales:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Con `make`:

```powershell
make setup
make bootstrap
make lint
make typecheck
make test
make check
```

Pre-commit:

```powershell
.\.venv\Scripts\python.exe -m pre_commit install
```

## Estructura

```text
src\
  doom_agent\
    cli\         CLI unificada
    config\      catalogo tipado y rutas
    envs\        entorno Gymnasium y acciones
    models\      modelo PPO recurrente
    services\    entrenamiento, evaluacion y compatibilidad
    shared\      contratos y tipos
    utils\       checkpoints, reportes y filesystem
  cli.py         entrypoint principal
  train.py       wrapper legacy de entrenamiento
  evaluate.py    wrapper legacy
configs\         catalogo por escenario
data\scenarios\  escenarios .cfg y .wad
tests\           pruebas automatizadas
artifacts\       salidas historicas
```
