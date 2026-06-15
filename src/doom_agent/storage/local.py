from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doom_agent.config.schema import ProjectPaths


@dataclass(frozen=True, slots=True)
class RunArtifactPaths:
    run_id: str
    run_dir: Path
    checkpoints_dir: Path
    videos_dir: Path
    tensorboard_dir: Path
    report_path: Path
    final_checkpoint_stem: Path
    best_checkpoint_stem: Path


def build_run_artifact_paths(project_paths: ProjectPaths, run_id: str) -> RunArtifactPaths:
    run_dir = project_paths.runs_dir / run_id
    checkpoints_dir = run_dir / "checkpoints"
    return RunArtifactPaths(
        run_id=run_id,
        run_dir=run_dir,
        checkpoints_dir=checkpoints_dir,
        videos_dir=run_dir / "videos",
        tensorboard_dir=run_dir / "tensorboard",
        report_path=run_dir / "report.json",
        final_checkpoint_stem=checkpoints_dir / "final_model",
        best_checkpoint_stem=checkpoints_dir / "best_model",
    )
