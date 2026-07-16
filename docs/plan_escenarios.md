# Plan de escenarios

Documento consolidado del roadmap de curriculum y del registro operativo por escenario.

Modelo objetivo: `foundation`

## Estado actual

- fase actual de entrenamiento: `Fase 4`
- ultimo escenario fuerte cerrado: `deadly_corridor`
- escenarios especializados ya integrados: `basic_audio`, `basic_notifications`
- siguiente escenario exacto recomendado: ninguno, curriculum cerrado (2026-07-14)
- motivo del cierre: 9 escenarios oficiales de ViZDoom cerrados (7 fuerte + 2 provisional); `my_way_home` y `predict_position` pendientes definitivos por razones tecnicas documentadas; `deathmatch` descartado explicitamente por complejidad de action space (16 botones binarios + 3 delta) y alto riesgo de repetir el patron de `my_way_home` (multiples intentos sin cierre); foco pasa a consolidacion/reentrenamiento
- **bug critico corregido (2026-07-14)**: `promote_checkpoint` sin `scenario_name` explicito nombraba el alias promovido segun perfil default (`basic`) en vez del escenario real del checkpoint origen; sobrescribio momentaneamente el promoted de `basic`. Ver `docs/estado_actual.md` para el detalle del incidente. Fix: `promoted_checkpoint_stem` ahora se deriva de la metadata del checkpoint origen, no del perfil por parametro. Leccion operativa: pasar siempre `SCENARIO=` explicito en `make promote` hasta ganar mas confianza en el fix

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
| `my_way_home` | Fase 3 | Pendiente definitivo (tres intentos) | [my_way_home.toml](/E:/agente-doom/configs/scenarios/my_way_home.toml:1) | Si | navegacion espacial | reward shaping por exploracion (constante y con decaimiento) no mejoro la tasa real de exito; requiere presupuesto mucho mayor o curiosity real |
| `predict_position` | Fase 3 | Pendiente indefinido (bloqueo tecnico) | [predict_position.toml](/E:/agente-doom/configs/scenarios/predict_position.toml:1) | Si | precision temporal | ViZDoom no expone posicion del objetivo movil; reward shaping inviable sin modificar WAD/ACS, fuera de alcance |
| `health_gathering_supreme` | Fase 3 | Cerrado oficial | [health_gathering_supreme.toml](/E:/agente-doom/configs/scenarios/health_gathering_supreme.toml:1) | Si | supervivencia compleja | transfer learning desde `health_gathering`; `mean_reward=416.02`, `std=85.45`; cierre solido para layout dificil |
| `deadly_corridor` | Fase 4 | Cerrado oficial | [deadly_corridor.toml](/E:/agente-doom/configs/scenarios/deadly_corridor.toml:1) | Si | integracion de combate y navegacion | preset nuevo `corridor_combat` (7 botones); `doom_skill=5`, muy alta dificultad; from-scratch, sin transfer learning posible; `mean_reward=43.62`, `std=16.62`, reward denso y positivo, sin colapso |
| `deathmatch` | Fase 4 | Descartado (2026-07-14) | No creado aun | No | escenario complejo y costoso | curriculum cerrado, no se integra |

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
4. `my_way_home` (piloto, fallido)
5. `predict_position` (piloto, fallido)
6. `health_gathering_supreme` (piloto, cerrado oficial)

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
- `my_way_home`
  - estado: pendiente definitivo, no promovido, cinco intentos en total
  - intento 1 (run_id `doom_foundation_agent__my_way_home__20260713T125239487614Z`, from-scratch, `ent_coef=0.01`):
    - best model (step 100000): `mean_reward = -0.186`, `std_reward = 0.166`
    - final model (step 300000): `mean_reward = -0.210`, `std_reward = 0.0` (colapso total, nunca alcanzo la meta)
  - intento 2 (run_id `doom_foundation_agent__my_way_home__20260713T165146392158Z`, resume desde best + `ent_coef=0.03`, 200k steps adicionales):
    - final model (step 300704 acumulado): `mean_reward = -0.186`, `std_reward = 0.169` (igualo el techo del intento 1, no lo supero)
  - intento 3 (run_id `doom_foundation_agent__my_way_home__20260714T102740939077Z`, from-scratch, bonus de exploracion constante `exploration_bonus=0.02`):
    - best model (step 50000): `mean_reward = -0.106`, `std_reward = 0.196`, `mean_episode_length = 2063.1`
    - final model (step 300000): `mean_reward = -0.149`, `std_reward = 0.062`, `mean_episode_length = 2100.0` (0% exito)
  - intento 4 (run_id `doom_foundation_agent__my_way_home__20260714T135745889554Z`, from-scratch, bonus con decaimiento lineal a 150000 steps):
    - best model (step 75000): `mean_reward = -0.147`, `std_reward = 0.170`, `mean_episode_length = 2058.58`
    - final model (step 300000): `mean_reward = -0.175`, `std_reward = 0.025`, `mean_episode_length = 2100.0` (0% exito)
  - causa: reward disperso, sin señal de progreso consistente; ni `ent_coef` alto, ni bonus de exploracion constante, ni con decaimiento lineal rompieron el techo. Los `mean_episode_length` del best model son practicamente identicos entre los cuatro intentos entrenados (~2060-2063), evidencia de que ninguna variante cambio la tasa real de exito
  - decision: no invertir mas tiempo; escenario queda pendiente definitivo. Codigo de reward shaping por exploracion queda disponible y testeado para otros escenarios, pero se revirtio la config de `my_way_home` a default. Solucionarlo de verdad requeriria presupuesto de timesteps mucho mayor (2-5M+ steps, literatura curiosity-driven) o motivacion intrinseca real tipo ICM, no solo conteo de celdas
- `predict_position`
  - estado: pendiente, no promovido, un intento completo hasta el presupuesto original
  - run_id principal: `doom_foundation_agent__predict_position__20260714T062711396598Z` (cierre de la corrida, acumulado real `301480` steps repartido en 4 corridas por interrupciones de infraestructura)
  - eval offline 50 episodios: best model `mean_reward = -0.300`, `std_reward = 0.0`; final model `mean_reward = -0.300`, `std_reward = 0.0`
  - eval periodica: 12+ checkpoints distintos a lo largo de todo el entrenamiento, siempre exactamente `-0.300` (equivalente a `living_reward x episode_timeout`, `-0.001 x 300`), episodio siempre al timeout completo, cero impactos al objetivo en ningun punto
  - causa: reward binario disperso (unica señal positiva es impactar el objetivo movil, nunca ocurrio); mismo patron de fondo que `my_way_home`
  - incidentes de infraestructura durante esta corrida (no relacionados a la config): crash por framebuffer de ViZDoom, y crash repetido por bloqueo de Windows Defender sobre el checkpoint `_active.zip` (resuelto con exclusion de Defender sobre `artifacts/`)
  - decision: no invertir mas tiempo ahora; escenario queda pendiente, requiere reward shaping (bonus por acercarse al objetivo o señal de distancia angular) para tener otra oportunidad real
- `health_gathering_supreme`
  - estado: cerrado oficial, primer piloto exitoso
  - run_id: `doom_foundation_agent__health_gathering_supreme__20260714T071306043795Z`
  - estrategia: transfer learning desde checkpoint promovido de `health_gathering` (2300000 steps heredados, `ALLOW_SCENARIO_RESUME=1`), `301056` steps adicionales
  - eval periodica (12 checkpoints): rango `372.4` a `550.8` de mean_reward, sin colapso, reward denso y positivo en todo momento
  - eval offline 50 episodios (unico checkpoint: `final_model.zip`, nunca se guardo un `best_model` propio porque el tracker heredo el umbral `1580.28` de `health_gathering` y ninguna eval de esta corrida lo supero): `mean_reward = 416.02`, `std_reward = 85.45`, `mean_episode_length = 418.02`
  - decision: promovido. Es primer cierre del escenario (no hay checkpoint previo que superar); resultado solido y consistente para un layout mas dificil que `health_gathering`
  - nota tecnica: accion dominante `TURN_RIGHT+MOVE_FORWARD` con sesgo hasta `62%` en algunos checkpoints, sin llegar a colapso de politica

Lectura:

- `defend_the_line` ya no necesita mas trabajo ahora
- `basic_audio` y `basic_notifications` se pueden reabrir en el futuro, pero hoy no son mejor uso del tiempo
- `my_way_home` y `predict_position` quedan pendientes
- `health_gathering_supreme` cerro fuerte via transfer learning; confirma que la estrategia de reusar checkpoints compatibles funciona bien cuando el action space es identico

## Fase 4

Escenarios:
1. `deadly_corridor`
2. `deathmatch`

Estado:
- cerrado: `deadly_corridor` integrado, entrenado from-scratch y promovido oficial
- `deathmatch` descartado (2026-07-14): decision explicita de no integrar, curriculum cerrado

## Seguimiento

### Hecho

- baseline `basic` consolidado
- expansion generalista de Fase 2 consolidada
- `defend_the_line` consolidado como referencia oficial de Fase 3
- escenarios sensoriales `basic_audio` y `basic_notifications` integrados, entrenados y promovidos provisionalmente
- `health_gathering_supreme` integrado, entrenado via transfer learning y promovido como referencia oficial
- reward shaping por exploracion probado a fondo en `my_way_home` (bonus constante y con decaimiento); no funciono, escenario queda pendiente definitivo, config revertida a default
- `deadly_corridor` integrado: preset nuevo `corridor_combat`, config, tests, `make check` en `105` tests
- `deadly_corridor` entrenado from-scratch, evaluado y promovido oficial (`mean_reward=43.62`, `std=16.62`)
- bug critico en `promote_checkpoint` detectado y corregido (naming del alias promovido dependia del perfil default en vez del checkpoint origen); regresion agregada en `tests/services/test_promoter.py`

- curriculum cerrado (2026-07-14): decision explicita de no integrar `deathmatch`

### En progreso

- alineacion documental para handoff a otra IA o a otra PC
- foco pasa a consolidacion/reentrenamiento, no escenarios nuevos

### Siguiente

1. curriculum cerrado, no hay escenario nuevo pendiente; `deathmatch` descartado
2. `my_way_home` y `predict_position` quedan pendientes definitivos; no bloquean nada
3. pasar siempre `SCENARIO=` explicito en `make promote` hasta ganar mas confianza en el fix del bug critico

## Post-curriculum (cerrado, 2026-07-15/16)

`basic_audio` y `basic_notifications` ya se reabrieron post-curriculum, dos veces:

1. **Intento 1** (misma config, +301k steps c/u): ambos empeoraron. Confirmo que mas steps solos no alcanza.
2. **Intento 2** (fix real de arquitectura): se encontro un bug real — el buffer auxiliar (audio PCM crudo / texto de notificacion) se codificaba como canal de imagen falso via `cv2.resize`, destruyendo la señal. Fix: `Dict` observation space (`image`+`features`) + `DoomMultiModalFeatureExtractor` + `MultiInputLstmPolicy` (ver `src/doom_agent/envs/doom_env.py`, `src/doom_agent/models/recurrent_ppo.py`). Retrain from-scratch con arquitectura correcta (`explained_variance` 0.9-0.99): tampoco supero el baseline (`basic_audio` mejor resultado formal `-73.04` vs `-64.84`; `basic_notifications` `-110.84` vs `-73.60`).

**Conclusion:** la varianza intrinseca de ambos escenarios (`std_reward` 90-145 con 50 episodios) es demasiado grande para que cualquier mejora de politica se refleje en el eval. Quedan cerrados provisional tal cual, sin mas reaperturas previstas — mismo estado que `my_way_home`/`predict_position`: pendientes definitivos, no por falta de esfuerzo.

`defend_the_line` sigue como cierre fuerte estable, sin necesidad de reentrenamiento.

No hay una fase posterior al curriculum documentada mas alla de esto — el alcance del proyecto es entrenar el modelo `foundation` por escenario y mantener storage sincronizado, no hay plan de despliegue o integracion a partida completa.

## Niveles completos de Doom original — investigado y descartado (2026-07-16)

La documentacion oficial de ViZDoom (`environments/original_doom_levels/`) si define un paso natural mas alla de los 9 escenarios default: entrenar sobre niveles completos originales (`E1M1`, `MAP01`, etc.), usando `doom.cfg`/`doom2.cfg` o `freedoom1.cfg`/`freedoom2.cfg` (el proyecto ya usa `freedoom2.wad`, sin costo adicional).

Investigado a fondo, descartado por alto riesgo:

- action space de 13 botones (movimiento, giro, `ATTACK`, `SPEED`, `STRAFE`, `USE`, 7 armas + next/prev) — requeriria `MultiDiscrete`, no el sistema de combos actual
- reward por defecto disperso total (`1` al terminar el nivel, `0` el resto); ViZDoom expone shaping nativo mas rico (`set_kill_reward`, `set_item_reward`, `set_secret_reward`, etc.) pero igual exige diseño nuevo
- HUD completo + automap + audio por defecto, mapas grandes con puertas/switches/secretos, sin manejo nativo de campana multi-nivel

**Motivo del descarte:** es la misma categoria de problema que ya fallo 5 veces en `my_way_home` (reward disperso + navegacion de mapa) pero mas dificil aun (accion mas grande, mapa mas grande, mas mecanicas). Mismo razonamiento que llevo a descartar `deathmatch`. No es un escenario mas del curriculum, es un proyecto de investigacion nuevo (probablemente necesitaria curiosity/ICM real). Decision explicita del usuario: no perseguir.
