# Scenario registry

Este documento centraliza el estado operativo de escenarios dentro del proyecto.

| Escenario | Fase | Estado | Config | Tests minimos | Rol principal | Notas |
|---|---|---|---|---|---|---|
| `basic` | Fase 1 | Activo | [basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1) | Si | combate base y validacion del pipeline | escenario inicial de `foundation` |
| `defend_the_center` | Fase 2 | Planificado | No creado aun | No | punteria, giro, reaccion | primer candidato tras estabilizar `basic` |
| `health_gathering` | Fase 2 | Planificado | No creado aun | No | navegacion y supervivencia | puede entrar despues de `defend_the_center` |
| `take_cover` | Fase 2 | Planificado | No creado aun | No | evasion y timing defensivo | conviene antes de escenarios muy duros |
| `basic_audio` | Fase 3 | Pendiente | No creado aun | No | percepcion por audio | escenario especializado |
| `defend_the_line` | Fase 3 | Pendiente | No creado aun | No | combate frontal sostenido | complemento de `defend_the_center` |
| `basic_notifications` | Fase 3 | Pendiente | No creado aun | No | seleccion de objetivo | escenario especializado |
| `my_way_home` | Fase 3 | Pendiente | No creado aun | No | navegacion mas compleja | util para generalizacion espacial |
| `predict_position` | Fase 3 | Pendiente | No creado aun | No | precision temporal | escenario especializado |
| `health_gathering_supreme` | Fase 3 | Pendiente | No creado aun | No | supervivencia compleja | version dura de `health_gathering` |
| `deadly_corridor` | Fase 4 | Pendiente | No creado aun | No | integracion de combate y navegacion | muy alta dificultad |
| `deathmatch` | Fase 4 | Pendiente | No creado aun | No | escenario complejo y costoso | dejar al final |

## Convencion de estados

- `Activo`: escenario en trabajo real ahora
- `Planificado`: escenario ya priorizado para fase cercana
- `Pendiente`: escenario reconocido pero no preparado todavia
- `Pausado`: escenario deliberadamente postergado
- `Descartado`: no entra al plan actual

## Regla de actualizacion

Cuando un escenario cambie:

1. actualiza su `Estado`
2. agrega o corrige su columna `Config`
3. marca si ya tiene tests minimos
4. agrega nota si su prioridad cambia
