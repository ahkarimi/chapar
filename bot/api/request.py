import json
import base64
import aiohttp
import asyncio
import time
import logging

from .admin_requests import AdminRequestsMixin
from .analysis_requests import AnalysisRequestsMixin
from .market_requests import MarketRequestsMixin
from .news_requests import NewsRequestsMixin
from .user_requests import UserRequestsMixin

# Setup logging
logger = logging.getLogger(__name__)

class APIRequest(
    AdminRequestsMixin,
    AnalysisRequestsMixin,
    MarketRequestsMixin,
    NewsRequestsMixin,
    UserRequestsMixin,
):
    """Class to handle API requests to the external stock analysis service."""

    def __init__(
        self,
        endpoint,
        access_token,
        timeout=80,
        max_retries=3,
        backoff_factor=1.5,
        admin_access_token=None,
    ):
        """Initialize with API endpoint and access token.

        Args:
            endpoint (str): The API endpoint URL
            access_token (str): The access token for API authentication
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retry attempts
            backoff_factor (float): Backoff factor for exponential retry delays
        """
        self.endpoint = endpoint
        self.access_token = access_token
        self.admin_access_token = admin_access_token or access_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = None

    async def create_session(self):
        """Create aiohttp client session if it doesn't exist."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close_session(self):
        """Close the aiohttp client session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close_session()



















    async def _request(self, method, path, data=None, headers=None, query=None, accept='application/json', parse_json=True):
        """Make an HTTP request to the API with retry mechanism.

        Args:
            method (str): HTTP method (GET, POST, PUT)
            path (str): API path
            data (dict, optional): Request data
            headers (dict, optional): Request headers
            query (dict, optional): Query parameters
            accept (str, optional): Accept header value
            parse_json (bool, optional): Whether to parse JSON response

        Returns:
            tuple: (Response body or parsed JSON dict or None on error, status code or None)
        """
        # Fix URL construction to avoid double slashes
        if self.endpoint.endswith('/') and path.startswith('/'):
            url = self.endpoint[:-1] + path
        elif not self.endpoint.endswith('/') and not path.startswith('/'):
            url = self.endpoint + '/' + path
        else:
            url = self.endpoint + path

        # Add query parameters if present
        if query:
            query_string = "&".join([f"{k}={v}" for k, v in query.items() if v is not None])
            if query_string:
                url = f"{url}?{query_string}"

        # Prepare headers
        request_headers = {
            'accept': accept,
            'access_token': self.access_token
        }

        if method in ('POST', 'PUT'):
            request_headers['content-type'] = 'application/json'

        # Add custom headers
        if headers:
            request_headers.update(headers)

        logger.info(f"Request URL: {url}")
        if isinstance(data, dict):
            logger.debug("Request payload keys: %s", sorted(data))

        # Initialize variables
        retry_count = 0
        last_exception = None

        # Ensure we have a session
        await self.create_session()

        while retry_count <= self.max_retries:
            # Calculate backoff delay based on retry count
            backoff_delay = self.backoff_factor * (2 ** retry_count) if retry_count > 0 else 0

            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count}/{self.max_retries} for {method} {url} after {backoff_delay:.2f}s delay")
                await asyncio.sleep(backoff_delay)

            try:
                # Set timeout - use a lower timeout for first attempt, then increase for retries
                timeout_value = min(self.timeout * (1 + 0.5 * retry_count), 120)  # Cap at 2 minutes max
                timeout = aiohttp.ClientTimeout(total=timeout_value,
                                              connect=min(10, timeout_value/3),
                                              sock_connect=min(10, timeout_value/3),
                                              sock_read=timeout_value)

                start_time = time.time()
                logger.debug(f"Making {method} request to {url} with timeout {timeout_value}s")

                # Make request with appropriate method
                if method == 'GET':
                    async with self.session.get(url, headers=request_headers, timeout=timeout) as response:
                        if accept == 'image/png':
                            image_data = await response.read()
                            elapsed = time.time() - start_time
                            logger.debug(f"Request completed in {elapsed:.2f}s with status {response.status}")
                            return base64.b64encode(image_data).decode('utf-8'), response.status

                        response_text = await response.text()
                        elapsed = time.time() - start_time
                        logger.debug(f"Request completed in {elapsed:.2f}s with status {response.status}")

                        # Parse JSON if requested and content type is appropriate
                        if parse_json and accept == 'application/json' and response_text:
                            try:
                                return json.loads(response_text), response.status
                            except json.JSONDecodeError as e:
                                logger.error(f"JSON decode error: {str(e)}")
                                return response_text, response.status

                        return response_text, response.status

                elif method == 'POST':
                    async with self.session.post(url, json=data, headers=request_headers, timeout=timeout) as response:
                        if accept == 'image/png':
                            image_data = await response.read()
                            elapsed = time.time() - start_time
                            logger.debug(f"Request completed in {elapsed:.2f}s with status {response.status}")
                            return base64.b64encode(image_data).decode('utf-8'), response.status

                        response_text = await response.text()
                        elapsed = time.time() - start_time
                        logger.debug(f"Request completed in {elapsed:.2f}s with status {response.status}")

                        # Parse JSON if requested and content type is appropriate
                        if parse_json and accept == 'application/json' and response_text:
                            try:
                                return json.loads(response_text), response.status
                            except json.JSONDecodeError as e:
                                logger.error(f"JSON decode error: {str(e)}")
                                return response_text, response.status

                        return response_text, response.status

                elif method == 'PUT':
                    async with self.session.put(url, json=data, headers=request_headers, timeout=timeout) as response:
                        response_text = await response.text()
                        elapsed = time.time() - start_time
                        logger.debug(f"Request completed in {elapsed:.2f}s with status {response.status}")

                        # Parse JSON if requested and content type is appropriate
                        if parse_json and accept == 'application/json' and response_text:
                            try:
                                return json.loads(response_text), response.status
                            except json.JSONDecodeError as e:
                                logger.error(f"JSON decode error: {str(e)}")
                                return response_text, response.status

                        return response_text, response.status

            except (aiohttp.ClientResponseError, aiohttp.ClientPayloadError) as e:
                last_exception = e
                logger.warning(f"API response error ({retry_count}/{self.max_retries}): {str(e)}")
                # Only retry on 5xx errors or specific conditions
                if hasattr(e, 'status') and (e.status < 500 and e.status != 429):
                    return None, e.status
            except aiohttp.ClientConnectorError as e:
                last_exception = e
                logger.warning(f"API connection error ({retry_count}/{self.max_retries}): {str(e)}")
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"API request timeout ({retry_count}/{self.max_retries}) after {self.timeout}s")
            except Exception as e:
                last_exception = e
                logger.error(f"API request error ({retry_count}/{self.max_retries}): {str(e)}", exc_info=True)

            retry_count += 1

        # If we've exhausted all retries, return the appropriate error
        if isinstance(last_exception, asyncio.TimeoutError):
            logger.error(f"All retry attempts failed with timeout for {method} {url}")
            return None, 504  # Gateway Timeout
        elif isinstance(last_exception, aiohttp.ClientConnectorError):
            logger.error(f"All retry attempts failed with connection error for {method} {url}")
            return None, 503  # Service Unavailable
        else:
            logger.error(f"All retry attempts failed for {method} {url}: {str(last_exception)}")
            return None, 500  # Internal Server Error
