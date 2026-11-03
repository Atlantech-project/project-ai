"""Loading the contract schemas and reading a message from a queue (CT-08 §1 to §3, §6 step 2).

A message arriving on another job type's queue is never claimed. CT-08 §6 step 3 says to finish
the run when `run_id` can be read, but that id belongs to the other job type's table: claiming it
here could fail an unrelated run with the same number. This is a deliberate deviation, with a
Proposed change to CT-08 (AI-011).
"""

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, best_match
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from common.config import ConfigurationError, OptionalEnvVar

_REPO_ROOT: Final = Path(__file__).resolve().parents[2]
_DEV_SCHEMA_DIR: Final = Path("docs") / "ref" / "ai-payloads"
_ENVELOPE_FILE: Final = "envelope.schema.json"
_COMPLETION_FILE: Final = "c06-completion.schema.json"
_JOB_ID_TEXT: Final = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

SCHEMA_FILES: Final = (
    _ENVELOPE_FILE,
    "c01-part1-run.schema.json",
    "c02-part2-solve.schema.json",
    "c03-yard.schema.json",
    "c04-baplie.schema.json",
    "c05-validation.schema.json",
    _COMPLETION_FILE,
)


class JobType(StrEnum):
    PART1_RUN = "PART1_RUN"
    PART2_SOLVE = "PART2_SOLVE"
    YARD_PLACEMENT = "YARD_PLACEMENT"
    BAPLIE_PARSE = "BAPLIE_PARSE"
    VALIDATION = "VALIDATION"


QUEUES: Final[Mapping[JobType, str]] = {
    JobType.PART1_RUN: "queue:part1",
    JobType.PART2_SOLVE: "queue:part2",
    JobType.YARD_PLACEMENT: "queue:yard",
    JobType.BAPLIE_PARSE: "queue:edi",
    JobType.VALIDATION: "queue:validate",
}


@dataclass(frozen=True)
class Schemas:
    envelope: Draft202012Validator
    completion: Draft202012Validator


def resolve_schema_dir(env: Mapping[str, str], repo_root: Path = _REPO_ROOT) -> Path:
    """`AI_SCHEMA_DIR`, or the `docs/ref` mirror only inside a Git checkout (development and CI).

    A deployment has no `.git`, so it must set the variable and ship the files (AI-090).
    """
    configured = env.get(OptionalEnvVar.SCHEMA_DIR, "").strip()
    if configured:
        return Path(configured)
    if (repo_root / ".git").exists():
        return repo_root / _DEV_SCHEMA_DIR
    raise ConfigurationError(
        f"{OptionalEnvVar.SCHEMA_DIR} must be set outside a development checkout",
        [OptionalEnvVar.SCHEMA_DIR],
    )


def _load_schema(directory: Path, name: str) -> dict[str, Any]:
    try:
        contents: dict[str, Any] = json.loads((directory / name).read_text(encoding="utf-8"))
        if not isinstance(contents, dict) or "$id" not in contents:
            raise ValueError("not a schema object with an $id")
        Draft202012Validator.check_schema(contents)
    except (OSError, ValueError, SchemaError) as error:
        raise ConfigurationError(
            f"schema {name} can't be loaded from {directory}: {type(error).__name__}", [name]
        ) from error
    return contents


def _references(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _references(value)
    elif isinstance(node, list):
        for item in node:
            yield from _references(item)


def load_schemas(directory: Path) -> Schemas:
    """Load every contract schema. A problem stops the worker at startup."""
    loaded = {name: _load_schema(directory, name) for name in SCHEMA_FILES}
    registry: Registry[Any] = Registry().with_resources(
        (
            contents["$id"],
            Resource.from_contents(contents, default_specification=DRAFT202012),
        )
        for contents in loaded.values()
    )
    # The registry resolves lazily: without this, a dangling $ref would only fail at job time.
    for name, contents in loaded.items():
        resolver = registry.resolver(contents["$id"])
        for reference in _references(contents):
            try:
                resolver.lookup(reference)
            except Unresolvable as error:
                raise ConfigurationError(
                    f"schema {name} has an unresolvable $ref {reference}", [name]
                ) from error
    checker = Draft202012Validator.FORMAT_CHECKER
    return Schemas(
        envelope=Draft202012Validator(
            loaded[_ENVELOPE_FILE], registry=registry, format_checker=checker
        ),
        completion=Draft202012Validator(
            loaded[_COMPLETION_FILE], registry=registry, format_checker=checker
        ),
    )


@dataclass(frozen=True)
class Envelope:
    contract_version: str
    job_type: JobType
    job_id: str
    run_id: int | None
    enqueued_at: str
    triggered_by_user_id: int | None
    payload: Mapping[str, Any]


class RejectionKind(StrEnum):
    WRONG_QUEUE = "WRONG_QUEUE"
    FINISH = "FINISH"
    UNREADABLE = "UNREADABLE"


@dataclass(frozen=True)
class Rejection:
    """Why a message wasn't accepted, and what could still be read from it."""

    kind: RejectionKind
    reason: str
    job_type: str | None = None
    job_id: str | None = None
    run_id: int | None = None
    contract_version: str | None = None


def _reject_json_constant(_: str) -> None:
    raise ValueError("NaN and Infinity are not JSON")


def _readable_run_id(value: object) -> int | None:
    is_id = isinstance(value, int) and not isinstance(value, bool) and value >= 1
    return value if is_id else None  # type: ignore[return-value]


def _readable_job_id(value: object) -> str | None:
    return value if isinstance(value, str) and _JOB_ID_TEXT.fullmatch(value) else None


def _reason(body: dict[str, Any], schemas: Schemas) -> str | None:
    error = best_match(schemas.envelope.iter_errors(body))
    if error is None:
        return None
    # The path and keyword only: the message itself can repeat the value.
    path = "/".join(str(part) for part in error.absolute_path) or "(message)"
    return f"{path} fails {error.validator}"


def parse_message(raw: bytes | str, job_type: JobType, schemas: Schemas) -> Envelope | Rejection:
    """Read one queue element for a worker of this job type (CT-08 §6 steps 1 to 3).

    A Redis client returns `str` when it's set to decode responses, `bytes` otherwise.
    """
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        body = json.loads(text, parse_constant=_reject_json_constant)
    except ValueError, RecursionError:
        return Rejection(RejectionKind.UNREADABLE, "not UTF-8 JSON")
    if not isinstance(body, dict):
        return Rejection(RejectionKind.UNREADABLE, "not a JSON object")

    version = body.get("contract_version")
    job_id = _readable_job_id(body.get("job_id"))
    run_id = _readable_run_id(body.get("run_id"))
    contract_version = version if isinstance(version, str) else None
    if "job_type" in body and body["job_type"] != job_type:
        sent = body["job_type"]
        return Rejection(
            RejectionKind.WRONG_QUEUE,
            f"job_type doesn't match {QUEUES[job_type]}",
            job_type=sent if isinstance(sent, str) else repr(sent),
            job_id=job_id,
            run_id=run_id,
            contract_version=contract_version,
        )
    reason = _reason(body, schemas)
    if reason is None and job_type is not JobType.VALIDATION and run_id is None:
        # The schema's `integer` accepts 1.0, which isn't a usable run id.
        return Rejection(
            RejectionKind.UNREADABLE,
            "run_id isn't an integer",
            job_type=job_type,
            job_id=job_id,
            contract_version=contract_version,
        )
    if reason is None:
        return Envelope(
            contract_version=body["contract_version"],
            job_type=job_type,
            job_id=body["job_id"],
            run_id=body["run_id"],
            enqueued_at=body["enqueued_at"],
            triggered_by_user_id=body["triggered_by_user_id"],
            payload=body["payload"],
        )
    key = job_id if job_type is JobType.VALIDATION else run_id
    kind = RejectionKind.UNREADABLE if key is None else RejectionKind.FINISH
    return Rejection(
        kind,
        reason,
        job_type=job_type,
        job_id=job_id,
        run_id=run_id,
        contract_version=contract_version,
    )
