"""
Celery Worker Entry Point

This module exposes the Celery application for the worker command:
    celery -A app.worker worker --loglevel=info

Reference: app/core/celery_app.py for full configuration
"""

from app.core.celery_app import celery_app

# Re-export celery_app as 'app' for celery CLI compatibility
app = celery_app

# Also export as celery_app for explicit imports
__all__ = ["celery_app", "app"]
