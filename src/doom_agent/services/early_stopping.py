from __future__ import annotations

from dataclasses import dataclass
from math import inf

from doom_agent.config.schema import EarlyStoppingConfig


@dataclass(slots=True)
class EarlyStoppingTracker:
    config: EarlyStoppingConfig
    best_mean_reward: float = -inf
    evaluations_seen: int = 0
    no_improvement_evaluations: int = 0
    stopped: bool = False
    stop_reason: str | None = None

    def register(self, mean_reward: float) -> bool:
        improved = mean_reward > (self.best_mean_reward + self.config.min_delta)
        self.evaluations_seen += 1

        if improved:
            self.best_mean_reward = mean_reward
            self.no_improvement_evaluations = 0
        else:
            self.no_improvement_evaluations += 1

        if (
            self.config.enabled
            and self.evaluations_seen >= self.config.min_evaluations
            and self.no_improvement_evaluations >= self.config.patience_evaluations
        ):
            self.stopped = True
            self.stop_reason = (
                "Early stopping activado por falta de mejora en evaluacion: "
                f"{self.no_improvement_evaluations} evaluaciones sin superar "
                f"min_delta={self.config.min_delta}."
            )
        return improved
