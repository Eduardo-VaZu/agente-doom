from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import cv2
import gymnasium as gym
import numpy as np
import vizdoom as zd
from gymnasium.core import RenderFrame
from stable_baselines3.common.vec_env import (
    DummyVecEnv,
    VecEnv,
    VecFrameStack,
    VecMonitor,
    VecVideoRecorder,
)

from doom_agent.config.schema import ProjectPaths, TrainingProfile
from doom_agent.envs.reward import RewardShaper
from doom_agent.shared.types import AgentAction, BinaryAction, DictObservation, Observation
from doom_agent.utils.filesystem import ensure_directories

OPPOSING_BUTTON_PAIRS = frozenset(
    {
        frozenset(("MOVE_LEFT", "MOVE_RIGHT")),
        frozenset(("TURN_LEFT", "TURN_RIGHT")),
        frozenset(("MOVE_FORWARD", "MOVE_BACKWARD")),
    }
)


def normalize_rgb_frame(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 3 and frame.shape[0] in {1, 3} and frame.shape[-1] != 3:
        return np.moveaxis(frame, 0, -1)
    return frame


# Preprocesa un cuadro crudo de ViZDoom para que lo consuma la CNN.
# Pasos: ordenar canales -> pasar a gris -> reescalar a (width, height) -> enteros uint8.
def preprocess_frame(frame: np.ndarray, width: int, height: int) -> Observation:
    frame = normalize_rgb_frame(frame)  # asegura formato (alto, ancho, canales)
    if frame.ndim == 3 and frame.shape[-1] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)  # color -> gris (menos datos)

    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)  # a 84x84
    # Forma final (1, alto, ancho) y uint8 (0-255) para ahorrar memoria.
    return resized.reshape(1, height, width).astype(np.uint8)


def extract_audio_features(audio_buffer: np.ndarray | None) -> np.ndarray:
    """RMS por canal + panning + volumen a partir de PCM estereo crudo (int16, shape (N, 2))."""
    if audio_buffer is None or np.asarray(audio_buffer).size == 0:
        return np.zeros(4, dtype=np.float32)

    samples = np.asarray(audio_buffer, dtype=np.float32).reshape(-1, 2) / 32768.0
    left, right = samples[:, 0], samples[:, 1]
    rms_left = float(np.sqrt(np.mean(np.square(left))))
    rms_right = float(np.sqrt(np.mean(np.square(right))))
    total = rms_left + rms_right
    pan = (rms_left - rms_right) / total if total > 1e-6 else 0.0
    loudness = total / 2.0
    return np.array([rms_left, rms_right, pan, loudness], dtype=np.float32)


NOTIFICATION_VOCABULARY: tuple[str, ...] = ("", "Cacodemon", "Demon", "DoomImp")


def parse_notification_label(text: str | None) -> str:
    if not text:
        return ""
    stripped = text.strip()
    prefix = "Shoot: "
    if stripped.startswith(prefix):
        return stripped[len(prefix) :]
    return stripped


def extract_notification_features(
    text: str | None,
    vocabulary: tuple[str, ...] = NOTIFICATION_VOCABULARY,
) -> np.ndarray:
    features = np.zeros(len(vocabulary), dtype=np.float32)
    label = parse_notification_label(text)
    if label in vocabulary:
        features[vocabulary.index(label)] = 1.0
    return features


def observation_feature_dim(observation_mode: str) -> int:
    if observation_mode == "vision_audio":
        return 4
    if observation_mode == "vision_notifications":
        return len(NOTIFICATION_VOCABULARY)
    raise ValueError(f"El modo de observacion '{observation_mode}' no usa features auxiliares.")


def button_name(button: object) -> str:
    name = getattr(button, "name", None)
    if isinstance(name, str):
        return name
    return str(button).rsplit(".", maxsplit=1)[-1]


def has_opposing_buttons(button_names: set[str]) -> bool:
    return any(pair.issubset(button_names) for pair in OPPOSING_BUTTON_PAIRS)


def bucket_position(x: float, y: float, grid_size: float) -> tuple[int, int]:
    return (int(x // grid_size), int(y // grid_size))


def compute_exploration_bonus(
    cell: tuple[int, int],
    visited_cells: set[tuple[int, int]],
    bonus: float,
) -> float:
    if cell in visited_cells:
        return 0.0
    visited_cells.add(cell)
    return bonus


def decayed_exploration_bonus(
    base_bonus: float,
    elapsed_steps: int,
    decay_steps: int,
) -> float:
    if decay_steps <= 0:
        return base_bonus
    progress = min(1.0, elapsed_steps / decay_steps)
    return base_bonus * (1.0 - progress)


# Construye el conjunto de acciones discretas del agente a partir de combos de botones curados.
# Cada preset define que combinaciones tienen sentido para un tipo de escenario.
# Devuelve (etiquetas legibles, vectores binarios de botones) que consume el action space.
def build_button_combination_actions(
    available_button_names: tuple[str, ...],
    preset: str = "default",
) -> tuple[tuple[tuple[str, ...], ...], tuple[BinaryAction, ...]]:
    actions: list[BinaryAction] = []
    labels: list[tuple[str, ...]] = []
    # Mapa nombre-de-boton -> indice, para saber que posicion prender en el vector.
    button_index = {button_name: index for index, button_name in enumerate(available_button_names)}

    # Helper: agrega una accion (combo de botones) al conjunto, filtrando invalidas y repetidas.
    def add_action(selected_buttons: tuple[str, ...]) -> None:
        missing_buttons = set(selected_buttons) - set(button_index)
        if missing_buttons:  # el preset pidio un boton que este escenario no tiene
            raise ValueError(
                "El preset de acciones requiere botones no disponibles: "
                f"{', '.join(sorted(missing_buttons))}."
            )

        selected_button_set = set(selected_buttons)
        if has_opposing_buttons(selected_button_set):
            return  # descarta combos contradictorios (IZQ+DER, ADELANTE+ATRAS, etc.)

        # Codifica el combo como vector binario: 1 = boton presionado, 0 = suelto.
        encoded_action = np.zeros(len(available_button_names), dtype=np.int32)
        for selected_button in selected_buttons:
            encoded_action[button_index[selected_button]] = 1

        if any(np.array_equal(encoded_action, existing_action) for existing_action in actions):
            return  # evita duplicados

        actions.append(encoded_action)
        labels.append(selected_buttons)

    if preset == "basic_combat":
        add_action(("ATTACK",))
        add_action(("MOVE_LEFT", "ATTACK"))
        add_action(("MOVE_RIGHT", "ATTACK"))
        return tuple(labels), tuple(actions)

    if preset == "turn_combat":
        add_action(("ATTACK",))
        add_action(("TURN_LEFT", "ATTACK"))
        add_action(("TURN_RIGHT", "ATTACK"))
        return tuple(labels), tuple(actions)

    if preset == "health_navigation":
        add_action(("MOVE_FORWARD",))
        add_action(("TURN_LEFT", "MOVE_FORWARD"))
        add_action(("TURN_RIGHT", "MOVE_FORWARD"))
        return tuple(labels), tuple(actions)

    if preset == "my_way_home_navigation":
        add_action(("MOVE_FORWARD",))
        add_action(("TURN_LEFT",))
        add_action(("TURN_RIGHT",))
        add_action(("MOVE_LEFT",))
        add_action(("MOVE_RIGHT",))
        return tuple(labels), tuple(actions)

    if preset == "take_cover_dodge":
        add_action(("MOVE_LEFT",))
        add_action(("MOVE_RIGHT",))
        return tuple(labels), tuple(actions)

    if preset == "corridor_combat":
        add_action(("ATTACK",))
        add_action(("MOVE_FORWARD",))
        add_action(("MOVE_FORWARD", "ATTACK"))
        add_action(("MOVE_BACKWARD",))
        add_action(("TURN_LEFT",))
        add_action(("TURN_RIGHT",))
        add_action(("MOVE_LEFT",))
        add_action(("MOVE_RIGHT",))
        return tuple(labels), tuple(actions)

    # Preset para niveles reales completos de Doom: incluye moverse, girar, disparar,
    # avanzar disparando, abrir puertas (USE) y cambiar de arma.
    if preset == "full_doom_basic":
        add_action(("ATTACK",))  # disparar
        add_action(("MOVE_FORWARD",))  # avanzar
        add_action(("MOVE_FORWARD", "ATTACK"))  # avanzar disparando
        add_action(("MOVE_BACKWARD",))  # retroceder
        add_action(("TURN_LEFT",))  # girar izquierda
        add_action(("TURN_RIGHT",))  # girar derecha
        add_action(("MOVE_LEFT",))  # desplazarse a la izquierda
        add_action(("MOVE_RIGHT",))  # desplazarse a la derecha
        add_action(("USE",))  # abrir puertas / activar interruptores
        add_action(("SELECT_NEXT_WEAPON",))  # cambiar de arma
        return tuple(labels), tuple(actions)

    actions.append(np.zeros(len(available_button_names), dtype=np.int32))
    labels.append(("NOOP",))

    for available_button_name in available_button_names:
        add_action((available_button_name,))

    if "ATTACK" in button_index:
        for available_button_name in available_button_names:
            if available_button_name != "ATTACK":
                add_action((available_button_name, "ATTACK"))

    return tuple(labels), tuple(actions)


# Entorno Gymnasium que envuelve un juego ViZDoom. Define que ve el agente (observation_space),
# que puede hacer (action_space) y como avanza el juego (step/reset).
class DoomEnv(gym.Env[Observation | DictObservation, AgentAction]):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 35}

    def __init__(
        self,
        game: zd.DoomGame,
        observation_width: int,
        observation_height: int,
        observation_mode: str,
        action_space_kind: str,
        action_combo_preset: str,
        render_mode: str,
        reward_shaper: RewardShaper,
        exploration_bonus: float = 0.0,
        exploration_grid_size: float = 48.0,
        exploration_bonus_decay_steps: int = 0,
    ) -> None:
        super().__init__()
        self.game = game
        self.observation_width = observation_width
        self.observation_height = observation_height
        self.observation_mode = observation_mode
        self.button_count = self.game.get_available_buttons_size()
        self.action_space_kind = action_space_kind
        self.action_combo_preset = action_combo_preset
        self.render_mode = render_mode
        self.reward_shaper = reward_shaper
        self.exploration_bonus = exploration_bonus
        self.exploration_grid_size = exploration_grid_size
        self.exploration_bonus_decay_steps = exploration_bonus_decay_steps
        self._visited_cells: set[tuple[int, int]] = set()
        self._elapsed_steps = 0
        self.available_button_names = tuple(
            button_name(button) for button in self.game.get_available_buttons()
        )
        self.action_labels: tuple[str, ...] = ()
        self.action_definitions: tuple[BinaryAction, ...] = ()
        self.action_space: gym.Space[Any]

        # Define el ESPACIO DE ACCIONES segun el tipo configurado:
        if self.action_space_kind == "button_combinations":
            # Combos curados: el agente elige 1 entre N combos predefinidos (Discrete).
            labels, actions = build_button_combination_actions(
                self.available_button_names,
                preset=self.action_combo_preset,
            )
            self.action_labels = tuple("+".join(label) for label in labels)
            self.action_definitions = actions
            self.action_space = gym.spaces.Discrete(len(self.action_definitions))
        elif self.action_space_kind == "multidiscrete":
            # Cada boton independiente (mas libre, mas dificil de aprender).
            self.action_space = gym.spaces.MultiDiscrete(
                np.full(self.button_count, 2, dtype=np.int64)
            )
        else:
            # Discreto simple: un boton por accion.
            self.action_space = gym.spaces.Discrete(self.button_count)
        # Define el ESPACIO DE OBSERVACIONES (lo que ve el agente):
        if self.observation_mode in {"vision_audio", "vision_notifications"}:
            # Modo multimodal: imagen + un vector de features (audio o notificaciones).
            self.observation_space = gym.spaces.Dict(
                {
                    "image": gym.spaces.Box(
                        low=0,
                        high=255,
                        shape=(1, self.observation_height, self.observation_width),
                        dtype=np.uint8,
                    ),
                    "features": gym.spaces.Box(
                        low=-1.0,
                        high=1.0,
                        shape=(observation_feature_dim(self.observation_mode),),
                        dtype=np.float32,
                    ),
                }
            )
        else:
            # Modo vision pura: solo la imagen en escala de grises.
            self.observation_space = gym.spaces.Box(
                low=0,
                high=255,
                shape=(1, self.observation_height, self.observation_width),
                dtype=np.uint8,
            )

    def step(
        self,
        action: AgentAction,
    ) -> tuple[Observation | DictObservation, float, bool, bool, dict[str, object]]:
        # Traduce la accion del agente (indice o vector) al vector de botones que espera ViZDoom.
        binary_action = self._normalize_action(action)
        # Ejecuta la accion en el juego; ViZDoom devuelve la recompensa nativa de este paso.
        raw_reward = float(self.game.make_action(binary_action.tolist()))
        self._elapsed_steps += 1
        # Bonus de exploracion: premia pisar celdas nuevas del mapa (se desvanece con el tiempo).
        if self.exploration_bonus > 0 and not self.game.is_episode_finished():
            current_bonus = decayed_exploration_bonus(
                self.exploration_bonus, self._elapsed_steps, self.exploration_bonus_decay_steps
            )
            if current_bonus > 0:
                raw_reward += compute_exploration_bonus(
                    self._current_cell(), self._visited_cells, current_bonus
                )
        reward = self.reward_shaper.apply(raw_reward)  # aplica escala/recorte a la recompensa
        state = self.game.get_state()
        terminated = self.game.is_episode_finished()  # True si el episodio termino (muerte/salida)
        truncated = False  # este entorno no corta episodios por tiempo maximo
        observation = self._observation_from_state(state)  # arma la observacion del nuevo estado
        # info devuelve tanto la recompensa cruda como la ya transformada (util para depurar).
        info: dict[str, object] = {"raw_reward": raw_reward, "shaped_reward": reward}
        if self.action_space_kind == "button_combinations":
            action_index = int(np.asarray(action).item())
            info["action_index"] = action_index
            info["action_label"] = self.action_labels[action_index]
        return observation, reward, terminated, truncated, info

    def reset(
        self,
        seed: int | None = None,
        options: dict[str, object] | None = None,
    ) -> tuple[Observation | DictObservation, dict[str, object]]:
        super().reset(seed=seed)
        self.game.new_episode()  # arranca un episodio nuevo en ViZDoom
        self._visited_cells.clear()  # olvida las celdas visitadas del episodio anterior
        if self.exploration_bonus > 0:
            self._visited_cells.add(self._current_cell())  # marca la celda inicial
        state = self.game.get_state()
        return self._observation_from_state(state), {}  # observacion inicial + info vacia

    def _current_cell(self) -> tuple[int, int]:
        x = self.game.get_game_variable(zd.GameVariable.POSITION_X)
        y = self.game.get_game_variable(zd.GameVariable.POSITION_Y)
        return bucket_position(x, y, self.exploration_grid_size)

    def render(self) -> RenderFrame | list[RenderFrame] | None:
        state = cast(zd.GameState | None, self.game.get_state())
        if state is None:
            return cast(RenderFrame, np.zeros((240, 320, 3), dtype=np.uint8))
        return cast(RenderFrame, normalize_rgb_frame(state.screen_buffer))

    def close(self) -> None:
        self.game.close()

    # Traduce la accion que emite el agente al vector binario de botones que espera ViZDoom.
    def _normalize_action(self, action: AgentAction) -> BinaryAction:
        if self.action_space_kind == "button_combinations":
            # El agente da un indice; lo mapeamos al combo de botones predefinido.
            action_index = int(np.asarray(action).item())
            if action_index < 0 or action_index >= len(self.action_definitions):
                raise ValueError(
                    f"La accion debe estar entre 0 y {len(self.action_definitions) - 1}."
                )
            return self.action_definitions[action_index].copy()

        if self.action_space_kind == "discrete":
            discrete_action = int(np.asarray(action).item())
            if discrete_action < 0 or discrete_action >= self.button_count:
                raise ValueError(
                    f"La accion discreta debe estar entre 0 y {self.button_count - 1}."
                )
            encoded_action = np.zeros(self.button_count, dtype=np.int32)
            encoded_action[discrete_action] = 1
            return encoded_action

        normalized_action = np.asarray(action, dtype=np.int32).reshape(-1)
        if normalized_action.size != self.button_count:
            raise ValueError(
                f"Se esperaban {self.button_count} botones y se recibieron {normalized_action.size}."
            )
        return np.clip(normalized_action, 0, 1)

    # Convierte el estado crudo de ViZDoom en la observacion que consume la red.
    def _observation_from_state(
        self, state: zd.GameState | None
    ) -> Observation | DictObservation:
        # Preprocesa la imagen; si no hay estado (episodio terminado) usa un cuadro en negro.
        image = (
            preprocess_frame(
                state.screen_buffer,
                width=self.observation_width,
                height=self.observation_height,
            )
            if state is not None
            else np.zeros((1, self.observation_height, self.observation_width), dtype=np.uint8)
        )
        # Segun el modo, adjunta features de audio o de notificaciones (o solo imagen).
        if self.observation_mode == "vision_audio":
            audio_buffer = getattr(state, "audio_buffer", None) if state is not None else None
            return {"image": image, "features": extract_audio_features(audio_buffer)}
        if self.observation_mode == "vision_notifications":
            notifications = (
                getattr(state, "notifications_buffer", None) if state is not None else None
            )
            return {"image": image, "features": extract_notification_features(notifications)}
        return image


# Crea e inicializa el juego ViZDoom a partir de la config del escenario.
def build_doom_game(profile: TrainingProfile, project_paths: ProjectPaths) -> zd.DoomGame:
    scenario_path = profile.scenario_path(project_paths)
    game = zd.DoomGame()
    game.load_config(str(Path(scenario_path)))  # carga el .cfg (mapa, botones, reward)
    game.set_seed(profile.seed)  # semilla para reproducibilidad
    game.set_window_visible(profile.render)  # muestra ventana solo si render=True
    game.set_screen_format(zd.ScreenFormat.RGB24)  # formato de la imagen cruda
    game.set_screen_resolution(zd.ScreenResolution.RES_320X240)  # resolucion nativa
    game.init()
    return game


def should_record_video(step: int, frequency: int) -> bool:
    return step == 0 or step % frequency == 0


def make_vectorized_env(
    profile: TrainingProfile,
    project_paths: ProjectPaths,
    *,
    video_dir: Path | None = None,
) -> VecEnv:
    def _build_env() -> DoomEnv:
        game = build_doom_game(profile, project_paths)
        return DoomEnv(
            game=game,
            observation_width=profile.screen_width,
            observation_height=profile.screen_height,
            observation_mode=profile.observation_mode,
            action_space_kind=profile.action_space_kind,
            action_combo_preset=profile.action_combo_preset,
            render_mode="rgb_array",
            reward_shaper=RewardShaper(profile.reward_shaping),
            exploration_bonus=profile.exploration_bonus,
            exploration_grid_size=profile.exploration_grid_size,
            exploration_bonus_decay_steps=profile.exploration_bonus_decay_steps,
        )

    env: VecEnv = DummyVecEnv([_build_env])  # SB3 espera un entorno "vectorizado" aunque sea 1 solo
    env = VecMonitor(env)  # registra recompensa y duracion de cada episodio
    env = VecFrameStack(env, n_stack=profile.frame_stack)  # APILA los N cuadros (movimiento)

    if profile.record_video:
        resolved_video_dir = project_paths.videos_dir if video_dir is None else video_dir
        ensure_directories([resolved_video_dir])
        env = VecVideoRecorder(
            venv=env,
            video_folder=str(resolved_video_dir),
            record_video_trigger=lambda step: should_record_video(
                step, profile.video_record_frequency
            ),
            video_length=profile.video_length,
            name_prefix=profile.checkpoint_name,
        )
    return env
