# Agente Doom

Proyecto de entrenamiento en ViZDoom con `Stable-Baselines3` y `RecurrentPPO`.

Hoy el flujo principal entrena modelo `foundation` sobre escenario `basic`, usando `make` como punto unico de operacion.

## Requisitos

- Windows x64
- Python 3.12
- `py` disponible en PowerShell
- `make` disponible en terminal

## Instalar Python y make

Si todavia no los tienes instalados:

Python:
- descarga para Windows: [python.org/downloads/windows](https://www.python.org/downloads/windows/)
- durante instalacion, marca opcion para agregar Python al `PATH`

make:
- opcion recomendada en Windows con Chocolatey:

```powershell
choco install make
```

- paquete de referencia: [community.chocolatey.org/packages/make](https://community.chocolatey.org/packages/make)

Verificar instalacion:

```powershell
py --version
make --version
```

## Inicio rapido

Entrar al proyecto:

```powershell
cd E:\agente-doom
```

Crear entorno virtual e instalar dependencias:

```powershell
make setup
```

Validar proyecto completo:

```powershell
make check
```

Entrenar desde cero:

```powershell
make train-from-scratch
```

Ver TensorBoard:

```powershell
make tensorboard
```

Evaluar modelo visualmente:

```powershell
make evaluate
```

## Flujo recomendado

Primer uso:

```powershell
make setup
make check
make train-from-scratch
```

Mientras entrena, en otra terminal:

```powershell
make tensorboard
```

Luego revisar resultados:

```powershell
make list-runs
make list-checkpoints
make evaluate
```

## Comandos principales

Preparacion:

```powershell
make venv
make install
make setup
make bootstrap
```

Validacion:

```powershell
make lint
make typecheck
make test
make check
```

Entrenamiento:

```powershell
make train
make train-from-scratch
make train-latest
```

Evaluacion e inspeccion:

```powershell
make evaluate
make evaluate-last
make play
make inspect
```

Seguimiento:

```powershell
make list-runs
make list-checkpoints
make tensorboard
```

## Variables utiles

Escenario:

```powershell
make train SCENARIO=basic
make evaluate SCENARIO=basic
```

Timesteps y seed:

```powershell
make train TIMESTEPS=750000 SEED=42
```

Evaluacion limitada:

```powershell
make evaluate STEPS=2000
```

Checkpoint explicito:

```powershell
make evaluate CHECKPOINT=artifacts\checkpoints\doom_foundation_agent.zip
make inspect CHECKPOINT=artifacts\checkpoints\doom_foundation_agent.zip
```

## Que guarda el proyecto

- `artifacts/checkpoints/`: checkpoint canonico para `resume` y `evaluate`
- `artifacts/checkpoints/auto/`: checkpoints automaticos por progreso
- `artifacts/runs/<run_id>/`: snapshot historico por corrida
- `artifacts/reports/`: indice resumido de corridas

## Estado actual

- modelo activo: `foundation`
- escenario activo: `basic`
- flujo principal: `train --scenario <scenario>`
- comandos retirados del flujo publico:
  - `sweep`
  - `list-scenarios`
  - `list-profiles`

## Ayuda

Ver ayuda general del Makefile:

```powershell
make help
```

Si necesitas mas contexto funcional o roadmap, revisa carpeta `docs/`.
