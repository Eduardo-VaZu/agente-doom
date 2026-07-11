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
| `my_way_home` | Fase 3 | Preparado para piloto | [my_way_home.toml](/E:/agente-doom/configs/scenarios/my_way_home.toml:1) | Si | navegacion espacial | siguiente escenario exacto ya integrado |
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
- siguiente avance sano del curriculum: correr primer piloto de `my_way_home`

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

1. decidir si `my_way_home` arranca desde cero o por transferencia segun compatibilidad de action space
2. correr piloto inicial de `300000` steps
3. evaluar `best_model.zip` y `final_model.zip` offline con `50` episodios
4. promover solo si resultado offline lo justifica

## Post-curriculum

Cuando termine el bloque actual de escenarios pendientes, el orden recomendado de reentrenamiento es:

1. `basic_audio`
2. `basic_notifications`
3. `my_way_home`, solo si no cierra fuerte en su primer ciclo
4. `defend_the_line`, solo si se necesita una version mas fuerte

Objetivo de esas reaperturas:

- convertir escenarios provisionales en referencias oficiales fuertes
- probar una `v2` de configuracion sin tocar checkpoints ya promovidos
- medir si la mejora viene de hyperparams o si ya hace falta cambiar representacion/arquitectura

Criterio para considerar una `v2` exitosa:

- supera checkpoint promovido vigente en evaluacion offline de `50` episodios
- reduce sesgo de acciones dominante
- no se degrada tanto entre `best_model.zip` y `final_model.zip`
- deja una narrativa mas fuerte para presentacion y cierre del proyecto
