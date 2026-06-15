"""Application services for training and evaluation."""

__all__ = ["evaluate", "train"]


def __getattr__(name: str) -> object:
    if name == "evaluate":
        from doom_agent.services.evaluator import evaluate

        return evaluate
    if name == "train":
        from doom_agent.services.trainer import train

        return train
    raise AttributeError(name)
