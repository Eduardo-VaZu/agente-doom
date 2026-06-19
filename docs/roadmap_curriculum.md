# Roadmap de curriculum

Modelo objetivo: `foundation`

Este documento no lista todo lo que existe en ViZDoom. Lista el orden practico de trabajo para
entrenar y expandir el modelo de forma progresiva, estable y mantenible.

Referencia de escenarios oficiales: [vizdoom_escenarios_oficiales.md](/E:/agente-doom/docs/vizdoom_escenarios_oficiales.md:1)
Estado vivo: [current_status.md](/E:/agente-doom/docs/current_status.md:1)
Registro de escenarios: [scenario_registry.md](/E:/agente-doom/docs/scenario_registry.md:1)
Bitacora de pruebas: [experiment_log.md](/E:/agente-doom/docs/experiment_log.md:1)

## Estado actual

- modelo actual: `foundation`
- escenario activo actual: `basic`
- fase actual de entrenamiento: `Fase 1`
- fase actual de storage: `Fase 2`
- ultimo objetivo claro: estabilizar pipeline y configuracion base
- infraestructura remota actual:
  - metadata en `Neon`
  - artefactos en `AWS S3`

## Regla general

Solo se avanza a la siguiente fase cuando:

- entrenamiento actual es estable
- reward deja de subir de forma significativa o converge de forma razonable
- action usage es coherente con el escenario
- checkpoint final y mejor checkpoint se guardan bien
- evaluacion es reproducible
- configuracion del escenario queda documentada

## Fase 1: Nucleo base

Objetivo:
- estabilizar entrenamiento
- validar pipeline completo
- aprender control minimo de combate 3D

Escenarios:
1. `basic`

Por que:
- dificultad baja
- espacio de acciones reducido
- ideal para tuning inicial de hiperparametros y reward shaping

Entregables:
- `configs/scenarios/basic.toml` estable
- checkpoint base funcional de `foundation`
- reporte de comportamiento del entrenamiento
- criterio claro para saber cuando `basic` esta suficientemente bien

Estado:
- en progreso

Bloqueos de salida actuales:

- falta corrida larga limpia de `basic`
- falta criterio numerico de salida de `basic`
- falta registrar resultado empirico final post-limpieza

## Fase 2: Expansion generalista

Objetivo:
- agregar habilidades centrales sin saltar todavia a escenarios extremadamente duros

Escenarios:
1. `defend_the_center`
2. `health_gathering`
3. `take_cover`

Por que:
- `defend_the_center` refuerza punteria, giro y reaccion
- `health_gathering` introduce navegacion y supervivencia
- `take_cover` introduce evasion y timing defensivo

Entregables:
- un archivo TOML por escenario en `configs/scenarios/`
- pruebas minimas por escenario
- decision de si cada escenario entra como nueva etapa secuencial del mismo modelo

Estado:
- pendiente

## Fase 3: Expansion especializada

Objetivo:
- agregar escenarios que desarrollan capacidades mas especificas o mas ricas, pero todavia no son
  el techo maximo de dificultad

Escenarios:
1. `basic_audio`
2. `defend_the_line`
3. `basic_notifications`
4. `my_way_home`
5. `predict_position`
6. `health_gathering_supreme`

Por que:
- aportan percepcion, navegacion, precision temporal y variantes mas complejas
- son utiles para hacer al modelo menos especializado en un solo patron simple

Entregables:
- decidir para cada escenario si entra al curriculum principal o si queda como fase opcional
- documentar impacto de cada escenario sobre el modelo base

Estado:
- pendiente

## Fase 4: Escenarios avanzados

Objetivo:
- llevar `foundation` a escenarios de alta dificultad o gran complejidad operacional

Escenarios:
1. `deadly_corridor`
2. `deathmatch`

Por que:
- `deadly_corridor` combina navegacion, supervivencia y combate bajo mucha presion
- `deathmatch` es escenario muy costoso y complejo; no conviene temprano

Entregables:
- estrategia clara para evitar olvido catastrofico
- criterio de exito y criterio de rollback si rendimiento cae demasiado

Estado:
- pendiente

## Seguimiento de trabajo

### Hecho

- modelo renombrado conceptualmente a `foundation`
- arquitectura de config separada en `base.toml` + `configs/scenarios/*.toml`
- `basic` dejado como escenario activo inicial
- arquitectura de persistencia remota base validada con `Neon + S3`

### En progreso

- afinado de `basic`
- consolidacion de pruebas y estructura del proyecto
- validacion de primera corrida larga limpia tras limpieza de artefactos de prueba

### Siguiente

1. estabilizar completamente `basic`
2. documentar criterio de salida de `basic`
3. agregar `defend_the_center`
4. decidir si `health_gathering` o `take_cover` entra despues

## Como actualizar este documento

Cuando una fase cambie:

1. mueve items entre `Hecho`, `En progreso` y `Siguiente`
2. actualiza `fase actual`
3. documenta si un escenario entra, se posterga o se descarta
4. anota si el modelo mejoro, empeoro o sufrio olvido
