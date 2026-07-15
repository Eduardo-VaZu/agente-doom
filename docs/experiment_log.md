# Experiment log

Bitacora cronologica de decisiones y resultados.

## Formato recomendado

Cada entrada debe incluir:

- fecha
- escenario
- fase
- cambio realizado
- comando ejecutado
- resultado observado
- decision siguiente

## Entradas

### 2026-07-14 (piloto deadly_corridor, cierre oficial + bug critico en promote-checkpoint)

- escenario: `deadly_corridor` (y `basic`, afectado por el incidente)
- fase entrenamiento: `Fase 4`
- fase storage: `Fase 2`
- cambio realizado:
  - piloto `from-scratch`, `SEED=42`, `TIMESTEPS=300000`, run_id `doom_foundation_agent__deadly_corridor__20260714T175934084462Z`
  - eval periodica (12 checkpoints): reward siempre positivo, rango `36.5` a `49.5`, sin colapso de acciones (mezcla sana de `MOVE_FORWARD`, `MOVE_FORWARD+ATTACK`, `ATTACK`, giros, strafes); mejor eval en step `75000`, nunca superado despues (politica determinista se satura temprano, pesos siguen cambiando pero `argmax` deja de cambiar)
  - eval offline 50 episodios: best (step 75000) y final (step 300000) dan resultados **identicos** (`mean_reward=43.623`, `std=16.615`, `mean_episode_length=56.06`); confirmado con `md5sum` que son archivos genuinamente distintos, la politica determinista simplemente convergio a las mismas decisiones desde step 75000 en adelante
  - **incidente critico**: `make promote CHECKPOINT=artifacts\checkpoints\doom_foundation_agent__deadly_corridor_best.zip PROMOTE_EPISODES=50` (sin `SCENARIO=` explicito) **sobrescribio el checkpoint promovido oficial de `basic`** (`doom_foundation_agent_promoted.zip`), el baseline congelado del proyecto
  - causa raiz: `src/doom_agent/services/promoter.py` resolvia el nombre del alias promovido usando `get_training_profile(profile_name, scenario_name=scenario_name)` con `scenario_name=None` (porque `--scenario` no se paso), lo que caia al escenario default (`basic`) en vez de usar el escenario real del checkpoint que se estaba promoviendo
  - verificado que la perdida era recuperable: `doom_foundation_agent_active.zip` (alias `active`, distinto del `promoted` dañado) seguia intacto con los pesos correctos de `basic` (`scenario_key=basic`, `saved_timesteps=1501184`)
  - recuperacion: `make promote CHECKPOINT=artifacts\checkpoints\doom_foundation_agent_active.zip SCENARIO=basic PROMOTE_EPISODES=50` reconstruyo `doom_foundation_agent_promoted.zip` con resultado identico al documentado historicamente (`mean_reward=-11.840`, `std=11.256`, `mean_episode_length=13.840`)
  - fix aplicado en `src/doom_agent/services/promoter.py`: se elimino la dependencia de `get_training_profile`/`target_profile` para nombrar el alias promovido; ahora se deriva directamente de `source_metadata["profile"]["checkpoint_name"]` (metadata embebida en el checkpoint que se esta promoviendo), correcto sin importar si se invoca con `--checkpoint` explicito o `--scenario`
  - agregado test de regresion `test_promote_checkpoint_uses_source_scenario_name_not_default_when_scenario_omitted` en `tests/services/test_promoter.py`, reproduce exactamente el trigger del bug (checkpoint explicito de un escenario no-default, sin pasar `scenario_name`) y verifica que el alias promovido usa el nombre correcto
  - re-promovido `deadly_corridor` con el fix aplicado: `doom_foundation_agent__deadly_corridor_promoted.zip` creado correctamente esta vez
- comando ejecutado:
  - `make train-from-scratch SCENARIO=deadly_corridor SEED=42 TIMESTEPS=300000`
  - `make evaluate SCENARIO=deadly_corridor EPISODES=50 NO_RENDER=1 JSON=1` / `python src/cli.py evaluate ... final_model.zip`
  - `md5sum` para confirmar que best/final eran archivos distintos pese a resultados identicos
  - `make promote CHECKPOINT=...deadly_corridor_best.zip PROMOTE_EPISODES=50` (disparo del bug)
  - inspeccion de `doom_foundation_agent_promoted.json`, `doom_foundation_agent_active.json`, `doom_foundation_agent_best.json`, `doom_foundation_agent.json` para confirmar recuperabilidad
  - `make promote CHECKPOINT=...doom_foundation_agent_active.zip SCENARIO=basic PROMOTE_EPISODES=50` (recuperacion de `basic`)
  - `make check` (validacion del fix, `106` tests)
  - `make promote CHECKPOINT=...deadly_corridor_best.zip SCENARIO=deadly_corridor PROMOTE_EPISODES=50` (re-promocion correcta de `deadly_corridor`)
- resultado observado:
  - `basic` recuperado exacto, sin perdida de datos real (solo el alias se dañaba, los pesos originales en `_active.zip` nunca se tocaron)
  - `deadly_corridor` promovido correctamente como primer cierre oficial: `mean_reward=43.623`, `std=16.615`, `mean_episode_length=56.06`
  - `106` tests pasando (105 previos + 1 regresion)
- decision siguiente:
  - `deadly_corridor` cerrado oficial, primer piloto de un escenario `doom_skill=5` con reward denso y positivo, sin colapso
  - **recomendacion fuerte**: cualquier `make promote CHECKPOINT=...` futuro debe incluir `SCENARIO=<escenario>` explicito hasta confiar plenamente en el fix en produccion real (ya cubierto por test, pero el costo de un error es alto: puede sobrescribir un baseline congelado)
  - decidir si se integra `deathmatch` (ultimo escenario oficial de ViZDoom sin integrar) o se cierra el curriculum aqui

### 2026-07-14 (integracion deadly_corridor, Fase 4)

- escenario: `deadly_corridor`
- fase entrenamiento: `Fase 4`
- fase storage: `Fase 2`
- cambio realizado:
  - copiados `deadly_corridor.cfg` y `deadly_corridor.wad` desde ViZDoom a `data/scenarios/`
  - 7 botones (`MOVE_LEFT`, `MOVE_RIGHT`, `ATTACK`, `MOVE_FORWARD`, `MOVE_BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`); ningun preset existente los cubria, se creo preset nuevo `corridor_combat` en `src/doom_agent/envs/doom_env.py` (8 acciones: ATTACK, MOVE_FORWARD, MOVE_FORWARD+ATTACK, MOVE_BACKWARD, TURN_LEFT, TURN_RIGHT, MOVE_LEFT, MOVE_RIGHT)
  - agregado `corridor_combat` a la lista de presets validos en `src/doom_agent/config/schema.py`
  - creado `configs/scenarios/deadly_corridor.toml`, mismos hiperparametros estandar del proyecto (`learning_rate=0.0001`, `TIMESTEPS=300000` para primer piloto)
  - agregados tests: `test_corridor_combat_actions_cover_navigation_and_attack`, `test_deadly_corridor_scenario_uses_corridor_combat_profile`, `test_deadly_corridor_preset_matches_available_buttons`
  - actualizada tupla esperada de escenarios en `test_training_catalog_is_loaded_from_split_toml`
  - actualizada documentacion: `vizdoom_escenarios_oficiales.md` (tambien se corrigio que `health_gathering_supreme` no aparecia en la lista de integrados, gap previo), `plan_escenarios.md`, `estado_actual.md`
  - decision con el usuario: `deadly_corridor` elegido sobre `deathmatch` como siguiente paso de Fase 4, por action space mucho mas manejable (7 botones vs 16 binarios + 3 delta de `deathmatch`)
  - sin transfer learning posible: `doom_skill=5` (dificultad alta) y action space nuevo, sin checkpoint previo compatible; primer piloto sera `from-scratch`
- comando ejecutado:
  - `make check` (corrido por el usuario, no por Claude directamente — feedback explicito de que el usuario prefiere correr `make`/CLI el mismo, incluso validaciones rapidas como `make check`)
- resultado observado:
  - `105` tests pasando (102 previos + 3 nuevos)
  - no hizo falta cambiar codigo core de entorno mas alla de agregar el preset; arquitectura de presets ya soportaba agregar uno nuevo sin tocar `DoomEnv`
- decision siguiente:
  - correr piloto inicial: `make train-from-scratch SCENARIO=deadly_corridor SEED=42 TIMESTEPS=300000`
  - evaluar offline con `50` episodios antes de promover
  - `deathmatch` queda como ultimo escenario oficial de ViZDoom sin integrar, decidir despues del piloto de `deadly_corridor`

### 2026-07-14 (my_way_home: cierre definitivo tras intento con decaimiento, revert de config)

- escenario: `my_way_home`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - completado intento 4 (bonus con decaimiento lineal a 150000 steps), run_id `doom_foundation_agent__my_way_home__20260714T135745889554Z`
  - eval offline 50 episodios: best (step 75000) `mean_reward=-0.147`, `std=0.170`, `mean_episode_length=2058.58`; final (step 300000) `mean_reward=-0.175`, `std=0.025`, `mean_episode_length=2100.0` (0% exito)
  - comparacion final entre los tres intentos entrenados (original sin bonus, bonus constante, bonus con decaimiento): los tres `mean_episode_length` del best model son practicamente identicos (2063.1, 2063.1, 2058.58); ninguna variante de reward shaping por exploracion cambio la tasa real de exito de forma medible
  - conclusion: el bonus de exploracion (constante o decaido) no es la palanca correcta para este escenario; causa mas probable es limitacion fundamental de PPO on-policy con meta dispersa en laberinto grande, no densidad de reward
  - revertida `configs/scenarios/my_way_home.toml` a default (`exploration_bonus`, `exploration_grid_size`, `exploration_bonus_decay_steps` removidos, quedan en su default `0.0`/`48.0`/`0` como cualquier otro escenario)
  - actualizados tests que asumian el bonus activo en `my_way_home`: eliminado `test_my_way_home_scenario_enables_exploration_bonus` (ya no aplica), reemplazado `test_my_way_home_environment_tracks_visited_cells_after_reset` por dos tests que verifican el comportamiento con bonus explicitamente habilitado via override de perfil (`test_environment_tracks_visited_cells_after_reset_when_exploration_bonus_enabled`) y con bonus desactivado por default (`test_environment_does_not_track_visited_cells_when_exploration_bonus_disabled`)
- comando ejecutado:
  - `python src/cli.py evaluate --checkpoint .../final_model.zip --scenario my_way_home --episodes 50 --no-render --json` (intento 4, final)
  - `make evaluate SCENARIO=my_way_home EPISODES=50 NO_RENDER=1 JSON=1` (intento 4, best)
  - `make check` (validacion post-revert, `102` tests)
- resultado observado:
  - `102` tests pasando tras arreglar los dos tests desactualizados
  - codigo de reward shaping por exploracion (`bucket_position`, `compute_exploration_bonus`, `decayed_exploration_bonus`) queda disponible, testeado y documentado en memoria del proyecto para uso futuro en otros escenarios de navegacion, aunque no resolvio `my_way_home`
- decision siguiente:
  - `my_way_home` queda pendiente definitivo, mismo tratamiento que `predict_position`
  - no reintentar salvo que se invierta en presupuesto de timesteps mucho mayor (2-5M+) o motivacion intrinseca real (curiosity/ICM)
  - curriculum sigue: decidir entre `deadly_corridor` y `deathmatch` como siguiente escenario

### 2026-07-14 (my_way_home intento 1 con exploration bonus: resultado y ajuste a decaimiento)

- escenario: `my_way_home`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - primer piloto con `exploration_bonus = 0.02` constante (sin decaimiento), `from-scratch`, `SEED=42`, `TIMESTEPS=300000`
  - resultado offline 50 episodios: best (step 50000) `mean_reward=-0.106`, `std=0.196`, `mean_episode_length=2063.1` (algunos episodios llegaron a la meta); final (step 300000) `mean_reward=-0.149`, `std=0.062`, `mean_episode_length=2100.0` (0 de 50 episodios llego a la meta)
  - hallazgo clave: `mean_episode_length` del best (`2063.1`) coincide exactamente con el del intento original sin exploration bonus (piloto de 2026-07-13); la tasa real de exito no mejoro de forma medible pese al bonus
  - diagnostico: el bonus por celda visitada no es "potential-based" (no preserva la politica optima del problema original); permite que la politica aprenda a "cosechar" bonus por explorar en vez de perseguir la meta dispersa. Eval periodica confirma: `mean_episode_length` volvio a `2100.0` exacto en las 10 evaluaciones posteriores al step 50000, sugiriendo que la politica encontro la meta por casualidad temprano y luego derivo hacia comportamiento de "farmear" el bonus
  - decision con el usuario: no promover, ajustar a intento 2 con decaimiento lineal del bonus
  - implementado `decayed_exploration_bonus(base_bonus, elapsed_steps, decay_steps)` en `src/doom_agent/envs/doom_env.py`, nuevo campo de perfil `exploration_bonus_decay_steps` (default `0` = sin decaimiento, compatible con escenarios existentes)
  - `configs/scenarios/my_way_home.toml`: agregado `exploration_bonus_decay_steps = 150000` (decae a cero en la primera mitad del presupuesto de `300000` steps)
  - agregados tests: `test_decayed_exploration_bonus_linearly_reduces_to_zero`, `test_decayed_exploration_bonus_disabled_stays_constant`, `test_my_way_home_scenario_enables_exploration_bonus` actualizado con el nuevo campo
- comando ejecutado:
  - `make train-from-scratch SCENARIO=my_way_home SEED=42 TIMESTEPS=300000` (intento 1, sin decaimiento)
  - `make evaluate SCENARIO=my_way_home EPISODES=50 NO_RENDER=1 JSON=1` (best)
  - `python src/cli.py evaluate --checkpoint .../final_model.zip --scenario my_way_home --episodes 50 --no-render --json` (final)
  - `make check` (validacion del ajuste v2, 102 tests)
  - verificacion manual en runtime real del threading de `exploration_bonus_decay_steps`
- resultado observado:
  - `102` tests pasando
  - intento 1 no promovido; diagnostico de reward hacking documentado
- decision siguiente:
  - lanzar intento 2 (decaimiento lineal): `make train-from-scratch SCENARIO=my_way_home SEED=42 TIMESTEPS=300000`
  - evaluar offline con `50` episodios; comparar `mean_episode_length` contra los `2063.1`/`2100.0` de intentos previos como referencia de exito real
  - si intento 2 tampoco muestra mejora medible en tasa de exito, dejar `my_way_home` pendiente definitivamente (igual que `predict_position`), documentando que reward shaping por exploracion no resuelve este escenario

### 2026-07-14 (reward shaping para my_way_home, cambio de codigo)

- escenario: `my_way_home` (y evaluacion de factibilidad para `predict_position`)
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - investigacion: se listaron las 134 `GameVariable` de ViZDoom; confirmado que `POSITION_X`/`POSITION_Y` del jugador existen y son consultables via `game.get_game_variable(...)` sin necesidad de declararlas en `available_game_variables` del `.cfg` (verificado empiricamente)
  - confirmado que `predict_position` NO tiene forma de acceder a la posicion del objetivo movil (ninguna `GameVariable` la expone); reward shaping por distancia/angulo es inviable sin modificar el WAD/ACS del escenario, fuera de alcance del proyecto; decision con el usuario: `predict_position` queda pendiente indefinido, documentado como bloqueo tecnico, no de esfuerzo
  - implementado bonus de exploracion por celda nueva del mapa para `my_way_home`:
    - `bucket_position(x, y, grid_size)` y `compute_exploration_bonus(cell, visited_cells, bonus)` en `src/doom_agent/envs/doom_env.py`, funciones puras testeables sin dependencia de ViZDoom
    - `DoomEnv` trackea `_visited_cells` por episodio (reset en `reset()`, poblado en `step()` via `_current_cell()`)
    - nuevos campos de perfil `exploration_bonus` (default `0.0`) y `exploration_grid_size` (default `48.0`) en `TrainingProfile`, `TrainingProfilePayload`, validacion, `to_dict`/`from_dict`, y agregados a `resume_compatibility_signature` (cambiar el bonus fuerza from-scratch o `--allow-scenario-resume`)
    - `configs/scenarios/my_way_home.toml`: `exploration_bonus = 0.02`, `exploration_grid_size = 48.0`
    - mecanismo generico y reusable, no exclusivo de `my_way_home`; otros escenarios quedan en `0.0` (desactivado) por defecto, sin cambio de comportamiento
  - agregados tests: `test_bucket_position_groups_nearby_coordinates_into_same_cell`, `test_compute_exploration_bonus_rewards_new_cells_only_once`, `test_my_way_home_environment_tracks_visited_cells_after_reset`, `test_my_way_home_scenario_enables_exploration_bonus`, `test_other_scenarios_default_exploration_bonus_disabled`
- comando ejecutado:
  - `make check`
  - script manual de verificacion en runtime real (100 pasos avanzando en `my_way_home`, confirmando `raw_reward` positivo exactamente al cruzar de celda)
- resultado observado:
  - `100` tests pasando (95 previos + 5 nuevos)
  - verificacion runtime: bonus se dispara correctamente (`raw_reward=0.0199` = `0.02` bonus `- 0.0001` living_reward, en los pasos donde el agente cruza a una celda nueva)
- decision siguiente:
  - correr reintento de `my_way_home` con `make train-from-scratch SCENARIO=my_way_home SEED=42 TIMESTEPS=300000` (config ya actualizada con el bonus)
  - evaluar offline con `50` episodios; promover solo si el agente alcanza la meta de forma consistente
  - `predict_position` permanece pendiente indefinido, sin plan de reintento salvo que aparezcan herramientas de edicion WAD/ACS

### 2026-07-14 (piloto health_gathering_supreme, cierre oficial)

- escenario: `health_gathering_supreme`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - piloto via transfer learning desde checkpoint promovido de `health_gathering` (`mean_reward=1580.28`)
  - resume con `2300000` steps heredados + `301056` steps adicionales (`TIMESTEPS=300000` solicitados)
  - `ALLOW_SCENARIO_RESUME=1` para saltar chequeo estricto (mismo action space, distinto `scenario_name`)
  - sin incidentes de infraestructura esta vez (exclusion de Defender aplicada previamente funciono)
- comando ejecutado:
  - `make train SCENARIO=health_gathering_supreme RESUME=artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip ALLOW_SCENARIO_RESUME=1 TIMESTEPS=300000`
  - `make evaluate SCENARIO=health_gathering_supreme EPISODES=50 NO_RENDER=1 JSON=1`
  - `make promote CHECKPOINT=artifacts\checkpoints\doom_foundation_agent__health_gathering_supreme.zip PROMOTE_EPISODES=50`
- resultado observado:
  - run_id: `doom_foundation_agent__health_gathering_supreme__20260714T071306043795Z`
  - eval periodica (12 checkpoints, steps 2325000 a 2600000): rango `372.4` a `550.8` de mean_reward, siempre positivo, sin colapso
  - `best_mean_reward_so_far` se mantuvo heredado en `1580.28` (umbral de `health_gathering`) durante toda la corrida; ninguna eval lo supero, por eso nunca se guardo un `best_model.zip` propio de este escenario
  - eval offline 50 episodios (sobre `final_model.zip`, unico checkpoint disponible): `mean_reward = 416.02`, `std_reward = 85.45`, `mean_episode_length = 418.02`
  - accion dominante `TURN_RIGHT+MOVE_FORWARD` con sesgo hasta `62%` en algunos checkpoints intermedios, sin llegar a colapso total de politica
  - resultado muy distinto a `my_way_home`/`predict_position`: reward denso (no disperso), agente claramente funcional, solo con techo mas bajo por el layout mas dificil
- decision siguiente:
  - promovido como primer cierre oficial de `health_gathering_supreme` (no habia checkpoint previo que superar)
  - confirma que transfer learning es la estrategia correcta cuando el action space es identico entre escenarios
  - siguiente paso del curriculum: decidir entre `deadly_corridor` y `deathmatch` (unicos escenarios oficiales de ViZDoom que faltan integrar)

### 2026-07-14 (integracion health_gathering_supreme)

- escenario: `health_gathering_supreme`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - copiados `health_gathering_supreme.cfg` y `health_gathering_supreme.wad` desde ViZDoom a `data/scenarios/`
  - creado `configs/scenarios/health_gathering_supreme.toml`, reusa preset `health_navigation` (botones TURN_LEFT, TURN_RIGHT, MOVE_FORWARD, identicos a `health_gathering`)
  - agregado test `test_health_gathering_supreme_scenario_uses_navigation_profile` en `tests/configuration/test_config.py`
  - agregado test `test_health_gathering_supreme_navigation_preset_matches_available_buttons` en `tests/envs/test_environment.py`
  - actualizada tupla esperada de escenarios en `test_training_catalog_is_loaded_from_split_toml`
  - actualizada documentacion: `plan_escenarios.md`, `estado_actual.md`
  - decision con el usuario: piloto via transfer learning desde checkpoint promovido de `health_gathering` (`mean_reward=1580.28`), dado que action space es identico (mismo preset, mismos botones); no from-scratch
- comando ejecutado:
  - `make check`
- resultado observado:
  - `95` tests pasando (93 previos + 2 nuevos)
  - no hizo falta cambiar codigo core; preset `health_navigation` ya cubria el action space
- decision siguiente:
  - lanzar `make train SCENARIO=health_gathering_supreme RESUME=artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip ALLOW_SCENARIO_RESUME=1 TIMESTEPS=300000`
  - evaluar offline con `50` episodios, comparar contra baseline `health_gathering`

### 2026-07-14 (piloto predict_position, resultado)

- escenario: `predict_position`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - primer piloto `from-scratch`, `SEED=42`, `TIMESTEPS=300000`
  - corrida se dividio en 4 tramos por dos incidentes de infraestructura no relacionados a la config:
    1. crash `vizdoom.vizdoom.ViZDoomErrorException: Could not rebuild framebuffer` en step 125001 (probable hiccup de GPU/pantalla)
    2. crash repetido `PermissionError: [WinError 32]` al copiar el checkpoint `_active.zip`, causado por Windows Defender bloqueando el archivo recien escrito; esto ademas rompio el resume automatico dos veces (`RESUME=auto` volvia siempre al checkpoint viejo de step 25000 en vez de continuar)
  - arreglo aplicado: `Add-MpPreference -ExclusionPath "E:\agente-doom\artifacts"` (exclusion de Defender), y resume manual explicito apuntando al checkpoint real mas avanzado en vez de depender del alias `_active` roto
  - acumulado final real: `301480` steps
- comando ejecutado (resumen, ver detalle en conversacion):
  - `make train-from-scratch SCENARIO=predict_position SEED=42 TIMESTEPS=300000`
  - `make train SCENARIO=predict_position RESUME=<checkpoint explicito> TIMESTEPS=...` (varias veces, para sortear el bug de resume)
  - `make evaluate SCENARIO=predict_position EPISODES=50 NO_RENDER=1 JSON=1` (best model)
  - `python src/cli.py evaluate --checkpoint .../final_model.zip --scenario predict_position --episodes 50 --no-render --json` (final model)
- resultado observado:
  - run_id final: `doom_foundation_agent__predict_position__20260714T062711396598Z`
  - best model: `mean_reward = -0.300`, `std_reward = 0.0`, `mean_episode_length = 300.0`
  - final model: `mean_reward = -0.300`, `std_reward = 0.0`, `mean_episode_length = 300.0`
  - `-0.300` es exactamente `living_reward (-0.001) x episode_timeout (300)`: el agente nunca impacto el objetivo movil, en ninguna de las 12+ evaluaciones periodicas a lo largo de todo el entrenamiento ni en los 50 episodios de evaluacion offline final (ambos checkpoints)
  - accion dominante oscilo entre `TURN_LEFT+ATTACK` y `ATTACK` puro sin patron claro de puntería, consistente con politica que nunca aprendio a sincronizar el disparo
  - bug adicional encontrado: columna `resume_mode` en `training_runs` (Postgres) es `VARCHAR(80)`; al usar `--resume` con ruta de checkpoint explicita (mas larga que 80 caracteres) la persistencia remota de esa corrida especifica fallo (`StringDataRightTruncation`); reporte local no se vio afectado
- decision siguiente:
  - no promover ningun checkpoint de este piloto
  - `predict_position` queda en estado "pendiente", mismo tratamiento que `my_way_home`
  - reward binario (solo +1 al impactar, sin señal parcial) es la causa de fondo; timesteps y `ent_coef` no son la palanca correcta
  - si se retoma en el futuro, la mejora candidata es reward shaping (bonus por cercania angular al objetivo), cambio de codigo en `doom_env.py`, no solo config
  - pendiente decidir si se amplia la columna `resume_mode` via migracion Alembic
  - curriculum avanza a `health_gathering_supreme` sin esperar a `predict_position`

### 2026-07-13 (integracion predict_position)

- escenario: `predict_position`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - copiados `predict_position.cfg` y `predict_position.wad` desde ViZDoom a `data/scenarios/`
  - creado `configs/scenarios/predict_position.toml`, reusa preset `turn_combat` (botones TURN_LEFT, TURN_RIGHT, ATTACK, identicos a `defend_the_center`/`defend_the_line`)
  - agregado test `test_predict_position_scenario_uses_turn_combat_profile` en `tests/configuration/test_config.py`
  - agregado test `test_predict_position_turn_preset_matches_available_buttons` en `tests/envs/test_environment.py`
  - actualizada tupla esperada de escenarios en `test_training_catalog_is_loaded_from_split_toml`
  - actualizada documentacion: `vizdoom_escenarios_oficiales.md`, `plan_escenarios.md`, `estado_actual.md`
- comando ejecutado:
  - `make check`
- resultado observado:
  - `93` tests pasando (91 previos + 2 nuevos), sin romper nada existente
  - no hizo falta cambiar codigo core (`doom_env.py`); preset `turn_combat` ya cubria el action space del escenario
- decision siguiente:
  - correr piloto inicial de `predict_position` con `make train-from-scratch SCENARIO=predict_position SEED=42 TIMESTEPS=300000`
  - evaluar offline con `50` episodios antes de promover

### 2026-07-13

- escenario: `my_way_home`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - primer piloto de `my_way_home`, entrenamiento `from-scratch` (action space incompatible con escenarios previos, no habia checkpoint transferible)
  - config: `SEED=42`, `TIMESTEPS=300000`
- comando ejecutado:
  - `make train-from-scratch SCENARIO=my_way_home SEED=42 TIMESTEPS=300000`
  - `make evaluate SCENARIO=my_way_home EPISODES=50 NO_RENDER=1 JSON=1` (best model)
  - `python src/cli.py evaluate --checkpoint .../final_model.zip --scenario my_way_home --episodes 50 --no-render --json` (final model)
- resultado observado:
  - run_id: `doom_foundation_agent__my_way_home__20260713T125239487614Z`
  - best model (step 100000): `mean_reward = -0.186`, `std_reward = 0.166`, `mean_episode_length = 2063.1`
  - final model (step 300000): `mean_reward = -0.210`, `std_reward = 0.0`, `mean_episode_length = 2100.0`
  - `-0.21` es exactamente `living_reward (-0.0001) x episode_timeout (2100)`: el agente nunca alcanzo la meta en ninguno de los 50 episodios de evaluacion del final model
  - reward se mantuvo plano durante todo el entrenamiento (sin curva de aprendizaje visible en TensorBoard, iteraciones 1 a 147)
  - causa probable: reward disperso (unica recompensa positiva es llegar a la meta) combinado con `300000` steps insuficientes para este escenario de navegacion
- decision siguiente:
  - no promover ningun checkpoint de este piloto
  - relanzar `my_way_home` con `TIMESTEPS=1500000` como primer ajuste
  - si vuelve a fallar, subir `ent_coef` en `configs/scenarios/my_way_home.toml` para forzar mas exploracion
  - mantener `my_way_home` en estado "piloto fallido, pendiente de reintento" hasta proximo ciclo

### 2026-07-13 (segundo intento, mismo dia)

- escenario: `my_way_home`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - segundo intento: resume desde `best_model.zip` (step 100000) del piloto anterior
  - `ent_coef` subido de `0.01` a `0.03` para forzar mas exploracion
  - `TIMESTEPS=200000` adicionales (acumulado hasta step 300704)
  - uso de `--allow-scenario-resume` para saltar el chequeo estricto de hiperparametros (ent_coef distinto al checkpoint)
- comando ejecutado:
  - `make train SCENARIO=my_way_home RESUME=artifacts\checkpoints\doom_foundation_agent__my_way_home_best.zip ALLOW_SCENARIO_RESUME=1 TIMESTEPS=200000`
  - `python src/cli.py evaluate --checkpoint .../final_model.zip --scenario my_way_home --episodes 50 --no-render --json`
- resultado observado:
  - run_id: `doom_foundation_agent__my_way_home__20260713T165146392158Z`
  - final model (step 300704): `mean_reward = -0.186`, `std_reward = 0.169`, `mean_episode_length = 2058.58`
  - practicamente identico al best del piloto anterior (`-0.186` vs `-0.186`); no se supero el techo
  - `best_reward_so_far` durante esta corrida se mantuvo congelado en `-0.150` (el mismo del piloto anterior), nunca broto un nuevo best
  - eval periodica igual de inestable: solo el checkpoint de step 200000 empato el mejor valor previo, el resto oscilo en `-0.210` (timeout total)
  - dato relevante: `rollout/ep_rew_mean` (politica estocastica durante entrenamiento) mejoro de `-0.21` a `-0.0996`, sugiriendo que la exploracion si encuentra la meta mas seguido, pero la politica determinista (usada en eval) no logra capturar ese comportamiento de forma consistente
- decision siguiente:
  - no promover ningun checkpoint
  - `ent_coef` revertido a `0.01` en `configs/scenarios/my_way_home.toml` (no se valido como mejora, se evita drift de config sin justificar)
  - diagnostico: el problema no es solo exploracion, es reward disperso sin señal de progreso; subir `ent_coef` evito el colapso total pero no rompio el techo
  - decisión de negocio: no invertir mas tiempo ahora en `my_way_home`; seguir el curriculum y dejar `my_way_home` pendiente
  - si se retoma en el futuro, la mejora candidata es reward shaping por distancia (requiere exponer `POSITION_X`/`POSITION_Y` en `data/scenarios/my_way_home.cfg` y logica nueva en `doom_env.py`), no solo ajuste de hiperparametros

### 2026-06-14

- escenario: `basic`
- fase: `Fase 1`
- cambio realizado:
  - modelo renombrado a `foundation`
  - config separada en `base.toml` + `configs/scenarios/basic.toml`
  - `Makefile` reactivado con `make train`
  - tests reorganizados por area
  - `docs/` reorganizado como sistema de referencia + seguimiento
  - storage local por corrida implementado en `artifacts/runs/<run_id>/`
  - consola de entrenamiento mejorada con bloques visuales
  - cancelacion limpia por `Ctrl+C` aplicada a comandos largos de `make`
  - fix de compatibilidad BOM para `make list-runs`
- comando ejecutado:
  - `make check`
  - `make list-runs`
- resultado observado:
  - arquitectura lista para comenzar iteracion operativa sobre `basic`
  - validacion automatica estable
  - operacion diaria mas clara para entrenamiento, evaluacion y seguimiento
- decision siguiente:
  - correr `make train-from-scratch`
  - observar TensorBoard y consola visual
  - registrar comportamiento real del entrenamiento

### 2026-06-16

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se agrego schema remoto en `PostgreSQL`
  - se conecto `Neon`
  - se empezo persistencia de `training_runs` y `run_artifacts`
  - se corrigio copia heredada incorrecta de `best checkpoint`
- comando ejecutado:
  - `alembic upgrade head`
  - corridas cortas de prueba
  - consultas SQL en `Neon`
- resultado observado:
  - metadata de corridas registrada correctamente en DB
  - `best checkpoint` ya no se hereda falsamente si la corrida no evaluo
- decision siguiente:
  - agregar sync remoto de artefactos pesados

### 2026-06-17

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se valido `MinIO` local para object storage
  - se agrego backend `AWS S3`
  - se sincronizan checkpoints finales y videos
  - se registran `sync_events`
  - se limpio historial de pruebas local, `Neon` y bucket
- comando ejecutado:
  - corridas cortas de prueba
  - queries a `training_runs`, `run_artifacts`, `sync_events`
- resultado observado:
  - `Neon + AWS S3` funcionando
  - `storage_backend = s3`
  - `remote_uri = s3://...`
  - corrida nueva marcada como `synced`
- decision siguiente:
  - correr primera corrida larga limpia de `basic`
  - registrar resultado empirico real del entrenamiento

### 2026-06-18

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se implemento `sync-artifacts`
  - se agregaron modos `--run-id`, `--all-local-only`, `--all-failed` y `--dry-run`
  - se agregaron targets `make sync-artifacts`, `make sync-local-only`, `make sync-failed` y `make sync-dry-run`
  - se alineo documentacion de storage con resync manual implementado
  - se valido limpieza total de local, `Neon` y bucket `S3`
- comando ejecutado:
  - `make check`
  - `make sync-dry-run RUN_ID=doom_foundation_agent__20260617T040513523127Z`
  - `make sync-local-only LIMIT=20`
  - queries de verificacion en `training_runs` y `run_artifacts`
- resultado observado:
  - `sync-artifacts` operativo y validado
  - sistema limpio responde sin falsos positivos
  - no quedaron corridas, artefactos ni candidatos pendientes de sync
- decision siguiente:
  - correr nueva corrida limpia para repoblar metadata y artefactos reales
  - validar pipeline completo de entrenamiento, persistencia y sync remoto

### 2026-06-20

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se corrio una baseline larga limpia de `basic`
  - se reevaluaron checkpoints automaticos con protocolo offline consistente
  - se agrego `promote-checkpoint` para fijar checkpoint oficial validado
  - se agrego `hydrate-workspace` para continuidad operativa entre PCs
  - se agrego `inspect-run` para consolidar `report.json` + `manifest.json`
  - se paso a usar `report.json` y `manifest.json` dentro del flujo de sync/handoff
  - se elimino `MinIO` del camino operativo principal; backend remoto unico `AWS S3`
- comando ejecutado:
  - `make train-from-scratch SEED=42 TIMESTEPS=1500000`
  - `make evaluate CHECKPOINT=artifacts\\checkpoints\\auto\\doom_foundation_agent_1250000_steps.zip EPISODES=50 NO_RENDER=1 JSON=1`
  - `make evaluate CHECKPOINT=artifacts\\runs\\doom_foundation_agent__20260620T172048583643Z\\checkpoints\\final_model.zip EPISODES=50 NO_RENDER=1 JSON=1`
  - `make promote CHECKPOINT=artifacts\\checkpoints\\auto\\doom_foundation_agent_1250000_steps.zip PROMOTE_EPISODES=50`
- resultado observado:
  - checkpoint auto de `1250000` pasos quedo mejor que `final_model` bajo evaluacion offline de `50` episodios
  - `promoted` quedo apuntando al checkpoint oficialmente preservado
  - `workspace_state.json` y `hydrate-workspace` dejan listo el flujo base entre PCs
  - el repo ya no depende solo del disco local para reconstruir continuidad minima
- decision siguiente:
  - alinear documentacion con el flujo real de `promoted`, `manifest` y `hydrate`
  - definir politica simple de retencion/limpieza de artefactos
  - decidir si `basic` se congela como baseline oficial o si abre iteracion `v2`

### 2026-06-22

- escenario: `basic`
- fase entrenamiento: `Fase 1`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo corrida larga oficial de `basic`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `final_model.zip` como checkpoint oficial del escenario
  - se documento TensorBoard y lectura de metricas para presentacion
- comando ejecutado:
  - `make train-from-scratch`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\best_model.zip --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\final_model.zip --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__20260622T024012285164Z\checkpoints\final_model.zip --episodes 50`
- resultado observado:
  - `basic` quedo cerrado con checkpoint oficial promovido
  - metricas finales oficiales:
    - `mean_reward = -11.84`
    - `std_reward = 11.26`
    - `mean_episode_length = 13.84`
  - el `final_model.zip` supero al `best_model.zip` cuando se comparo offline con `50` episodios
- decision siguiente:
  - congelar `basic` como baseline oficial
  - abrir `defend_the_center` como primer escenario de transferencia
  - correr piloto inicial desde `doom_foundation_agent_promoted.zip`

### 2026-06-24

- escenario: `defend_the_center`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo primer piloto por transferencia desde checkpoint promovido de `basic`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial del escenario
  - se cerro administrativamente validacion inicial de `defend_the_center`
- comando ejecutado:
  - `make train SCENARIO=defend_the_center RESUME=artifacts\checkpoints\doom_foundation_agent_promoted.zip ALLOW_SCENARIO_RESUME=1 SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\final_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260623T025602580980Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_center__20260623T025602580980Z`
  - `best_model.zip` supero a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 7.98`
    - `std_reward = 1.30`
    - `mean_episode_length = 650.48`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- decision siguiente:
  - decidir si `defend_the_center` recibe segundo tramo de entrenamiento o si se congela como referencia de Fase 2
  - si se extiende, reanudar desde checkpoint promovido del escenario
  - si no se extiende, abrir siguiente escenario del curriculum

### 2026-06-25

- escenario: `defend_the_center`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un segundo tramo de entrenamiento reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` mejorado como nuevo checkpoint oficial del escenario
  - se cerro `defend_the_center` con una referencia final mas fuerte
- comando ejecutado:
  - `make train SCENARIO=defend_the_center RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\final_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_center__20260625T025825622091Z\checkpoints\best_model.zip --scenario defend_the_center --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_center__20260625T025825622091Z`
  - `best_model.zip` supero a `final_model.zip` y al checkpoint promovido anterior en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 9.90`
    - `std_reward = 1.38`
    - `mean_episode_length = 634.12`
  - sesgo de acciones mejoro respecto al piloto inicial, aunque no desaparecio por completo
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip`
- decision siguiente:
  - congelar `defend_the_center` como referencia fuerte de Fase 2
  - abrir el siguiente escenario del curriculum con config y protocolo inicial

### 2026-06-25

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se incorporo `health_gathering` al catalogo local como siguiente escenario preparado
  - se agregaron assets oficiales `.cfg` y `.wad`
  - se agrego config de escenario y tests minimos del preset de navegacion
- comando ejecutado:
  - integracion local en repo
- resultado observado:
  - `health_gathering` ya existe en `configs/scenarios/` y `data/scenarios/`
  - el preset esperado queda definido como `health_navigation`
  - el escenario queda listo para piloto inicial por transferencia o desde cero
- decision siguiente:
  - correr piloto inicial de `health_gathering`
  - validar `best_model.zip` y `final_model.zip` offline con `50` episodios

### 2026-06-25

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo piloto inicial por transferencia desde `defend_the_center`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial inicial del escenario
- comando ejecutado:
  - `make train SCENARIO=health_gathering RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip ALLOW_SCENARIO_RESUME=1 SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\final_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260625T113629214351Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__health_gathering__20260625T113629214351Z`
  - `best_model.zip` supero ampliamente a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 1539.16`
    - `std_reward = 635.51`
    - `mean_episode_length = 1541.04`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- decision siguiente:
  - decidir si `health_gathering` recibe un ultimo tramo de mejora o si se congela como referencia fuerte de Fase 2

### 2026-06-26

- escenario: `health_gathering`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un tramo adicional de mejora reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` mejorado como nuevo checkpoint oficial del escenario
- comando ejecutado:
  - `make train SCENARIO=health_gathering RESUME=artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\final_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__health_gathering__20260626T014540629370Z\checkpoints\best_model.zip --scenario health_gathering --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__health_gathering__20260626T014540629370Z`
  - `best_model.zip` supero a `final_model.zip` y al checkpoint promovido anterior en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 1580.28`
    - `std_reward = 736.36`
    - `mean_episode_length = 1581.04`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__health_gathering_promoted.zip`
- decision siguiente:
  - congelar `health_gathering` como referencia fuerte de Fase 2
  - abrir el siguiente escenario del curriculum

### 2026-06-29

- escenario: `take_cover`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se incorporo `take_cover` al catalogo local como siguiente escenario preparado
  - se agregaron assets oficiales `.cfg` y `.wad`
  - se agrego preset de acciones `take_cover_dodge`
  - se agrego config de escenario y tests minimos del preset de evasion
- comando ejecutado:
  - integracion local en repo
- resultado observado:
  - `take_cover` ya existe en `configs/scenarios/` y `data/scenarios/`
  - el preset esperado queda definido como `MOVE_LEFT` y `MOVE_RIGHT`
  - el escenario queda listo para piloto inicial por transferencia o desde cero
- decision siguiente:
  - correr piloto inicial de `take_cover`
  - validar `best_model.zip` y `final_model.zip` offline con `50` episodios

### 2026-06-30

- escenario: `take_cover`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo piloto inicial desde cero por incompatibilidad de action space con `health_gathering`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial inicial del escenario
- comando ejecutado:
  - `make train-from-scratch SCENARIO=take_cover SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260630T011932555138Z\checkpoints\final_model.zip --scenario take_cover --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260630T011932555138Z\checkpoints\best_model.zip --scenario take_cover --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260630T011932555138Z\checkpoints\best_model.zip --scenario take_cover --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__take_cover__20260630T011932555138Z`
  - `best_model.zip` y `final_model.zip` quedaron equivalentes bajo evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 205.98`
    - `std_reward = 45.54`
    - `mean_episode_length = 205.98`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__take_cover_promoted.zip`
- decision siguiente:
  - congelar `take_cover` como referencia inicial de Fase 2
  - abrir siguiente escenario del curriculum

### 2026-07-03

- escenario: `take_cover`
- fase entrenamiento: `Fase 2`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un segundo tramo de entrenamiento reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `final_model.zip` mejorado como nuevo checkpoint oficial del escenario
- comando ejecutado:
  - `make train SCENARIO=take_cover RESUME=artifacts\checkpoints\doom_foundation_agent__take_cover_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260703T140745071243Z\checkpoints\final_model.zip --scenario take_cover --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260703T140745071243Z\checkpoints\best_model.zip --scenario take_cover --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__take_cover__20260703T140745071243Z\checkpoints\final_model.zip --scenario take_cover --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__take_cover__20260703T140745071243Z`
  - `final_model.zip` supero a `best_model.zip` y al checkpoint promovido anterior en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 331.90`
    - `std_reward = 178.23`
    - `mean_episode_length = 331.90`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__take_cover_promoted.zip`
- decision siguiente:
  - congelar `take_cover` como referencia pulida de Fase 2
  - abrir siguiente escenario del curriculum

### 2026-07-03

- escenario: `defend_the_line`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se incorporo `defend_the_line` al catalogo local como siguiente escenario preparado
  - se agregaron assets oficiales `.cfg` y `.wad`
  - se agrego config de escenario y tests minimos con preset `turn_combat`
- comando ejecutado:
  - integracion local en repo
- resultado observado:
  - `defend_the_line` ya existe en `configs/scenarios/` y `data/scenarios/`
  - el preset esperado queda definido como `ATTACK`, `TURN_LEFT+ATTACK` y `TURN_RIGHT+ATTACK`
  - el escenario queda listo para piloto inicial por transferencia o desde cero
- decision siguiente:
  - correr piloto inicial de `defend_the_line`
  - validar `best_model.zip` y `final_model.zip` offline con `50` episodios

### 2026-07-03

- escenario: `defend_the_line`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo piloto inicial por transferencia desde checkpoint promovido de `defend_the_center`
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` como checkpoint oficial del escenario
  - se cerro administrativamente validacion inicial de `defend_the_line`
- comando ejecutado:
  - `make train SCENARIO=defend_the_line RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_center_promoted.zip ALLOW_SCENARIO_RESUME=1 SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T195759636148Z\checkpoints\best_model.zip --scenario defend_the_line --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T195759636148Z\checkpoints\final_model.zip --scenario defend_the_line --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T195759636148Z\checkpoints\best_model.zip --scenario defend_the_line --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_line__20260703T195759636148Z`
  - `best_model.zip` supero claramente a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 25.96`
    - `std_reward = 4.87`
    - `mean_episode_length = 939.30`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_line_promoted.zip`
  - transferencia valida desde `defend_the_center` por compatibilidad de action space `Discrete(3)`
- decision siguiente:
  - congelar `defend_the_line` como referencia inicial de Fase 3
  - preparar siguiente escenario especializado con verificacion previa de compatibilidad de `action_space`

### 2026-07-03

- escenario: `defend_the_line`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se completo un tramo adicional de mejora reanudando desde checkpoint promovido del escenario
  - se reevaluaron `best_model.zip` y `final_model.zip` con protocolo offline de `50` episodios
  - se promovio `best_model.zip` mejorado como nuevo checkpoint oficial del escenario
- comando ejecutado:
  - `make train SCENARIO=defend_the_line RESUME=artifacts\checkpoints\doom_foundation_agent__defend_the_line_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T231100240178Z\checkpoints\best_model.zip --scenario defend_the_line --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T231100240178Z\checkpoints\final_model.zip --scenario defend_the_line --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__defend_the_line__20260703T231100240178Z\checkpoints\best_model.zip --scenario defend_the_line --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__defend_the_line__20260703T231100240178Z`
  - `best_model.zip` supero al checkpoint promovido anterior y a `final_model.zip` en evaluacion offline de `50` episodios
  - metricas oficiales del checkpoint promovido:
    - `mean_reward = 27.06`
    - `std_reward = 7.43`
    - `mean_episode_length = 1026.78`
  - checkpoint promovido oficial:
    - `E:\agente-doom\artifacts\checkpoints\doom_foundation_agent__defend_the_line_promoted.zip`
- decision siguiente:
  - congelar `defend_the_line` como referencia oficial mejorada de Fase 3
  - abrir `basic_audio` como siguiente escenario exacto

### 2026-07-07

- escenario: `basic_audio`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se integro soporte de observacion especializada para `audio_buffer`
  - se agrego `observation_mode = vision_audio`
  - se valido compatibilidad de perfiles, resume y tests
- comando ejecutado:
  - `make check`
  - tests y typecheck locales
- resultado observado:
  - `basic_audio` deja de comportarse como `basic` normal
  - el escenario ya usa entrada especializada real
- decision siguiente:
  - correr `basic_audio` desde cero

### 2026-07-08

- escenario: `basic_audio`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se corrio primer tramo desde cero para validar escenario especializado
  - se reevaluaron `best_model.zip` y `final_model.zip` con `50` episodios
  - se promovio `best_model.zip` de forma provisional
- comando ejecutado:
  - `make train-from-scratch SCENARIO=basic_audio SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260708T021922363894Z\checkpoints\best_model.zip --scenario basic_audio --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260708T021922363894Z\checkpoints\final_model.zip --scenario basic_audio --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260708T021922363894Z\checkpoints\best_model.zip --scenario basic_audio --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__basic_audio__20260708T021922363894Z`
  - `best_model.zip` y `final_model.zip` quedaron equivalentes offline
  - metricas provisionales:
    - `mean_reward = -73.04`
    - `std_reward = 120.88`
    - `mean_episode_length = 74.60`
- decision siguiente:
  - probar un segundo tramo para ver si se consolida mejora real

### 2026-07-09

- escenario: `basic_audio`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se corrio un segundo tramo reanudando desde checkpoint promovido provisional
  - se compararon `best_model.zip` y `final_model.zip` con `50` episodios
  - se promovio un nuevo `best_model.zip` mejorado
- comando ejecutado:
  - `make train SCENARIO=basic_audio RESUME=artifacts\checkpoints\doom_foundation_agent__basic_audio_promoted.zip SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260709T002815511667Z\checkpoints\final_model.zip --scenario basic_audio --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260709T002815511667Z\checkpoints\best_model.zip --scenario basic_audio --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__basic_audio__20260709T002815511667Z\checkpoints\best_model.zip --scenario basic_audio --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__basic_audio__20260709T002815511667Z`
  - `best_model.zip` supero al promovido provisional anterior
  - metricas promovidas vigentes:
    - `mean_reward = -64.84`
    - `std_reward = 111.19`
    - `mean_episode_length = 66.48`
  - el escenario mejora, pero queda con varianza alta y sin consolidacion fuerte
- decision siguiente:
  - cerrar `basic_audio` como referencia provisional
  - abrir `basic_notifications`

### 2026-07-09

- escenario: `basic_notifications`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se integro soporte de observacion especializada para `notifications_buffer`
  - se agrego `observation_mode = vision_notifications`
  - se corrio primer tramo desde cero
  - se compararon `best_model.zip` y `final_model.zip` offline
  - se promovio `best_model.zip` como referencia provisional
- comando ejecutado:
  - `make train-from-scratch SCENARIO=basic_notifications SEED=42 TIMESTEPS=300000`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_notifications__20260709T024948566839Z\checkpoints\final_model.zip --scenario basic_notifications --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py evaluate --checkpoint artifacts\runs\doom_foundation_agent__basic_notifications__20260709T024948566839Z\checkpoints\best_model.zip --scenario basic_notifications --episodes 50 --no-render --json`
  - `.\.venv\Scripts\python.exe src\cli.py promote-checkpoint --checkpoint artifacts\runs\doom_foundation_agent__basic_notifications__20260709T024948566839Z\checkpoints\best_model.zip --scenario basic_notifications --episodes 50`
- resultado observado:
  - corrida validada: `doom_foundation_agent__basic_notifications__20260709T024948566839Z`
  - `best_model.zip` supero con claridad a `final_model.zip`
  - metricas promovidas vigentes:
    - `mean_reward = -73.60`
    - `std_reward = 120.65`
    - `mean_episode_length = 75.16`
  - el escenario aprende algo, pero queda sesgado e inestable
- decision siguiente:
  - cerrar `basic_notifications` como referencia provisional
  - dejar `my_way_home` como siguiente escenario exacto del roadmap

### 2026-07-09

- escenario: `my_way_home`
- fase entrenamiento: `Fase 3`
- fase storage: `Fase 2`
- cambio realizado:
  - se integraron assets oficiales `.cfg` y `.wad`
  - se agrego config de escenario en `configs/scenarios/my_way_home.toml`
  - se agregaron tests minimos de config y preset de navegacion
- comando ejecutado:
  - integracion local en repo
- resultado observado:
  - `my_way_home` ya existe en `configs/scenarios/` y `data/scenarios/`
  - el escenario queda preparado para piloto inicial
  - el preset actual usa `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `MOVE_LEFT` y `MOVE_RIGHT`
- decision siguiente:
  - correr `make check`
  - decidir si `my_way_home` arranca desde cero o por transferencia
