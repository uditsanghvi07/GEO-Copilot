"""Custom exception hierarchy.

No except block in this codebase should silently swallow an error: it must
log via loguru and either re-raise one of these typed exceptions or return a
typed error response. Keeping them here (rather than per-module) gives the
Orchestrator and API layer a single place to catch known failure classes.
"""


class AppError(Exception):
    """Base class for all application-raised errors."""


class ExternalServiceError(AppError):
    """Raised when an outbound call (LLM, website fetch, Play Store, etc.)
    fails after all retry attempts have been exhausted."""


class AgentExecutionError(AppError):
    """Raised when an agent's `run()` fails in a way that should be
    surfaced distinctly from a generic external service failure."""


class NotFoundError(AppError):
    """Raised when a requested entity does not exist."""


class AuthError(AppError):
    """Raised for authentication/authorization failures."""
