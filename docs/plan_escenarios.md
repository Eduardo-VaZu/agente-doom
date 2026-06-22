# Plan de escenarios

Documento consolidado del roadmap de curriculum y del registro operativo por escenario.

Modelo objetivo: `foundation`

## Estado actual

- escenario activo actual: `basic`
- fase actual de entrenamiento: `Fase 1`
- fase actual de storage: `Fase 2`
- ultimo objetivo claro: cerrar baseline reproducible de `basic` y dejar flujo operativo estable

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
| `basic` | Fase 1 | Activo | [basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1) | Si | combate base y validacion del pipeline | baseline inicial de `foundation` |
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

## Fase 1: Nucleo base

Objetivo:
- estabilizar entrenamiento
- validar pipeline completo
- aprender control minimo de combate 3D

Escenarios:
1. `basic`

Estado:
- en progreso

Bloqueos de salida actuales:

- falta cerrar criterio oficial de promotion y salida para `basic`
- falta consolidar documentacion final del baseline y del handoff multi-PC
- falta decidir si `basic` ya se congela como baseline oficial o si se avanza al siguiente escenario

## Fase 2: Expansion generalista

Escenarios:
1. `defend_the_center`
2. `health_gathering`
3. `take_cover`

Estado:
- pendiente

## Fase 3: Expansion especializada

Escenarios:
1. `basic_audio`
2. `defend_the_line`
3. `basic_notifications`
4. `my_way_home`
5. `predict_position`
6. `health_gathering_supreme`

Estado:
- pendiente

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

- consolidacion de `basic` como baseline operable
- consolidacion de storage/handoff multi-PC
- alineacion final de documentacion, promotion y criterio de continuidad

### Siguiente

1. cerrar decision oficial sobre `basic` baseline
2. documentar criterio de salida y promotion de `basic`
3. agregar `defend_the_center`
4. decidir si `health_gathering` o `take_cover` entra despues
