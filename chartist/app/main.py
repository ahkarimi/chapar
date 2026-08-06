import sys
import logging
import secrets
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import users, referrals, analysis, admin, news, currency
from app.utils.db_init import init_db
from app.config import settings
from app.core.security import verify_docs_credentials

# Import security utilities
from fastapi.security import APIKeyHeader, APIKeyQuery
from fastapi.openapi.docs import get_swagger_ui_html


# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    handlers=[
        RotatingFileHandler("app.log", maxBytes=10485760, backupCount=5),  # 10MB
        logging.StreamHandler(sys.stdout),
    ],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================
# 1. API Token Security Setup
# ============================

API_KEY = settings.CHARTIST_API_KEY
ADMIN_API_KEY = settings.CHARTIST_ADMIN_API_KEY
API_KEY_NAME = "access_token"

# Create a dependency that reads the API key from the header
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def verify_api_token(api_key: str = Depends(api_key_header)):
    if not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate API token",
        )
    # If needed, you can return the token or user info here
    return api_key


async def verify_admin_api_token(api_key: str = Depends(api_key_header)):
    if not secrets.compare_digest(api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate admin API token",
        )
    return api_key


# ====================================
# 3. Application Lifespan and Initialization
# ====================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting database initialization")
    await init_db()
    logger.info("Database initialization completed")
    try:
        yield  # Application runs within this context
    finally:
        logger.info("Database connection closed (if applicable)")


# Disable the default docs and redoc endpoints so we can secure them.
app = FastAPI(
    title="Chapar API",
    description=(
        "Self-hosted market charts, LLM-assisted analysis, and grounded news "
        "for the Chapar Telegram application."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


# ====================================
# 4. Middlewares and Routers
# ====================================

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add API token dependency to your routers (all endpoints under these routers require a valid API token)
app.include_router(
    analysis.router,
    prefix="/api/v1/stocks",
    tags=["stocks"],
    dependencies=[Depends(verify_api_token)],
)
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(verify_api_token)],
)
app.include_router(
    referrals.router,
    prefix="/api/v1/referrals",
    tags=["referrals"],
    dependencies=[Depends(verify_api_token)],
)
app.include_router(
    news.router,
    prefix="/api/v1/news",
    tags=["news"],
    dependencies=[Depends(verify_api_token)],
)
app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_token)])
app.include_router(
    currency.router,
    prefix="/api/v1/currency",
    tags=["currency"],
    dependencies=[Depends(verify_api_token)],
)


# ====================================
# 5. Custom Docs Route Secured with Basic Auth
# ====================================


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(username: str = Depends(verify_docs_credentials)):
    """
    Serve Swagger UI behind the configured HTTP Basic credentials.
    """
    return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title + " - Docs")


@app.get("/openapi.json", include_in_schema=False)
async def protected_openapi_schema(
    username: str = Depends(verify_docs_credentials),
):
    """Serve the API schema behind the same credentials as Swagger UI."""
    return JSONResponse(app.openapi())


# ====================================
# 6. Main Entrypoint
# ====================================
