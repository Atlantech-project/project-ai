import json
import shutil
from pathlib import Path

import pytest

from common.config import ConfigurationError
from common.runtime.envelope import (
    QUEUES,
    SCHEMA_FILES,
    Envelope,
    JobType,
    Rejection,
    RejectionKind,
    Schemas,
    load_schemas,
    parse_message,
    resolve_schema_dir,
)
from tests.support.runtime_messages import envelope, raw

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "docs" / "ref" / "ai-payloads"


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(SCHEMA_DIR)


def _rejected(result: Envelope | Rejection) -> Rejection:
    assert isinstance(result, Rejection)
    return result


# Loading


@pytest.mark.parametrize("job_type", list(JobType))
def test_every_job_types_schema_loads_and_accepts_a_valid_message(
    schemas: Schemas, job_type: JobType
) -> None:
    result = parse_message(raw(job_type), job_type, schemas)
    assert isinstance(result, Envelope)
    assert result.job_type is job_type


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_missing_schema_stops_loading_and_names_the_file(tmp_path: Path, name: str) -> None:
    for file in SCHEMA_FILES:
        if file != name:
            shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    with pytest.raises(ConfigurationError, match=name):
        load_schemas(tmp_path)


def test_broken_schema_stops_loading(tmp_path: Path) -> None:
    for file in SCHEMA_FILES:
        shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    (tmp_path / "envelope.schema.json").write_text("{", encoding="utf-8")
    with pytest.raises(ConfigurationError, match=r"envelope\.schema\.json"):
        load_schemas(tmp_path)


def test_invalid_schema_stops_loading(tmp_path: Path) -> None:
    for file in SCHEMA_FILES:
        shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    (tmp_path / "c03-yard.schema.json").write_text('{"type": 5}', encoding="utf-8")
    with pytest.raises(ConfigurationError, match=r"c03-yard\.schema\.json"):
        load_schemas(tmp_path)


def test_a_schema_without_an_id_stops_loading(tmp_path: Path) -> None:
    for file in SCHEMA_FILES:
        shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    (tmp_path / "c03-yard.schema.json").write_text('{"type": "object"}', encoding="utf-8")
    with pytest.raises(ConfigurationError, match=r"c03-yard\.schema\.json"):
        load_schemas(tmp_path)


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        ("envelope.schema.json", "c01-part1-run.schema.json", "c01-NOPE.schema.json"),
        ("c02-part2-solve.schema.json", '#/$defs/trigger"', '#/$defs/nope"'),
        ("c06-completion.schema.json", "#/$defs/violation", "#/$defs/nope"),
        ("c01-part1-run.schema.json", "c01-part1-run.schema.json", "c01-moved.schema.json"),
    ],
)
def test_a_dangling_reference_stops_loading(tmp_path: Path, name: str, old: str, new: str) -> None:
    for file in SCHEMA_FILES:
        shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    text = (tmp_path / name).read_text(encoding="utf-8")
    assert old in text
    (tmp_path / name).write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="schema"):
        load_schemas(tmp_path)


@pytest.mark.parametrize("contents", ["true", "[]"])
def test_a_schema_that_isnt_an_object_stops_loading(tmp_path: Path, contents: str) -> None:
    for file in SCHEMA_FILES:
        shutil.copy(SCHEMA_DIR / file, tmp_path / file)
    (tmp_path / "c03-yard.schema.json").write_text(contents, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=r"c03-yard\.schema\.json"):
        load_schemas(tmp_path)


def test_queues_match_ct08() -> None:
    assert {job_type.value: queue for job_type, queue in QUEUES.items()} == {
        "PART1_RUN": "queue:part1",
        "PART2_SOLVE": "queue:part2",
        "YARD_PLACEMENT": "queue:yard",
        "BAPLIE_PARSE": "queue:edi",
        "VALIDATION": "queue:validate",
    }


# Where the schemas come from


def test_ai_schema_dir_wins(tmp_path: Path) -> None:
    assert resolve_schema_dir({"AI_SCHEMA_DIR": "/opt/schemas"}, tmp_path) == Path("/opt/schemas")


def test_checkout_defaults_to_the_mirror(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    assert resolve_schema_dir({}, tmp_path) == tmp_path / "docs" / "ref" / "ai-payloads"


@pytest.mark.parametrize("env", [{}, {"AI_SCHEMA_DIR": ""}, {"AI_SCHEMA_DIR": "   "}])
def test_outside_a_checkout_the_variable_is_required(tmp_path: Path, env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError, match="AI_SCHEMA_DIR"):
        resolve_schema_dir(env, tmp_path)


# Parsing


def test_a_decoded_message_is_read_the_same(schemas: Schemas) -> None:
    message = raw(JobType.PART1_RUN).decode()
    assert isinstance(parse_message(message, JobType.PART1_RUN, schemas), Envelope)


def test_minor_versions_are_accepted(schemas: Schemas) -> None:
    message = raw(JobType.PART1_RUN, contract_version="1.7")
    assert isinstance(parse_message(message, JobType.PART1_RUN, schemas), Envelope)


@pytest.mark.parametrize(
    "message",
    [b"{", b"\xff\xfe", b"[]", b"5", b"null", b"", b'{"run_id": NaN}', b"[" * 100_000],
)
def test_unreadable_messages_are_dropped(schemas: Schemas, message: bytes) -> None:
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.UNREADABLE


@pytest.mark.parametrize("run_id", [None, 0, -1, "5", 1.5, True, [1]])
def test_no_readable_run_id_is_dropped(schemas: Schemas, run_id: object) -> None:
    message = json.dumps(envelope(JobType.PART1_RUN, run_id=None) | {"run_id": run_id}).encode()
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.UNREADABLE


@pytest.mark.parametrize("message", [b'"run_id": 1.0', b'"run_id": 1e0'])
def test_a_float_run_id_is_dropped_not_claimed(schemas: Schemas, message: bytes) -> None:
    body = raw(JobType.PART1_RUN, run_id=1).replace(b'"run_id": 1', message)
    result = _rejected(parse_message(body, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.UNREADABLE


def test_missing_run_id_is_dropped(schemas: Schemas) -> None:
    body = envelope(JobType.PART1_RUN)
    del body["run_id"]
    result = _rejected(parse_message(json.dumps(body).encode(), JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.UNREADABLE


@pytest.mark.parametrize("sent", [JobType.PART2_SOLVE, JobType.VALIDATION])
def test_another_job_type_is_the_wrong_queue(schemas: Schemas, sent: JobType) -> None:
    result = _rejected(parse_message(raw(sent, run_id=9), JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.WRONG_QUEUE
    assert result.job_type == sent.value


@pytest.mark.parametrize("job_type", ["NOT_A_JOB", 5, None])
def test_an_unknown_job_type_is_the_wrong_queue(schemas: Schemas, job_type: object) -> None:
    message = raw(JobType.PART1_RUN, run_id=9, job_type=job_type)
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.WRONG_QUEUE


@pytest.mark.parametrize(
    "overrides",
    [
        {"contract_version": "2.0"},
        {"payload": {}},
        {"enqueued_at": "2026-11-03T10:00:00"},
        {"enqueued_at": "not a time Z"},
        {"extra": 1},
    ],
)
def test_invalid_with_a_readable_run_id_is_finished(
    schemas: Schemas, overrides: dict[str, object]
) -> None:
    message = raw(JobType.PART1_RUN, run_id=9, **overrides)
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.FINISH
    assert result.run_id == 9
    assert result.reason


def test_a_missing_job_type_with_a_run_id_is_finished(schemas: Schemas) -> None:
    body = envelope(JobType.PART1_RUN, run_id=9)
    del body["job_type"]
    result = _rejected(parse_message(json.dumps(body).encode(), JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.FINISH


@pytest.mark.parametrize("job_id", ["not-a-uuid", 5, None])
def test_an_unusable_job_id_is_not_kept(schemas: Schemas, job_id: object) -> None:
    message = raw(JobType.PART1_RUN, run_id=9, job_id=job_id)
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert result.kind is RejectionKind.FINISH
    assert result.job_id is None


def test_invalid_validation_with_a_job_id_is_finished(schemas: Schemas) -> None:
    message = raw(JobType.VALIDATION, payload={})
    result = _rejected(parse_message(message, JobType.VALIDATION, schemas))
    assert result.kind is RejectionKind.FINISH
    assert result.run_id is None
    assert result.job_id is not None


def test_invalid_validation_without_a_job_id_is_dropped(schemas: Schemas) -> None:
    message = raw(JobType.VALIDATION, payload={}, job_id="nope")
    result = _rejected(parse_message(message, JobType.VALIDATION, schemas))
    assert result.kind is RejectionKind.UNREADABLE


def test_completion_formats_are_checked(schemas: Schemas) -> None:
    message = {
        "contract_version": "1.0",
        "job_type": "PART2_SOLVE",
        "job_id": "not-a-uuid",
        "run_id": 1,
        "status": "DONE",
        "outcome": "SOLVED",
        "error_category": None,
        "finished_at": "not a time",
        "worker_version": "0.1.0",
    }
    assert list(schemas.completion.iter_errors(message))


def test_the_reason_does_not_echo_values(schemas: Schemas) -> None:
    message = raw(JobType.PART1_RUN, run_id=9, payload={"berthing_request_id": "SENTINEL"})
    result = _rejected(parse_message(message, JobType.PART1_RUN, schemas))
    assert "SENTINEL" not in result.reason
