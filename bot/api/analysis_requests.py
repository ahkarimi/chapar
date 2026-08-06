"""Market analysis API operations used by the Telegram bot."""

import asyncio
import json
import logging
import time


logger = logging.getLogger(__name__)


class AnalysisRequestsMixin:
    """Requests that start, poll, and retrieve market analyses."""

    async def start_analysis(self, user_id, analyze_method, period, show_volume, symbol, language="fa"):
        """
        Start an analysis task without waiting for completion.

        Args:
            user_id (int): Telegram user ID
            analyze_method (str): Analysis method to use
            period (str): Time period for analysis
            show_volume (bool): Whether to show volume
            symbol (str): Stock symbol

        Returns:
            dict: Initial response with task_id or error details
        """
        request_start = time.time()
        logger.info(f"==== BOT ANALYSIS REQUEST (START) ====")
        logger.info(f"User: {user_id}, Symbol: {symbol}, Method: {analyze_method}")

        chart_schema = {
            'period': period,
            'show_volume': show_volume,
            'symbol': symbol
        }

        # Submit the analysis request
        logger.info(f"Sending analysis request to API...")
        request_data = {
            'analyze_method': analyze_method,
            'chart_schema': chart_schema,
            'symbol': symbol,
            'response_language': 'English' if language == 'en' else 'Persian',
        }

        # JSON parsing is now handled by _request
        result, status_code = await self._request(
            method='POST',
            path='/api/v1/stocks/analyze/',
            data=request_data,
            headers={'TelegramUID': str(user_id)}
        )

        request_duration = time.time() - request_start
        logger.info(f"Initial API response received in {request_duration:.2f}s with status {status_code}")

        # Handle connection errors
        if result is None:
            logger.error(f"Connection error: status={status_code}")
            print(f"Connection error: status={status_code}")
            return {"error": True, "status": status_code, "message": "خطا در اتصال به سرور. لطفا مجددا تلاش کنید."}

        # Handle HTTP error codes
        if status_code != 200:
            error_message = "خطا در دریافت تحلیل"
            if status_code == 404:
                # Try to extract detail from error response
                if isinstance(result, dict) and "detail" in result:
                    error_message = f"نماد وارد شده معتبر نیست: {result['detail']}"
                else:
                    error_message = "نماد وارد شده معتبر نیست یا داده ای برای آن یافت نشد."
            elif status_code == 401 or status_code == 403:
                error_message = "دسترسی به سرور محدود شده است. لطفا با پشتیبانی تماس بگیرید."
            elif status_code == 429:
                error_message = "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید."
            elif status_code >= 500:
                error_message = "خطای داخلی سرور. لطفا بعدا مجددا تلاش کنید."

            logger.error(f"API Error: {error_message}, status={status_code}")
            return {"error": True, "status": status_code, "message": error_message}

        # Check response structure
        if not isinstance(result, dict):
            logger.error(f"Unexpected response type: {type(result)}")
            return {"error": True, "status": 500, "message": "پاسخ نامعتبر از سرور. لطفا بعدا مجددا تلاش کنید."}

        # If the response contains results directly (cached response), return it
        if "llm_response" in result and "images" in result:
            total_time = time.time() - request_start
            logger.info(f"✅ CACHE HIT: Returning cached result, total time: {total_time:.2f}s")
            return result

        # Check if this is a task response with task_id
        if "task_id" in result and result.get("status") == "processing":
            # Get the task ID
            task_id = result.get("task_id")
            logger.info(f"🔄 TASK QUEUED: task_id={task_id}")

            # Return the task ID for later polling
            return {
                "is_task": True,
                "task_id": task_id,
                "status": "processing",
                "symbol": symbol,
                "method": analyze_method
            }

        # If we don't have a task_id or results, something unexpected happened
        logger.error(f"❓ UNEXPECTED RESPONSE: {result}")
        return {"error": True, "status": 500, "message": "تحلیل ناقص است."}

    async def check_analysis_status(self, user_id, task_id):
        """
        Check the status of an analysis task.

        Args:
            user_id (int): Telegram user ID
            task_id (str): Task ID to check

        Returns:
            dict: Status information or result if complete
        """
        check_start = time.time()
        logger.info(f"Checking status for task {task_id}")

        # Check task status
        poll_result, poll_status = await self._request(
            method='GET',
            path=f'/api/v1/stocks/analyze/status/{task_id}',
            headers={'TelegramUID': str(user_id)}
        )

        poll_duration = time.time() - check_start
        logger.info(f"Status check response received in {poll_duration:.2f}s with status {poll_status}")

        if poll_result is None:
            logger.warning(f"Failed to poll task status: {poll_status}")
            return {"error": True, "status": poll_status, "message": "خطا در دریافت وضعیت تحلیل"}

        # Result is already a dictionary from _request
        if isinstance(poll_result, dict):
            status_data = poll_result
            status = status_data.get("status")
            logger.info(f"Task status: {status}")

            # If the task is complete, return the result
            if status == "completed":
                total_time = time.time() - check_start
                logger.info(f"✅ TASK COMPLETED: {task_id}, time: {total_time:.2f}s")

                result_data = status_data.get("result", {})
                # Log result summary
                if isinstance(result_data, dict):
                    has_llm = "llm_response" in result_data
                    has_images = "images" in result_data
                    result_size = len(json.dumps(result_data)) / 1024  # KB
                    logger.info(f"Result summary: has_llm={has_llm}, has_images={has_images}, size={result_size:.2f}KB")

                return result_data

            # If the task failed, return the error
            elif status == "failed":
                total_time = time.time() - check_start
                error_message = status_data.get("error", "تحلیل با خطا مواجه شد.")
                logger.error(f"❌ TASK FAILED: {task_id}, error: {error_message}, time: {total_time:.2f}s")
                return {"error": True, "status": 500, "message": error_message}

            # If task is still processing, return the status
            return {
                "is_task": True,
                "task_id": task_id,
                "status": status,
                "message": status_data.get("message", "تحلیل در حال انجام است...")
            }
        else:
            # Handle case where response is not a proper dictionary
            logger.error(f"Invalid response when checking task status: {type(poll_result)}")
            return {"error": True, "status": poll_status, "message": "پاسخ نامعتبر از سرور"}

    async def analyze(self, user_id, analyze_method, period, show_volume, symbol):
        """
        Legacy analyze method that maintains compatibility with existing code.
        This now delegates to start_analysis and then polls for results.

        IMPORTANT: This is a BLOCKING method that waits for the analysis to complete.
        For non-blocking operation, use start_analysis instead.

        Args:
            user_id (int): Telegram user ID
            analyze_method (str): Analysis method to use
            period (str): Time period for analysis
            show_volume (bool): Whether to show volume
            symbol (str): Stock symbol

        Returns:
            dict: Analysis results or error details
        """
        # Start the analysis
        result = await self.start_analysis(user_id, analyze_method, period, show_volume, symbol)

        # If it's not a task (either error or cached result), return immediately
        if not result.get("is_task", False):
            return result

        # Get the task ID for polling
        task_id = result.get("task_id")
        if not task_id:
            return {"error": True, "status": 500, "message": "خطا در دریافت شناسه تحلیل"}

        # Start polling for the result (THIS IS THE BLOCKING PART)
        logger.info(f"Legacy analyze method polling for results: {task_id}")

        # Poll for results
        max_attempts = 60  # Maximum number of polling attempts
        poll_interval = 5  # Initial polling interval in seconds

        for attempt in range(max_attempts):
            # Exponential backoff for longer-running tasks
            current_interval = min(poll_interval * (1.1 ** attempt), 15)

            # Wait before polling
            logger.info(f"⏳ Waiting {current_interval:.2f}s before polling attempt {attempt+1}/{max_attempts}")
            await asyncio.sleep(current_interval)

            # Check the task status
            status_result = await self.check_analysis_status(user_id, task_id)

            # If it's no longer a task (completed or failed), return the result
            if not status_result.get("is_task", False):
                return status_result

        # If we've exhausted all polling attempts
        logger.error(f"⏱️ POLLING TIMEOUT: {task_id}")
        return {"error": True, "status": 408, "message": "زمان انتظار برای تحلیل به پایان رسید. لطفا مجددا تلاش کنید."}
