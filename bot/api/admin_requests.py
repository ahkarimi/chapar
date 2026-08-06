"""Admin-facing API operations used by the Telegram bot."""

import logging

from constants import PLAN_PACKAGES_DAYS


logger = logging.getLogger(__name__)


class AdminRequestsMixin:
    """Requests for plan management and administrative reports."""

    async def add_plan_time(self, user_id, package_days):
        """Add time to a user's plan.

        Args:
            user_id (int): The ID of the user to add plan time to
            package_days (int): The configured number of days to add

        Returns:
            dict: Response with confirmation or error details
        """
        # Ensure both values are integers
        try:
            user_id = int(user_id)
            package_days = int(package_days)

            if package_days not in PLAN_PACKAGES_DAYS:
                return {
                    "error": True,
                    "status": 400,
                    "message": f"بسته زمانی نامعتبر. بسته‌های مجاز: {PLAN_PACKAGES_DAYS}",
                }

        except ValueError:
            return {"error": True, "status": 400, "message": "مقادیر ورودی باید عدد باشند."}

        # Log the request for debugging
        logger.info(f"Sending plan add request: user_id={user_id}, package_days={package_days}")

        request_data = {
            "user_id": user_id,
            "package_days": package_days
        }

        result, status_code = await self._request(
            method='POST',
            path='/api/v1/admin/plan/add',
            data=request_data,
            headers={'access_token': self.admin_access_token}
        )

        logger.info(f"Plan add response status: {status_code}")
        if result:
            logger.info(f"Plan add response: {result}")

        if result is None:
            return {"error": True, "status": status_code, "message": "خطا در اتصال به سرور. لطفا مجددا تلاش کنید."}

        # Handle HTTP error codes
        if status_code != 200:
            error_message = "خطا در افزودن زمان به طرح کاربر"
            if status_code == 404:
                if isinstance(result, dict) and "detail" in result:
                    error_message = f"کاربر یافت نشد: {result['detail']}"
                else:
                    error_message = "کاربر مورد نظر یافت نشد."
            elif status_code == 400:
                if isinstance(result, dict) and "detail" in result:
                    error_message = result.get("detail", "درخواست نامعتبر")
                else:
                    error_message = "درخواست نامعتبر"
            elif status_code == 401 or status_code == 403:
                error_message = "دسترسی به سرور محدود شده است. لطفا با پشتیبانی تماس بگیرید."
            elif status_code == 429:
                error_message = "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید."
            elif status_code >= 500:
                error_message = "خطای داخلی سرور. لطفا بعدا مجددا تلاش کنید."

            return {"error": True, "status": status_code, "message": error_message}

        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "پاسخ نامعتبر از سرور. لطفا بعدا مجددا تلاش کنید."}

    async def get_admin_reports(self):
        """Get admin reports including monthly analysis data, credit usage, and credit increases.

        Returns:
            dict: Admin reports data or error details
        """
        result, status_code = await self._request(
            method='GET',
            path='/api/v1/admin/reports',
            headers={'access_token': self.admin_access_token},
        )

        # Handle connection errors
        if result is None:
            return {"error": True, "status": status_code, "message": "خطا در اتصال به سرور. لطفا مجددا تلاش کنید."}

        # Handle HTTP error codes
        if status_code != 200:
            error_message = "خطا در دریافت گزارشات"
            if status_code == 401 or status_code == 403:
                error_message = "دسترسی به سرور محدود شده است. لطفا با پشتیبانی تماس بگیرید."
            elif status_code == 429:
                error_message = "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید."
            elif status_code >= 500:
                error_message = "خطای داخلی سرور. لطفا بعدا مجددا تلاش کنید."

            return {"error": True, "status": status_code, "message": error_message}

        # Return the result directly as it's already been parsed by _request
        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "پاسخ نامعتبر از سرور. لطفا بعدا مجددا تلاش کنید."}
