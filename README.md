# Agente Doom

Agente de aprendizaje por refuerzo para escenarios de ViZDoom usando `Gymnasium`, `Stable-Baselines3` y `RecurrentPPO`.

Estado actual del proyecto:
- un solo flujo publico de entrenamiento
- una sola configuracion base: `default`
- optimizacion real por escenario desde `configs/training_profiles.toml`
- checkpoints, reportes, TensorBoard y videos en `artifacts/`

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

## Flujo Rapido

Listar escenarios:

```powershell
.\.venv\Scripts\python.exe src\cli.py list-scenarios
```

Entrenar escenario normal:

```powershell
.\.venv\Scripts\python.exe src\cli.py train --scenario basic
.\.venv\Scripts\python.exe src\cli.py train --scenario defend_the_center
.\.venv\Scripts\python.exe src\cli.py train --scenario deadly_corridor
.\.venv\Scripts\python.exe src\cli.py train --scenario health_gathering
```

Evaluar checkpoint del escenario:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic
```

Inspeccionar metadata:

```powershell
.\.venv\Scripts\python.exe src\cli.py inspect-checkpoint --scenario basic
```

## Makefile

Atajos principales:

```powershell
make help
make install
make check
make list-scenarios
make train SCENARIO=basic
make train SCENARIO=deadly_corridor RESUME=latest
make evaluate SCENARIO=health_gathering
make inspect SCENARIO=basic
make sweep SCENARIO=basic LEARNING_RATES=0.0001,0.0002 N_STEPS_VALUES=1024,2048 BATCH_SIZES=32,64 SEEDS=42,43
```

Targets utiles:
- `make train-basic`
- `make train-defend`
- `make train-deadly`
- `make train-health`
- `make list-checkpoints LIMIT=10`
- `make list-runs LIMIT=10`
- `make tensorboard`

## CLI

Comandos publicos:
- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-scenarios`
- `list-checkpoints`
- `list-runs`

Alias compatible:
- `list-profiles` -> mismo resultado que `list-scenarios`

Comando avanzado:
- `sweep`

## Entrenamiento

El entrenamiento normal usa siempre la configuracion base `default`. El usuario elige solo el escenario.

Ejemplos:

```powershell
.\.venv\Scripts\python.exe src\cli.py train --scenario deadly_corridor
.\.venv\Scripts\python.exe src\cli.py train --scenario health_gathering --resume latest
.\.venv\Scripts\python.exe src\cli.py train --scenario basic --from-scratch
.\.venv\Scripts\python.exe src\cli.py train --scenario defend_the_center --seed 123
```

Flags utiles de `train`:
- `--resume auto|latest|<checkpoint>`
- `--from-scratch`
- `--seed <int>`
- `--timesteps <int>`
- `--eval-freq <int>`
- `--eval-episodes <int>`
- `--no-save-best`
- `--allow-scenario-resume`

Notas importantes:
- `RecurrentPPO` entrena en bloques de `n_steps`
- `effective_timesteps` puede ser mayor que `requested_timesteps`
- si el escenario no es `basic`, el checkpoint agrega sufijo `__<scenario>`
- por defecto, una corrida intenta reanudar desde el ultimo checkpoint compatible

## Evaluacion

Evaluacion normal por escenario:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario deadly_corridor
```

Evaluar checkpoint explicito:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\checkpoints\ppo_doom_recurrent_actions_v2__deadly_corridor.zip
```

Forzar seleccion:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --select last
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --select best
```

Limitar pasos:

```powershell
.\.venv\Scripts\python.exe src\cli.py evaluate --scenario basic --steps 500
```

## Sweep

`sweep` ejecuta varias corridas secuenciales cambiando hiperparametros sobre la configuracion `default`.

Ejemplo:

```powershell
.\.venv\Scripts\python.exe src\cli.py sweep --scenario basic --learning-rates 0.0001,0.0002 --n-steps-values 1024,2048 --batch-sizes 32,64 --seeds 42,43
```

## Escenarios Disponibles

- `basic`
- `defend_the_center`
- `deadly_corridor`
- `health_gathering`

Los presets de cada escenario viven en:

```text
configs/training_profiles.toml
```

## Artefactos

Salidas generadas:
- `artifacts/checkpoints/`
- `artifacts/checkpoints/auto/`
- `artifacts/reports/`
- `artifacts/tensorboard/`
- `artifacts/videos/`

Comportamiento:
- ultimo estado: `<checkpoint>.zip`
- mejor modelo por evaluacion: `<checkpoint>_best.zip`
- metadata estructurada: `<checkpoint>.json`
- indice de corridas: `artifacts/reports/index.json`

## Desarrollo

Checks locales:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Con Makefile:

```powershell
make lint
make typecheck
make test
make check
```

Pre-commit:

```powershell
.\.venv\Scripts\python.exe -m pre_commit install
```

TensorBoard:

```powershell
.\.venv\Scripts\tensorboard.exe --logdir artifacts\tensorboard
```

## Estructura

```text
src\
  doom_agent\
    cli\         CLI unificada
    config\      carga tipada del catalogo TOML y rutas
    envs\        entorno Gymnasium, acciones y reward shaping
    models\      modelo PPO recurrente
    services\    entrenamiento, evaluacion y sweep
    shared\      contratos y tipos compartidos
    utils\       checkpoints, reportes y filesystem
  cli.py         entrypoint principal
  train.py       wrapper legacy
  evaluate.py    wrapper legacy
configs\         configuracion por escenario
data\scenarios\  escenarios .cfg y .wad
tests\           pruebas automatizadas
artifacts\       salidas generadas
```

## Notas

- `src\train.py` y `src\evaluate.py` siguen existiendo por compatibilidad, pero el entrypoint recomendado es `src\cli.py`
- `list-profiles` sigue funcionando como alias, pero el nombre recomendado es `list-scenarios`
- si necesitas cambiar timesteps, reward shaping o frecuencias por escenario, edita `configs/training_profiles.toml`
