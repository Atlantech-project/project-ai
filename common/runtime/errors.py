"""The CT-08 §7 error categories, and the error a job handler raises to report one."""

from enum import StrEnum


class ErrorCategory(StrEnum):
    INVALID_ENVELOPE = "INVALID_ENVELOPE"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INFEASIBLE = "INFEASIBLE"
    SOLVER_ERROR = "SOLVER_ERROR"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class JobError(Exception):
    """A job failed for a reason the contract names. The message is stored and shown to staff."""

    def __init__(self, category: ErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
