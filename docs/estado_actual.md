# Estado actual

Documento consolidado del estado vivo del repo.

Sirve para responder rapido:

- en que estamos hoy
- que escenarios ya quedaron cerrados
- que escenarios quedaron provisionales
- cual es el siguiente escenario exacto

Fecha base: 2026-07-14

## Resumen ejecutivo

- modelo actual: `foundation`
- fase actual de entrenamiento: `Fase 4`
- fase actual de storage: `Fase 2`
- baseline oficial: `basic`
- ultimo escenario cerrado fuerte: `deadly_corridor`
- ultimos escenarios especializados cerrados: `basic_audio`, `basic_notifications`
- escenario siguiente exacto recomendado: ninguno, curriculum cerrado (2026-07-14); `deathmatch` descartado por complejidad, no se integra
- estado operativo actual: `my_way_home` y `predict_position` quedaron pendientes definitivos (ambos con reward disperso, ninguno aprendio la habilidad objetivo); `health_gathering_supreme` y `deadly_corridor` cerrados oficiales
- configuracion baseline: [configs/base.toml](/E:/agente-doom/configs/base.toml:1) + [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- flujo principal: `make train`
- flujo recomendado para escenario nuevo: `make train-from-scratch`
- metadata remota activa: `Neon / PostgreSQL`
- object storage remoto activo: `AWS S3`
- handoff remoto activo: `hydrate-workspace` + `workspace_state.json`

## Foco actual

- `my_way_home` queda pendiente definitivo: se probaron dos variantes de reward shaping (bonus constante y bonus con decaimiento lineal), ninguna mejoro la tasa real de exito sobre el baseline original; ver `Reward shaping implementado` para el analisis completo
- `predict_position` queda pendiente indefinido: bloqueado por limitacion tecnica de ViZDoom (no expone posicion del objetivo movil), no por falta de esfuerzo; requeriria modificar WAD/ACS, fuera de alcance
- `health_gathering_supreme` cerrado oficial: transfer learning desde `health_gathering` funciono bien, `mean_reward=416.02`, `std=85.45` (50 episodios)
- `deadly_corridor` cerrado oficial: primer piloto `from-scratch`, `mean_reward=43.62`, `std=16.62`, reward denso y positivo, sin colapso (escenario `doom_skill=5`, muy dificil por diseño)
- congelar por ahora escenarios ya entrenados
- **curriculum cerrado (2026-07-14)**: decision explicita de no integrar `deathmatch` (16 botones binarios + 3 delta, action space muy complejo, alto riesgo de multiples intentos como `my_way_home`); 9 escenarios oficiales de ViZDoom cerrados (7 fuerte + 2 provisional), foco pasa a consolidacion/reentrenamiento en vez de escenarios nuevos
- mantener el flujo de handoff multi-PC legible para otra IA o para otra PC del equipo
- bug menor pendiente: columna `resume_mode` en `training_runs` (Postgres) es `VARCHAR(80)`, muy corta para rutas de checkpoint explicitas usadas en `--resume`; rompe persistencia remota de esa corrida (reporte local no se pierde)
- **bug critico corregido (2026-07-14)**: `make promote CHECKPOINT=...` sin `SCENARIO=` explicito sobrescribia el checkpoint promovido de `basic` en vez del escenario real que se estaba promoviendo; ver seccion `Incidente critico` mas abajo
- **bug de codificacion corregido, sin ganancia (2026-07-15)**: `basic_audio`/`basic_notifications` codificaban su buffer auxiliar (PCM crudo / texto de notificacion) como canal de imagen falso (`cv2.resize`), destruyendo la señal. Fix real: `Dict` observation space (`image`+`features`) + `DoomMultiModalFeatureExtractor` + `MultiInputLstmPolicy`. Arquitectura confirmada correcta (`explained_variance` 0.9+), pero tras retrain from-scratch ninguno de los dos escenarios supero el baseline anterior — la varianza intrinseca del escenario (`std` 90-145 con 50 episodios) es demasiado grande para que la mejora de codificacion se refleje en el eval. Ninguno promovido, checkpoints oficiales sin cambios.

## Reward shaping: intentado y descartado para my_way_home (2026-07-14)

- se implemento bonus de exploracion por celda nueva del mapa, generico y reusable (no exclusivo de `my_way_home`), incluyendo variante con decaimiento lineal
- mecanismo: `POSITION_X`/`POSITION_Y` del jugador via `game.get_game_variable(...)` (no requiere declarar la variable en el `.cfg`), bucket en grilla configurable, bonus unico por celda nueva visitada en el episodio, con decaimiento lineal opcional a lo largo del entrenamiento
- codigo permanece disponible y testeado para uso futuro en otros escenarios: `src/doom_agent/envs/doom_env.py` (`bucket_position`, `compute_exploration_bonus`, `decayed_exploration_bonus`, `DoomEnv._current_cell`), `src/doom_agent/config/schema.py`, `src/doom_agent/shared/contracts.py`
- campos de perfil `exploration_bonus` (default `0.0`), `exploration_grid_size` (default `48.0`), `exploration_bonus_decay_steps` (default `0`); forman parte de `resume_compatibility_signature`
- `configs/scenarios/my_way_home.toml` revertido a default (`exploration_bonus` no seteado, feature desactivada) tras confirmar que no ayuda

### Resultado: tres intentos, evidencia consistente de que no funciona

| Intento | best `mean_episode_length` | best `mean_reward` | final `mean_episode_length` | final `mean_reward` |
|---|---|---|---|---|
| Original (sin bonus) | 2063.1 | -0.186 | 2100.0 | -0.210 |
| Bonus constante (`0.02`) | 2063.1 | -0.106 | 2100.0 | -0.149 |
| Bonus con decaimiento lineal (150k steps) | 2058.58 | -0.147 | 2100.0 | -0.175 |

- los tres `mean_episode_length` del best model son practicamente identicos (~2058-2063); la tasa real de exito (episodios que llegan a la meta) no cambio de forma medible entre las tres variantes
- los tres modelos finales dan exactamente `2100.0` (0% de exito); el reward shaping no evito el colapso final
- diagnostico: el bonus de exploracion (constante o decaido) no es la palanca correcta para este escenario. Causa mas probable: limitacion fundamental de PPO on-policy con meta dispersa en un laberinto grande, no densidad de reward. Solucionarlo de verdad probablemente requiere o un presupuesto de timesteps mucho mayor (literatura de curiosity-driven usa 2-5M+ steps) o un mecanismo de motivacion intrinseca mas sofisticado (curiosity real tipo ICM, no solo conteo de celdas), fuera del alcance razonable ahora
- decision: `my_way_home` queda pendiente definitivo, mismo tratamiento que `predict_position`; no se reintenta salvo que se invierta en una de esas dos vias mayores

## Incidente critico: bug en promote-checkpoint sobrescribio el baseline de `basic` (2026-07-14)

- al promover el primer checkpoint de `deadly_corridor` con `make promote CHECKPOINT=<ruta explicita> PROMOTE_EPISODES=50` (sin `SCENARIO=`), el comando sobrescribio `doom_foundation_agent_promoted.zip` — el checkpoint promovido oficial de `basic`, el baseline congelado del proyecto
- causa raiz: `src/doom_agent/services/promoter.py` nombraba el alias promovido usando un perfil materializado con `scenario_name=None` (cuando no se pasa `--scenario`), lo que caia al escenario default (`basic`) en vez de usar el escenario real del checkpoint que se estaba promoviendo
- **no hubo perdida real de datos**: el alias `_active.zip` de `basic` seguia intacto (`scenario_key=basic`, `mean_reward=-11.84` al re-evaluar, identico al valor historico documentado); la recuperacion fue directa
- fix aplicado: el nombre del alias promovido ahora se deriva de la metadata embebida en el checkpoint que se esta promoviendo (`source_metadata["profile"]["checkpoint_name"]`), no de un perfil separado que podia no coincidir con el escenario real
- test de regresion agregado: `test_promote_checkpoint_uses_source_scenario_name_not_default_when_scenario_omitted`
- **leccion operativa**: hasta ganar mas confianza en el fix, incluir siempre `SCENARIO=<escenario>` explicito en `make promote`, incluso cuando se usa `CHECKPOINT=<ruta>` explicita

## Estado de escenarios

| Escenario | Estado actual | Calidad operativa | Checkpoint oficial | Resultado resumido | Nota |
|---|---|---|---|---|---|
| `basic` | Cerrado oficial | Bueno | `doom_foundation_agent_promoted.zip` | `mean_reward = -11.84`, `std = 11.26` | Baseline fuerte del proyecto. |
| `defend_the_center` | Cerrado oficial | Bueno | `doom_foundation_agent__defend_the_center_promoted.zip` | `mean_reward = 9.90`, `std = 1.38` | Referencia fuerte de Fase 2. |
| `health_gathering` | Cerrado oficial | Bueno | `doom_foundation_agent__health_gathering_promoted.zip` | `mean_reward = 1580.28`, `std = 736.36` | Muy buen resultado para supervivencia. |
| `take_cover` | Cerrado oficial | Bueno | `doom_foundation_agent__take_cover_promoted.zip` | `mean_reward = 331.90`, `std = 178.23` | Referencia pulida de evasion. |
| `defend_the_line` | Cerrado oficial | Bueno | `doom_foundation_agent__defend_the_line_promoted.zip` | `mean_reward = 27.06`, `std = 7.43` | Mejor cierre actual de Fase 3 estable. |
| `basic_audio` | Cerrado provisional | Regular | `doom_foundation_agent__basic_audio_promoted.zip` | `mean_reward = -64.84`, `std = 111.19` | Refuerzo con misma config (+301k) empeoro. **Bug real encontrado y corregido (2026-07-15)**: el audio/notificaciones se codificaban como canal de imagen falso (`cv2.resize` sobre PCM crudo), destruyendo la señal. Fix: `Dict` observation space real (imagen + features numericas) + `DoomMultiModalFeatureExtractor` + `MultiInputLstmPolicy`. Retrain from-scratch + 151k mas (451k total): `-73.04` y `-74.72`, ambos dentro del ruido del baseline (`std` ~110-140, SEM~17 con 50 eps). Arquitectura corregida y validada (`explained_variance` 0.95-0.99), pero eval no se despega del ruido intrinseco del escenario. No promovido, checkpoint oficial sin cambios. |
| `basic_notifications` | Cerrado provisional | Regular | `doom_foundation_agent__basic_notifications_promoted.zip` | `mean_reward = -73.60`, `std = 120.65` | Mismo bug de codificacion de imagen falsa que `basic_audio`, mismo fix (`Dict` space + `DoomMultiModalFeatureExtractor`). Retrain from-scratch (300k): `-110.84`, `std=141.88` (peor, fuera del margen de ruido). Arquitectura corregida, pero eval no mejora el baseline. No promovido, checkpoint oficial sin cambios. |
| `my_way_home` | Pendiente definitivo (tres intentos) | Malo | No aplica | Mejor resultado: `mean_episode_length ~2060` en los tres intentos, nunca mejora; final siempre `2100.0` (0% exito) | Reward disperso; ni `ent_coef` alto, ni bonus de exploracion constante, ni con decaimiento resolvieron el problema. Requiere presupuesto mucho mayor o curiosity real (fuera de alcance). |
| `predict_position` | Pendiente (entrenado, sin exito) | Malo | No aplica | `mean_reward = -0.30`, `std = 0.0` en ambos best y final (50 episodios); nunca impacto el objetivo | 300k+ steps completos. Reward binario disperso: unica señal positiva es el impacto directo, nunca ocurrio. Requiere reward shaping, no solo mas timesteps. |
| `health_gathering_supreme` | Cerrado oficial | Bueno | `doom_foundation_agent__health_gathering_supreme_promoted.zip` | `mean_reward = 416.02`, `std = 85.45` | Transfer learning desde `health_gathering` (2.3M steps heredados + 301k adicionales). Reward denso, varianza relativa razonable. |
| `deadly_corridor` | Cerrado oficial | Bueno | `doom_foundation_agent__deadly_corridor_promoted.zip` | `mean_reward = 43.62`, `std = 16.62` | Primer piloto `from-scratch`. Reward denso y positivo, sin colapso. `doom_skill=5`, muy dificil por diseño. |
| `deathmatch` | Futuro | Pendiente | No aplica | No entrenado aun | Dejar al final; ultimo escenario oficial sin integrar. |

## Lectura operativa

- `basic`, `defend_the_center`, `health_gathering`, `take_cover`, `defend_the_line`, `health_gathering_supreme` y `deadly_corridor` quedaron como referencias oficiales fuertes.
- `basic_audio` y `basic_notifications` ya quedaron integrados y promovidos, pero solo como referencias provisionales.
- no conviene gastar mas ciclos ahora en `basic_audio` y `basic_notifications` con la misma configuracion.
- `my_way_home` y `predict_position` quedan pendientes definitivos, ninguno promovido, ninguno se reintenta sin inversion mayor.
- para presentacion o continuidad del proyecto, la narrativa correcta es:
  - baseline fuerte en `basic`
  - expansion fuerte en Fase 2
  - Fase 3 probo escenario frontal estable, dos escenarios sensoriales especializados, y cerro una version dificil de supervivencia via transfer learning
  - Fase 4 cerro un escenario de combate+navegacion muy dificil (`doom_skill=5`) desde cero

## Ya implementado

### Configuracion

- se usa:
  - [configs/base.toml](/E:/agente-doom/configs/base.toml:1)
  - [configs/scenarios/basic.toml](/E:/agente-doom/configs/scenarios/basic.toml:1)
- arquitectura por escenario en `configs/scenarios/*.toml`
- modos de observacion especializados ya integrados:
  - `vision`
  - `vision_audio`
  - `vision_notifications`

### CLI publica

Comandos visibles:

- `train`
- `evaluate`
- `inspect-checkpoint`
- `list-checkpoints`
- `list-runs`
- `inspect-run`
- `promote-checkpoint`
- `sync-artifacts`
- `hydrate-workspace`

Comandos retirados del flujo publico:

- `sweep`
- `list-scenarios`
- `list-profiles`

### Makefile

Comandos principales disponibles:

- `make setup`
- `make bootstrap`
- `make check`
- `make train`
- `make train-from-scratch`
- `make train-latest`
- `make evaluate`
- `make evaluate-last`
- `make play`
- `make inspect`
- `make inspect-run`
- `make promote`
- `make hydrate`
- `make list-runs`
- `make list-checkpoints`
- `make sync-artifacts RUN_ID=<run_id>`
- `make sync-local-only LIMIT=20`
- `make sync-failed LIMIT=20`
- `make sync-dry-run RUN_ID=<run_id>`
- `make tensorboard`

### Storage y handoff

- schema remoto operativo en `PostgreSQL`
- persistencia de corridas en `Neon`
- sync remoto de `report.json`, `manifest.json`, checkpoints elegibles y videos a `AWS S3`
- `workspace_state.json` publica punteros `active` y `promoted`
- `hydrate-workspace` reconstruye continuidad en otra PC
- flujo oficial: una sola PC entrena linea principal a la vez

## Bloqueos o riesgos actuales

- `my_way_home` queda pendiente tras dos intentos (from-scratch 300k y resume+ent_coef alto 200k adicionales); ninguno resolvio el reward disperso
- `my_way_home` necesita cambio de codigo (reward shaping por distancia, exponer `POSITION_X`/`POSITION_Y`) para tener chance real, no solo ajuste de config
- `predict_position` queda pendiente tras entrenamiento completo (300k+ steps, 12+ evaluaciones periodicas y 50 episodios offline, siempre `-0.3` exacto); reward binario sin señal parcial, mismo patron de fondo que `my_way_home`
- bug de infraestructura Windows detectado y mitigado: Defender bloqueaba el checkpoint `_active.zip` justo al copiarlo, rompiendo el resume automatico dos veces seguidas; se agrego exclusion de Defender sobre `artifacts/`
- bug de datos pendiente: columna `resume_mode` en Postgres (`VARCHAR(80)`) no soporta rutas de checkpoint largas pasadas a `--resume`; rompe sync remoto de esa corrida especifica (no afecta corridas con `RESUME=auto`)
- escenarios sensoriales quedaron usables, pero no fuertes
- auto-checkpoints siguen siendo apoyo local, no fuente oficial de verdad

## Politica recomendada para reentrenar escenarios pasados

Si, se pueden volver a entrenar escenarios ya cerrados, pero no todos merecen eso ahora.

Regla sugerida:

- reentrenar un escenario fuerte solo si hace falta para una demo puntual o una comparacion formal
- reabrir un escenario provisional si cambia la observacion, reward, arquitectura o si aparece una configuracion mejor claramente justificada
- no reabrir `basic_audio` ni `basic_notifications` ahora con la misma config; el retorno esperado es bajo
- si se reabre algo en el futuro:
  - usar nueva corrida
  - reevaluar offline con `50` episodios
  - promover solo si supera checkpoint oficial vigente

## Post-curriculum

Despues de terminar la integracion y entrenamiento del resto del curriculum, el orden recomendado para volver a escenarios ya entrenados es este:

1. `basic_audio`
2. `basic_notifications`
3. `my_way_home`, solo si su primer piloto queda regular
4. `defend_the_line`, solo si hace falta una version mas fuerte para demo o comparacion

Escenarios que hoy no merecen reentrenamiento prioritario:

- `basic`
- `defend_the_center`
- `health_gathering`
- `take_cover`

Esos ya estan lo bastante bien para quedar como referencias oficiales fuertes.

Para que un escenario provisional pase a oficial fuerte, la regla sugerida es:

- mejorar claramente su checkpoint promovido vigente en evaluacion offline de `50` episodios
- bajar sesgo de acciones dominante si hoy esta muy cargado a un lado
- mantener una varianza mas razonable que la actual
- repetir el resultado en al menos un segundo tramo o una segunda corrida si el escenario sigue siendo inestable

Escenarios con mayor margen real de mejora futura:

- `basic_audio`
  - motivo: ya mejoro entre primer y segundo tramo
  - problema actual: alta varianza
  - mejora candidata: `ent_coef` un poco mas alto, `n_epochs` un poco mas bajo, tramos mas cortos
- `basic_notifications`
  - motivo: aprende algo, pero conserva sesgo fuerte
  - problema actual: colapso de politica hacia un lado
  - mejora candidata: misma linea que `basic_audio`, con mas control de exploracion y cortes de entrenamiento mas tempranos

En palabras simples:

- si terminamos el curriculum, los dos primeros escenarios que vale la pena reabrir son `basic_audio` y `basic_notifications`
- se pueden volver a entrenar con una nueva configuracion
- lo ya promovido no se pierde
- solo pasarian a oficiales fuertes si la nueva version supera claramente la actual

## Operacion recomendada hoy

1. `make setup`
2. `make check`
3. `make list-runs`
4. `make inspect-run RUN_ID=<run_id>`
5. `make evaluate CHECKPOINT=... EPISODES=50 NO_RENDER=1 JSON=1`
6. `make promote CHECKPOINT=... PROMOTE_EPISODES=50`
7. validar en `Neon`
8. validar en `S3`
9. `make hydrate ONLY=promoted` en otra PC si hace falta

## Siguiente accion recomendada

1. curriculum cerrado: `deathmatch` no se integra, no hay escenario nuevo pendiente
2. `my_way_home` y `predict_position` quedan pendientes definitivos, no se reintentan sin inversion mayor (presupuesto de computo o herramientas WAD/ACS)
3. hasta ganar mas confianza en el fix de `promote-checkpoint`, incluir siempre `SCENARIO=<escenario>` explicito en `make promote`
4. decidir si vale la pena ampliar la columna `resume_mode` en Postgres via migracion Alembic (bug de persistencia con `--resume` de ruta larga)
5. mantener congelados checkpoints oficiales actuales; foco pasa a consolidacion/reentrenamiento, no escenarios nuevos
