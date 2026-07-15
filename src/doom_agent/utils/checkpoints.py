from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from doom_agent.config.schema import ProjectPaths, TrainingProfile
from doom_agent.shared.contracts import (
    CheckpointMetadataPayload,
    CheckpointSelection,
    EvaluationMetricsPayload,
    SaveableModel,
)
from doom_agent.utils.filesystem import read_json, write_json


@dataclass(frozen=True, slots=True)
class ResolvedCheckpoint:
    checkpoint_stem: Path
    metadata: CheckpointMetadataPayload | None
    saved_timesteps: int | None


def checkpoint_zip_path(checkpoint_stem: Path) -> Path:
    return checkpoint_stem.with_suffix(".zip")


def checkpoint_metadata_path(checkpoint_stem: Path) -> Path:
    return checkpoint_stem.with_suffix(".json")


def best_checkpoint_stem(checkpoint_stem: Path) -> Path:
    if checkpoint_stem.name.endswith("_best"):
        return checkpoint_stem
    return checkpoint_stem.with_name(f"{checkpoint_stem.name}_best")


def active_checkpoint_stem(checkpoint_stem: Path) -> Path:
    if checkpoint_stem.name.endswith("_active"):
        return checkpoint_stem
    return checkpoint_stem.with_name(f"{checkpoint_stem.name}_active")


def promoted_checkpoint_stem(checkpoint_stem: Path) -> Path:
    if checkpoint_stem.name.endswith("_promoted"):
        return checkpoint_stem
    return checkpoint_stem.with_name(f"{checkpoint_stem.name}_promoted")


def build_checkpoint_metadata(
    profile_name: str,
    profile: TrainingProfile,
    saved_timesteps: int | None = None,
    *,
    run_id: str | None = None,
    resume_source: str | None = None,
    resume_saved_timesteps: int | None = None,
    training_status: str | None = None,
    checkpoint_role: str | None = None,
    evaluation_source: str | None = None,
    canonical_checkpoint_path: str | None = None,
    evaluation_metrics: EvaluationMetricsPayload | None = None,
    is_best_checkpoint: bool = False,
) -> CheckpointMetadataPayload:
    payload: CheckpointMetadataPayload = {
        "profile_name": profile_name,
        "run_id": run_id,
        "saved_timesteps": saved_timesteps
        if saved_timesteps is not None
        else profile.effective_timesteps,
        "saved_at_utc": datetime.now(UTC).isoformat(),
        "profile": profile.to_dict(),
        "resume_source": resume_source,
        "resume_saved_timesteps": resume_saved_timesteps,
        "training_status": training_status,
        "checkpoint_role": checkpoint_role,
        "evaluation_source": evaluation_source,
        "canonical_checkpoint_path": canonical_checkpoint_path,
        "evaluation_metrics": evaluation_metrics,
        "is_best_checkpoint": is_best_checkpoint,
    }
    return payload


def _resolved_checkpoint_from_stem(checkpoint_stem: Path) -> ResolvedCheckpoint:
    metadata = load_checkpoint_metadata(checkpoint_stem)
    saved_timesteps = extract_saved_timesteps(checkpoint_stem, metadata)
    return ResolvedCheckpoint(
        checkpoint_stem=checkpoint_stem,
        metadata=metadata,
        saved_timesteps=saved_timesteps,
    )


def save_checkpoint_bundle(
    model: SaveableModel,
    checkpoint_stem: Path,
    metadata: CheckpointMetadataPayload,
) -> None:
    model.save(str(checkpoint_stem))
    write_json(checkpoint_metadata_path(checkpoint_stem), metadata)


def _copy2_with_retry(source: Path, target: Path, attempts: int = 6, delay_seconds: float = 0.5) -> None:
    for attempt in range(1, attempts + 1):
        try:
            shutil.copy2(source, target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(delay_seconds * attempt)


def copy_checkpoint_bundle(source_stem: Path, target_stem: Path) -> None:
    _copy2_with_retry(checkpoint_zip_path(source_stem), checkpoint_zip_path(target_stem))
    source_metadata_path = checkpoint_metadata_path(source_stem)
    if source_metadata_path.exists():
        _copy2_with_retry(source_metadata_path, checkpoint_metadata_path(target_stem))


def update_checkpoint_metadata(
    checkpoint_stem: Path,
    **overrides: object,
) -> CheckpointMetadataPayload | None:
    metadata = load_checkpoint_metadata(checkpoint_stem)
    if metadata is None:
        return None

    updated_metadata = dict(metadata)
    updated_metadata.update(overrides)
    write_json(
        checkpoint_metadata_path(checkpoint_stem),
        cast(CheckpointMetadataPayload, updated_metadata),
    )
    return cast(CheckpointMetadataPayload, updated_metadata)


def load_checkpoint_metadata(checkpoint_stem: Path) -> CheckpointMetadataPayload | None:
    metadata_path = checkpoint_metadata_path(checkpoint_stem)
    if not metadata_path.exists():
        return None
    return cast(CheckpointMetadataPayload, read_json(metadata_path))


def resolve_checkpoint_stem(project_paths: ProjectPaths, checkpoint_name: str) -> Path:
    candidate = Path(checkpoint_name)
    if candidate.suffix == ".zip":
        candidate = candidate.with_suffix("")

    search_candidates: list[Path]
    if candidate.parent != Path("."):
        search_candidates = [candidate]
    else:
        search_candidates = [
            project_paths.checkpoints_dir / candidate.name,
            project_paths.auto_checkpoints_dir / candidate.name,
            project_paths.legacy_checkpoints_dir / candidate.name,
            project_paths.legacy_auto_checkpoints_dir / candidate.name,
        ]

    for checkpoint_stem in search_candidates:
        if checkpoint_zip_path(checkpoint_stem).exists():
            return checkpoint_stem

    searched = ", ".join(str(path) for path in search_candidates)
    raise FileNotFoundError(
        f"No se encontro el checkpoint '{checkpoint_name}'. Rutas buscadas: {searched}"
    )


def extract_saved_timesteps(
    checkpoint_stem: Path,
    metadata: CheckpointMetadataPayload | None = None,
) -> int | None:
    checkpoint_metadata = (
        metadata if metadata is not None else load_checkpoint_metadata(checkpoint_stem)
    )
    if checkpoint_metadata is not None and checkpoint_metadata.get("saved_timesteps") is not None:
        return int(checkpoint_metadata["saved_timesteps"])

    stem_name = checkpoint_stem.name
    if stem_name.endswith("_steps"):
        value = stem_name.rsplit("_", 2)[-2]
        if value.isdigit():
            return int(value)
    return None


def resolve_checkpoint(project_paths: ProjectPaths, checkpoint_name: str) -> ResolvedCheckpoint:
    checkpoint_stem = resolve_checkpoint_stem(project_paths, checkpoint_name)
    return _resolved_checkpoint_from_stem(checkpoint_stem)


def list_matching_checkpoints(
    search_dir: Path,
    checkpoint_prefix: str,
    *,
    include_best: bool = False,
) -> list[ResolvedCheckpoint]:
    matches: list[ResolvedCheckpoint] = []
    if not search_dir.exists():
        return matches

    for checkpoint_zip in search_dir.glob(f"{checkpoint_prefix}*.zip"):
        checkpoint_stem = checkpoint_zip.with_suffix("")
        if not include_best and checkpoint_stem.name.endswith("_best"):
            continue
        metadata = load_checkpoint_metadata(checkpoint_stem)
        matches.append(
            ResolvedCheckpoint(
                checkpoint_stem=checkpoint_stem,
                metadata=metadata,
                saved_timesteps=extract_saved_timesteps(checkpoint_stem, metadata),
            )
        )
    return matches


def select_latest_checkpoint(candidates: list[ResolvedCheckpoint]) -> ResolvedCheckpoint | None:
    if not candidates:
        return None

    def sort_key(candidate: ResolvedCheckpoint) -> tuple[int, float]:
        timesteps = candidate.saved_timesteps if candidate.saved_timesteps is not None else -1
        modified = checkpoint_zip_path(candidate.checkpoint_stem).stat().st_mtime
        return timesteps, modified

    return max(candidates, key=sort_key)


def resolve_latest_checkpoint(
    project_paths: ProjectPaths, checkpoint_prefix: str
) -> ResolvedCheckpoint | None:
    try:
        return resolve_checkpoint(
            project_paths, promoted_checkpoint_stem(Path(checkpoint_prefix)).name
        )
    except FileNotFoundError:
        pass

    candidates = [
        *list_matching_checkpoints(project_paths.checkpoints_dir, checkpoint_prefix),
        *list_matching_checkpoints(project_paths.auto_checkpoints_dir, checkpoint_prefix),
        *list_matching_checkpoints(project_paths.legacy_checkpoints_dir, checkpoint_prefix),
        *list_matching_checkpoints(project_paths.legacy_auto_checkpoints_dir, checkpoint_prefix),
    ]
    return select_latest_checkpoint(candidates)


def resolve_resume_checkpoint(
    project_paths: ProjectPaths, checkpoint_prefix: str
) -> ResolvedCheckpoint | None:
    try:
        return resolve_checkpoint(project_paths, active_checkpoint_stem(Path(checkpoint_prefix)).name)
    except FileNotFoundError:
        pass

    try:
        return resolve_checkpoint(
            project_paths, promoted_checkpoint_stem(Path(checkpoint_prefix)).name
        )
    except FileNotFoundError:
        pass

    return resolve_latest_checkpoint(project_paths, checkpoint_prefix)


def list_all_checkpoints(project_paths: ProjectPaths) -> list[ResolvedCheckpoint]:
    candidates = [
        *list_matching_checkpoints(project_paths.checkpoints_dir, "", include_best=True),
        *list_matching_checkpoints(project_paths.auto_checkpoints_dir, "", include_best=True),
        *list_matching_checkpoints(project_paths.legacy_checkpoints_dir, "", include_best=True),
        *list_matching_checkpoints(
            project_paths.legacy_auto_checkpoints_dir, "", include_best=True
        ),
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.saved_timesteps if candidate.saved_timesteps is not None else -1,
            checkpoint_zip_path(candidate.checkpoint_stem).stat().st_mtime,
        ),
        reverse=True,
    )


def resolve_checkpoint_preference(
    project_paths: ProjectPaths,
    checkpoint_name: str,
    preference: CheckpointSelection = "exact",
) -> ResolvedCheckpoint:
    if preference == "exact":
        return resolve_checkpoint(project_paths, checkpoint_name)

    candidate = Path(checkpoint_name)
    if candidate.suffix == ".zip":
        candidate = candidate.with_suffix("")

    if preference == "last":
        if candidate.parent != Path(".") or candidate.name.endswith("_best"):
            return resolve_checkpoint(project_paths, checkpoint_name)

        latest_checkpoint = resolve_latest_checkpoint(project_paths, candidate.name)
        if latest_checkpoint is not None:
            return latest_checkpoint
        return resolve_checkpoint(project_paths, checkpoint_name)

    preferred_promoted = promoted_checkpoint_stem(candidate)
    preferred_best = best_checkpoint_stem(candidate)
    if candidate.parent != Path("."):
        if checkpoint_zip_path(preferred_promoted).exists():
            return _resolved_checkpoint_from_stem(preferred_promoted)
        if checkpoint_zip_path(preferred_best).exists():
            return _resolved_checkpoint_from_stem(preferred_best)
        return resolve_checkpoint(project_paths, checkpoint_name)

    try:
        return resolve_checkpoint(project_paths, preferred_promoted.name)
    except FileNotFoundError:
        pass

    try:
        return resolve_checkpoint(project_paths, preferred_best.name)
    except FileNotFoundError:
        return resolve_checkpoint(project_paths, checkpoint_name)
