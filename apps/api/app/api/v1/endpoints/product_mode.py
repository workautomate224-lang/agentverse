"""
Product Mode API Endpoints

Exposes product mode information for frontend feature gating.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.services.product_mode import (
    get_product_mode_info,
    is_feature_enabled,
    get_enabled_modules,
    get_disabled_modules,
)

router = APIRouter()


@router.get("/info")
async def get_mode_info():
    """
    Get current product mode information.

    Returns product mode, enabled modules, and disabled modules.
    This endpoint is public and used by frontend for navigation gating.
    """
    return get_product_mode_info()


@router.get("/check/{module}")
async def check_feature(module: str):
    """
    Check if a specific feature module is enabled.

    Args:
        module: The feature module to check (e.g., 'universe-map', 'event-lab')

    Returns:
        enabled: True if the feature is enabled
        module: The module name
        product_mode: Current product mode
    """
    return {
        "module": module,
        "enabled": is_feature_enabled(module),
        "product_mode": get_product_mode_info()["mode"],
    }


@router.get("/modules/enabled")
async def list_enabled_modules():
    """Get list of all enabled modules in current product mode."""
    return {
        "modules": get_enabled_modules(),
        "product_mode": get_product_mode_info()["mode"],
    }


@router.get("/modules/disabled")
async def list_disabled_modules():
    """Get list of all disabled modules in current product mode."""
    return {
        "modules": get_disabled_modules(),
        "product_mode": get_product_mode_info()["mode"],
    }
