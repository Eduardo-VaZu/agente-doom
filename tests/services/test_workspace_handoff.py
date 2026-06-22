from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from doom_agent.config import build_project_paths, get_training_profile
from doom_agent.config.schema import ProjectPaths, TrainingProfile
from doom_agent.services.workspace_handoff import (
    hydrate_workspace,
    publish_local_workspace_state,
    update_local_workspace_pointer,
    workspace_state_path,
)
from doom_agent.shared.contracts import EvaluationMetricsPayload
from doom_agent.storage import RunArtifactPaths, build_run_artifact_paths
from doom_agent.storage.remote import RemoteArtifactLocation
from doom_agent.utils.checkpoints import (
    active_checkpoint_stem,
    build_checkpoint_metadata,
    checkpoint_zip_path,
    promoted_checkpoint_stem,
    save_checkpoint_bundle,
)
from doom_agent.utils.manifests import build_run_manifest, save_run_manifest
from doom_agent.utils.reports import (
    build_run_id,
    build_training_run_report,
    save_training_run_report,
)


class DummyModel:
    def save(self, checkpoint_stem: str) -> None:
        checkpoint_zip_path(Path(checkpoint_stem)).write_text("dummy model", encoding="utf-8")


class FakeArtifactStore:
    def __init__(self) -> None:
        self.object_prefix = "runs"
        self.storage_backend = "s3"
        self._objects: dict[str, bytes] = {}

    def upload_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> RemoteArtifactLocation:
        _ = content_type
        self._objects[object_key] = local_path.read_bytes()
        return RemoteArtifactLocation(
            storage_backend="s3",
            bucket_name="agente-doom-artifacts",
            object_key=object_key,
            remote_uri=f"s3://agente-doom-artifacts/{object_key}",
            etag="etag-1",
        )

    def download_file(
        self,
        *,
        object_key: str,
        local_path: Path,
    ) -> None:
        payload = self._objects[object_key]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(payload)


class ExplodingArtifactStore(FakeArtifactStore):
    def download_file(
        self,
        *,
        object_key: str,
        local_path: Path,
    ) -> None:
        if object_key.endswith("manifest.json"):
            raise PermissionError("remote auth failed")
        super().download_file(object_key=object_key, local_path=local_path)


class WorkspaceHandoffTests(unittest.TestCase):
    def test_publish_local_workspace_state_uploads_active_alias_and_state(self) -> None:
        root_dir = Path("artifacts") / "test-temp" / "workspace-handoff-publish"
        shutil.rmtree(root_dir, ignore_errors=True)
        fake_store = FakeArtifactStore()
        project_paths, profile, run_artifacts = _build_run_fixture(root_dir)

        try:
            update_local_workspace_pointer(
                run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
                pointer_kind="active",
                root_dir=root_dir,
            )
            with patch(
                "doom_agent.services.workspace_handoff.has_explicit_remote_storage_config",
                return_value=True,
            ):
                result = publish_local_workspace_state(
                    root_dir=root_dir,
                    artifact_store=fake_store,
                    object_prefix="runs",
                )

            self.assertTrue(result.uploaded)
            self.assertEqual(result.alias_count, 1)
            self.assertIn("runs/workspace/state.json", fake_store._objects)
            self.assertIn(
                f"runs/workspace/checkpoints/{profile.checkpoint_name}_active.zip",
                fake_store._objects,
            )
            self.assertTrue(
                checkpoint_zip_path(
                    active_checkpoint_stem(project_paths.checkpoints_dir / profile.checkpoint_name)
                ).exists()
            )
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)

    def test_hydrate_workspace_restores_aliases_and_run_support_files(self) -> None:
        source_root = Path("artifacts") / "test-temp" / "workspace-handoff-source"
        target_root = Path("artifacts") / "test-temp" / "workspace-handoff-target"
        shutil.rmtree(source_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
        fake_store = FakeArtifactStore()
        _, profile, run_artifacts = _build_run_fixture(source_root)
        run_id = run_artifacts.run_id

        try:
            _upload_run_support_files(fake_store, run_artifacts, object_prefix="runs")
            update_local_workspace_pointer(
                run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
                pointer_kind="active",
                root_dir=source_root,
            )
            update_local_workspace_pointer(
                run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
                pointer_kind="promoted",
                root_dir=source_root,
            )
            with patch(
                "doom_agent.services.workspace_handoff.has_explicit_remote_storage_config",
                return_value=True,
            ):
                publish_local_workspace_state(
                    root_dir=source_root,
                    artifact_store=fake_store,
                    object_prefix="runs",
                )
                result = hydrate_workspace(
                    profile_name="default",
                    root_dir=target_root,
                    artifact_store=fake_store,
                    object_prefix="runs",
                )

            self.assertEqual(result.checkpoint_name, profile.checkpoint_name)
            self.assertEqual(len(result.hydrated_pointers), 2)
            self.assertTrue(workspace_state_path(root_dir=target_root).exists())
            target_project_paths = build_project_paths(root_dir=target_root)
            self.assertTrue(
                checkpoint_zip_path(
                    active_checkpoint_stem(
                        target_project_paths.checkpoints_dir / profile.checkpoint_name
                    )
                ).exists()
            )
            self.assertTrue(
                checkpoint_zip_path(
                    promoted_checkpoint_stem(
                        target_project_paths.checkpoints_dir / profile.checkpoint_name
                    )
                ).exists()
            )
            restored_report_path = target_project_paths.runs_dir / run_id / "report.json"
            self.assertTrue(restored_report_path.exists())
            restored_manifest_path = target_project_paths.runs_dir / run_id / "manifest.json"
            self.assertTrue(restored_manifest_path.exists())
            restored_best_checkpoint = (
                target_project_paths.runs_dir / run_id / "checkpoints" / "best_model.zip"
            )
            self.assertTrue(restored_best_checkpoint.exists())
            self.assertTrue(
                (target_project_paths.runs_dir / run_id / "checkpoints" / "final_model.zip").exists()
            )
            restored_report = json.loads(restored_report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                restored_report["run_dir"],
                str(target_project_paths.runs_dir / run_id),
            )
            self.assertEqual(
                restored_report["manifest_path"],
                str(restored_manifest_path),
            )
            restored_selected_auto = restored_report["selected_auto_checkpoint_archive_paths"]
            self.assertEqual(len(restored_selected_auto), 1)
            self.assertTrue(Path(restored_selected_auto[0]).exists())
            self.assertEqual(
                Path(restored_selected_auto[0]).parent,
                target_project_paths.runs_dir / run_id / "checkpoints" / "auto",
            )
            self.assertTrue(
                (
                    target_project_paths.runs_dir
                    / run_id
                    / "videos"
                    / "doom_foundation_agent-step-0-to-step-1500.mp4"
                ).exists()
            )
        finally:
            shutil.rmtree(source_root, ignore_errors=True)
            shutil.rmtree(target_root, ignore_errors=True)

    def test_hydrate_workspace_bubbles_remote_errors_for_optional_files(self) -> None:
        source_root = Path("artifacts") / "test-temp" / "workspace-handoff-source-error"
        target_root = Path("artifacts") / "test-temp" / "workspace-handoff-target-error"
        shutil.rmtree(source_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
        fake_store = ExplodingArtifactStore()
        _, _, run_artifacts = _build_run_fixture(source_root)

        try:
            _upload_run_support_files(fake_store, run_artifacts, object_prefix="runs")
            update_local_workspace_pointer(
                run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
                pointer_kind="active",
                root_dir=source_root,
            )
            with patch(
                "doom_agent.services.workspace_handoff.has_explicit_remote_storage_config",
                return_value=True,
            ):
                publish_local_workspace_state(
                    root_dir=source_root,
                    artifact_store=fake_store,
                    object_prefix="runs",
                )
                with self.assertRaises(PermissionError):
                    hydrate_workspace(
                        profile_name="default",
                        root_dir=target_root,
                        artifact_store=fake_store,
                        object_prefix="runs",
                        include_promoted=False,
                    )
        finally:
            shutil.rmtree(source_root, ignore_errors=True)
            shutil.rmtree(target_root, ignore_errors=True)


def _build_run_fixture(root_dir: Path) -> tuple[ProjectPaths, TrainingProfile, RunArtifactPaths]:
    project_paths = build_project_paths(root_dir=root_dir)
    profile = get_training_profile("default", seed=123)
    run_id = build_run_id(profile)
    run_artifacts = build_run_artifact_paths(project_paths, run_id)
    run_artifacts.run_dir.mkdir(parents=True, exist_ok=True)
    run_artifacts.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    final_metadata = build_checkpoint_metadata(
        "default",
        profile,
        saved_timesteps=profile.effective_timesteps,
        run_id=run_id,
        training_status="completed",
        checkpoint_role="final",
        evaluation_source="training_internal",
        canonical_checkpoint_path=str(run_artifacts.final_checkpoint_stem.with_suffix(".zip")),
        evaluation_metrics=EvaluationMetricsPayload(
            mean_reward=10.0,
            std_reward=1.0,
            mean_episode_length=30.0,
            episodes=5,
        ),
    )
    best_metadata = build_checkpoint_metadata(
        "default",
        profile,
        saved_timesteps=profile.effective_timesteps,
        run_id=run_id,
        training_status="best_model",
        checkpoint_role="best",
        evaluation_source="training_internal",
        canonical_checkpoint_path=str(run_artifacts.best_checkpoint_stem.with_suffix(".zip")),
        evaluation_metrics=EvaluationMetricsPayload(
            mean_reward=12.0,
            std_reward=0.8,
            mean_episode_length=28.0,
            episodes=5,
        ),
        is_best_checkpoint=True,
    )
    save_checkpoint_bundle(DummyModel(), run_artifacts.final_checkpoint_stem, final_metadata)
    save_checkpoint_bundle(DummyModel(), run_artifacts.best_checkpoint_stem, best_metadata)
    run_artifacts.auto_checkpoints_dir.mkdir(parents=True, exist_ok=True)
    selected_auto_checkpoint_path = (
        run_artifacts.auto_checkpoints_dir / f"{profile.checkpoint_name}_50000_steps.zip"
    )
    selected_auto_checkpoint_path.write_text("auto", encoding="utf-8")
    selected_auto_checkpoint_path.with_suffix(".json").write_text("{}", encoding="utf-8")
    run_artifacts.videos_dir.mkdir(parents=True, exist_ok=True)
    (run_artifacts.videos_dir / "doom_foundation_agent-step-0-to-step-1500.mp4").write_text(
        "video",
        encoding="utf-8",
    )

    report = build_training_run_report(
        run_id=run_id,
        created_at_utc="2026-01-01T00:00:00+00:00",
        profile_name="default",
        run_label="manual:test",
        profile=profile,
        run_artifacts=run_artifacts,
        checkpoint_path=run_artifacts.final_checkpoint_stem.with_suffix(".zip"),
        best_checkpoint_path=run_artifacts.best_checkpoint_stem.with_suffix(".zip"),
        selected_auto_checkpoint_paths=[selected_auto_checkpoint_path],
        official_checkpoint_path=project_paths.checkpoints_dir / f"{profile.checkpoint_name}.zip",
        official_best_checkpoint_path=project_paths.checkpoints_dir
        / f"{profile.checkpoint_name}_best.zip",
        training_status="completed",
        completed=True,
        saved_timesteps=profile.effective_timesteps,
        resume_mode="auto",
        resume_source=None,
        resume_saved_timesteps=None,
        evaluation_metrics=EvaluationMetricsPayload(
            mean_reward=12.0,
            std_reward=0.8,
            mean_episode_length=28.0,
            episodes=5,
        ),
        duration_seconds=12.5,
        stopped_early=False,
        stop_reason=None,
    )
    report_path = save_training_run_report(project_paths, report)
    manifest = build_run_manifest(
        report,
        run_artifacts=run_artifacts,
        report_path=report_path,
    )
    save_run_manifest(run_artifacts, manifest)
    return project_paths, profile, run_artifacts


def _upload_run_support_files(
    fake_store: FakeArtifactStore,
    run_artifacts: RunArtifactPaths,
    *,
    object_prefix: str,
) -> None:
    manifest = json.loads(run_artifacts.manifest_path.read_text(encoding="utf-8"))
    relative_paths = {"report.json", "manifest.json"}
    relative_paths.update(
        artifact["relative_path"]
        for artifact in manifest["artifacts"]
        if artifact["remote_sync_candidate"]
    )
    for relative_path in sorted(relative_paths):
        local_path = run_artifacts.run_dir / Path(relative_path)
        fake_store.upload_file(
            local_path=local_path,
            object_key=f"{object_prefix}/{run_artifacts.run_id}/{relative_path.replace('\\', '/')}",
            content_type=None,
        )
