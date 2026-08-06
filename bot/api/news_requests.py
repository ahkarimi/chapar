"""News-analysis API operations used by the Telegram bot."""

import asyncio
import json
import logging
import time


logger = logging.getLogger(__name__)


class NewsRequestsMixin:
    """Requests that start, poll, and retrieve news analyses."""

    async def news(self, user_id, symbol, method='summary_sites'):
        """
        Legacy news method that maintains compatibility with existing code.
        This now delegates to start_news and then polls for results.

        IMPORTANT: This is a BLOCKING method that waits for the analysis to complete.
        For non-blocking operation, use start_news instead.

        Args:
            user_id (int): Telegram user ID
            symbol (str): Stock symbol
            method (str): Analysis method to use

        Returns:
            dict: News analysis results or error details
        """
        # Start the news analysis
        result = await self.start_news(user_id, symbol, method)

        # If it's not a task (either error or cached result), return immediately
        if not result.get("is_task", False):
            return result

        # Get the task ID for polling
        task_id = result.get("task_id")
        if not task_id:
            return {"error": True, "status": 500, "message": "خطا در دریافت شناسه تحلیل اخبار"}

        # Start polling for the result (THIS IS THE BLOCKING PART)
        logger.info(f"Legacy news method polling for results: {task_id}")

        # Poll for results
        max_attempts = 30  # Maximum number of polling attempts
        poll_interval = 3  # Initial polling interval in seconds

        for attempt in range(max_attempts):
            # Exponential backoff for longer-running tasks
            current_interval = min(poll_interval * (1.05 ** attempt), 10)

            # Wait before polling
            logger.info(f"⏳ Waiting {current_interval:.2f}s before polling attempt {attempt+1}/{max_attempts}")
            await asyncio.sleep(current_interval)

            # Check the task status
            status_result = await self.check_news_status(user_id, task_id)

            # If it's no longer a task (completed or failed), return the result
            if not status_result.get("is_task", False):
                return status_result

        # If we've exhausted all polling attempts
        logger.error(f"⏱️ POLLING TIMEOUT: {task_id}")
        return {"error": True, "status": 408, "message": "زمان انتظار برای تحلیل اخبار به پایان رسید. لطفا مجددا تلاش کنید."}

    async def start_news(self, user_id, symbol, method='summary_sites', language="fa"):
        """
        Start a news analysis task without waiting for completion.

        Args:
            user_id (int): Telegram user ID
            symbol (str): Stock symbol
            method (str): Analysis method to use

        Returns:
            dict: Initial response with task_id or error details
        """
        request_start = time.time()
        logger.info(f"==== BOT NEWS REQUEST (START) ====")
        logger.info(f"User: {user_id}, Symbol: {symbol}, Method: {method}")

        # Submit the news request
        logger.info(f"Sending news request to API...")
        request_data = {
            'symbol': symbol,
            'method': method,
            'response_language': 'English' if language == 'en' else 'Persian',
        }

        result, status_code = await self._request(
            method='POST',
            path='/api/v1/news/news',
            data=request_data,
            headers={'TelegramUID': str(user_id)}
        )

        request_duration = time.time() - request_start
        logger.info(f"Initial API response received in {request_duration:.2f}s with status {status_code}")

        # Handle connection errors
        if result is None:
            logger.error(f"Connection error: status={status_code}")
            return {"error": True, "status": status_code, "message": "خطا در اتصال به سرور. لطفا مجددا تلاش کنید."}

        # Handle HTTP error codes
        if status_code != 200:
            error_message = "خطا در دریافت تحلیل اخبار"
            if status_code == 404:
                # Try to extract error details from the parsed result
                if isinstance(result, dict) and "detail" in result:
                    error_message = f"نماد وارد شده معتبر نیست: {result['detail']}"
                else:
                    error_message = "نماد وارد شده معتبر نیست یا اخباری برای آن یافت نشد."
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

        # If the response has cached news results, return it directly
        if "news" in result and "cached" in result:
            total_time = time.time() - request_start
            logger.info(f"✅ CACHE HIT: Returning cached news result, total time: {total_time:.2f}s")
            return result

        # Check if this is a task response with task_id
        if "task_id" in result and result.get("status") == "processing":
            # Get the task ID
            task_id = result.get("task_id")
            logger.info(f"🔄 NEWS TASK QUEUED: task_id={task_id}")

            # Return the task ID for later polling
            return {
                "is_task": True,
                "task_id": task_id,
                "status": "processing",
                "symbol": symbol,
                "method": method
            }

        # If we don't have a task_id or results, something unexpected happened
        logger.error(f"❓ UNEXPECTED RESPONSE: {result}")
        return {"error": True, "status": 500, "message": "تحلیل اخبار ناقص است."}

    async def check_news_status(self, user_id, task_id):
        """
        Check the status of a news analysis task.

        Args:
            user_id (int): Telegram user ID
            task_id (str): Task ID to check

        Returns:
            dict: Status information or result if complete
        """
        check_start = time.time()
        logger.info(f"Checking status for news task {task_id}")

        # Check task status
        poll_result, poll_status = await self._request(
            method='GET',
            path=f'/api/v1/news/news/status/{task_id}',
            headers={'TelegramUID': str(user_id)}
        )

        poll_duration = time.time() - check_start
        logger.info(f"News status check response received in {poll_duration:.2f}s with status {poll_status}")

        if poll_result is None:
            logger.warning(f"Failed to poll news task status: {poll_status}")
            return {"error": True, "status": poll_status, "message": "خطا در دریافت وضعیت تحلیل اخبار"}

        # Result is already a dictionary from _request
        if isinstance(poll_result, dict):
            status_data = poll_result
            status = status_data.get("status")
            logger.info(f"News task status: {status}")

            # If the task is complete, return the result
            if status == "completed":
                total_time = time.time() - check_start
                logger.info(f"✅ NEWS TASK COMPLETED: {task_id}, time: {total_time:.2f}s")

                result_data = status_data.get("result", {})
                # Log result summary
                if isinstance(result_data, dict):
                    has_news = "news" in result_data
                    result_size = len(json.dumps(result_data)) / 1024  # KB
                    logger.info(f"News result summary: has_news={has_news}, size={result_size:.2f}KB")

                return result_data

            # If the task failed, return the error
            elif status == "failed":
                total_time = time.time() - check_start
                error_message = status_data.get("error", "تحلیل اخبار با خطا مواجه شد.")
                logger.error(f"❌ NEWS TASK FAILED: {task_id}, error: {error_message}, time: {total_time:.2f}s")
                return {"error": True, "status": 500, "message": error_message}

            # If task is still processing, return the status
            return {
                "is_task": True,
                "task_id": task_id,
                "status": status,
                "message": status_data.get("message", "تحلیل اخبار در حال انجام است...")
            }
        else:
            # Handle case where response is not a proper dictionary
            logger.error(f"Invalid response when checking news task status: {type(poll_result)}")
            return {"error": True, "status": poll_status, "message": "پاسخ نامعتبر از سرور"}
