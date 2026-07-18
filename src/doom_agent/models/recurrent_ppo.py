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


# Extractor de features para observaciones de solo imagen (visión pura).
# Convierte la pila de cuadros en un vector de 512 números que luego alimenta al LSTM.
class DoomFeatureExtractor(BaseFeaturesExtractor):
    """CNN extractor tuned for stacked grayscale observations."""

    def __init__(self, observation_space: gym.Space[Observation], features_dim: int = 512) -> None:
        super().__init__(observation_space, features_dim)
        shape = cast(tuple[int, ...], observation_space.shape)
        input_channels = shape[0]  # canales de entrada = frames apilados (p.ej. 4)
        # Red convolucional estilo Nature-DQN: tres capas conv + ReLU que detectan
        # patrones cada vez mas abstractos (bordes -> formas -> enemigos/paredes/items).
        self.cnn = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=8, stride=4),  # capa 1: filtros grandes
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),  # capa 2: filtros medianos
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),  # capa 3: filtros finos
            nn.ReLU(),
            nn.Flatten(),  # aplana el mapa de features a un vector 1D
        )

        # Pasa una observacion de ejemplo por la CNN para medir el tamano del vector aplanado.
        with th.no_grad():
            sample = th.as_tensor(observation_space.sample()[None]).float()
            flattened_size = self.cnn(sample).shape[1]

        # Capa lineal final: proyecta el vector aplanado a exactamente features_dim (512).
        self.projection = nn.Sequential(
            nn.Linear(flattened_size, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: th.Tensor) -> th.Tensor:
        # Imagen -> CNN -> proyeccion -> 512 features con significado.
        return cast(th.Tensor, self.projection(self.cnn(observations)))


# Extractor multimodal: imagen + un vector de features auxiliares (audio o notificaciones).
# Procesa cada modalidad por separado y las concatena en un unico vector de 512.
class DoomMultiModalFeatureExtractor(BaseFeaturesExtractor):
    """CNN sobre 'image' + MLP sobre 'features', concatenados y proyectados."""

    def __init__(
        self,
        observation_space: gym.spaces.Dict,
        features_dim: int = 512,
        cnn_features_dim: int = 448,  # cuanto aporta la rama de imagen
        mlp_features_dim: int = 64,  # cuanto aporta la rama auxiliar (audio/notificaciones)
    ) -> None:
        super().__init__(observation_space, features_dim)
        image_space = observation_space.spaces["image"]
        features_space = observation_space.spaces["features"]
        image_shape = cast(tuple[int, ...], image_space.shape)
        input_channels = image_shape[0]

        # Rama de imagen: misma CNN estilo Nature-DQN que en el modo de solo vision.
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
        # Proyecta la salida de la CNN a 448 features.
        self.cnn_projection = nn.Sequential(
            nn.Linear(flattened_size, cnn_features_dim),
            nn.ReLU(),
        )

        # Rama auxiliar: un MLP pequeno que procesa el vector de features (audio o notificaciones).
        feature_dim = cast(tuple[int, ...], features_space.shape)[0]
        self.mlp = nn.Sequential(
            nn.Linear(feature_dim, 64),
            nn.ReLU(),
            nn.Linear(64, mlp_features_dim),  # -> 64 features
            nn.ReLU(),
        )

        # Une las dos ramas (448 + 64 = 512) y las proyecta al vector final de 512.
        self.output_projection = nn.Sequential(
            nn.Linear(cnn_features_dim + mlp_features_dim, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: dict[str, th.Tensor]) -> th.Tensor:
        image_features = self.cnn_projection(self.cnn(observations["image"]))  # rama imagen
        aux_features = self.mlp(observations["features"])  # rama audio/notificaciones
        combined = th.cat([image_features, aux_features], dim=1)  # concatena ambas ramas
        return cast(th.Tensor, self.output_projection(combined))  # -> 512 features


# Construye el modelo RecurrentPPO (PPO + LSTM) con TODOS los hiperparametros de la config.
# El LSTM lo aporta la propia politica de sb3-contrib; nosotros inyectamos nuestro extractor CNN.
def build_recurrent_ppo_model(
    env: VecEnv,
    profile: TrainingProfile,
    tensorboard_log_dir: str,
) -> RecurrentPPO:
    # Si la observacion es un dict (imagen + features) usamos la politica y el extractor multimodal;
    # si es solo imagen, la politica y el extractor de vision pura. Ambas politicas llevan LSTM.
    is_dict_observation = isinstance(env.observation_space, gym.spaces.Dict)
    policy = "MultiInputLstmPolicy" if is_dict_observation else "CnnLstmPolicy"
    features_extractor_class = (
        DoomMultiModalFeatureExtractor if is_dict_observation else DoomFeatureExtractor
    )
    return RecurrentPPO(
        policy=policy,
        env=env,
        learning_rate=profile.learning_rate,  # tamano del paso de ajuste
        n_steps=profile.n_steps,  # largo del rollout y horizonte del BPTT
        batch_size=profile.batch_size,  # muestras por minibatch
        n_epochs=profile.n_epochs,  # pasadas de aprendizaje por lote
        gamma=profile.gamma,  # descuento de la recompensa futura
        gae_lambda=profile.gae_lambda,  # sesgo/varianza de la ventaja (GAE)
        ent_coef=profile.ent_coef,  # fuerza de exploracion (bonus de entropia)
        seed=profile.seed,  # semilla para reproducibilidad
        tensorboard_log=tensorboard_log_dir,
        verbose=1,
        # Inyecta nuestra CNN como extractor de features de la politica.
        policy_kwargs={"features_extractor_class": features_extractor_class},
    )
