from __future__ import annotations

from typing import cast

import gymnasium as gym
import torch as th
import torch.nn as nn
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.vec_env import VecEnv

from doom_agent.config.schema import TrainingProfile
from doom_agent.shared.types import Observation


class DoomFeatureExtractor(BaseFeaturesExtractor):
    """CNN extractor tuned for stacked grayscale observations."""

    def __init__(self, observation_space: gym.Space[Observation], features_dim: int = 512) -> None:
        super().__init__(observation_space, features_dim)
        shape = cast(tuple[int, ...], observation_space.shape)
        input_channels = shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Flatten(),
        )

        with th.no_grad():
            sample = th.as_tensor(observation_space.sample()[None]).float()
            flattened_size = self.cnn(sample).shape[1]

        self.projection = nn.Sequential(
            nn.Linear(flattened_size, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: th.Tensor) -> th.Tensor:
        return cast(th.Tensor, self.projection(self.cnn(observations)))


class DoomMultiModalFeatureExtractor(BaseFeaturesExtractor):
    """CNN sobre 'image' + MLP sobre 'features', concatenados y proyectados."""

    def __init__(
        self,
        observation_space: gym.spaces.Dict,
        features_dim: int = 512,
        cnn_features_dim: int = 448,
        mlp_features_dim: int = 64,
    ) -> None:
        super().__init__(observation_space, features_dim)
        image_space = observation_space.spaces["image"]
        features_space = observation_space.spaces["features"]
        image_shape = cast(tuple[int, ...], image_space.shape)
        input_channels = image_shape[0]

        self.cnn = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        with th.no_grad():
            sample = th.as_tensor(image_space.sample()[None]).float()
            flattened_size = self.cnn(sample).shape[1]
        self.cnn_projection = nn.Sequential(
            nn.Linear(flattened_size, cnn_features_dim),
            nn.ReLU(),
        )

        feature_dim = cast(tuple[int, ...], features_space.shape)[0]
        self.mlp = nn.Sequential(
            nn.Linear(feature_dim, 64),
            nn.ReLU(),
            nn.Linear(64, mlp_features_dim),
            nn.ReLU(),
        )

        self.output_projection = nn.Sequential(
            nn.Linear(cnn_features_dim + mlp_features_dim, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: dict[str, th.Tensor]) -> th.Tensor:
        image_features = self.cnn_projection(self.cnn(observations["image"]))
        aux_features = self.mlp(observations["features"])
        combined = th.cat([image_features, aux_features], dim=1)
        return cast(th.Tensor, self.output_projection(combined))


def build_recurrent_ppo_model(
    env: VecEnv,
    profile: TrainingProfile,
    tensorboard_log_dir: str,
) -> RecurrentPPO:
    is_dict_observation = isinstance(env.observation_space, gym.spaces.Dict)
    policy = "MultiInputLstmPolicy" if is_dict_observation else "CnnLstmPolicy"
    features_extractor_class = (
        DoomMultiModalFeatureExtractor if is_dict_observation else DoomFeatureExtractor
    )
    return RecurrentPPO(
        policy=policy,
        env=env,
        learning_rate=profile.learning_rate,
        n_steps=profile.n_steps,
        batch_size=profile.batch_size,
        n_epochs=profile.n_epochs,
        gamma=profile.gamma,
        gae_lambda=profile.gae_lambda,
        ent_coef=profile.ent_coef,
        seed=profile.seed,
        tensorboard_log=tensorboard_log_dir,
        verbose=1,
        policy_kwargs={"features_extractor_class": features_extractor_class},
    )
