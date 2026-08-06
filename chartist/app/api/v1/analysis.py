from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import Response
from app.schemas.chart import ChartRequest
from app.schemas.analysis import AnalysisRequest
from app.services.chart_service import ChartService
from app.services.llm_service import LLMService
from app.services.analysis_manager import AnalysisManager
from app.core.cache import CacheManager
import logging
from app.tasks.analysis_tasks import analyze_stock_task
from celery.result import AsyncResult
import json
import time

from app.core.dependency import get_user_by_telegram
from sqlalchemy.ext.asyncio import AsyncSession
# Use the renamed AsyncSessionLocal for the async dependency
from app.models.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.history import AnalysisHistory
from app.utils.plan_utils import has_active_plan

# Get logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection for ChartGenerator
def get_chart_generator() -> ChartService:
    """Dependency to provide an instance of ChartGenerator."""
    return ChartService()


@router.post(
    "/chart/",
    response_class=Response,
    responses={
        200: {
            "content": {
                "image/png": {},
                "image/jpeg": {},
                "image/svg+xml": {},
                "application/pdf": {},
            },
            "description": "Returns the generated stock chart in the requested format",
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {"error": "Invalid symbol or parameters"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {"example": {"error": "Failed to generate chart"}}
            },
        },
    },
)
async def create_chart(
    request: ChartRequest,
    chart_generator: ChartService = Depends(
        get_chart_generator
    ),  # Inject the ChartGenerator dependency
):
    """
    Generate a stock chart based on the provided parameters.

    The chart can include:
    - Price candlesticks
    - Volume
    - Technical indicators (SMA, EMA, RSI, MACD, ROC)
    - Custom watermark

    Returns the chart in the requested format (PNG, JPEG, SVG, or PDF)
    """
    try:
        logger.info(f"Generating chart for symbol: {request.symbol}")
        chart_bytes, filename, content_type = await chart_generator.generate_chart(
            request
        )

        content_length = str(len(chart_bytes))
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": content_length,
            "X-File-Size": content_length,
            "X-Chart-Format": request.file_format.value,
        }

        logger.info(f"Successfully generated chart: {filename}")
        return Response(content=chart_bytes, media_type=content_type, headers=headers)

    except Exception as e:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if isinstance(e, ValueError)
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        logger.error(f"Error while generating chart: {str(e)}")
        raise HTTPException(status_code=status_code, detail=str(e))


# Dependency injection for services
def get_analysis_manager() -> AnalysisManager:
    chart_service = ChartService()
    llm_service = LLMService()
    cache_manager = CacheManager()
    return AnalysisManager(chart_service, llm_service, cache_manager)


@router.post("/analyze/")
async def analyze(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    manager: AnalysisManager = Depends(get_analysis_manager),
    user=Depends(get_user_by_telegram),  # Identify the Telegram user from header.
    db: AsyncSession = Depends(get_db),
):
    # Log the incoming request details
    logger.info(f"=== ANALYSIS REQUEST RECEIVED ===")
    logger.info(f"User: {user.id}")
    logger.info(f"Symbol: {request.chart_schema.symbol}")
    logger.info(f"Method: {request.analyze_method.value}")
    logger.info(f"Period: {request.chart_schema.period}")
    logger.info(f"Plan status: {user.plan_status}, End date: {user.plan_end_date}")

    # Check for existing cached result first
    cache_key = f"analysis:{request.response_language}:{request.analyze_method.value}:{request.chart_schema.symbol}:{request.chart_schema.period}:{request.chart_schema.interval}"
    cached_result = await manager.cache_manager.get(cache_key)

    if cached_result:
        logger.info(f"✅ CACHE HIT: Returning cached result for {cache_key}")
        # Log analysis history for cached analysis result
        background_tasks.add_task(_log_analysis_history, user.id, request.chart_schema.symbol, request.analyze_method.value)
        return json.loads(cached_result)

    # Log cache miss
    logger.info(f"❌ CACHE MISS: No cached result found for {cache_key}")

    # Check if user has an active plan
    if not has_active_plan(user.plan_end_date):
        logger.warning(f"⚠️ PLAN EXPIRED: User {user.id} has no active plan")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your plan has expired. Please renew your subscription to continue using analysis.",
        )

    # Convert request to dict for serialization
    request_dict = request.model_dump()

    try:
        # Launch Celery task
        request_time = time.time()

        # Task name is 'analyze_stock' not 'app.tasks.analysis_tasks.analyze_stock'
        task = analyze_stock_task.delay(request_dict, user.id)

        logger.info(f"🚀 TASK LAUNCHED: {task.id} for symbol {request.chart_schema.symbol}")

        # Return task ID and status immediately
        return {
            "task_id": task.id,
            "status": "processing",
            "message": "Analysis request has been queued. Check the status endpoint for results.",
            "request_time": request_time
        }
    except Exception as e:
        logger.error(f"❌ ERROR LAUNCHING TASK: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue analysis task: {str(e)}"
        )

@router.get("/analyze/status/{task_id}")
async def check_analysis_status(task_id: str):
    """
    Check the status of an analysis task and return results if complete.
    """
    logger.info(f"👀 STATUS CHECK: Task {task_id}")

    task_result = AsyncResult(task_id)

    if task_result.ready():
        if task_result.successful():
            logger.info(f"✅ TASK COMPLETE: {task_id}")
            return {
                "status": "completed",
                "result": task_result.result,
                "completion_time": time.time()
            }
        else:
            error_message = str(task_result.result) if task_result.result else "Unknown error"

            # Check if it's a validation error
            is_validation_error = "Invalid analysis result" in error_message or "Failed to generate valid analysis" in error_message

            logger.error(f"❌ TASK FAILED: {task_id}, Error: {error_message}")

            # Return a more specific error code and message for validation failures
            if is_validation_error:
                return {
                    "status": "failed",
                    "error": "We couldn't generate a valid analysis. Please try again or try a different symbol/method.",
                    "failure_time": time.time(),
                    "details": error_message if not is_validation_error else None,
                    "error_type": "validation_error" if is_validation_error else "system_error"
                }
            else:
                return {
                    "status": "failed",
                    "error": error_message,
                    "failure_time": time.time()
                }
    else:
        logger.info(f"⏳ TASK IN PROGRESS: {task_id}")
        return {
            "status": "processing",
            "message": "Analysis is still in progress",
            "check_time": time.time()
        }

async def _log_analysis_history(user_id: int, symbol: str, method: str):
    """Log analysis history for cached analysis result (no credit deduction)"""
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                user = await db.get(User, user_id)
                if user:
                    user.total_requests += 1

                log_entry = AnalysisHistory(
                    user_id=user_id,
                    symbol=symbol,
                    method=method,
                    status="success"
                )
                db.add(log_entry)
    except Exception as e:
        logger.error(f"Error logging cached analysis history for user {user_id}: {e}")
        logger.exception(e)
