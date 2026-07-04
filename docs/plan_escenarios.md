# Plan de escenarios

Documento consolidado del roadmap de curriculum y del registro operativo por escenario.

Modelo objetivo: `foundation`

## Estado actual

- escenario activo actual: `defend_the_line`
- fase actual de entrenamiento: `Fase 3`
- fase actual de storage: `Fase 2`
- ultimo objetivo claro: cerrar `defend_the_line` como referencia inicial de Fase 3 y abrir siguiente escenario especializado

## Regla general

Solo se avanza a la siguiente fase cuando:

- entrenamiento actual es estable
- reward deja de subir de forma significativa o converge de forma razonable
- action usage es coherente con el escenario
- checkpoint final y mejor checkpoint se guardan bien
- evaluacion es reproducible
- configuracion del escenario queda documentada

## Registro operativo

| Escenario | Fase | Estado | Config | Tests minimos | Rol principal | Notas |
|---|---|---|---|---|---|---|
| `basic` | Fase 1 | Baseline oficial cerrada | [basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1) | Si | combate base y validacion del pipeline | baseline inicial validada y congelada |
| `defend_the_center` | Fase 2 | Escenario activo oficial validado | [defend_the_center.toml](/E:/agente-doom/configs/scenarios/defend_the_center.toml:1) | Si | punteria, giro, reaccion | segundo tramo validado; checkpoint promovido mejorado |
| `health_gathering` | Fase 2 | Escenario activo oficial validado | [health_gathering.toml](/E:/agente-doom/configs/scenarios/health_gathering.toml:1) | Si | navegacion y supervivencia | segundo tramo validado; checkpoint promovido mejorado |
| `take_cover` | Fase 2 | Escenario activo oficial validado | [take_cover.toml](/E:/agente-doom/configs/scenarios/take_cover.toml:1) | Si | evasion y timing defensivo | segundo tramo validado; checkpoint promovido mejorado |
| `basic_audio` | Fase 3 | Pendiente | No creado aun | No | percepcion por audio | siguiente candidato a integrar |
| `defend_the_line` | Fase 3 | Escenario activo oficial validado | [defend_the_line.toml](/E:/agente-doom/configs/scenarios/defend_the_line.toml:1) | Si | combate frontal sostenido | piloto por transferencia validado; checkpoint promovido oficial |
| `basic_notifications` | Fase 3 | Pendiente | No creado aun | No | seleccion de objetivo | escenario especializado |
| `my_way_home` | Fase 3 | Pendiente | No creado aun | No | navegacion mas compleja | util para generalizacion espacial |
| `predict_position` | Fase 3 | Pendiente | No creado aun | No | precision temporal | escenario especializado |
| `health_gathering_supreme` | Fase 3 | Pendiente | No creado aun | No | supervivencia compleja | version dura de `health_gathering` |
| `deadly_corridor` | Fase 4 | Pendiente | No creado aun | No | integracion de combate y navegacion | muy alta dificultad |
| `deathmatch` | Fase 4 | Pendiente | No creado aun | No | escenario complejo y costoso | dejar al final |

## Fase 1: Nucleo base

Objetivo:
- estabilizar entrenamiento
- validar pipeline completo
- aprender control minimo de combate 3D

Escenarios:
1. `basic`

Estado:
- cerrado

## Fase 2: Expansion generalista

Escenarios:
1. `defend_the_center`
2. `health_gathering`
3. `take_cover`

Estado:
- cerrada

Comando de arranque historico:

```powershell
.\.venv\Scripts\python.exe src\cli.py train --scenario defend_the_center --resume artifacts\checkpoints\doom_foundation_agent_promoted.zip --allow-scenario-resume --seed 42 --timesteps 300000
```

Resultado actual:
- piloto inicial completado y validado offline
- tramo adicional de mejora completado y validado offline
- `defend_the_center` corridas:
  - `doom_foundation_agent__defend_the_center__20260623T025602580980Z`
  - `doom_foundation_agent__defend_the_center__20260625T025825622091Z`
- `defend_the_center` checkpoint promovido oficial:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- `defend_the_center` metricas oficiales del checkpoint promovido:
  - `mean_reward = 9.90`
  - `std_reward = 1.38`
  - `mean_episode_length = 634.12`
- `health_gathering` corridas:
  - `doom_foundation_agent__health_gathering__20260625T113629214351Z`
  - `doom_foundation_agent__health_gathering__20260626T014540629370Z`
- `health_gathering` checkpoint promovido oficial:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- `health_gathering` metricas oficiales del checkpoint promovido:
  - `mean_reward = 1580.28`
  - `std_reward = 736.36`
  - `mean_episode_length = 1581.04`
- `take_cover` corridas:
  - `doom_foundation_agent__take_cover__20260630T011932555138Z`
  - `doom_foundation_agent__take_cover__20260703T140745071243Z`
- `take_cover` checkpoint promovido oficial:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__take_cover_promoted.zip`
- `take_cover` metricas oficiales del checkpoint promovido:
  - `mean_reward = 331.90`
  - `std_reward = 178.23`
  - `mean_episode_length = 331.90`

## Fase 3: Expansion especializada

Escenarios:
1. `basic_audio`
2. `defend_the_line`
3. `basic_notifications`
4. `my_way_home`
5. `predict_position`
6. `health_gathering_supreme`

Estado:
- en progreso

Resultado actual:
- piloto inicial completado y validado offline
- tramo adicional de mejora completado y validado offline
- `defend_the_line` corridas:
  - `doom_foundation_agent__defend_the_line__20260703T195759636148Z`
  - `doom_foundation_agent__defend_the_line__20260703T231100240178Z`
- `defend_the_line` checkpoint promovido oficial:
  - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_line_promoted.zip`
- `defend_the_line` metricas oficiales del checkpoint promovido:
  - `mean_reward = 27.06`
  - `std_reward = 7.43`
  - `mean_episode_length = 1026.78`

## Fase 4: Escenarios avanzados

Escenarios:
1. `deadly_corridor`
2. `deathmatch`

Estado:
- pendiente

## Seguimiento

### Hecho

- modelo renombrado conceptualmente a `foundation`
- arquitectura de config separada en `base.toml` + `configs/scenarios/*.toml`
- `basic` dejado como escenario activo inicial
- arquitectura de persistencia remota base validada con `Neon + S3`

### En progreso

- `basic` consolidado como baseline oficial
- consolidacion de storage/handoff multi-PC
- alineacion final de documentacion, promotion y criterio de continuidad
- preparacion del siguiente escenario de Fase 3

### Siguiente

1. congelar `defend_the_line` como referencia oficial mejorada de Fase 3
2. abrir `basic_audio` como siguiente escenario exacto
3. crear config, assets y tests minimos de `basic_audio`
4. mantener `defend_the_center`, `health_gathering`, `take_cover` y `defend_the_line` congelados como referencias oficiales hasta nuevo aviso
