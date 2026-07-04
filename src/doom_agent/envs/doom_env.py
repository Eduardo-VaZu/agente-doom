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
from doom_agent.shared.types import AgentAction, BinaryAction, Observation
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


def preprocess_frame(frame: np.ndarray, width: int, height: int) -> Observation:
    frame = normalize_rgb_frame(frame)
    if frame.ndim == 3 and frame.shape[-1] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return resized.reshape(1, height, width).astype(np.uint8)


def button_name(button: object) -> str:
    name = getattr(button, "name", None)
    if isinstance(name, str):
        return name
    return str(button).rsplit(".", maxsplit=1)[-1]


def has_opposing_buttons(button_names: set[str]) -> bool:
    return any(pair.issubset(button_names) for pair in OPPOSING_BUTTON_PAIRS)


def build_button_combination_actions(
    available_button_names: tuple[str, ...],
    preset: str = "default",
) -> tuple[tuple[tuple[str, ...], ...], tuple[BinaryAction, ...]]:
    actions: list[BinaryAction] = []
    labels: list[tuple[str, ...]] = []
    button_index = {button_name: index for index, button_name in enumerate(available_button_names)}

    def add_action(selected_buttons: tuple[str, ...]) -> None:
        missing_buttons = set(selected_buttons) - set(button_index)
        if missing_buttons:
            raise ValueError(
                "El preset de acciones requiere botones no disponibles: "
                f"{', '.join(sorted(missing_buttons))}."
            )

        selected_button_set = set(selected_buttons)
        if has_opposing_buttons(selected_button_set):
            return

        encoded_action = np.zeros(len(available_button_names), dtype=np.int32)
        for selected_button in selected_buttons:
            encoded_action[button_index[selected_button]] = 1

        if any(np.array_equal(encoded_action, existing_action) for existing_action in actions):
            return

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

    if preset == "take_cover_dodge":
        add_action(("MOVE_LEFT",))
        add_action(("MOVE_RIGHT",))
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


class DoomEnv(gym.Env[Observation, AgentAction]):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 35}

    def __init__(
        self,
        game: zd.DoomGame,
        observation_width: int,
        observation_height: int,
        action_space_kind: str,
        action_combo_preset: str,
        render_mode: str,
        reward_shaper: RewardShaper,
    ) -> None:
        super().__init__()
        self.game = game
        self.observation_width = observation_width
        self.observation_height = observation_height
        self.button_count = self.game.get_available_buttons_size()
        self.action_space_kind = action_space_kind
        self.action_combo_preset = action_combo_preset
        self.render_mode = render_mode
        self.reward_shaper = reward_shaper
        self.available_button_names = tuple(
            button_name(button) for button in self.game.get_available_buttons()
        )
        self.action_labels: tuple[str, ...] = ()
        self.action_definitions: tuple[BinaryAction, ...] = ()
        self.action_space: gym.Space[Any]

        if self.action_space_kind == "button_combinations":
            labels, actions = build_button_combination_actions(
                self.available_button_names,
                preset=self.action_combo_preset,
            )
            self.action_labels = tuple("+".join(label) for label in labels)
            self.action_definitions = actions
            self.action_space = gym.spaces.Discrete(len(self.action_definitions))
        elif self.action_space_kind == "multidiscrete":
            self.action_space = gym.spaces.MultiDiscrete(
                np.full(self.button_count, 2, dtype=np.int64)
            )
        else:
            self.action_space = gym.spaces.Discrete(self.button_count)
        self.observation_space = gym.spaces.Box(
            low=0,
            high=255,
            shape=(1, self.observation_height, self.observation_width),
            dtype=np.uint8,
        )

    def step(
        self,
        action: AgentAction,
    ) -> tuple[Observation, float, bool, bool, dict[str, object]]:
        binary_action = self._normalize_action(action)
        raw_reward = float(self.game.make_action(binary_action.tolist()))
        reward = self.reward_shaper.apply(raw_reward)
        state = self.game.get_state()
        terminated = self.game.is_episode_finished()
        truncated = False
        observation = self._observation_from_state(state)
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
    ) -> tuple[Observation, dict[str, object]]:
        super().reset(seed=seed)
        self.game.new_episode()
        state = self.game.get_state()
        return self._observation_from_state(state), {}

    def render(self) -> RenderFrame | list[RenderFrame] | None:
        state = cast(zd.GameState | None, self.game.get_state())
        if state is None:
            return cast(RenderFrame, np.zeros((240, 320, 3), dtype=np.uint8))
        return cast(RenderFrame, normalize_rgb_frame(state.screen_buffer))

    def close(self) -> None:
        self.game.close()

    def _normalize_action(self, action: AgentAction) -> BinaryAction:
        if self.action_space_kind == "button_combinations":
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

    def _observation_from_state(self, state: zd.GameState | None) -> Observation:
        if state is None:
            shape = cast(tuple[int, int, int], self.observation_space.shape)
            return np.zeros(shape, dtype=np.uint8)
        return preprocess_frame(
            state.screen_buffer,
            width=self.observation_width,
            height=self.observation_height,
        )


def build_doom_game(profile: TrainingProfile, project_paths: ProjectPaths) -> zd.DoomGame:
    scenario_path = profile.scenario_path(project_paths)
    game = zd.DoomGame()
    game.load_config(str(Path(scenario_path)))
    game.set_seed(profile.seed)
    game.set_window_visible(profile.render)
    game.set_screen_format(zd.ScreenFormat.RGB24)
    game.set_screen_resolution(zd.ScreenResolution.RES_320X240)
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
            action_space_kind=profile.action_space_kind,
            action_combo_preset=profile.action_combo_preset,
            render_mode="rgb_array",
            reward_shaper=RewardShaper(profile.reward_shaping),
        )

    env: VecEnv = DummyVecEnv([_build_env])
    env = VecMonitor(env)
    env = VecFrameStack(env, n_stack=profile.frame_stack)

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
