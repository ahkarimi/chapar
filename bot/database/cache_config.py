import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
APP_NAMESPACE = os.getenv("APP_NAMESPACE", "chapar_bot")

# Redis connection pool configuration for high performance
REDIS_POOL_CONFIG = {
    "max_connections": 50,  # High connection pool for 100k users
    "retry_on_timeout": True,
    "retry_on_error": [ConnectionError, TimeoutError],
    "health_check_interval": 30,
    "socket_connect_timeout": 2,
    "socket_timeout": 2,
    "decode_responses": True
}

# Trending coins cache TTL (default 4 hours)
TRENDING_CACHE_TTL = int(os.getenv("TRENDING_CACHE_TTL", "46100"))
