"""Shared exceptions for deterministic platform services."""


class AdvayError(Exception):
    """Base platform error."""


class ValidationError(AdvayError):
    """Raised when contract validation fails."""


class UnsupportedMetricError(AdvayError):
    """Raised when a requested metric is not supported."""


class UnsupportedFilterError(AdvayError):
    """Raised when a requested filter key is not supported."""


class MetricNotFoundError(AdvayError):
    """Raised when deterministic SQL returns no metric value."""


class MetricComputationError(AdvayError):
    """Raised when deterministic SQL cannot compute a metric safely."""
