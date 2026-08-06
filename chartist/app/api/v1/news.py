from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from app.schemas.news import NewsRequest
from app.services.llm_service import LLMService
from app.services.news_manager import NewsManager
from app.core.cache import CacheManager
from app.core.dependency import get_user_by_telegram
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.history import AnalysisHistory
from app.tasks.news_tasks import process_news_task
import logging
import time

# Get logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection for services
def get_news_manager() -> NewsManager:
    llm_service = LLMService()
    cache_manager = CacheManager()
    return NewsManager(llm_service, cache_manager)

@router.post("/news/")
async def get_news(
    request: NewsRequest,
    background_tasks: BackgroundTasks,
    manager: NewsManager = Depends(get_news_manager),
    user=Depends(get_user_by_telegram),
    db: AsyncSession = Depends(get_db),
):
    """
    Get news about a cryptocurrency using background task processing:
    1. Submit the task to Celery
    2. Return task ID for client to poll
    """
    start_time = time.time()
    logger.info(f"==== NEWS REQUEST RECEIVED ====")
    logger.info(f"User: {user.id}, Symbol: {request.symbol}, Method: {request.method.value}")

    # Check cache first for immediate response
    cached_result_data = None # Initialize
    try:
        # Create a cache key based on the request
        cache_key = f"news:v2:{request.symbol}:{request.method.value}:{request.response_language}:{request.query or 'default'}"
        logger.info(f"Checking cache for key: {cache_key}")
        cached_raw = await manager.cache_manager.get(cache_key)

        if cached_raw:
            logger.info(f"Raw data found in cache for {cache_key}")
            # Attempt to deserialize
            cached_result_data = manager.cache_manager.deserialize(cached_raw)
            if cached_result_data: # Check if deserialization was successful
                # We have a valid cached result, return it immediately
                cached_time = time.time() - start_time
                logger.info(f"✅ CACHE HIT: Returning valid cached news result in {cached_time:.2f}s")

                # Still need to deduct credits and log the request for cache hit
                background_tasks.add_task(_deduct_credits_for_cached_result, user.id, request)

                return {
                    "cached": True,
                    **cached_result_data # Return deserialized data
                }
            else:
                logger.warning(f"Cache data found for {cache_key} but failed to deserialize. Proceeding to task.")
        else:
            logger.info(f"❌ CACHE MISS: No data found for key {cache_key}")

    except Exception as e:
        # Log the cache error but continue with the request
        logger.error(f"Cache check/deserialize error: {str(e)}. Proceeding to task.")
        logger.exception(e) # Log stack trace for cache errors

    # If cache_result_data is still None here, it means cache miss or deserialization failed
    logger.info(f"Proceeding to queue Celery task for news request (Symbol: {request.symbol}, Method: {request.method.value})")
    # Step 3: Run the request through Celery
    try:
        # Convert the request to a dictionary for serialization
        request_dict = request.dict()

        # Submit task to Celery
        task = process_news_task.delay(request_dict, user.id)
        task_id = task.id

        process_time = time.time() - start_time
        logger.info(f"🔄 TASK QUEUED: {task_id} in {process_time:.2f}s")

        # Return task information to the client
        return {
            "is_task": True,
            "task_id": task_id,
            "status": "processing",
            "symbol": request.symbol,
            "method": request.method.value
        }

    except Exception as e:
        logger.error(f"Error submitting news task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process news request. Please try again later.",
        )

@router.get("/news/status/{task_id}")
async def check_news_status(
    task_id: str,
    user=Depends(get_user_by_telegram),
):
    """
    Check the status of a news task.
    """
    start_time = time.time()
    logger.info(f"Checking status for news task {task_id}")

    try:
        # Get the task result
        task = process_news_task.AsyncResult(task_id)

        if task.state == 'PENDING':
            # Task hasn't started yet
            return {
                "is_task": True,
                "task_id": task_id,
                "status": "pending",
                "message": "Task is pending processing"
            }
        elif task.state == 'STARTED':
            # Task has started but not completed
            return {
                "is_task": True,
                "task_id": task_id,
                "status": "processing",
                "message": "Task is processing"
            }
        elif task.state == 'SUCCESS':
            # Task completed successfully
            result = task.result
            process_time = time.time() - start_time
            logger.info(f"✅ TASK RESULT RETRIEVED: {task_id} in {process_time:.2f}s")

            # Return the result
            return {
                "status": "completed",
                "result": result
            }
        elif task.state == 'FAILURE':
            # Task failed
            error = str(task.result) if task.result else "Unknown error"
            logger.error(f"❌ TASK FAILED: {task_id}, error: {error}")

            return {
                "status": "failed",
                "error": error
            }
        else:
            # Other states
            return {
                "is_task": True,
                "task_id": task_id,
                "status": task.state.lower(),
                "message": f"Task is in state: {task.state}"
            }
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check task status: {str(e)}",
        )

async def _deduct_credits_for_cached_result(user_id: int, request: NewsRequest):
    """Background task to log cached news requests."""
    try:
        # Use the async session maker for the background task
        async with AsyncSessionLocal() as db:
            async with db.begin():
                user = await db.get(User, user_id)
                if user:
                    # Log the request (no credit deduction in time-based system)
                    log_entry = AnalysisHistory(
                        user_id=user_id,
                        symbol=request.symbol,
                        method="news_" + request.method.value,
                        status="success"
                    )
                    db.add(log_entry)

                    logger.info(f"Logged cached news request for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log cached news request: {str(e)}")
