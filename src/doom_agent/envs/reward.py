from __future__ import annotations

from doom_agent.config.schema import RewardShapingConfig


# Envuelve el reward shaping en su propia clase para mantenerlo FUERA del entorno.
# El entorno (DoomEnv) solo llama a apply(); la logica de escala/recorte vive aca y en la config.
class RewardShaper:
    """Applies deterministic reward shaping configured outside the environment code."""

    def __init__(self, config: RewardShapingConfig) -> None:
        # Guarda la configuracion (scale, offset, clip_min, clip_max) que define la transformacion.
        self.config = config

    def apply(self, reward: float) -> float:
        # Delega en la config: shaped = (reward + offset) * scale, luego recorta al rango permitido.
        return self.config.apply(reward)
