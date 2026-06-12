"""Application services for training and evaluation."""

__all__ = ["evaluate", "run_sweep", "train"]


def __getattr__(name: str) -> object:
    if name == "evaluate":
        from doom_agent.services.evaluator import evaluate

        return evaluate
    if name == "run_sweep":
        from doom_agent.services.sweeps import run_sweep

        return run_sweep
    if name == "train":
        from doom_agent.services.trainer import train

        return train
    raise AttributeError(name)
