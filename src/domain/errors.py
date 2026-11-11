from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    CLARIFICATION_REQUIRED = "clarification_required"
    SOURCE_ERROR = "source_error"
    NO_DATA = "no_data"


class DomainError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

