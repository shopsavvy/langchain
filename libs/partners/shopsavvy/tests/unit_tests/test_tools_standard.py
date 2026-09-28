"""LangChain standard unit tests for the ShopSavvy tools."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langchain_tests.unit_tests import ToolsUnitTests

from langchain_shopsavvy import (
    ShopSavvyPriceComparison,
    ShopSavvyPriceHistory,
    ShopSavvyProductSearch,
)

API_KEY = "ss_test_standard_unit_tests"


class TestShopSavvyProductSearchUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return ShopSavvyProductSearch

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {"shopsavvy_api_key": API_KEY}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"query": "sony wh-1000xm5", "max_results": 3}

    @property
    def init_from_env_params(
        self,
    ) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
        return (
            {"SHOPSAVVY_API_KEY": API_KEY},
            {},
            {"shopsavvy_api_key": API_KEY},
        )


class TestShopSavvyPriceComparisonUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return ShopSavvyPriceComparison

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {"shopsavvy_api_key": API_KEY}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"identifier": "B09XS7JWHH"}


class TestShopSavvyPriceHistoryUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return ShopSavvyPriceHistory

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {"shopsavvy_api_key": API_KEY}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"identifier": "B09XS7JWHH", "days_back": 30}
