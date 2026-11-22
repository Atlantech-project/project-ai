"""AI-031 follow-up against MySQL: a value the `int` columns cannot store is quarantined.

Before the follow-up, a weight above the `int` maximum passed the rule set and the write failed
with MySQL error 1264, so the file could never reach staff correction. SYNTHETIC data.
"""

from pathlib import Path
from typing import Any

import pytest

from common.db.connection import WorkerConnection
from edi.job import make_handler
from tests.integration.test_edi_job import (  # noqa: F401 (fixtures)
    _context,
    _count,
    _seed,
    fresh_sessions,
    root,
    worker,
)

pytestmark = pytest.mark.integration


def test_weight_the_column_cannot_store_is_quarantined(
    root: Any,  # noqa: F811
    worker: WorkerConnection,  # noqa: F811
    tmp_path: Path,
) -> None:
    file_id = _seed(root, tmp_path, "01-valid-221")
    path = tmp_path / "01-valid-221.edi"
    text = path.read_text()
    edited = text.replace("MEA+WT++KGM:24500'", "MEA+WT++KGM:3000000000'", 1)
    assert edited != text
    path.write_text(edited)

    result = make_handler(tmp_path)(_context(worker, file_id))
    worker.commit()

    assert result.outcome == "QUARANTINED"
    assert _count(root, f"SELECT parse_status FROM baplie_files WHERE id = {file_id}") == (  # noqa: S608
        "QUARANTINED"
    )
    assert _count(root, "SELECT COUNT(*) FROM container_manifest_entries") == 0
    assert _count(root, "SELECT severity FROM baplie_parse_issues") == "ERROR"
    message = _count(root, "SELECT message FROM baplie_parse_issues")
    assert "larger than the stored maximum" in message
