# Comandos principales

Esta guia resume los comandos que el equipo deberia usar en el dia a dia.

La idea es evitar comandos largos a mano y trabajar casi siempre con `make`.

## Preparacion

### `make setup`

Que hace:
- crea `.venv`
- instala dependencias del proyecto

Cuando usarlo:
- primera vez que clonas el repo
- cuando recreas el entorno local

### `make check`

Que hace:
- corre `ruff`
- corre `mypy`
- corre `unittest`

Cuando usarlo:
- antes de una corrida importante
- despues de cambios en codigo

## Entrenamiento

### `make train`

Que hace:
- entrena con `resume=auto`
- si encuentra un checkpoint compatible, continua desde ahi
- si no encuentra uno, arranca desde cero

Cuando usarlo:
- flujo normal de trabajo
- cuando quieres seguir la linea activa sin decidir manualmente el checkpoint

Ejemplo:

```powershell
make train SEED=42 TIMESTEPS=1500000
```

### `make train-from-scratch`

Que hace:
- ignora checkpoints previos
- fuerza una corrida nueva y limpia

Cuando usarlo:
- corrida oficial nueva
- pilotos por seed
- cuando no quieres arrastrar historia previa

Ejemplo:

```powershell
make train-from-scratch SEED=42 TIMESTEPS=1500000
```

### `make train-latest`

Que hace:
- intenta reanudar desde el checkpoint mas reciente
- no usa la logica flexible de `auto`

Cuando usarlo:
- cuando una corrida se corto y quieres retomarla
- cuando sabes que quieres continuar exactamente el ultimo estado

Ejemplo:

```powershell
make train-latest SEED=42
```

### `make tensorboard`

Que hace:
- abre TensorBoard apuntando a `artifacts/runs`

Cuando usarlo:
- mientras entrena una corrida
- cuando quieres revisar curvas por `run_id`

## Evaluacion

### `make evaluate`

Que hace:
- evalua un checkpoint con `select=best` por defecto
- puede evaluar por escenario o por ruta explicita
- soporta evaluacion offline por episodios

Cuando usarlo:
- validar el mejor checkpoint actual
- comparar checkpoints con el mismo protocolo

Ejemplo:

```powershell
make evaluate CHECKPOINT=artifacts\checkpoints\doom_foundation_agent_best.zip EPISODES=50 NO_RENDER=1 JSON=1
```

### `make evaluate-last`

Que hace:
- igual que `make evaluate`
- pero resuelve `select=last`

Cuando usarlo:
- revisar el ultimo checkpoint guardado
- comparar `last` contra `best`

Ejemplo:

```powershell
make evaluate-last CHECKPOINT=artifacts\checkpoints\auto\doom_foundation_agent_1250000_steps.zip EPISODES=50 NO_RENDER=1 JSON=1
```

### `make inspect`

Que hace:
- imprime metadata estructurada del checkpoint

Cuando usarlo:
- revisar de que corrida salio un checkpoint
- confirmar `saved_timesteps`, `checkpoint_role` y metricas

## Corridas y promotion

### `make list-runs`

Que hace:
- lista corridas registradas
- mezcla lectura desde DB con fallback local

Cuando usarlo:
- ver historial reciente
- ubicar un `run_id`

### `make inspect-run`

Que hace:
- consolida `report.json` + `manifest.json`
- muestra estado de artefactos, sync y handoff

Cuando usarlo:
- entender una corrida completa
- verificar si una corrida esta lista para sync o handoff

Ejemplo:

```powershell
make inspect-run RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ JSON=1
```

### `make promote`

Que hace:
- reevaluar un checkpoint offline
- si pasa la reevaluacion, lo copia al alias promovido oficial

Cuando usarlo:
- elegir el checkpoint oficial que el equipo quiere preservar
- no depender de inspeccion visual aislada

Ejemplo:

```powershell
make promote CHECKPOINT=artifacts\checkpoints\auto\doom_foundation_agent_1250000_steps.zip PROMOTE_EPISODES=50
```

## Sync y handoff

### `make sync-artifacts`

Que hace:
- sube artefactos de una corrida a `S3`

Cuando usarlo:
- corrida puntual que quedo `local_only`
- cerrar una corrida antes de mover trabajo entre PCs

Ejemplo:

```powershell
make sync-artifacts RUN_ID=doom_foundation_agent__YYYYMMDDTHHMMSSffffffZ
```

### `make sync-local-only`

Que hace:
- busca corridas `local_only`
- intenta resincronizarlas en batch

### `make sync-failed`

Que hace:
- reintenta corridas con sync fallido

### `make sync-dry-run`

Que hace:
- muestra que subiria
- no sube nada ni toca DB

## Multi-PC

### `make hydrate`

Que hace:
- reconstruye alias oficiales y soporte minimo desde `S3`
- puede traer `active`, `promoted` o ambos

Cuando usarlo:
- preparar otra PC para continuar trabajo
- reconstruir el estado oficial sin copiar manualmente artifacts

Ejemplo:

```powershell
make hydrate ONLY=promoted
```

## Variables mas utiles

- `SEED=42`: seed de entrenamiento
- `TIMESTEPS=1500000`: pasos solicitados
- `CHECKPOINT=...`: ruta o nombre de checkpoint
- `RUN_ID=...`: corrida exacta
- `EPISODES=50`: evaluacion offline mas estable
- `NO_RENDER=1`: evaluacion sin ventana
- `JSON=1`: salida estructurada
- `ONLY=active|promoted|both`: alcance de hidratacion

## Flujo recomendado del proyecto hoy

1. `make setup`
2. `make check`
3. `make train-from-scratch SEED=42 TIMESTEPS=1500000`
4. `make tensorboard`
5. `make evaluate CHECKPOINT=... EPISODES=50 NO_RENDER=1 JSON=1`
6. `make promote CHECKPOINT=... PROMOTE_EPISODES=50`
7. `make sync-artifacts RUN_ID=...`
8. `make hydrate ONLY=promoted` en otra PC si hace falta
