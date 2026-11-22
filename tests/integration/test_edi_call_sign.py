"""R12 against MySQL: a corrected `call_sign` must fit `vessels.call_sign` (`varchar(10)`).

The file parser never reads a call sign (TDT gives the IMO and name only), so the value can only
come from staff on the quarantine screen, through a `STAGED_PAYLOAD` run. SYNTHETIC data.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from common.config import PortSettings
from common.db.connection import WorkerConnection
from common.runtime.envelope import Envelope, JobType
from common.runtime.worker import JobContext
from edi import parse_baplie
from edi.job import make_handler
from tests.integration.test_edi_job import (  # noqa: F401 (fixtures)
    _count,
    _seed,
    fresh_sessions,
    root,
    worker,
)
from tests.support.edi_corpus import CORPUS_ROOT
from tests.unit.edi.test_rules import _payload

pytestmark = pytest.mark.integration


def _correction(conn: Any, tmp_path: Path, call_sign: str) -> int:
    """A QUARANTINED file whose corrected payload is clean apart from `call_sign`."""
    file_id = _seed(conn, tmp_path, "01-valid-221")
    parsed = parse_baplie((CORPUS_ROOT / "01-valid-221.edi").read_bytes())
    payload = _payload(parsed.vessel, parsed.lines)
    payload["vessel"]["call_sign"] = call_sign
    with conn.cursor() as cursor:
        cursor.execute("UPDATE vessels SET call_sign = NULL")
        cursor.execute(
            "UPDATE baplie_files SET parse_status = 'QUARANTINED', staged_payload = %s "
            "WHERE id = %s",
            (json.dumps(payload), file_id),
        )
    conn.commit()
    return file_id


def _staged_context(connection: WorkerConnection, file_id: int) -> JobContext:
    envelope = Envelope(
        "1.0",
        JobType.BAPLIE_PARSE,
        "job-2",
        2,
        "2026-11-22T12:00:00Z",
        None,
        {"baplie_file_id": file_id, "source": "STAGED_PAYLOAD"},
    )
    return JobContext(envelope, PortSettings([]), connection, 0)


def test_ten_character_call_sign_is_filled(
    root: Any,  # noqa: F811
    worker: WorkerConnection,  # noqa: F811
    tmp_path: Path,
) -> None:
    file_id = _correction(root, tmp_path, "A" * 10)
    result = make_handler(tmp_path)(_staged_context(worker, file_id))
    worker.commit()

    assert result.outcome == "PARSED"
    assert _count(root, "SELECT call_sign FROM vessels") == "A" * 10


def test_eleven_character_call_sign_is_quarantined(
    root: Any,  # noqa: F811
    worker: WorkerConnection,  # noqa: F811
    tmp_path: Path,
) -> None:
    file_id = _correction(root, tmp_path, "A" * 11)
    result = make_handler(tmp_path)(_staged_context(worker, file_id))
    worker.commit()

    assert result.outcome == "QUARANTINED"
    assert _count(root, "SELECT call_sign FROM vessels") is None
    assert _count(root, "SELECT COUNT(*) FROM container_manifest_entries") == 0
    assert _count(root, f"SELECT parse_status FROM baplie_files WHERE id = {file_id}") == (  # noqa: S608
        "QUARANTINED"
    )
    message = _count(root, "SELECT message FROM baplie_parse_issues WHERE severity = 'ERROR'")
    assert "call sign" in message.lower()
