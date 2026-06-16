from __future__ import annotations

from pathlib import Path

from smart_trade.application.ports.ml import ArtifactDeletionResult


class LocalModelArtifactStore:
    def delete(self, artifact_path: str) -> ArtifactDeletionResult:
        artifact = Path(artifact_path)
        dataset = artifact.with_suffix(".dataset.npz")

        artifact_deleted = _unlink_if_exists(artifact)
        dataset_deleted = _unlink_if_exists(dataset)

        return ArtifactDeletionResult(
            artifact_path=str(artifact),
            artifact_deleted=artifact_deleted,
            dataset_path=str(dataset),
            dataset_deleted=dataset_deleted,
        )


def _unlink_if_exists(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True
