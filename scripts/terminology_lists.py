"""Terminology lists for FSAA Alpha (PDP/PEP/PIP industry language)."""

FORBIDDEN_LEGACY: frozenset[str] = frozenset()

REQUIRED_INDUSTRY: frozenset[str] = frozenset(
    {
        "policy decision point",
        "policy enforcement point",
        "policy information point",
    }
)

ALLOWED_EVERYWHERE: frozenset[str] = frozenset()
