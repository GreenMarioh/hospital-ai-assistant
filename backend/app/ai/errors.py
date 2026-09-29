class AIError(Exception):
    """Base class for AI-layer failures. Callers degrade gracefully instead of failing the request."""


class AIUnavailable(AIError):
    """AI disabled, unconfigured, circuit open, or the provider kept failing."""


class AIInvalidOutput(AIError):
    """The model did not return output matching the required schema (after one retry)."""
