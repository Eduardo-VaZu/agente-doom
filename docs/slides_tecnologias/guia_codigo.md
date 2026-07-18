# Guia de codigo para exposicion — Agente Doom

Para explicar el proyecto abriendo VS Code. Trae:
1. **Orden de archivos a mostrar** (que abrir y en que secuencia).
2. **Comentario bloque por bloque** de cada archivo, con referencia `archivo:linea` para saltar rapido.

Registro: pensado para leer/parafrasear mientras muestras el codigo en pantalla.

---

## 1. Lista de archivos (orden sugerido de exposicion)

| # | Archivo | Que muestra | Por que importa |
|---|---------|-------------|-----------------|
| 1 | `configs/base.toml` | Configuracion compartida | Todo el comportamiento sale de aca |
| 2 | `configs/scenarios/basic.toml` | Config de un escenario | Hiperparametros reales del entrenamiento |
| 3 | `src/doom_agent/config/schema.py` | `TrainingProfile`, `RewardShapingConfig` | Valida y da forma a la config |
| 4 | `src/doom_agent/envs/doom_env.py` | Entorno, preprocesado, acciones | **El corazon de la percepcion y el control** |
| 5 | `src/doom_agent/envs/reward.py` | `RewardShaper` | Como se transforma la recompensa |
| 6 | `src/doom_agent/models/recurrent_ppo.py` | Red CNN+LSTM y el modelo | **El corazon del algoritmo** |
| 7 | `src/doom_agent/services/training_support.py` | Carga del modelo, callback, evaluacion | Como se orquesta el aprendizaje |
| 8 | `src/doom_agent/services/trainer.py` | Bucle de entrenamiento y curriculum | El pegamento de todo |
| 9 | `src/cli.py` | Punto de entrada | Como se lanza (`make train`) |

**Si tienes poco tiempo:** muestra solo el 4 (`doom_env.py`) y el 6 (`recurrent_ppo.py`). Son el nucleo.

---

## 2. `configs/base.toml` — configuracion compartida

Abrir y explicar que el proyecto se maneja por archivos de configuracion, no por codigo hardcodeado.

```toml
[defaults]
scenario_key = "basic"        # escenario activo por defecto
render = false                # no dibuja ventana durante entrenamiento (mas rapido)
record_video = true           # graba videos de muestra
checkpoint_name = "doom_foundation_agent"   # prefijo de los modelos guardados
frame_stack = 4               # apila 4 cuadros -> percibe movimiento
screen_width = 84             # imagen reescalada a 84x84
screen_height = 84
seed = 42                     # semilla -> reproducibilidad
action_space_kind = "button_combinations"   # usa combos de botones curados
```

**Que decir:** "Todo lo que gobierna el entrenamiento vive en estos archivos. Cambiando un valor aca, cambia el comportamiento sin tocar el codigo. Por ejemplo `frame_stack = 4` es lo que le da al agente sentido de movimiento, y `seed = 42` hace que el experimento sea reproducible."

El bloque `[defaults.reward_shaping]` y `[defaults.early_stopping]` fijan valores base que cada escenario puede sobrescribir.

---

## 3. `configs/scenarios/basic.toml` — un escenario concreto

```toml
[scenario]
scenario_name = "basic.cfg"   # archivo .cfg de ViZDoom que define el mapa/objetivo
learning_rate = 0.0001        # paso de aprendizaje
n_steps = 2048                # pasos por rollout (y horizonte del BPTT)
batch_size = 128              # muestras por minibatch
n_epochs = 4                  # pasadas por lote
gamma = 0.99                  # descuento del futuro
gae_lambda = 0.95             # sesgo/varianza de la ventaja
ent_coef = 0.01               # fuerza de exploracion
requested_timesteps = 1500000 # cuanto entrenar en total
action_combo_preset = "basic_combat"   # que combos de botones se permiten

[scenario.reward_shaping]
clip_min = -1.0               # recorta recompensa minima
clip_max = 1.0                # recorta recompensa maxima
```

**Que decir:** "Cada escenario tiene su propia config. Estos son los hiperparametros reales del algoritmo. Fijense que el reward se recorta entre -1 y 1 para estabilizar el aprendizaje."

---

## 4. `src/doom_agent/config/schema.py` — la config con forma y validacion

Aca la config cruda se vuelve un objeto tipado y validado.

### `RewardShapingConfig.apply` (schema.py:43)

```python
def apply(self, reward: float) -> float:
    shaped_reward = (reward + self.offset) * self.scale   # desplaza y escala
    if self.clip_min is not None and shaped_reward < self.clip_min:
        shaped_reward = self.clip_min                     # piso
    if self.clip_max is not None and shaped_reward > self.clip_max:
        shaped_reward = self.clip_max                     # techo
    return float(shaped_reward)
```

**Que decir:** "Esta funcion toma la recompensa cruda del juego, la ajusta con offset y escala, y la recorta a un rango. Recortar evita que un valor gigante desestabilice el entrenamiento."

### `TrainingProfile` (schema.py:134)

Es el `dataclass` que junta TODA la configuracion de una corrida: hiperparametros, escenario, modo de observacion, reward shaping, early stopping, exploracion. Propiedades utiles:

```python
@property
def effective_timesteps(self) -> int:
    return ceil(self.requested_timesteps / self.n_steps) * self.n_steps
    # redondea al siguiente multiplo de n_steps (asi lo exige PPO)

@property
def stacked_observation_channels(self) -> int:
    return self.observation_channels * self.frame_stack
    # canales reales que entran a la CNN (1 gris x 4 frames = 4)
```

### `TrainingProfile.validate` (schema.py:209)

**Que decir:** "Antes de entrenar, se valida todo. Esto evita corridas rotas por config invalida."

```python
if self.batch_size > self.n_steps:                 # batch no puede exceder el rollout
    raise ValueError(...)
if not 0 < self.gamma <= 1:                         # gamma es una probabilidad de descuento
    raise ValueError(...)
if self.action_space_kind not in {"button_combinations", "discrete", "multidiscrete"}:
    raise ValueError(...)                           # solo tipos de accion soportados
```

---

## 5. `src/doom_agent/envs/doom_env.py` — EL CORAZON de percepcion y control

Este es el archivo mas importante para mostrar. Cuatro partes.

### 5.1 Preprocesado de imagen (doom_env.py:39)

```python
def preprocess_frame(frame, width, height):
    frame = normalize_rgb_frame(frame)                    # ordena canales (C,H,W) -> (H,W,C)
    if frame.ndim == 3 and frame.shape[-1] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)   # color -> gris
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)  # a 84x84
    return resized.reshape(1, height, width).astype(np.uint8)  # forma (1,84,84), enteros 0-255
```

**Que decir:** "Aca esta OpenCV en accion. La imagen del juego se pasa a gris y se achica a 84x84. Se devuelve como enteros de 8 bits para ahorrar memoria. Esto es lo que 've' el agente."

### 5.2 Construccion del espacio de acciones (doom_env.py:132)

```python
def build_button_combination_actions(available_button_names, preset="default"):
    ...
    def add_action(selected_buttons):
        if has_opposing_buttons(selected_button_set):   # descarta IZQ+DER, ADELANTE+ATRAS...
            return
        encoded_action = np.zeros(len(available_button_names), dtype=np.int32)
        for selected_button in selected_buttons:
            encoded_action[button_index[selected_button]] = 1   # 1 = boton presionado
        ...
```

Y los presets concretos, ej. el del nivel completo (doom_env.py:204):

```python
if preset == "full_doom_basic":
    add_action(("ATTACK",))                 # disparar
    add_action(("MOVE_FORWARD",))           # avanzar
    add_action(("MOVE_FORWARD", "ATTACK"))  # avanzar disparando
    add_action(("TURN_LEFT",)); add_action(("TURN_RIGHT",))
    add_action(("USE",))                    # abrir puertas
    add_action(("SELECT_NEXT_WEAPON",))     # cambiar arma
```

**Que decir:** "En vez de dejar todos los botones sueltos, definimos combos utiles y descartamos combinaciones sin sentido, como ir a izquierda y derecha a la vez. Menos acciones = aprende mas rapido."

### 5.3 La clase `DoomEnv` — el metodo `step` (doom_env.py:309)

Es el latido del entorno: recibe una accion, la ejecuta, devuelve observacion y recompensa.

```python
def step(self, action):
    binary_action = self._normalize_action(action)          # traduce el indice al vector de botones
    raw_reward = float(self.game.make_action(binary_action.tolist()))  # ViZDoom ejecuta la accion
    self._elapsed_steps += 1
    if self.exploration_bonus > 0 and not self.game.is_episode_finished():
        current_bonus = decayed_exploration_bonus(...)      # bonus por explorar, con decaimiento
        if current_bonus > 0:
            raw_reward += compute_exploration_bonus(        # premia celda nueva del mapa
                self._current_cell(), self._visited_cells, current_bonus)
    reward = self.reward_shaper.apply(raw_reward)           # aplica shaping (escala/clip)
    terminated = self.game.is_episode_finished()            # murio o gano?
    observation = self._observation_from_state(state)       # arma la observacion
    info = {"raw_reward": raw_reward, "shaped_reward": reward}
    return observation, reward, terminated, truncated, info
```

**Que decir:** "Este metodo es el ciclo basico: entra una accion, ViZDoom la ejecuta y devuelve una recompensa. Le sumamos el bonus de exploracion, aplicamos el reward shaping, y devolvemos la nueva observacion. Esto se repite miles de veces por segundo."

### 5.4 `reset` (doom_env.py:336) y observacion multimodal (doom_env.py:389)

```python
def reset(self, seed=None, options=None):
    self.game.new_episode()          # arranca episodio nuevo
    self._visited_cells.clear()      # olvida celdas visitadas
    ...
```

```python
def _observation_from_state(self, state):
    image = preprocess_frame(...)            # siempre hay imagen
    if self.observation_mode == "vision_audio":
        return {"image": image, "features": extract_audio_features(audio_buffer)}   # + audio
    if self.observation_mode == "vision_notifications":
        return {"image": image, "features": extract_notification_features(...)}     # + enemigo visto
    return image
```

**Que decir:** "El agente puede ver solo imagen, o imagen + audio, o imagen + notificaciones de que enemigo aparecio. Eso es el modo multimodal."

### 5.5 Construccion del entorno vectorizado (doom_env.py:428)

```python
def make_vectorized_env(profile, project_paths, *, video_dir=None):
    env = DummyVecEnv([_build_env])          # envuelve el env (SB3 espera 'vectorizado')
    env = VecMonitor(env)                    # registra recompensas y longitudes de episodio
    env = VecFrameStack(env, n_stack=profile.frame_stack)   # APILA los 4 cuadros
    if profile.record_video:
        env = VecVideoRecorder(...)          # graba video cada N pasos
    return env
```

**Que decir:** "Aca se arma la pila de wrappers. Lo clave es `VecFrameStack`: apila los 4 cuadros para que la red perciba movimiento."

---

## 6. `src/doom_agent/envs/reward.py` — RewardShaper

Archivo corto, muestra la separacion de responsabilidades.

```python
class RewardShaper:
    def __init__(self, config: RewardShapingConfig) -> None:
        self.config = config
    def apply(self, reward: float) -> float:
        return self.config.apply(reward)     # delega en la config (escala + clip)
```

**Que decir:** "El shaping de recompensa vive fuera del entorno, en su propia clase configurable. El entorno solo lo llama."

---

## 7. `src/doom_agent/models/recurrent_ppo.py` — EL CORAZON del algoritmo

### 7.1 Extractor de features CNN (recurrent_ppo.py:16)

```python
class DoomFeatureExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim=512):
        input_channels = shape[0]                          # 4 (frames apilados)
        self.cnn = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=8, stride=4), nn.ReLU(),  # capa 1
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),             # capa 2
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),             # capa 3
            nn.Flatten(),                                                      # aplana
        )
        with th.no_grad():
            sample = th.as_tensor(observation_space.sample()[None]).float()
            flattened_size = self.cnn(sample).shape[1]     # calcula tamano tras las conv
        self.projection = nn.Sequential(
            nn.Linear(flattened_size, features_dim), nn.ReLU())  # proyecta a 512

    def forward(self, observations):
        return self.projection(self.cnn(observations))     # imagen -> 512 numeros
```

**Que decir:** "Esta es la red convolucional que ya explicamos: tres capas conv y una lineal que termina en 512 features. Es literalmente la vision del agente en codigo."

### 7.2 Extractor multimodal (recurrent_ppo.py:46)

```python
class DoomMultiModalFeatureExtractor(BaseFeaturesExtractor):
    # CNN sobre 'image' (448 features) + MLP sobre 'features' (64) -> concatena -> 512
    def forward(self, observations):
        image_features = self.cnn_projection(self.cnn(observations["image"]))  # rama imagen
        aux_features = self.mlp(observations["features"])                      # rama audio/notif
        combined = th.cat([image_features, aux_features], dim=1)               # une las dos
        return self.output_projection(combined)                               # -> 512
```

**Que decir:** "Cuando hay audio o notificaciones, ademas de la CNN hay un pequeno MLP, y las dos ramas se concatenan. Asi el agente combina lo que ve con lo que oye."

### 7.3 Construccion del modelo RecurrentPPO (recurrent_ppo.py:99)

```python
def build_recurrent_ppo_model(env, profile, tensorboard_log_dir):
    is_dict_observation = isinstance(env.observation_space, gym.spaces.Dict)
    policy = "MultiInputLstmPolicy" if is_dict_observation else "CnnLstmPolicy"  # elige politica
    features_extractor_class = (DoomMultiModalFeatureExtractor
                                if is_dict_observation else DoomFeatureExtractor)
    return RecurrentPPO(
        policy=policy,
        env=env,
        learning_rate=profile.learning_rate,     # <- viene de la config
        n_steps=profile.n_steps,
        batch_size=profile.batch_size,
        n_epochs=profile.n_epochs,
        gamma=profile.gamma,
        gae_lambda=profile.gae_lambda,
        ent_coef=profile.ent_coef,
        seed=profile.seed,
        tensorboard_log=tensorboard_log_dir,
        policy_kwargs={"features_extractor_class": features_extractor_class},  # inyecta nuestra CNN
    )
```

**Que decir:** "Aca se arma el algoritmo. Segun el tipo de observacion elige la politica —con LSTM en ambos casos— y le inyecta nuestro extractor CNN. Todos los hiperparametros salen de la config que vimos al principio. El LSTM lo aporta la propia politica de la libreria; nosotros ponemos la vision."

---

## 8. `src/doom_agent/services/training_support.py` — orquestacion del aprendizaje

### 8.1 Cargar o crear el modelo (training_support.py:55)

```python
def load_training_model(env, profile, tensorboard_dir, resume_state):
    if not resume_state.is_resumed:
        return build_recurrent_ppo_model(env, profile, str(tensorboard_dir))  # desde cero
    model = RecurrentPPO.load(...)          # o continua desde un checkpoint
    model.set_random_seed(profile.seed)
    return model
```

**Que decir:** "El entrenamiento puede empezar de cero o continuar desde un checkpoint guardado. Esto permite entrenar por partes o retomar en otra maquina."

### 8.2 El callback periodico (training_support.py:161)

`PeriodicTrainingCallback` corre DURANTE el entrenamiento. Su metodo `_on_step` (training_support.py:209):

```python
def _on_step(self) -> bool:
    self._record_actions()                          # cuenta que acciones usa
    if self.num_timesteps >= self.next_eval_step:
        self._run_periodic_evaluation()             # evalua cada N pasos
        if self.early_stopping.stopped:
            return False                            # corta si dejo de mejorar
        self.next_eval_step += self.evaluation_settings.frequency
    if self.num_timesteps >= self.next_checkpoint_step:
        self._save_periodic_checkpoint()            # guarda checkpoint cada N pasos
        self.next_checkpoint_step += self.profile.checkpoint_frequency
    return True
```

**Que decir:** "Mientras entrena, cada cierto numero de pasos el agente se evalua y se guarda. Si deja de mejorar, el early stopping lo detiene. Asi no desperdiciamos computo."

### 8.3 La evaluacion (training_support.py:225)

```python
def _run_periodic_evaluation(self):
    rewards, lengths = evaluate_policy(              # juega episodios de prueba
        self.model, self.eval_env,
        n_eval_episodes=self.evaluation_settings.episodes,
        deterministic=True,                          # sin azar, para medir bien
        return_episode_rewards=True)
    self.last_evaluation_metrics = build_evaluation_metrics(rewards, lengths, ...)
    mean_reward = self.last_evaluation_metrics["mean_reward"]
    ...
    if self.evaluation_settings.save_best and improved:
        save_checkpoint_bundle(self.model, ...)      # guarda el MEJOR modelo hasta ahora
```

**Que decir:** "La evaluacion juega varios episodios de prueba de forma determinista y mide la recompensa media. Si es la mejor hasta ahora, guarda ese modelo como el 'best'."

---

## 9. `src/doom_agent/services/trainer.py` — el bucle principal

### 9.1 `train_profile` (trainer.py:256) — arma y corre una corrida

Puntos a senalar:

```python
env = make_vectorized_env(profile, project_paths, video_dir=...)   # entorno de entrenamiento
eval_env = make_vectorized_env(eval_profile, project_paths)        # entorno de evaluacion
model = load_training_model(env, profile, ..., resume_state)       # modelo (nuevo o resumido)
callback = PeriodicTrainingCallback(...)                           # el callback de arriba

model.learn(                                                       # <- AQUI ENTRENA
    total_timesteps=profile.effective_timesteps,
    callback=callback,
    reset_num_timesteps=not resume_state.is_resumed,
)
```

**Que decir:** "Esta funcion es el pegamento: crea el entorno, el modelo y el callback, y llama a `model.learn`, que es donde ocurre todo el entrenamiento. El resto del archivo guarda checkpoints, reportes, y sincroniza con la nube."

Despues de entrenar (bloque `finally`, trainer.py:382) guarda el checkpoint final, sube artefactos a S3 y persiste metadata en PostgreSQL.

### 9.2 `train` y el curriculum (trainer.py:527)

```python
if profile.curriculum:
    stages = materialize_curriculum_profiles(...)     # varias etapas encadenadas
    for stage_index, stage_profile in enumerate(stages, start=1):
        last_result = train_profile(..., 
            resume_mode=stage_resume_mode)            # cada etapa continua de la anterior
        stage_resume_mode = str(select_resume_checkpoint_path(last_result))
```

**Que decir:** "Si el perfil es un curriculum, se entrenan varias etapas en secuencia, y cada una arranca desde el modelo de la anterior. Es la idea de ensenar por dificultad creciente."

---

## 10. `src/cli.py` — punto de entrada

```python
from doom_agent.cli.main import main
if __name__ == "__main__":
    main()
```

**Que decir:** "El CLI es la puerta de entrada. Cuando corremos `make train`, por debajo se llama a este `main`, que parsea el comando y dispara `trainer.train`."

---

## Cierre de la demo de codigo

Frase para cerrar mostrando el codigo:

> "En resumen: la config define los parametros, `doom_env.py` construye lo que el agente ve y hace, `recurrent_ppo.py` arma la red y el algoritmo, y `trainer.py` junta todo y llama a `model.learn`. El resto es soporte: checkpoints, evaluacion, nube. Todo el aprendizaje pasa por ese ciclo de percibir, recordar, decidir y recibir recompensa."

### Orden de saltos en VS Code (para no perderte)
1. `configs/base.toml` → `configs/scenarios/basic.toml`
2. `schema.py:43` (reward apply) → `schema.py:209` (validate)
3. `doom_env.py:39` (preprocess) → `:204` (preset) → `:309` (step) → `:428` (env vectorizado)
4. `recurrent_ppo.py:16` (CNN) → `:99` (build model)
5. `training_support.py:209` (_on_step) → `:225` (evaluacion)
6. `trainer.py:256` (train_profile, la linea `model.learn`)
