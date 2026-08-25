"""Secure runtime boundaries for reviewed Google ADK skill bundles."""

from .adapter import AdkRuntimeAdapter
from .errors import (
    AuthorizationError,
    BudgetExceededError,
    BundleVerificationError,
    CancellationRequestedError,
)
from .models import (
    BundleManifest,
    ReleaseReceipt,
    RuntimePolicy,
    VerifiedSkillBundle,
)
from .synthetic import (
    SyntheticPrincipal,
    SyntheticResult,
    SyntheticSupportAgent,
    build_synthetic_bundle,
)
from .verification import verify_skill_bundle

__version__ = "0.1.0"

__all__ = [
    "AdkRuntimeAdapter",
    "AuthorizationError",
    "BudgetExceededError",
    "BundleManifest",
    "BundleVerificationError",
    "CancellationRequestedError",
    "ReleaseReceipt",
    "RuntimePolicy",
    "SyntheticPrincipal",
    "SyntheticResult",
    "SyntheticSupportAgent",
    "VerifiedSkillBundle",
    "build_synthetic_bundle",
    "verify_skill_bundle",
]
