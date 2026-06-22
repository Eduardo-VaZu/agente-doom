# Agente Doom

Proyecto de entrenamiento en ViZDoom con `Stable-Baselines3` y `RecurrentPPO`.

Hoy el repo entrena el modelo `foundation` sobre el escenario `basic`, usando `make`
como punto principal de operacion. La persistencia remota activa usa `Neon` para metadata
y `AWS S3` para artefactos pesados.

## Que es este repo

Este proyecto hace cinco cosas principales:

1. define configuraciones de entrenamiento por escenario
2. entrena y evalua agentes en ViZDoom
3. guarda corridas, checkpoints y reportes
4. sincroniza artefactos con `Neon + S3`
5. permite continuidad operativa entre PCs con `hydrate-workspace`

## Indice rapido

- [Inicio rapido](#inicio-rapido)
- [Flujo recomendado](#flujo-recomendado)
- [Comandos principales](#comandos-principales)
- [TensorBoard y metricas](#tensorboard-y-metricas)
- [Storage remoto](#storage-remoto)
- [Mapa de documentacion](#mapa-de-documentacion)

## Requisitos

- Windows x64
- Python 3.13
- `py` disponible en PowerShell
- `make` disponible en terminal

## Instalar Python y make

Si todavia no los tienes instalados:

Python:
- descarga para Windows: [python.org/downloads/windows](https://www.python.org/downloads/windows/)
- durante la instalacion, marca la opcion para agregar Python al `PATH`

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

Abrir TensorBoard:

```powershell
make tensorboard
```

Evaluar:

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
make inspect-run RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ
make evaluate CHECKPOINT=artifacts\checkpoints\doom_foundation_agent_best.zip EPISODES=50 NO_RENDER=1 JSON=1
```

Si quieres fijar un checkpoint oficial:

```powershell
make promote CHECKPOINT=artifacts\checkpoints\auto\doom_foundation_agent_1250000_steps.zip PROMOTE_EPISODES=50
```

Si quieres continuar en otra PC:

```powershell
make hydrate ONLY=promoted
```

## Comandos principales

Preparacion:

```powershell
make setup
make bootstrap
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
make inspect
make inspect-run RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ
make promote CHECKPOINT=artifacts\checkpoints\auto\doom_foundation_agent_1250000_steps.zip
```

Sync y handoff:

```powershell
make sync-artifacts RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ
make sync-local-only LIMIT=20
make sync-failed LIMIT=20
make sync-dry-run RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ
make hydrate ONLY=promoted
```

Observabilidad:

```powershell
make tensorboard
make list-runs
make list-checkpoints
```

## TensorBoard y metricas

TensorBoard ya produce los graficos; no hace falta reentrenar para explicar que significa cada uno.

La leyenda operativa del proyecto vive en:

- [docs/tensorboard_metricas.md](/E:/agente-doom/docs/tensorboard_metricas.md:1)

Uso rapido:

- `rollout/`: comportamiento durante entrenamiento
- `eval/`: calidad del checkpoint en evaluacion periodica
- `train/`: senales internas de optimizacion PPO
- `time/`: velocidad y progreso de corrida

Para presentacion, prioriza:

- `eval/mean_reward`
- `eval/std_reward`
- `eval/mean_episode_length`
- `eval/actions/*`
- `time/fps`

Variables utiles:

- `SEED=42`
- `TIMESTEPS=1500000`
- `CHECKPOINT=...`
- `RUN_ID=...`
- `EPISODES=50`
- `NO_RENDER=1`
- `JSON=1`
- `ONLY=active|promoted|both`

Para ver la guia operativa completa de comandos, abre
[docs/comandos_principales.md](/E:/agente-doom/docs/comandos_principales.md:1).

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

Con configuracion `S3` valida en `.env`, al final de cada corrida el proyecto intenta subir
artefactos elegibles y registrar metadata en `PostgreSQL`.

Si una corrida queda `local_only` o `failed`, puedes resincronizar sin reentrenar. Ese flujo
considera `report.json`, `manifest.json`, checkpoints y videos elegibles.

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
- flujo principal: `make train`

## Mapa de documentacion

Este mapa usa la misma estructura consolidada de la carpeta `docs`.

### Referencia

- [vizdoom_escenarios_oficiales.md](/E:/agente-doom/docs/vizdoom_escenarios_oficiales.md:1)
  Universo de escenarios oficiales de ViZDoom. Responde: que existe.

- [how_to_add_scenario.md](/E:/agente-doom/docs/how_to_add_scenario.md:1)
  Procedimiento tecnico para agregar un escenario al proyecto.

### Nucleo operativo

- [estado_actual.md](/E:/agente-doom/docs/estado_actual.md:1)
  Fuente de verdad del estado vivo del repo y de lo ya implementado.

- [storage_y_handoff.md](/E:/agente-doom/docs/storage_y_handoff.md:1)
  Storage remoto, sync, promotion, hydrate y continuidad entre PCs.

- [plan_escenarios.md](/E:/agente-doom/docs/plan_escenarios.md:1)
  Roadmap y estado operativo de escenarios por fase.

### Seguimiento y apoyo

- [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)
  Bitacora cronologica de cambios y resultados. Responde: que ya se probo y que paso.

- [comandos_principales.md](/E:/agente-doom/docs/comandos_principales.md:1)
  Guia practica de `make` y comandos reales del dia a dia. Responde: que comando usar, cuando y con que variables.

- [glosario.md](/E:/agente-doom/docs/glosario.md:1)
  Vocabulario operativo del proyecto. Responde: como nombramos cada concepto en espanol sin pelear con el codigo.

- [estructura_repo.md](/E:/agente-doom/docs/estructura_repo.md:1)
  Mapa del repo por carpetas, modulos y archivos clave. Responde: donde vive cada responsabilidad y que hace cada pieza.

- [tensorboard_metricas.md](/E:/agente-doom/docs/tensorboard_metricas.md:1)
  Leyenda practica de metricas y graficos de TensorBoard. Responde: como leer cada grafico y cual usar para presentar resultados.

### Como usarlos juntos

1. Abre [estado_actual.md](/E:/agente-doom/docs/estado_actual.md:1)
   Para saber en que estamos y que ya existe.

2. Si necesitas revisar storage, sync o multi-PC, abre [storage_y_handoff.md](/E:/agente-doom/docs/storage_y_handoff.md:1)
   Para entender continuidad operativa real.

3. Si necesitas ver escenarios y prioridad, abre [plan_escenarios.md](/E:/agente-doom/docs/plan_escenarios.md:1)

4. Si necesitas contexto historico real, abre [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)

5. Si necesitas guia operativa de comandos, abre [comandos_principales.md](/E:/agente-doom/docs/comandos_principales.md:1)

6. Si necesitas vocabulario consistente del proyecto, abre [glosario.md](/E:/agente-doom/docs/glosario.md:1)

7. Si necesitas mapa de modulos y archivos, abre [estructura_repo.md](/E:/agente-doom/docs/estructura_repo.md:1)

8. Si necesitas leer TensorBoard o explicar metricas en una presentacion, abre [tensorboard_metricas.md](/E:/agente-doom/docs/tensorboard_metricas.md:1)

9. Si necesitas agregar un escenario nuevo, abre [how_to_add_scenario.md](/E:/agente-doom/docs/how_to_add_scenario.md:1)

10. Si necesitas revisar universo oficial de ViZDoom, abre [vizdoom_escenarios_oficiales.md](/E:/agente-doom/docs/vizdoom_escenarios_oficiales.md:1)

## Ayuda

Ver ayuda general del Makefile:

```powershell
make help
```

Si quieres empezar entendiendo el repo sin perderte, abre en este orden:

1. [docs/estado_actual.md](/E:/agente-doom/docs/estado_actual.md:1)
2. [docs/comandos_principales.md](/E:/agente-doom/docs/comandos_principales.md:1)
3. [docs/estructura_repo.md](/E:/agente-doom/docs/estructura_repo.md:1)
