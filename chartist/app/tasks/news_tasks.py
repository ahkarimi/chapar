import logging
import time
import json
from celery import Task
from celery.signals import task_success, task_failure
from app.services.llm_service import LLMService
from app.services.news_manager import NewsManager
from app.core.cache import CacheManager
from app.schemas.news import NewsRequest
from app.models.database import SyncSessionLocal
from app.models.user import User
from app.models.history import AnalysisHistory
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='process_news')
def process_news_task(self, request_dict, user_id):
    """
    Background task to process news data using the LLM service.

    Args:
        request_dict: Dictionary representation of NewsRequest
        user_id: ID of the user who made the request

    Returns:
        The news analysis result from the LLM service
    """
    task_id = self.request.id
    start_time = time.time()
    logger.info(f"🔄 NEWS TASK STARTED: {task_id} for user {user_id}")

    try:
        # Log request details
        symbol = request_dict.get("symbol", "unknown")
        method = request_dict.get("method", "unknown")
        logger.info(f"📰 NEWS DETAILS: Symbol={symbol}, Method={method}")

        # Convert dict back to NewsRequest
        request = NewsRequest(**request_dict)

        # Create services
        logger.info(f"🔧 Creating services for news task {task_id}")
        llm_service = LLMService()
        cache_manager = CacheManager()
        manager = NewsManager(llm_service, cache_manager)

        # Get the news result - this is where the time-consuming operation happens
        logger.info(f"🔍 Starting news analysis for task {task_id}: symbol={symbol}, method={method}")

        analysis_start = time.time()
        result = manager.get_news_sync(request)  # Using synchronous version
        analysis_duration = time.time() - analysis_start

        # Log task completion
        total_duration = time.time() - start_time
        logger.info(f"✅ NEWS TASK COMPLETED: {task_id}, duration={total_duration:.2f}s (analysis={analysis_duration:.2f}s)")

        # Summarize response size
        if isinstance(result, dict):
            response_size = len(json.dumps(result)) / 1024  # size in KB
            if "content" in result:
                content_length = len(result.get("content", "")) if result.get("content") else 0
                logger.info(f"📑 NEWS RESPONSE STATS: Size={response_size:.2f}KB, Content length={content_length} chars")

        # Log news request (no credit deduction in time-based system)
        try:
            with SyncSessionLocal() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    log_entry = AnalysisHistory(
                        user_id=user_id,
                        symbol=request_dict.get('symbol'),
                        method="news_" + request_dict.get('method'),
                        status="success"
                    )
                    db.add(log_entry)
                    db.commit()
                    logger.info(f"Task {task_id}: Logged news request for user {user_id}")
        except Exception as ded_err:
            logger.error(f"Task {task_id}: Error logging news request: {ded_err}")
            logger.exception(ded_err)
        return result

    except Exception as e:
        error_duration = time.time() - start_time
        logger.error(f"❌ NEWS TASK ERROR: {task_id}, error={str(e)}, duration={error_duration:.2f}s")
        logger.exception(e)  # Log stack trace
        raise

# Signal handlers to update user credits and history
@task_success.connect(sender='process_news')
def handle_successful_news(sender: Task = None, **kwargs):
    """Log successful news task completion."""
    task_id = sender.request.id if sender and sender.request else "unknown"
    start_time = time.time()
    # Credit deduction is now handled directly in the task
    logger.info(f"SIGNAL: News Task {task_id} completed successfully (credit deduction handled in task). Duration: {time.time() - start_time:.2f}s")

logger.info("handle_successful_news signal handler defined and connected.")

@task_failure.connect(sender='process_news')
def handle_failed_news(sender: Task = None, **kwargs):
    """Update history on failed news processing."""
    task_id = sender.request.id if sender and sender.request else "unknown"
    start_time = time.time()
    logger.info(f"⚠️ SIGNAL - NEWS TASK FAILURE: {task_id}")

    try:
        # Access arguments from the sender's request context
        request_args = sender.request.args
        exception = kwargs.get('exception')

        # Assuming user_id is the second positional argument
        if len(request_args) >= 2:
            request_dict = request_args[0]
            user_id = request_args[1]

            # Use the synchronous DB session for failure logging
            with SyncSessionLocal() as db:
                log_entry = AnalysisHistory(
                    user_id=user_id,
                    symbol=request_dict.get('symbol'),
                    method="news_" + request_dict.get('method'),
                    status="failed"
                )
                db.add(log_entry)
                db.commit() # Commit the synchronous session

                elapsed = time.time() - start_time
                logger.info(f"📝 FAILURE LOGGED: User {user_id}, task {task_id}, duration={elapsed:.2f}s")
                logger.error(f"🔴 FAILURE REASON: {exception}")
        else:
            logger.error(f"⚠️ MISSING ARGS: Could not extract user_id from task {task_id} for failure logging")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ERROR LOGGING FAILURE: task={task_id}, error={str(e)}, duration={elapsed:.2f}s")
        logger.exception(e)

logger.info("handle_failed_news signal handler defined and connected.")
