"""The `queue:edi` job (AI-032): read the file, check it, and write the result in one go.

CT-12 run flow step 3. The handler only reads and calls `WorkerRepository`; it never commits.
The shared runtime (AI-011) commits these writes together with the guarded final run update, or
rolls all of them back, so a failure anywhere leaves nothing behind (NFR-REL-4).
"""

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Final

import sqlalchemy as sa

from common.config import OptionalEnvVar, WorkerPart
from common.db.connection import core_of
from common.db.repository import WorkerRepository
from common.db.tables import (
    BAPLIE_FILES,
    CONTAINER_SIZE_TYPES,
    CONTAINERS,
    IMDG_CLASSES,
    PORT_PROFILES,
    VESSELS,
)
from common.runtime.envelope import JobType
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.worker import JobContext, JobResult, WorkerDefinition
from edi.commit import FileContext, SizeType, WritePlan, plan_from_parse, plan_from_records
from edi.parser import parse_baplie
from edi.rules import StagedPayloadError, read_staged_payload
from edi.rules.checks import normalise_container_number

WORKER_VERSION: Final = "edi-0.2.0"
SOURCE_FILE: Final = "FILE"
SOURCE_STAGED: Final = "STAGED_PAYLOAD"
MAX_FILE_BYTES: Final = 10 * 1024 * 1024  # CT-12 upload limit


def make_handler(volume: Path) -> Any:
    """The BAPLIE_PARSE handler, reading uploaded files under `volume` (`AI_BAPLIE_VOLUME`)."""

    def handler(context: JobContext) -> JobResult:
        payload = context.envelope.payload
        file_id = int(payload["baplie_file_id"])
        source = str(payload["source"])
        connection = context.connection
        row = _file_row(connection, file_id)
        if source == SOURCE_FILE:
            parsed = parse_baplie(_read_file(volume, str(row["storage_path"])))
            numbers = [line.container_number for line in parsed.lines]
            plan = plan_from_parse(parsed, _context(connection, row, numbers))
        elif source == SOURCE_STAGED:
            staged = row["staged_payload"]
            if row["parse_status"] != "QUARANTINED" or not isinstance(staged, Mapping):
                raise JobError(
                    ErrorCategory.PRECONDITION_FAILED,
                    "a STAGED_PAYLOAD run needs a QUARANTINED file with a staged_payload",
                )
            try:
                vessel, lines = read_staged_payload(staged)
            except StagedPayloadError as error:
                raise JobError(ErrorCategory.PRECONDITION_FAILED, str(error)) from error
            numbers = [line.container_number for line in lines]
            plan = plan_from_records(vessel, lines, _context(connection, row, numbers))
        else:  # the envelope schema allows only the two sources
            raise JobError(ErrorCategory.INVALID_ENVELOPE, f"unknown source {source}")
        write(
            WorkerRepository(connection, WorkerPart.EDI, context.envelope.run_id),
            file_id,
            row,
            plan,
        )
        return JobResult(
            outcome=plan.outcome,
            run_columns={
                "container_count": plan.container_count,
                "result_detail": plan.result_detail,
            },
            completion_fields={"baplie_file_id": file_id},
        )

    return handler


def write(repo: WorkerRepository, file_id: int, row: Mapping[str, Any], plan: WritePlan) -> None:
    """Every write of the plan, in the caller's transaction."""
    if plan.outcome == "PARSED":
        ids = repo.insert_new_containers(_unique(plan.new_containers))
        entries = []
        for entry in plan.manifest:
            manifest_row = dict(entry)
            manifest_row["container_id"] = ids[str(manifest_row.pop("container_number"))]
            entries.append(manifest_row)
        repo.insert_many("container_manifest_entries", entries)
        if plan.vessel_fills:
            repo.fill_vessel_nulls(int(row["vessel_id"]), plan.vessel_fills)
    repo.insert_many("baplie_parse_issues", list(plan.issues))
    values: dict[str, object] = {"parse_status": plan.parse_status}
    if plan.outcome == "QUARANTINED":
        values["staged_payload"] = plan.staged_payload
    if not repo.update_baplie_file(file_id, values):
        raise JobError(ErrorCategory.PRECONDITION_FAILED, f"baplie_files {file_id} disappeared")


def _unique(rows: tuple[dict[str, object], ...]) -> list[dict[str, object]]:
    seen: dict[object, dict[str, object]] = {}
    for row in rows:
        seen.setdefault(row["container_number"], row)
    return list(seen.values())


def _file_row(connection: Any, file_id: int) -> Mapping[str, Any]:
    f = BAPLIE_FILES
    statement = sa.select(
        f.c.id, f.c.vessel_id, f.c.storage_path, f.c.parse_status, f.c.status, f.c.staged_payload
    ).where(f.c.id == file_id)
    row = core_of(connection).execute(statement).mappings().first()
    if row is None:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, f"no baplie_files row {file_id}")
    if row["status"] == "WITHDRAWN":
        raise JobError(ErrorCategory.PRECONDITION_FAILED, f"baplie_files {file_id} is WITHDRAWN")
    return dict(row)


def _context(connection: Any, row: Mapping[str, Any], numbers: list[str | None]) -> FileContext:
    core = core_of(connection)
    vessel = (
        core.execute(
            sa.select(VESSELS.c.imo_number, VESSELS.c.name, VESSELS.c.call_sign).where(
                VESSELS.c.id == row["vessel_id"]
            )
        )
        .mappings()
        .first()
    )
    if vessel is None or not vessel["imo_number"]:
        raise JobError(
            ErrorCategory.PRECONDITION_FAILED,
            "the request's vessel is missing or has no IMO number",
        )
    st = CONTAINER_SIZE_TYPES
    size_types = {
        r["code"]: SizeType(int(r["id"]), r["code"], bool(r["is_reefer"]))
        for r in core.execute(sa.select(st.c.id, st.c.code, st.c.is_reefer)).mappings()
    }
    if not size_types:
        raise JobError(ErrorCategory.CONFIGURATION_ERROR, "container_size_types is empty")
    imdg = frozenset(r[0] for r in core.execute(sa.select(IMDG_CLASSES.c.code)))
    port_code = core.execute(sa.select(PORT_PROFILES.c.port_code).limit(1)).scalar()
    keys = sorted({normalise_container_number(n) for n in numbers if n})
    stored: dict[str, str] = {}
    if keys:
        statement = (
            sa.select(CONTAINERS.c.container_number, st.c.code)
            .select_from(CONTAINERS.join(st, st.c.id == CONTAINERS.c.size_type_id))
            .where(CONTAINERS.c.container_number.in_(keys))
        )
        stored = {r[0]: r[1] for r in core.execute(statement)}
    return FileContext(
        baplie_file_id=int(row["id"]),
        vessel_id=int(row["vessel_id"]),
        vessel_imo=vessel["imo_number"],
        vessel_name=vessel["name"],
        vessel_call_sign=vessel["call_sign"],
        port_code=port_code,
        size_types=size_types,
        imdg_classes=imdg,
        stored_size_types=stored,
    )


def _read_file(volume: Path, storage_path: str) -> bytes:
    """The uploaded file, only from inside the BAPLIE volume."""
    posix = PurePosixPath(storage_path.replace("\\", "/"))
    if posix.is_absolute() or ".." in posix.parts or ":" in storage_path or not storage_path:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "storage_path must be inside the volume")
    root = volume.resolve()
    target = (root / Path(*posix.parts)).resolve()
    if not target.is_relative_to(root):
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "storage_path leaves the volume")
    try:
        size = target.stat().st_size
        if size > MAX_FILE_BYTES:
            raise JobError(ErrorCategory.PRECONDITION_FAILED, f"file is larger than 10 MB ({size})")
        return target.read_bytes()
    except FileNotFoundError as error:
        raise JobError(
            ErrorCategory.DATA_UNAVAILABLE, "the uploaded file is not on the volume"
        ) from error


def definition(env: Mapping[str, str]) -> WorkerDefinition:
    """The EDI worker for `run_worker` (`AI_BAPLIE_VOLUME` is required)."""
    volume = env.get(OptionalEnvVar.BAPLIE_VOLUME.value)
    if not volume:
        raise ValueError(f"{OptionalEnvVar.BAPLIE_VOLUME.value} is required for the EDI worker")
    return WorkerDefinition(JobType.BAPLIE_PARSE, make_handler(Path(volume)), (), WORKER_VERSION)
