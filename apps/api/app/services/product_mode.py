"""
Product Mode Service - MVP Feature Gating

Demo2 MVP focuses on Collective/Persona-driven predictions:
- Create Project (goal + temporal cutoff)
- Inputs (Personas + optional Evidence URLs)
- Baseline Run (one-click)
- What-if Scenarios (natural language → event script → branch run)
- Results Compare (baseline vs branch, probability deltas)
- Report Export (auditable: includes versions, cutoff, sources)

Hidden features in MVP_DEMO2 mode:
- Universe Map graph visualization
- World viewer
- Replay viewer
- Rules configuration
- Reliability dashboard
- Society/Target/Hybrid mode planners
"""

from enum import Enum
from typing import List, Set
from fastapi import HTTPException, status

from app.core.config import settings


class ProductMode(str, Enum):
    """Product mode options."""
    MVP_DEMO2 = "MVP_DEMO2"  # Collective/Persona-driven predictions only
    FULL = "FULL"  # All features enabled


class FeatureModule(str, Enum):
    """Feature modules that can be gated."""
    # Demo2 MVP - ENABLED
    OVERVIEW = "overview"
    DATA_PERSONAS = "data-personas"
    EVENT_LAB = "event-lab"
    RUN_CENTER = "run-center"
    REPORTS = "reports"
    SETTINGS = "settings"

    # Demo2 MVP - DISABLED (hidden)
    UNIVERSE_MAP = "universe-map"
    RULES = "rules"
    RELIABILITY = "reliability"
    REPLAY = "replay"
    WORLD_VIEWER = "world-viewer"
    SOCIETY = "society"
    TARGET = "target"


# Features enabled in MVP_DEMO2 mode
MVP_DEMO2_ENABLED_MODULES: Set[str] = {
    FeatureModule.OVERVIEW.value,
    FeatureModule.DATA_PERSONAS.value,
    FeatureModule.EVENT_LAB.value,
    FeatureModule.RUN_CENTER.value,
    FeatureModule.REPORTS.value,
    FeatureModule.SETTINGS.value,
}

# Features disabled in MVP_DEMO2 mode
MVP_DEMO2_DISABLED_MODULES: Set[str] = {
    FeatureModule.UNIVERSE_MAP.value,
    FeatureModule.RULES.value,
    FeatureModule.RELIABILITY.value,
    FeatureModule.REPLAY.value,
    FeatureModule.WORLD_VIEWER.value,
    FeatureModule.SOCIETY.value,
    FeatureModule.TARGET.value,
}


def get_current_product_mode() -> ProductMode:
    """Get the current product mode from settings."""
    mode = settings.PRODUCT_MODE.upper()
    if mode == ProductMode.MVP_DEMO2.value:
        return ProductMode.MVP_DEMO2
    elif mode == ProductMode.FULL.value:
        return ProductMode.FULL
    else:
        # Default to MVP_DEMO2 for safety
        return ProductMode.MVP_DEMO2


def is_mvp_mode() -> bool:
    """Check if we're running in MVP_DEMO2 mode."""
    return get_current_product_mode() == ProductMode.MVP_DEMO2


def is_feature_enabled(module: str) -> bool:
    """
    Check if a feature module is enabled in the current product mode.

    Args:
        module: The feature module name (e.g., 'universe-map', 'event-lab')

    Returns:
        True if the feature is enabled, False otherwise
    """
    current_mode = get_current_product_mode()

    if current_mode == ProductMode.FULL:
        return True

    # MVP_DEMO2 mode - check if module is in enabled list
    return module.lower() in MVP_DEMO2_ENABLED_MODULES


def get_enabled_modules() -> List[str]:
    """Get list of enabled modules for current product mode."""
    current_mode = get_current_product_mode()

    if current_mode == ProductMode.FULL:
        return [m.value for m in FeatureModule]

    return list(MVP_DEMO2_ENABLED_MODULES)


def get_disabled_modules() -> List[str]:
    """Get list of disabled modules for current product mode."""
    current_mode = get_current_product_mode()

    if current_mode == ProductMode.FULL:
        return []

    return list(MVP_DEMO2_DISABLED_MODULES)


class FeatureDisabledError(HTTPException):
    """Exception raised when a feature is disabled in current product mode."""

    def __init__(self, feature: str, detail: str = None):
        message = detail or f"Feature '{feature}' is disabled in MVP mode. This feature will be available in a future release."
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FeatureDisabled",
                "feature": feature,
                "message": message,
                "product_mode": get_current_product_mode().value,
            }
        )


def require_feature(module: str):
    """
    Dependency that raises FeatureDisabledError if the feature is disabled.

    Use as a FastAPI dependency:
        @router.get("/universe-map")
        async def get_universe_map(
            _: None = Depends(lambda: require_feature("universe-map"))
        ):
            ...
    """
    if not is_feature_enabled(module):
        raise FeatureDisabledError(module)
    return None


def feature_gate(module: str):
    """
    Decorator for gating endpoint functions based on product mode.

    Usage:
        @router.get("/universe-map")
        @feature_gate("universe-map")
        async def get_universe_map():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not is_feature_enabled(module):
                raise FeatureDisabledError(module)
            return await func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# Export product mode info for API responses
def get_product_mode_info() -> dict:
    """Get product mode information for API responses."""
    return {
        "mode": get_current_product_mode().value,
        "is_mvp": is_mvp_mode(),
        "enabled_modules": get_enabled_modules(),
        "disabled_modules": get_disabled_modules(),
    }
