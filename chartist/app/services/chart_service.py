from app.providers.market_data_provider import MarketDataProvider
from app.providers.factory import get_provider_for_symbol
from app.chart.chart_generator import ChartGenerator
from app.schemas.chart import ChartRequest
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ChartService:
    def __init__(self, data_provider: Optional[MarketDataProvider] = None):
        self._override_provider = data_provider is not None
        self.data_provider = data_provider
        if self.data_provider:
            self.chart_generator = ChartGenerator(data_provider=self.data_provider)

    def select_data_provider(self, symbol: str) -> None:
        if not self._override_provider or self.data_provider is None:
            self.data_provider = get_provider_for_symbol(symbol)
        self.chart_generator = ChartGenerator(data_provider=self.data_provider)

    async def generate_chart(self, request: ChartRequest) -> Tuple[bytes, str, str]:
        self.select_data_provider(request.symbol)
        return await self.chart_generator.generate_chart(request)
