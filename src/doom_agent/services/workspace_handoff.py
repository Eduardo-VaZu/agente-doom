from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal, cast

from doom_agent.config import DEFAULT_PROFILE_NAME, build_project_paths, get_training_profile
from doom_agent.config.schema import ProjectPaths
from doom_agent.shared.contracts import (
    CheckpointMetadataPayload,
    RunManifestArtifactPayload,
    RunManifestPayload,
    TrainingRunReportPayload,
    WorkspaceCheckpointLinePayload,
    WorkspaceCheckpointPointerPayload,
    WorkspaceStatePayload,
)
from doom_agent.storage import (
    DEFAULT_OBJECT_PREFIX,
    ArtifactStore,
    RunArtifactPaths,
    S3ArtifactStore,
    build_run_artifact_paths,
    guess_content_type,
    has_explicit_remote_storage_config,
)
from doom_agent.utils.checkpoints import (
    active_checkpoint_stem,
    checkpoint_metadata_path,
    checkpoint_zip_path,
    copy_checkpoint_bundle,
    load_checkpoint_metadata,
    promoted_checkpoint_stem,
    update_checkpoint_metadata,
)
from doom_agent.utils.filesystem import ensure_directories, read_json, write_json

PointerKind = Literal["active", "promoted"]
POINTER_KINDS: tuple[PointerKind, PointerKind] = ("active", "promoted")

WORKSPACE_STATE_FILE_NAME = "workspace_state.json"
WORKSPACE_REMOTE_DIR = "workspace"
WORKSPACE_REMOTE_CHECKPOINTS_DIR = f"{WORKSPACE_REMOTE_DIR}/checkpoints"


@dataclass(frozen=True, slots=True)
class WorkspacePointerUpdateResult:
    checkpoint_name: str
    pointer_kind: PointerKind
    alias_path: Path
    run_id: str
    state_path: Path


@dataclass(frozen=True, slots=True)
class WorkspacePublishResult:
    state_path: Path
    uploaded: bool
    alias_count: int
    state_object_key: str | None


@dataclass(frozen=True, slots=True)
class HydratedWorkspacePointer:
    checkpoint_name: str
    pointer_kind: PointerKind
    run_id: str
    local_alias_path: Path
    restored_run_checkpoint_path: Path | None
    restored_report_path: Path | None


@dataclass(frozen=True, slots=True)
class HydrateWorkspaceResult:
    checkpoint_name: str
    state_path: Path
    hydrated_pointers: list[HydratedWorkspacePointer]


def workspace_state_path(root_dir: Path | None = None) -> Path:
    project_paths = build_project_paths(root_dir=root_dir)
    return project_paths.artifacts_dir / WORKSPACE_STATE_FILE_NAME


def load_local_workspace_state(root_dir: Path | None = None) -> WorkspaceStatePayload:
    state_path = workspace_state_path(root_dir=root_dir)
    if not state_path.exists():
        return {"updated_at_utc": "", "checkpoint_lines": {}}
    return cast(WorkspaceStatePayload, read_json(state_path))


def update_local_workspace_pointer(
    source_checkpoint_path: Path,
    *,
    pointer_kind: PointerKind,
    root_dir: Path | None = None,
) -> WorkspacePointerUpdateResult:
    project_paths = build_project_paths(root_dir=root_dir)
    source_checkpoint_stem = source_checkpoint_path.with_suffix("")
    metadata = load_checkpoint_metadata(source_checkpoint_stem)
    if metadata is None:
        raise ValueError("No se puede publicar handoff desde checkpoint sin metadata estructurada.")

    run_id = metadata["run_id"]
    if run_id is None:
        raise ValueError("Checkpoint sin run_id. No se puede usar para handoff multi-PC.")

    checkpoint_name = str(metadata["profile"]["checkpoint_name"])
    pointer = _build_workspace_pointer(
        project_paths,
        source_checkpoint_path=source_checkpoint_path,
        metadata=metadata,
    )

    state = load_local_workspace_state(root_dir=project_paths.root_dir)
    checkpoint_line = state["checkpoint_lines"].setdefault(
        checkpoint_name,
        cast(WorkspaceCheckpointLinePayload, {}),
    )
    checkpoint_line[pointer_kind] = pointer
    state["updated_at_utc"] = pointer["updated_at_utc"]

    state_path = _save_local_workspace_state(project_paths, state)
    alias_stem = _alias_stem(project_paths, checkpoint_name, pointer_kind)
    ensure_directories([alias_stem.parent])
    copy_checkpoint_bundle(source_checkpoint_stem, alias_stem)
    update_checkpoint_metadata(
        alias_stem,
        saved_at_utc=pointer["updated_at_utc"],
        training_status=f"{pointer_kind}_checkpoint",
        checkpoint_role=pointer_kind,
        evaluation_source="workspace_handoff",
        canonical_checkpoint_path=str(source_checkpoint_path),
        is_best_checkpoint=pointer_kind == "promoted",
    )
    return WorkspacePointerUpdateResult(
        checkpoint_name=checkpoint_name,
        pointer_kind=pointer_kind,
        alias_path=checkpoint_zip_path(alias_stem),
        run_id=run_id,
        state_path=state_path,
    )


def publish_local_workspace_state(
    *,
    root_dir: Path | None = None,
    artifact_store: ArtifactStore | None = None,
    object_prefix: str | None = None,
) -> WorkspacePublishResult:
    project_paths = build_project_paths(root_dir=root_dir)
    state_path = workspace_state_path(root_dir=project_paths.root_dir)
    if not state_path.exists():
        return WorkspacePublishResult(
            state_path=state_path,
            uploaded=False,
            alias_count=0,
            state_object_key=None,
        )

    if not has_explicit_remote_storage_config():
        return WorkspacePublishResult(
            state_path=state_path,
            uploaded=False,
            alias_count=0,
            state_object_key=None,
        )

    resolved_artifact_store = artifact_store or _build_default_artifact_store()
    resolved_object_prefix = _resolve_object_prefix(resolved_artifact_store, object_prefix)
    state = load_local_workspace_state(root_dir=project_paths.root_dir)

    alias_count = 0
    for checkpoint_name, checkpoint_line in state["checkpoint_lines"].items():
        for pointer_kind in POINTER_KINDS:
            pointer = checkpoint_line.get(pointer_kind)
            if pointer is None:
                continue
            alias_stem = _alias_stem(project_paths, checkpoint_name, pointer_kind)
            alias_zip_path = checkpoint_zip_path(alias_stem)
            alias_metadata_path = checkpoint_metadata_path(alias_stem)
            if not alias_zip_path.exists() or not alias_metadata_path.exists():
                raise FileNotFoundError(
                    f"Alias local faltante para publicar workspace state: {alias_zip_path}"
                )
            resolved_artifact_store.upload_file(
                local_path=alias_zip_path,
                object_key=_workspace_checkpoint_object_key(
                    resolved_object_prefix,
                    checkpoint_name,
                    pointer_kind,
                    ".zip",
                ),
                content_type=guess_content_type(alias_zip_path),
            )
            resolved_artifact_store.upload_file(
                local_path=alias_metadata_path,
                object_key=_workspace_checkpoint_object_key(
                    resolved_object_prefix,
                    checkpoint_name,
                    pointer_kind,
                    ".json",
                ),
                content_type="application/json",
            )
            alias_count += 1

    state_object_key = _workspace_state_object_key(resolved_object_prefix)
    resolved_artifact_store.upload_file(
        local_path=state_path,
        object_key=state_object_key,
        content_type="application/json",
    )
    return WorkspacePublishResult(
        state_path=state_path,
        uploaded=True,
        alias_count=alias_count,
        state_object_key=state_object_key,
    )


def hydrate_workspace(
    *,
    profile_name: str = DEFAULT_PROFILE_NAME,
    scenario_name: str | None = None,
    root_dir: Path | None = None,
    artifact_store: ArtifactStore | None = None,
    object_prefix: str | None = None,
    include_active: bool = True,
    include_promoted: bool = True,
) -> HydrateWorkspaceResult:
    if not include_active and not include_promoted:
        raise ValueError("Debes hidratar al menos uno de 'active' o 'promoted'.")
    if not has_explicit_remote_storage_config():
        raise RuntimeError("No hay storage remoto configurado para hidratar workspace.")

    project_paths = build_project_paths(root_dir=root_dir)
    ensure_directories([project_paths.artifacts_dir, project_paths.checkpoints_dir, project_paths.runs_dir])
    resolved_artifact_store = artifact_store or _build_default_artifact_store()
    resolved_object_prefix = _resolve_object_prefix(resolved_artifact_store, object_prefix)
    state_path = workspace_state_path(root_dir=project_paths.root_dir)
    resolved_artifact_store.download_file(
        object_key=_workspace_state_object_key(resolved_object_prefix),
        local_path=state_path,
    )

    state = load_local_workspace_state(root_dir=project_paths.root_dir)
    profile = get_training_profile(profile_name, scenario_name=scenario_name)
    checkpoint_line = state["checkpoint_lines"].get(profile.checkpoint_name)
    if checkpoint_line is None:
        raise RuntimeError(
            f"No existe estado remoto publicado para checkpoint '{profile.checkpoint_name}'."
        )

    selected_kinds: list[PointerKind] = []
    if include_active and "active" in checkpoint_line:
        selected_kinds.append("active")
    if include_promoted and "promoted" in checkpoint_line:
        selected_kinds.append("promoted")
    if not selected_kinds:
        raise RuntimeError("Workspace remoto no contiene punteros compatibles para hidratar.")

    hydrated_pointers: list[HydratedWorkspacePointer] = []
    restored_run_ids: set[str] = set()
    for pointer_kind in selected_kinds:
        pointer = checkpoint_line[pointer_kind]
        alias_stem = _alias_stem(project_paths, profile.checkpoint_name, pointer_kind)
        alias_zip_path = checkpoint_zip_path(alias_stem)
        alias_json_path = checkpoint_metadata_path(alias_stem)
        resolved_artifact_store.download_file(
            object_key=_workspace_checkpoint_object_key(
                resolved_object_prefix,
                profile.checkpoint_name,
                pointer_kind,
                ".zip",
            ),
            local_path=alias_zip_path,
        )
        resolved_artifact_store.download_file(
            object_key=_workspace_checkpoint_object_key(
                resolved_object_prefix,
                profile.checkpoint_name,
                pointer_kind,
                ".json",
            ),
            local_path=alias_json_path,
        )

        restored_run_checkpoint_path: Path | None = None
        if pointer["source_relative_run_path"] is not None:
            restored_run_checkpoint_path = (
                project_paths.runs_dir / pointer["run_id"] / pointer["source_relative_run_path"]
            )
            ensure_directories([restored_run_checkpoint_path.parent])
            shutil.copy2(alias_zip_path, restored_run_checkpoint_path)
            shutil.copy2(alias_json_path, restored_run_checkpoint_path.with_suffix(".json"))
            update_checkpoint_metadata(
                restored_run_checkpoint_path.with_suffix(""),
                checkpoint_role=pointer["source_checkpoint_role"],
                canonical_checkpoint_path=str(restored_run_checkpoint_path),
            )

        restored_report_path = _hydrate_run_support_files(
            project_paths,
            artifact_store=resolved_artifact_store,
            object_prefix=resolved_object_prefix,
            run_id=pointer["run_id"],
        )
        restored_run_ids.add(pointer["run_id"])
        hydrated_pointers.append(
            HydratedWorkspacePointer(
                checkpoint_name=profile.checkpoint_name,
                pointer_kind=pointer_kind,
                run_id=pointer["run_id"],
                local_alias_path=alias_zip_path,
                restored_run_checkpoint_path=restored_run_checkpoint_path,
                restored_report_path=restored_report_path,
            )
        )

    for run_id in restored_run_ids:
        _rewrite_hydrated_report_paths(project_paths, run_id)

    return HydrateWorkspaceResult(
        checkpoint_name=profile.checkpoint_name,
        state_path=state_path,
        hydrated_pointers=hydrated_pointers,
    )


def _build_workspace_pointer(
    project_paths: ProjectPaths,
    *,
    source_checkpoint_path: Path,
    metadata: CheckpointMetadataPayload,
) -> WorkspaceCheckpointPointerPayload:
    run_id = cast(str, metadata["run_id"])
    canonical_checkpoint_path = metadata.get("canonical_checkpoint_path")
    candidate_paths: list[Path] = []
    if isinstance(canonical_checkpoint_path, str) and canonical_checkpoint_path:
        candidate_paths.append(Path(canonical_checkpoint_path))
    candidate_paths.append(source_checkpoint_path)

    run_dir = project_paths.runs_dir / run_id
    source_relative_run_path: str | None = None
    for candidate_path in candidate_paths:
        try:
            source_relative_run_path = candidate_path.relative_to(run_dir).as_posix()
            break
        except ValueError:
            continue

    profile_payload = metadata["profile"]
    scenario_key = str(profile_payload["scenario_key"])
    return {
        "profile_name": str(metadata["profile_name"]),
        "scenario_key": scenario_key,
        "run_id": run_id,
        "source_checkpoint_role": metadata["checkpoint_role"],
        "source_relative_run_path": source_relative_run_path,
        "report_relative_run_path": "report.json",
        "saved_timesteps": int(metadata["saved_timesteps"]),
        "evaluation_metrics": metadata.get("evaluation_metrics"),
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }


def _alias_stem(project_paths: ProjectPaths, checkpoint_name: str, pointer_kind: PointerKind) -> Path:
    checkpoint_stem = project_paths.checkpoints_dir / checkpoint_name
    if pointer_kind == "active":
        return active_checkpoint_stem(checkpoint_stem)
    return promoted_checkpoint_stem(checkpoint_stem)


def _save_local_workspace_state(
    project_paths: ProjectPaths,
    state: WorkspaceStatePayload,
) -> Path:
    state_path = workspace_state_path(root_dir=project_paths.root_dir)
    ensure_directories([state_path.parent])
    write_json(state_path, state)
    return state_path


def _workspace_state_object_key(object_prefix: str) -> str:
    return str(_workspace_remote_root(object_prefix) / "state.json")


def _workspace_checkpoint_object_key(
    object_prefix: str,
    checkpoint_name: str,
    pointer_kind: PointerKind,
    suffix: str,
) -> str:
    return str(
        _workspace_remote_root(object_prefix)
        / "checkpoints"
        / f"{checkpoint_name}_{pointer_kind}{suffix}"
    )


def _workspace_remote_root(object_prefix: str) -> PurePosixPath:
    cleaned_prefix = object_prefix.strip("/")
    root = PurePosixPath(cleaned_prefix) if cleaned_prefix else PurePosixPath()
    return root / WORKSPACE_REMOTE_DIR


def _resolve_object_prefix(artifact_store: ArtifactStore, object_prefix: str | None) -> str:
    if object_prefix is not None:
        normalized_prefix = object_prefix.strip("/")
        return normalized_prefix or DEFAULT_OBJECT_PREFIX
    store_prefix = getattr(artifact_store, "object_prefix", DEFAULT_OBJECT_PREFIX)
    normalized_store_prefix = str(store_prefix).strip("/")
    return normalized_store_prefix or DEFAULT_OBJECT_PREFIX


def _build_default_artifact_store() -> ArtifactStore:
    return S3ArtifactStore()


def _hydrate_run_support_files(
    project_paths: ProjectPaths,
    *,
    artifact_store: ArtifactStore,
    object_prefix: str,
    run_id: str,
) -> Path | None:
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    ensure_directories([run_artifacts.run_dir, run_artifacts.checkpoints_dir])

    restored_report_path: Path | None = None
    report_path = run_artifacts.report_path
    if _download_optional_file(
        artifact_store,
        object_key=str(PurePosixPath(object_prefix) / run_id / "report.json"),
        local_path=report_path,
    ):
        restored_report_path = report_path
    manifest_downloaded = _download_optional_file(
        artifact_store,
        object_key=str(PurePosixPath(object_prefix) / run_id / "manifest.json"),
        local_path=run_artifacts.manifest_path,
    )

    for relative_path in (
        "checkpoints/final_model.zip",
        "checkpoints/final_model.json",
        "checkpoints/best_model.zip",
        "checkpoints/best_model.json",
    ):
        _download_optional_file(
            artifact_store,
            object_key=str(PurePosixPath(object_prefix) / run_id / relative_path),
            local_path=run_artifacts.run_dir / Path(relative_path),
        )

    if manifest_downloaded:
        manifest = cast(RunManifestPayload, read_json(run_artifacts.manifest_path))
        _hydrate_manifest_artifacts(
            run_artifacts,
            artifact_store=artifact_store,
            object_prefix=object_prefix,
            manifest=manifest,
        )

    return restored_report_path


def _download_optional_file(
    artifact_store: ArtifactStore,
    *,
    object_key: str,
    local_path: Path,
) -> bool:
    try:
        artifact_store.download_file(object_key=object_key, local_path=local_path)
    except (FileNotFoundError, KeyError):
        return False
    return True


def _hydrate_manifest_artifacts(
    run_artifacts: RunArtifactPaths,
    *,
    artifact_store: ArtifactStore,
    object_prefix: str,
    manifest: RunManifestPayload,
) -> None:
    for artifact in manifest["artifacts"]:
        if not artifact["remote_sync_candidate"]:
            continue
        relative_path = artifact["relative_path"]
        local_path = run_artifacts.run_dir / Path(relative_path)
        if local_path.exists():
            continue
        artifact_store.download_file(
            object_key=str(PurePosixPath(object_prefix) / run_artifacts.run_id / relative_path),
            local_path=local_path,
        )


def _rewrite_hydrated_report_paths(project_paths: ProjectPaths, run_id: str) -> None:
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    report_path = run_artifacts.report_path
    if not report_path.exists():
        return

    report = cast(TrainingRunReportPayload, read_json(report_path))
    manifest = _load_hydrated_manifest(run_artifacts)
    report["run_dir"] = str(run_artifacts.run_dir)
    report["run_auto_checkpoints_dir"] = str(run_artifacts.auto_checkpoints_dir)
    report["tensorboard_dir"] = str(run_artifacts.tensorboard_dir)
    report["videos_dir"] = str(run_artifacts.videos_dir)
    report["manifest_path"] = str(run_artifacts.manifest_path)
    report["official_checkpoint_path"] = str(
        project_paths.checkpoints_dir / f"{report['checkpoint_name']}.zip"
    )
    report["official_best_checkpoint_path"] = str(
        project_paths.checkpoints_dir / f"{report['checkpoint_name']}_best.zip"
    )

    final_checkpoint_path = run_artifacts.final_checkpoint_stem.with_suffix(".zip")
    if final_checkpoint_path.exists():
        report["checkpoint_path"] = str(final_checkpoint_path)
        report["checkpoint_archive_path"] = str(final_checkpoint_path)

    best_checkpoint_path = run_artifacts.best_checkpoint_stem.with_suffix(".zip")
    if best_checkpoint_path.exists():
        report["best_checkpoint_path"] = str(best_checkpoint_path)
        report["best_checkpoint_archive_path"] = str(best_checkpoint_path)
    else:
        report["best_checkpoint_path"] = None
        report["best_checkpoint_archive_path"] = None

    report["selected_auto_checkpoint_archive_paths"] = _selected_auto_checkpoint_paths(
        run_artifacts,
        manifest,
    )

    write_json(report_path, report)


def _load_hydrated_manifest(run_artifacts: RunArtifactPaths) -> RunManifestPayload | None:
    if not run_artifacts.manifest_path.exists():
        return None
    return cast(RunManifestPayload, read_json(run_artifacts.manifest_path))


def _selected_auto_checkpoint_paths(
    run_artifacts: RunArtifactPaths,
    manifest: RunManifestPayload | None,
) -> list[str]:
    if manifest is not None:
        selected_paths = [
            str(run_artifacts.run_dir / Path(artifact["relative_path"]))
            for artifact in manifest["artifacts"]
            if _is_selected_auto_checkpoint_zip(artifact)
            and (run_artifacts.run_dir / Path(artifact["relative_path"])).exists()
        ]
        if selected_paths:
            return selected_paths

    return [
        str(path)
        for path in sorted(run_artifacts.auto_checkpoints_dir.glob("*.zip"))
    ]


def _is_selected_auto_checkpoint_zip(artifact: RunManifestArtifactPayload) -> bool:
    return (
        artifact["artifact_type"] == "checkpoint"
        and artifact["artifact_role"] == "auto"
        and artifact["sidecar_kind"] is None
        and artifact["remote_sync_candidate"]
        and artifact["relative_path"].endswith(".zip")
    )
