"""
Celery Worker Entry Point
Reference: start-worker.sh

This module provides the entry point for the Celery worker.
It imports the celery_app instance and registers all signal handlers.

Usage:
    celery -A app.worker worker --loglevel=info

The worker_ready signal in celery_app.py will fire when this worker starts,
registering the boot_id in Redis for chaos testing.
"""

# Import celery_app - this will register all signals
from app.core.celery_app import celery_app

# Re-export for Celery CLI
__all__ = ["celery_app"]
