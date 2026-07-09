# Plan de escenarios

Documento consolidado del roadmap de curriculum y del registro operativo por escenario.

Modelo objetivo: `foundation`

## Estado actual

- fase actual de entrenamiento: `Fase 3`
- ultimo escenario fuerte cerrado: `defend_the_line`
- escenarios especializados ya integrados: `basic_audio`, `basic_notifications`
- siguiente escenario exacto recomendado: `my_way_home`
- motivo del siguiente paso: avanzar curriculum sin seguir gastando tiempo en escenarios sensoriales que ya quedaron solo provisionales

## Regla general

Solo se avanza a siguiente tramo cuando:

- checkpoint oficial esta evaluado offline
- reportes y artifacts quedaron sincronizados
- accion dominante es coherente o al menos entendible para el escenario
- documentacion del cierre ya quedo actualizada

## Registro operativo

| Escenario | Fase | Estado | Config | Tests minimos | Rol principal | Nota |
|---|---|---|---|---|---|---|
| `basic` | Fase 1 | Baseline oficial cerrada | [basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1) | Si | combate base y validacion del pipeline | baseline oficial fuerte |
| `defend_the_center` | Fase 2 | Cerrado oficial | [defend_the_center.toml](/E:/agente-doom/configs/scenarios/defend_the_center.toml:1) | Si | punteria, giro, reaccion | referencia fuerte |
| `health_gathering` | Fase 2 | Cerrado oficial | [health_gathering.toml](/E:/agente-doom/configs/scenarios/health_gathering.toml:1) | Si | navegacion y supervivencia | referencia fuerte |
| `take_cover` | Fase 2 | Cerrado oficial | [take_cover.toml](/E:/agente-doom/configs/scenarios/take_cover.toml:1) | Si | evasion y timing defensivo | referencia fuerte |
| `defend_the_line` | Fase 3 | Cerrado oficial | [defend_the_line.toml](/E:/agente-doom/configs/scenarios/defend_the_line.toml:1) | Si | combate frontal sostenido | mejor cierre estable de Fase 3 hasta ahora |
| `basic_audio` | Fase 3 | Cerrado provisional | [basic_audio.toml](/E:/agente-doom/configs/scenarios/basic_audio.toml:1) | Si | percepcion por audio | promovido, pero con varianza alta |
| `basic_notifications` | Fase 3 | Cerrado provisional | [basic_notifications.toml](/E:/agente-doom/configs/scenarios/basic_notifications.toml:1) | Si | seleccion de objetivo por notificacion | promovido, pero con sesgo fuerte |
| `my_way_home` | Fase 3 | Siguiente exacto | No creado aun | No | navegacion espacial | mejor siguiente paso del curriculum |
| `predict_position` | Fase 3 | Pendiente | No creado aun | No | precision temporal | candidato despues de `my_way_home` |
| `health_gathering_supreme` | Fase 3 | Pendiente | No creado aun | No | supervivencia compleja | version dura de `health_gathering` |
| `deadly_corridor` | Fase 4 | Pendiente | No creado aun | No | integracion de combate y navegacion | muy alta dificultad |
| `deathmatch` | Fase 4 | Pendiente | No creado aun | No | escenario complejo y costoso | dejar al final |

## Fase 1

Escenarios:
1. `basic`

Estado:
- cerrada

Resultado oficial:
- `mean_reward = -11.84`
- `std_reward = 11.26`
- `mean_episode_length = 13.84`

## Fase 2

Escenarios:
1. `defend_the_center`
2. `health_gathering`
3. `take_cover`

Estado:
- cerrada

Resultados oficiales:

- `defend_the_center`
  - `mean_reward = 9.90`
  - `std_reward = 1.38`
  - `mean_episode_length = 634.12`
- `health_gathering`
  - `mean_reward = 1580.28`
  - `std_reward = 736.36`
  - `mean_episode_length = 1581.04`
- `take_cover`
  - `mean_reward = 331.90`
  - `std_reward = 178.23`
  - `mean_episode_length = 331.90`

## Fase 3

Escenarios ya trabajados:
1. `defend_the_line`
2. `basic_audio`
3. `basic_notifications`

Estado:
- en progreso

Resultados:

- `defend_the_line`
  - estado: oficial fuerte
  - `mean_reward = 27.06`
  - `std_reward = 7.43`
  - `mean_episode_length = 1026.78`
- `basic_audio`
  - estado: provisional mejorado
  - `mean_reward = -64.84`
  - `std_reward = 111.19`
  - `mean_episode_length = 66.48`
- `basic_notifications`
  - estado: provisional
  - `mean_reward = -73.60`
  - `std_reward = 120.65`
  - `mean_episode_length = 75.16`

Lectura:

- `defend_the_line` ya no necesita mas trabajo ahora
- `basic_audio` y `basic_notifications` se pueden reabrir en el futuro, pero hoy no son mejor uso del tiempo
- siguiente avance sano del curriculum: `my_way_home`

## Fase 4

Escenarios:
1. `deadly_corridor`
2. `deathmatch`

Estado:
- pendiente

## Seguimiento

### Hecho

- baseline `basic` consolidado
- expansion generalista de Fase 2 consolidada
- `defend_the_line` consolidado como referencia oficial de Fase 3
- escenarios sensoriales `basic_audio` y `basic_notifications` integrados, entrenados y promovidos provisionalmente

### En progreso

- preparacion del siguiente escenario de Fase 3
- alineacion documental para handoff a otra IA o a otra PC

### Siguiente

1. integrar `my_way_home` en `configs/scenarios/` y `data/scenarios/`
2. agregar tests minimos del preset de navegacion
3. definir si arranca desde cero o por transferencia segun compatibilidad de action space
4. correr piloto inicial de `300000` steps
5. evaluar `best_model.zip` y `final_model.zip` offline con `50` episodios
