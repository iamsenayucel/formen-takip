from __future__ import annotations

from typing import Any

from pydantic.alias_generators import to_camel


class ApiException(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


def fields_from_errors(errors: dict[str, str]) -> dict[str, Any]:
    return {"fields": [{"field": to_camel(field), "reason": reason} for field, reason in errors.items()]}


class BadRequestError(ApiException):
    status_code = 400
    code = "BAD_REQUEST"


class UnauthorizedError(ApiException):
    status_code = 401
    code = "UNAUTHORIZED"


class NotFoundError(ApiException):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class ConflictError(ApiException):
    status_code = 409
    code = "CONFLICT"


class ValidationFailedError(ApiException):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimitExceededError(ApiException):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str, *, retry_after_seconds: int, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details=details)
        self.retry_after_seconds = retry_after_seconds


class ServiceUnavailableError(ApiException):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"


class UpstreamServiceError(ApiException):
    status_code = 502
    code = "UPSTREAM_SERVICE_ERROR"


class ForemanNotFoundError(NotFoundError):
    code = "FOREMAN_NOT_FOUND"


class ForemanKpiRecordNotFoundError(NotFoundError):
    code = "FOREMAN_KPI_RECORD_NOT_FOUND"


class ChiefNotFoundError(NotFoundError):
    code = "CHIEF_NOT_FOUND"


class PlantNotFoundError(NotFoundError):
    code = "PLANT_NOT_FOUND"


class KpiNotFoundError(NotFoundError):
    code = "KPI_NOT_FOUND"


class AnomalyNotFoundError(NotFoundError):
    code = "ANOMALY_NOT_FOUND"


class AnomalyAnalysisNotFoundError(NotFoundError):
    code = "ANOMALY_ANALYSIS_NOT_FOUND"


class ContributionWorkNotFoundError(NotFoundError):
    code = "CONTRIBUTION_WORK_NOT_FOUND"


class ReportNotFoundError(NotFoundError):
    code = "REPORT_NOT_FOUND"


class MonthlyReportNotFoundError(NotFoundError):
    code = "MONTHLY_REPORT_NOT_FOUND"


class ShiftAnalysisNotFoundError(NotFoundError):
    code = "SHIFT_ANALYSIS_NOT_FOUND"


class InvalidCursorError(BadRequestError):
    code = "INVALID_CURSOR"


class InvalidMonthParameterError(BadRequestError):
    code = "INVALID_MONTH_PARAMETER"


class InvalidReportPeriodError(BadRequestError):
    code = "INVALID_REPORT_PERIOD"


class AnomalyAnalysisInProgressError(ConflictError):
    code = "ANOMALY_ANALYSIS_IN_PROGRESS"


class ContributionWorkValidationError(ValidationFailedError):
    code = "CONTRIBUTION_WORK_VALIDATION_FAILED"


class MonthlyReportPdfGenerationFailedError(UpstreamServiceError):
    code = "MONTHLY_REPORT_PDF_GENERATION_FAILED"


class MonthlyReportAccessUnavailableError(UpstreamServiceError):
    code = "MONTHLY_REPORT_ACCESS_UNAVAILABLE"
