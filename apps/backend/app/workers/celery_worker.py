"""
Celery worker エントリポイント.
"""

from app.adapters.queue import get_celery_app

celery_app = get_celery_app()
