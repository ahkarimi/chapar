"""Market-data API operations used by the Telegram bot."""


class MarketRequestsMixin:
    """Requests for prices and chart images."""

    async def get_currency(self, user_id, symbol=""):
        """Get currency prices and data.

        Args:
            user_id (int): Telegram user ID
            symbol (str, optional): Symbol to filter by. Default is empty string for all currencies.

        Returns:
            dict: Currency data or error details
        """
        result, status_code = await self._request(
            method='POST',
            path='/api/v1/currency',
            data={
                'symbol': symbol
            },
            headers={'TelegramUID': str(user_id)}
        )

        # Handle connection errors
        if result is None:
            return {"error": True, "status": status_code, "message": "خطا در اتصال به سرور. لطفا مجددا تلاش کنید."}

        # Handle HTTP error codes
        if status_code != 200:
            error_message = "خطا در دریافت قیمت‌ها"
            if status_code == 401 or status_code == 403:
                error_message = "دسترسی به سرور محدود شده است. لطفا با پشتیبانی تماس بگیرید."
            elif status_code == 429:
                error_message = "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید."
            elif status_code >= 500:
                error_message = "خطای داخلی سرور. لطفا بعدا مجددا تلاش کنید."

            return {"error": True, "status": status_code, "message": error_message}

        # Since JSON is already parsed by _request, we can return directly
        return result if isinstance(result, dict) else {"error": True, "status": status_code, "message": "پاسخ نامعتبر از سرور. لطفا بعدا مجددا تلاش کنید."}

    async def chart(self, period, show_rsi, show_volume, sma_periods, symbol):
        """Get chart data for a specific symbol.

        Args:
            period (str): Time period for the chart
            show_rsi (bool): Whether to show RSI indicator
            show_volume (bool): Whether to show volume
            sma_periods (list): List of SMA periods to display
            symbol (str): Stock symbol

        Returns:
            str: Chart data as PNG image bytes or None on error
        """
        result, _ = await self._request(
            method='POST',
            path='/api/v1/stocks/chart/',
            data={
                'period': period,
                'show_rsi': show_rsi,
                'show_volume': show_volume,
                'sma_periods': sma_periods,
                'symbol': symbol
            },
            accept='image/png'
        )
        return result
