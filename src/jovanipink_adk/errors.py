"""Public error types for fail-closed runtime behavior."""


class BundleVerificationError(ValueError):
    """A bundle failed integrity, policy, release, or compatibility checks."""


class AuthorizationError(PermissionError):
    """A principal or tool request is outside deterministic host policy."""


class BudgetExceededError(RuntimeError):
    """A deterministic execution budget has been exhausted."""


class CancellationRequestedError(RuntimeError):
    """A request was canceled before another effect could occur."""
