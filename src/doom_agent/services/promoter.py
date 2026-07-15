from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from doom_agent.config import DEFAULT_PROFILE_NAME, build_project_paths
from doom_agent.services.evaluator import evaluate
from doom_agent.services.workspace_handoff import (
    publish_local_workspace_state,
    update_local_workspace_pointer,
)
from doom_agent.shared.contracts import CheckpointSelection, EvaluationSummaryPayload
from doom_agent.utils.checkpoints import (
    copy_checkpoint_bundle,
    load_checkpoint_metadata,
    promoted_checkpoint_stem,
    update_checkpoint_metadata,
)


@dataclass(frozen=True, slots=True)
class PromotionResult:
    source_checkpoint_path: Path
    promoted_checkpoint_path: Path
    summary: EvaluationSummaryPayload


def promote_checkpoint(
    checkpoint_name: str | None = None,
    *,
    episodes: int = 50,
    profile_name: str = DEFAULT_PROFILE_NAME,
    checkpoint_selection: CheckpointSelection = "exact",
    scenario_name: str | None = None,
) -> PromotionResult:
    if episodes <= 0:
        raise ValueError("'episodes' debe ser mayor que cero.")

    project_paths = build_project_paths()
    summary = evaluate(
        checkpoint_name=checkpoint_name,
        episodes=episodes,
        profile_name=profile_name,
        checkpoint_selection=checkpoint_selection,
        scenario_name=scenario_name,
        render=False,
        json_output=False,
    )
    if summary is None:
        raise RuntimeError("La evaluacion offline no devolvio resumen.")

    source_checkpoint_path = Path(summary["checkpoint_path"])
    source_checkpoint_stem = source_checkpoint_path.with_suffix("")
    source_metadata = load_checkpoint_metadata(source_checkpoint_stem)
    if source_metadata is None:
        raise ValueError("No se puede promover un checkpoint legacy sin metadata estructurada.")

    source_checkpoint_name = source_metadata["profile"]["checkpoint_name"]
    promoted_checkpoint_path = (
        project_paths.checkpoints_dir
        / promoted_checkpoint_stem(Path(source_checkpoint_name)).with_suffix(".zip").name
    )
    promoted_checkpoint_stem_path = promoted_checkpoint_path.with_suffix("")

    if source_checkpoint_stem == promoted_checkpoint_stem_path:
        raise ValueError("El checkpoint origen ya corresponde al alias promovido.")

    copy_checkpoint_bundle(source_checkpoint_stem, promoted_checkpoint_stem_path)
    update_checkpoint_metadata(
        promoted_checkpoint_stem_path,
        saved_at_utc=datetime.now(UTC).isoformat(),
        training_status="promoted_checkpoint",
        checkpoint_role="promoted",
        evaluation_source="offline_cli",
        canonical_checkpoint_path=str(source_checkpoint_path),
        evaluation_metrics=summary["metrics"],
        is_best_checkpoint=True,
    )
    try:
        update_local_workspace_pointer(
            promoted_checkpoint_path,
            pointer_kind="promoted",
            root_dir=project_paths.root_dir,
        )
        if project_paths.root_dir.exists():
            publish_local_workspace_state(root_dir=project_paths.root_dir)
    except ValueError:
        pass
    except Exception:
        pass

    return PromotionResult(
        source_checkpoint_path=source_checkpoint_path,
        promoted_checkpoint_path=promoted_checkpoint_path,
        summary=summary,
    )
