"""Policy and configuration error taxonomy (Alpha)."""


class ConfigurationError(Exception):
    """Operator/environment configuration is invalid (e.g. missing WORKSPACE_ROOT)."""


class PolicyViolation(Exception):
    """A request violates policy."""


class PolicyEvaluationError(Exception):
    """Policy is loadable but this decision could not be completed (e.g. missing PIP data)."""


class PolicyConfigurationError(Exception):
    """Policy artifact is malformed, stale, or references missing resources."""


class EnforcementFailure(Exception):
    """Enforcement (PEP) could not apply a decided outcome."""


class TelemetryRecordTooLarge(Exception):
    """Serialized telemetry line exceeds the maximum allowed size (AppendOnlyStream)."""
