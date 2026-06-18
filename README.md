# Agente Doom

Proyecto de entrenamiento en ViZDoom con `Stable-Baselines3` y `RecurrentPPO`.

Hoy el flujo principal entrena modelo `foundation` sobre escenario `basic`, usando `make` como punto unico de operacion.
La persistencia remota activa usa `Neon` para metadata y `AWS S3` para artefactos pesados.

## Requisitos

- Windows x64
- Python 3.13
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

## Storage remoto

Backend remoto principal:

- metadata: `Neon / PostgreSQL`
- object storage: `AWS S3`

Variables esperadas en `.env`:

```env
AGENTE_DOOM_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/neondb?sslmode=require"
AGENTE_DOOM_STORAGE_BACKEND="s3"
AGENTE_DOOM_S3_BUCKET="agente-doom-artifacts-prod"
AGENTE_DOOM_S3_REGION="us-east-1"
AGENTE_DOOM_S3_ACCESS_KEY_ID="TU_ACCESS_KEY_ID"
AGENTE_DOOM_S3_SECRET_ACCESS_KEY="TU_SECRET_ACCESS_KEY"
AGENTE_DOOM_S3_ENDPOINT_URL=""
AGENTE_DOOM_S3_OBJECT_PREFIX="runs"
```

## MinIO local opcional

Si quieres probar sync remoto sin montar nada en nube, proyecto ya trae `docker-compose.yml`
para levantar `MinIO` local.

Levantar MinIO:

```powershell
make minio-up
```

Panel web:

- API S3: `http://127.0.0.1:9000`
- consola: `http://127.0.0.1:9001`
- usuario: `minio`
- password: `minioadmin`

Luego agrega estas variables a tu `.env` local:

```env
AGENTE_DOOM_MINIO_ENDPOINT="http://127.0.0.1:9000"
AGENTE_DOOM_MINIO_ACCESS_KEY="minio"
AGENTE_DOOM_MINIO_SECRET_KEY="minioadmin"
AGENTE_DOOM_MINIO_BUCKET="agente-doom-artifacts"
AGENTE_DOOM_MINIO_SECURE="false"
AGENTE_DOOM_MINIO_REGION=""
AGENTE_DOOM_MINIO_OBJECT_PREFIX="runs"
```

Parar MinIO:

```powershell
make minio-down
```

Ver logs:

```powershell
make minio-logs
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

Si MinIO esta configurado en `.env`, al final de cada corrida proyecto intentara subir
checkpoints remotos y registrar resultado en `PostgreSQL`.

Si `AGENTE_DOOM_STORAGE_BACKEND="s3"`, proyecto usara `AWS S3` como backend remoto principal.

Si una corrida queda `local_only` o `failed`, ahora puedes resincronizar artefactos manualmente
sin reentrenar. Este resync solo considera `checkpoint` y `video`; `report.json` sigue local.

Ejemplos:

```powershell
.\.venv\Scripts\python.exe src\cli.py sync-artifacts --run-id doom_foundation_agent__20260617T040513523127Z
.\.venv\Scripts\python.exe src\cli.py sync-artifacts --all-local-only --limit 20
.\.venv\Scripts\python.exe src\cli.py sync-artifacts --all-failed --limit 20
.\.venv\Scripts\python.exe src\cli.py sync-artifacts --run-id doom_foundation_agent__20260617T040513523127Z --dry-run
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
make sync-artifacts RUN_ID=doom_foundation_agent__20260617T040513523127Z
make sync-local-only LIMIT=20
make sync-failed LIMIT=20
make sync-dry-run RUN_ID=doom_foundation_agent__20260617T040513523127Z
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
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
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
