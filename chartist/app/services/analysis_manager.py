from typing import List, Dict, Any, Optional
from app.services.chart_service import ChartService
from app.services.llm_service import LLMService
from app.schemas.analysis import AnalysisRequest
from app.schemas.chart import ChartRequest, ChartInterval, ChartPeriod
from app.core.cache import CacheManager
from app.core.json_loader import load_json_file
from app.config import settings
import asyncio
import base64
import json
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.ERROR)  # Add this near the top of your main app entry point

class AnalysisManager:
    def __init__(
        self,
        chart_service: ChartService,
        llm_service: LLMService,
        cache_manager: CacheManager,
    ):
        self.chart_service = chart_service
        self.llm_service = llm_service
        self.cache_manager = cache_manager
        # Load settings from data.json instead of YAML
        try:
            self.data = load_json_file("data.json")
        except Exception as e:
            print(f"Warning: Failed to load data from JSON file: {e}")
            self.data = {}

    async def get_chart_configs(
        self, method: str, base_request: Optional[ChartRequest] = None
    ) -> List[ChartRequest]:
        """
        Generate chart configurations based on the analysis method.
        - For 'smart_money', generate two charts with different intervals.
        - For 'supply_and_demand', generate one chart with custom intervals.
        """
        if method == "crypto_technical_dh":
            return [
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_YEAR,
                    interval=ChartInterval.ONE_DAY,
                    show_mfi=True,
                    show_volume=True,
                    show_adx=True,
                    show_bbands=False,
                    ema_periods=[100, 200],
                ),
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_MONTH,
                    interval=ChartInterval.ONE_HOUR,
                    show_rsi=False,
                    show_volume=True,
                    show_adx=True,
                    show_bbands=True,
                ),
            ]
        elif method == "crypto_technical_h":
            return [
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_MONTH,
                    interval=ChartInterval.ONE_HOUR,
                    show_rsi=False,
                    show_volume=True,
                    show_adx=True,
                    show_bbands=True,
                ),
            ]
        elif method == "technical":
            return [
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_YEAR,
                    interval=ChartInterval.ONE_DAY,
                    show_rsi=True,
                    show_macd=True,
                    ema_periods=[50, 200],
                ),
            ]
        elif method == "technical_wd":
            return [
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.FIVE_YEARS,
                    interval=ChartInterval.ONE_WEEK,
                    ema_periods=[50, 200],
                ),
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_YEAR,
                    interval=ChartInterval.ONE_DAY,
                    show_rsi=True,
                    show_macd=True,
                    ema_periods=[50, 200],
                ),
            ]
        elif method == "technical_dh":
            return [
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_YEAR,
                    interval=ChartInterval.ONE_DAY,
                    show_rsi=True,
                    show_macd=True,
                    ema_periods=[50, 100],
                ),
                ChartRequest(
                    symbol=base_request.symbol,
                    period=ChartPeriod.ONE_MONTH,
                    interval=ChartInterval.ONE_HOUR,
                    show_rsi=True,
                    show_macd=True,
                    ema_periods=[50, 100],
                ),
            ]
        else:
            raise ValueError(f"Unsupported analysis method: {method}")

    def analyze_sync(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Synchronous version of analyze method for Celery tasks.
        This runs the same analysis as the async version but in a synchronous context.
        """
        # Create an event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the async analyze method in the synchronous context
            return loop.run_until_complete(self.analyze(request))
        finally:
            # Clean up the event loop
            loop.close()

    def _validate_llm_response(self, llm_response: Any) -> bool:
        """
        Validate the LLM response to ensure it's not broken or incomplete.

        Returns:
            bool: True if valid, False otherwise
        """
        logger.info(f"Validating LLM response: {type(llm_response)}")

        # Check if response is a dictionary
        if not isinstance(llm_response, dict):
            logger.warning("LLM response validation failed: not a dictionary")
            return False

        # Check for required fields
        if "answer" not in llm_response:
            logger.warning("LLM response validation failed: missing 'answer' field")
            return False

        # Check if answer is empty or None
        answer = llm_response.get("answer")
        if not answer or not isinstance(answer, str):
            logger.warning("LLM response validation failed: answer is empty or not a string")
            return False

        # Check if answer is too short (less than 300 characters might indicate broken response)
        # Adjust this threshold based on your specific use case
        min_answer_length = 300
        if len(answer) < min_answer_length:
            logger.warning(f"LLM response validation failed: answer too short ({len(answer)} chars)")
            return False

        # Reject explicit refusal/error responses, but do not scan the entire
        # analysis for ordinary phrases such as "failed to". Those phrases can
        # legitimately describe indicators, breakouts, or support tests.
        error_prefixes = [
            "unable to analyze",
            "not enough data",
            "error processing",
            "failed to generate",
            "sorry, i cannot",
        ]

        normalized_answer = answer.strip().lstrip("#*_`>- ").lower()
        for prefix in error_prefixes:
            if normalized_answer.startswith(prefix):
                logger.warning(f"LLM response validation failed: starts with error response '{prefix}'")
                return False

        logger.debug(f"LLM response structure: {json.dumps(llm_response, default=str)[:500]}...")

        return True

    async def analyze(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Perform analysis:
        1. Generate charts based on the method.
        2. Merge charts if needed.
        3. Send the chart and inputs to LLM for analysis.
        4. Stream the LLM responses alongside the final chart.
        """
        # Step 1: Create a cache key based on the request
        cache_key = f"analysis:{request.response_language}:{request.analyze_method.value}:{request.chart_schema.symbol}:{request.chart_schema.period}:{request.chart_schema.interval}"

        # Try to fetch result from the cache
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            parsed_result = json.loads(cached_result)
            # Validate cached results too
            if not self._validate_llm_response(parsed_result.get("llm_response", {})):
                logger.warning(f"Invalid cached response found for {cache_key}, ignoring cache")
                # Continue with analysis instead of returning cached result
            else:
                return parsed_result

        # Step 2: Get chart configurations
        chart_configs = await self.get_chart_configs(
            request.analyze_method, request.chart_schema
        )

        # Step 3: Generate charts
        chart_generation_tasks = [
            self.chart_service.generate_chart(config) for config in chart_configs
        ]
        charts = await asyncio.gather(*chart_generation_tasks)

        # Extract images, filenames, and MIME types from the charts
        image_bytes_list = [chart[0] for chart in charts]
        file_names_list = [chart[1] for chart in charts]
        mime_types_list = [chart[2] for chart in charts]

        # Step 4: Analyze the chart with LLM
        llm_response = await self.llm_service.analyze_image(
            images=image_bytes_list,
            method=request.analyze_method.value,
            symbol=request.chart_schema.symbol,
            filenames=file_names_list,
            mime_types=mime_types_list,
            query=".",
            response_language=request.response_language,
        )

        # Prepare the response
        response = {
            "images": [
                base64.b64encode(image).decode("utf-8") for image in image_bytes_list
            ],
            "llm_response": llm_response,
        }

        # Step 5: Validate the LLM response before caching
        if not self._validate_llm_response(llm_response):
            logger.warning(f"Invalid LLM response for {request.chart_schema.symbol} using {request.analyze_method.value}")
            raise ValueError(f"Failed to generate valid analysis for {request.chart_schema.symbol}")

        # Step 6: Determine the cache expiration time based on the symbol
        symbol = request.chart_schema.symbol

        # Get expiration times from JSON data
        redis_expiration = self.data.get("redis_expiration", {})
        fast_analysis_expire = redis_expiration.get("fast_analysis", 14400)  # Default 4 hours
        normal_analysis_expire = redis_expiration.get("normal_analysis", 86400)  # Default 1 day

        # Check if symbol is in fast_cache_symbols list
        fast_cache_symbols = self.data.get("fast_cache_symbols", [])
        if symbol in fast_cache_symbols:
            expire_time = fast_analysis_expire
        else:
            expire_time = normal_analysis_expire

        # Step 7: Store the result in cache with the appropriate expiration time
        await self.cache_manager.set(
            cache_key, json.dumps(response), expire=expire_time
        )
        logger.info(f"Cached analysis result for {cache_key} (expires in {expire_time}s)")

        # Step 8: Return the response (cached or not)
        return response
