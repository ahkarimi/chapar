import asyncio
import os

import pytest
from pydantic import ValidationError


for name in (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "DATABASE_URL",
    "REDIS_URL",
    "APP_NAMESPACE",
    "STOCK_API_KEY",
    "TOOBIT_API_KEY",
    "TOOBIT_SECRET_KEY",
    "CHARTIST_API_KEY",
    "CHARTIST_ADMIN_API_KEY",
    "SOURCEARENA_TOKEN",
    "DOCS_USERNAME",
    "DOCS_PASSWORD",
):
    os.environ.setdefault(name, "test")

os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@127.0.0.1:5432/test"

from app.schemas.analysis import AnalysisMethod, AnalysisRequest
from app.schemas.chart import ChartRequest
from app.services.analysis_manager import AnalysisManager


def test_every_public_analysis_method_builds_charts():
    manager = object.__new__(AnalysisManager)
    chart = ChartRequest(symbol="BTCUSDT")

    for method in AnalysisMethod:
        configs = asyncio.run(manager.get_chart_configs(method.value, chart))
        assert configs
        assert all(config.symbol == "BTCUSDT" for config in configs)


def test_analysis_requires_chart_schema():
    with pytest.raises(ValidationError):
        AnalysisRequest(symbol="BTCUSDT", analyze_method=AnalysisMethod.TECHNICAL)


def test_analysis_validation_allows_normal_failed_to_phrase():
    manager = object.__new__(AnalysisManager)
    answer = (
        "# BTCUSDT analysis\n\n"
        "Price failed to break resistance, while momentum remains neutral. "
        "Support is holding and volume should be watched before drawing a conclusion. "
    ) * 3

    assert manager._validate_llm_response({"answer": answer}) is True


def test_analysis_validation_rejects_explicit_failure_response():
    manager = object.__new__(AnalysisManager)
    answer = "Failed to generate the requested market analysis. " * 10

    assert manager._validate_llm_response({"answer": answer}) is False
