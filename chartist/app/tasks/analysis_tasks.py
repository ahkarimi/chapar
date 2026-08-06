import logging
import time
import json
from celery import Task
from celery.signals import task_success, task_failure
from app.services.chart_service import ChartService
from app.services.llm_service import LLMService
from app.services.analysis_manager import AnalysisManager
from app.core.cache import CacheManager
from app.schemas.analysis import AnalysisRequest
from app.models.database import SyncSessionLocal
from app.models.user import User
from app.models.history import AnalysisHistory
from app.config import settings
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='analyze_stock')
def analyze_stock_task(self, request_dict, user_id):
    """
    Background task to analyze stock data using the LLM service.
    No credit deduction - time-based plan system.

    Args:
        request_dict: Dictionary representation of AnalysisRequest
        user_id: ID of the user who made the request

    Returns:
        The analysis result from the LLM service
    """
    task_id = self.request.id
    start_time = time.time()
    logger.info(f"🔄 TASK STARTED: {task_id} for user {user_id}")

    try:
        # Log request details
        symbol = request_dict.get("symbol", request_dict.get("chart_schema", {}).get("symbol", "unknown"))
        method = request_dict.get("analyze_method", "unknown")
        logger.info(f"📊 ANALYSIS DETAILS: Symbol={symbol}, Method={method}")

        # Convert dict back to AnalysisRequest
        request = AnalysisRequest(**request_dict)

        # Create services
        logger.info(f"🔧 Creating services for task {task_id}")
        chart_service = ChartService()
        llm_service = LLMService()
        cache_manager = CacheManager()
        manager = AnalysisManager(chart_service, llm_service, cache_manager)

        # Get the analysis result - this is where the time-consuming operation happens
        logger.info(f"🔍 Starting analysis for task {task_id}: symbol={symbol}, method={method}")

        analysis_start = time.time()
        try:
            result = manager.analyze_sync(request)  # Using synchronous version
            analysis_duration = time.time() - analysis_start

            # Log task completion
            total_duration = time.time() - start_time
            logger.info(f"✅ TASK COMPLETED: {task_id}, duration={total_duration:.2f}s (analysis={analysis_duration:.2f}s)")

            # Summarize response size
            if isinstance(result, dict):
                response_size = len(json.dumps(result)) / 1024  # size in KB
                if "llm_response" in result:
                    llm_answer = result.get("llm_response", {}).get("answer", "")
                    answer_length = len(llm_answer) if llm_answer else 0
                    logger.info(f"📑 RESPONSE STATS: Size={response_size:.2f}KB, Answer length={answer_length} chars")

            # Log analysis history (no credit deduction in time-based system)
            try:
                with SyncSessionLocal() as db:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        user.total_requests += 1
                        logger.info(f"Task {task_id}: User {user_id} total_requests incremented to {user.total_requests}")

                        history_entry = AnalysisHistory(
                            user_id=user_id,
                            symbol=request_dict.get('symbol', request_dict.get('chart_schema', {}).get('symbol')),
                            method=request_dict.get('analyze_method'),
                            status='success'
                        )
                        db.add(history_entry)
                        db.commit()
            except Exception as log_err:
                logger.error(f"Task {task_id}: Error logging analysis history: {log_err}")
                logger.exception(log_err)

            # Return the result
            return result

        except ValueError as e:
            # This is the validation error raised by analysis_manager
            logger.error(f"❌ VALIDATION ERROR: {task_id}, error={str(e)}")
            # We need to raise the error to prevent history logging
            raise ValueError(f"Invalid analysis result: {str(e)}")

    except Exception as e:
        error_duration = time.time() - start_time
        logger.error(f"❌ TASK ERROR: {task_id}, error={str(e)}, duration={error_duration:.2f}s")
        logger.exception(e)  # Log stack trace
        raise

# Signal handlers to update user history
@task_success.connect(sender='analyze_stock')
def handle_successful_analysis(sender: Task = None, **kwargs):
    """Log successful analysis task completion."""
    task_id = sender.request.id if sender and sender.request else "unknown"
    start_time = time.time()
    logger.info(f"SIGNAL: Analysis Task {task_id} completed successfully (history logged in task). Duration: {time.time() - start_time:.2f}s")

logger.info("handle_successful_analysis signal handler defined and connected.")

@task_failure.connect(sender='analyze_stock')
def handle_failed_analysis(sender: Task = None, **kwargs):
    """Update history on failed analysis."""
    task_id = sender.request.id if sender and sender.request else "unknown"
    start_time = time.time()
    logger.info(f"⚠️ SIGNAL - TASK FAILURE: {task_id}")

    try:
        # Access arguments from the sender's request context
        request_args = sender.request.args
        request_kwargs = sender.request.kwargs
        exception = kwargs.get('exception')

        # Assuming user_id is the second positional argument
        if len(request_args) >= 2:
            request_dict = request_args[0]
            user_id = request_args[1]

            # Use the synchronous DB session for failure logging too
            with SyncSessionLocal() as db:
                log_entry = AnalysisHistory(
                    user_id=user_id,
                    symbol=request_dict.get('symbol', request_dict.get('chart_schema', {}).get('symbol')),
                    method=request_dict.get('analyze_method'),
                    status="failed"
                )
                db.add(log_entry)
                db.commit()

                elapsed = time.time() - start_time
                logger.info(f"📝 FAILURE LOGGED: User {user_id}, task {task_id}, duration={elapsed:.2f}s")
                logger.error(f"🔴 FAILURE REASON: {exception}")
        else:
            logger.error(f"⚠️ MISSING ARGS: Could not extract user_id from task {task_id} for failure logging")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ERROR LOGGING FAILURE: task={task_id}, error={str(e)}, duration={elapsed:.2f}s")
        logger.exception(e)

logger.info("handle_failed_analysis signal handler defined and connected.")
