"""Model registry (AI-070): artefact store, hash check, champion read and Phase 1 fallback."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from common import registry
from common.registry import (
    ArtifactError,
    ArtifactStore,
    ModelKey,
    ModelVersion,
    RegistryError,
    load_champion,
    read_champion,
)

TRAINED = datetime(2026, 11, 1, tzinfo=UTC)
NO_DB: Any = object()  # the fake `core_of` below never touches it


class _Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self, _statement: object) -> _Rows:
        return self

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


def _row(version_id: int, version_no: int = 1) -> dict[str, Any]:
    return {
        "id": version_id,
        "version_no": version_no,
        "status": "CHAMPION",
        "artifact_path": f"M2_SERVICE_TIME/v{version_no}/model.bin",
        "trained_at": TRAINED,
        "deployed_at": TRAINED,
    }


def _fake_db(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]) -> None:
    monkeypatch.setattr(registry, "core_of", lambda _connection: _Rows(rows))


def test_save_then_load_verifies_the_hash(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    path = store.path_for(ModelKey.M2_SERVICE_TIME, 3)
    digest = store.save(path, b"model bytes")

    assert path == "M2_SERVICE_TIME/v3/model.bin"
    assert (tmp_path / "M2_SERVICE_TIME/v3/model.bin.sha256").read_text().strip() == digest
    assert store.load(path) == (b"model bytes", digest)


def test_a_changed_artefact_fails_its_hash(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.save("M2_SERVICE_TIME/v1/model.bin", b"original")
    (tmp_path / "M2_SERVICE_TIME/v1/model.bin").write_bytes(b"tampered")

    with pytest.raises(ArtifactError, match="mismatch"):
        store.load("M2_SERVICE_TIME/v1/model.bin")


def test_missing_artefact_or_hash_is_an_error(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(ArtifactError, match="artefact missing"):
        store.load("M2_SERVICE_TIME/v1/model.bin")
    store.save("M2_SERVICE_TIME/v1/model.bin", b"x")
    (tmp_path / "M2_SERVICE_TIME/v1/model.bin.sha256").unlink()
    with pytest.raises(ArtifactError, match="hash missing"):
        store.load("M2_SERVICE_TIME/v1/model.bin")


def test_an_artefact_is_never_overwritten(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.save("M4_DELAY_RISK/v1/model.bin", b"first")
    with pytest.raises(ArtifactError, match="already exists"):
        store.save("M4_DELAY_RISK/v1/model.bin", b"second")
    assert store.load("M4_DELAY_RISK/v1/model.bin")[0] == b"first"


@pytest.mark.parametrize(
    "path",
    ["", "/etc/model.bin", "../outside.bin", "a/../../outside.bin", "C:/model.bin", "s3://b/m"],
)
def test_paths_outside_the_store_are_refused(tmp_path: Path, path: str) -> None:
    with pytest.raises(ArtifactError):
        ArtifactStore(tmp_path / "store").load(path)


def test_version_number_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ArtifactError):
        ArtifactStore(tmp_path).path_for(ModelKey.M3_DEMAND_FORECAST, 0)


def test_read_champion_returns_the_row(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_db(monkeypatch, [_row(7, 2)])

    assert read_champion(NO_DB, ModelKey.M2_SERVICE_TIME) == ModelVersion(
        7, ModelKey.M2_SERVICE_TIME, 2, "CHAMPION", "M2_SERVICE_TIME/v2/model.bin", TRAINED, TRAINED
    )


def test_two_champions_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_db(monkeypatch, [_row(7), _row(8, 2)])
    with pytest.raises(RegistryError, match="2 CHAMPION versions"):
        read_champion(NO_DB, ModelKey.M2_SERVICE_TIME)


def test_no_champion_falls_back_to_phase_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_db(monkeypatch, [])
    assert load_champion(NO_DB, ModelKey.M4_DELAY_RISK, ArtifactStore(tmp_path)) is None


def test_champion_loads_with_verified_artefact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = ArtifactStore(tmp_path)
    digest = store.save("M2_SERVICE_TIME/v1/model.bin", b"weights")
    _fake_db(monkeypatch, [_row(7)])
    loaded = load_champion(NO_DB, ModelKey.M2_SERVICE_TIME, store)

    assert loaded is not None
    assert (loaded.version.id, loaded.artifact, loaded.sha256) == (7, b"weights", digest)


def test_champion_with_a_damaged_artefact_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_db(monkeypatch, [_row(7)])
    with pytest.raises(ArtifactError):
        load_champion(NO_DB, ModelKey.M2_SERVICE_TIME, ArtifactStore(tmp_path))
