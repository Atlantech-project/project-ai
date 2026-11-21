"""Model registry (AI-070): the CHAMPION version per model key, and its artefact on the local
volume with a hash check.

- `read_champion` reads `ml_models` and `ml_model_versions` (every worker may read them).
- `load_champion` returns the champion with its verified artefact bytes, or `None` when the
  model has no champion, so the caller takes its Phase 1 path (rule, formula or NULL).
- `ArtifactStore` keeps artefacts under one root directory on the local volume (D8: never
  uploaded anywhere). `ml_model_versions` has no hash column, so each artefact has a SHA-256
  sidecar file next to it; `artifact_path` is relative to the root.

Registering versions and promoting a champion write `ml_model_versions`, which no worker may do
until retraining is built (DEC-08, CT-15): that part is not here.
"""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.tables import ML_MODEL_VERSIONS, ML_MODELS
from common.runtime.runs import Connection

HASH_SUFFIX: Final = ".sha256"
CHAMPION: Final = "CHAMPION"


class ModelKey(StrEnum):
    """`ml_models.model_key` (schema ENUM)."""

    M2_SERVICE_TIME = "M2_SERVICE_TIME"
    M3_DEMAND_FORECAST = "M3_DEMAND_FORECAST"
    M4_DELAY_RISK = "M4_DELAY_RISK"
    FORECAST_BIAS_CORRECTION = "FORECAST_BIAS_CORRECTION"


class RegistryError(RuntimeError):
    """The registry rows break a rule the schema should already hold (for example two CHAMPIONs)."""


class ArtifactError(RuntimeError):
    """An artefact path is unsafe, or the file or its hash is missing or does not match."""


@dataclass(frozen=True)
class ModelVersion:
    id: int
    model_key: ModelKey
    version_no: int
    status: str
    artifact_path: str
    trained_at: datetime
    deployed_at: datetime | None


@dataclass(frozen=True)
class LoadedModel:
    version: ModelVersion
    artifact: bytes
    sha256: str


def read_champion(connection: Connection, model_key: ModelKey) -> ModelVersion | None:
    """The CHAMPION version of a model, or None. More than one is a `RegistryError`."""
    m, v = ML_MODELS, ML_MODEL_VERSIONS
    statement = (
        sa.select(
            v.c.id,
            v.c.version_no,
            v.c.status,
            v.c.artifact_path,
            v.c.trained_at,
            v.c.deployed_at,
        )
        .select_from(v.join(m, m.c.id == v.c.ml_model_id))
        .where(m.c.model_key == model_key.value, v.c.status == CHAMPION)
        .order_by(v.c.id)
    )
    rows = list(core_of(connection).execute(statement).mappings())
    if len(rows) > 1:
        ids = ", ".join(str(r["id"]) for r in rows)
        raise RegistryError(f"{model_key} has {len(rows)} CHAMPION versions: {ids}")
    if not rows:
        return None
    row = rows[0]
    return ModelVersion(
        id=row["id"],
        model_key=model_key,
        version_no=row["version_no"],
        status=row["status"],
        artifact_path=row["artifact_path"],
        trained_at=row["trained_at"],
        deployed_at=row["deployed_at"],
    )


def load_champion(
    connection: Connection, model_key: ModelKey, store: ArtifactStore
) -> LoadedModel | None:
    """The champion with its verified artefact, or None: then the caller uses its Phase 1 path.

    A champion whose artefact is missing or fails its hash raises `ArtifactError`; a damaged
    model is never used, and the failure is never hidden by a silent fallback.
    """
    version = read_champion(connection, model_key)
    if version is None:
        return None
    data, digest = store.load(version.artifact_path)
    return LoadedModel(version, data, digest)


@dataclass(frozen=True)
class ArtifactStore:
    """Artefacts under `root` on the local volume; each has a `<name>.sha256` sidecar."""

    root: Path

    def path_for(self, model_key: ModelKey, version_no: int) -> str:
        """The `artifact_path` of a new version: `<model_key>/v<version_no>/model.bin`."""
        if version_no <= 0:
            raise ArtifactError(f"version_no must be positive: {version_no}")
        return f"{model_key.value}/v{version_no}/model.bin"

    def save(self, artifact_path: str, data: bytes) -> str:
        """Write the artefact and its hash; refuse to overwrite. Returns the SHA-256 hex digest."""
        target = self._resolve(artifact_path)
        if target.exists():
            raise ArtifactError(f"artefact already exists: {artifact_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(data).hexdigest()
        _atomic_write(target, data)
        _atomic_write(_sidecar(target), f"{digest}\n".encode("ascii"))
        return digest

    def load(self, artifact_path: str) -> tuple[bytes, str]:
        """The artefact bytes and digest, after checking them against the sidecar."""
        target = self._resolve(artifact_path)
        sidecar = _sidecar(target)
        if not target.is_file():
            raise ArtifactError(f"artefact missing: {artifact_path}")
        if not sidecar.is_file():
            raise ArtifactError(f"artefact hash missing: {artifact_path}{HASH_SUFFIX}")
        expected = sidecar.read_text(encoding="ascii").strip().lower()
        data = target.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ArtifactError(f"artefact hash mismatch for {artifact_path}")
        return data, actual

    def _resolve(self, artifact_path: str) -> Path:
        """Only a relative path inside the root: no absolute path, drive, URL or `..`."""
        posix = PurePosixPath(artifact_path.replace("\\", "/"))
        if not artifact_path or posix.is_absolute() or ":" in artifact_path or ".." in posix.parts:
            raise ArtifactError(
                f"artifact_path must be relative to the store root: {artifact_path}"
            )
        root = self.root.resolve()
        target = (root / Path(*posix.parts)).resolve()
        if not target.is_relative_to(root):
            raise ArtifactError(f"artifact_path leaves the store root: {artifact_path}")
        return target


def _sidecar(target: Path) -> Path:
    return target.with_name(target.name + HASH_SUFFIX)


def _atomic_write(target: Path, data: bytes) -> None:
    fd, temp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
