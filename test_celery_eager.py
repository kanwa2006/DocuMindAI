import os
import sys

# Set env vars to simulate render
os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
os.environ['CELERY_BROKER_URL'] = 'redis://invalid-host:6379/0'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://invalid-host:6379/0'
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://user:pass@localhost/db'
os.environ['STORAGE_PROVIDER'] = 'local'
os.environ['STORAGE_PATH'] = '/tmp/storage'
os.environ['JWT_SECRET'] = 'secret'
os.environ['EMBEDDING_PROVIDER'] = 'gemini'
os.environ['GEMINI_API_KEY_1'] = 'fake'
os.environ['RERANKER_PROVIDER'] = 'none'
os.environ['SUPABASE_URL'] = 'http://localhost'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'fake'
os.environ['AUTH_SECRET_KEY'] = 'fake'
os.environ['CSRF_SECRET_KEY'] = 'fake'
os.environ['FRONTEND_URL'] = 'fake'
os.environ['POSTGRES_SERVER'] = 'fake'
os.environ['POSTGRES_USER'] = 'fake'
os.environ['POSTGRES_PASSWORD'] = 'fake'
os.environ['POSTGRES_DB'] = 'fake'
os.environ['REDIS_URL'] = 'redis://invalid-host:6379/0'

sys.path.insert(0, os.path.abspath('backend'))

try:
    from backend.app.workers.celery_app import celery_app
    from backend.app.workers.tasks.document_tasks import process_document
    print("Celery app imported.")
    
    # Try calling a simple task
    @celery_app.task
    def dummy_task():
        return "ok"
        
    print("Executing dummy_task.delay()...")
    dummy_task.delay()
    print("dummy_task executed successfully.")
except Exception as e:
    print('CAUGHT EXCEPTION:', type(e).__name__, e)
