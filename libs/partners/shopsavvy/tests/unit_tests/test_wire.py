"""Wire-level tests for the ShopSavvy tools and retriever.

These run the real shopsavvy SDK client (request building and pydantic
response parsing) and the real LangChain tool/retriever machinery. Only the
network is swapped for an ``httpx.MockTransport`` that serves responses in the
ShopSavvy Data API's wire shape.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException
from pydantic import SecretStr

from langchain_shopsavvy import (
    ShopSavvyPriceComparison,
    ShopSavvyPriceHistory,
    ShopSavvyProductSearch,
    ShopSavvyRetriever,
)

API_KEY = "ss_test_wire_tests"

PRODUCT: dict[str, Any] = {
    "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
    "shopsavvy": "sp_456",
    "brand": "Sony",
    "category": "Headphones",
    "barcode": "027242923782",
    "amazon": "B09XS7JWHH",
    "model": "WH1000XM5/B",
    "description": "Industry-leading noise canceling headphones.",
}


def _offer(offer_id: str, retailer: str, price: float | None) -> dict[str, Any]:
    return {
        "id": offer_id,
        "retailer": retailer,
        "price": price,
        "currency": "USD",
        "availability": "in",
        "condition": "new",
        "URL": f"https://{retailer.lower().replace(' ', '')}.example/p/{offer_id}",
        "timestamp": "2026-09-01T12:00:00Z",
    }


def _wire(obj: Any, payload: dict[str, Any] | Callable[..., httpx.Response]) -> list:
    """Point obj's SDK client at a MockTransport; return the list of requests."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if callable(payload):
            return payload(request)
        return httpx.Response(200, json=payload)

    real = obj.client._client
    obj.client._client = httpx.Client(
        base_url=real.base_url,
        headers=real.headers,
        transport=httpx.MockTransport(handler),
    )
    return seen


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOPSAVVY_API_KEY", API_KEY)
    tool = ShopSavvyProductSearch()
    assert tool.shopsavvy_api_key.get_secret_value() == API_KEY
    assert tool.client._client.headers["authorization"] == f"Bearer {API_KEY}"


def test_missing_api_key_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHOPSAVVY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key is required"):
        ShopSavvyProductSearch()


def test_product_search() -> None:
    tool = ShopSavvyProductSearch(shopsavvy_api_key=SecretStr(API_KEY))
    seen = _wire(
        tool,
        {
            "success": True,
            "data": [PRODUCT],
            "pagination": {"total": 1, "limit": 3, "offset": 0, "returned": 1},
        },
    )

    out = json.loads(tool.invoke({"query": "sony headphones", "max_results": 3}))

    assert seen[0].url.path == "/v1/products/search"
    assert seen[0].url.params["q"] == "sony headphones"
    assert seen[0].url.params["limit"] == "3"
    assert out == [
        {
            "title": PRODUCT["title"],
            "brand": "Sony",
            "category": "Headphones",
            "barcode": "027242923782",
            "asin": "B09XS7JWHH",
            "shopsavvy_id": "sp_456",
            "model": "WH1000XM5/B",
        }
    ]


def test_price_comparison_sorted_by_price() -> None:
    tool = ShopSavvyPriceComparison(shopsavvy_api_key=SecretStr(API_KEY))
    product = dict(PRODUCT)
    product["offers"] = [
        _offer("of_1", "Best Buy", 329.99),
        _offer("of_2", "Amazon", 298.0),
        _offer("of_3", "eBay", None),
    ]
    seen = _wire(tool, {"success": True, "data": [product]})

    out = json.loads(tool.invoke({"identifier": "B09XS7JWHH"}))

    assert seen[0].url.path == "/v1/products/offers"
    assert seen[0].url.params["ids"] == "B09XS7JWHH"
    assert [o["retailer"] for o in out] == ["Amazon", "Best Buy", "eBay"]
    assert out[0]["price"] == 298.0
    assert out[0]["url"] == "https://amazon.example/p/of_2"
    assert out[0]["last_updated"] == "2026-09-01T12:00:00Z"


def test_price_history_summary() -> None:
    """History arrives as product -> offers -> history.

    GET /products/offers/history returns the same product -> offers shape as
    GET /products/offers, each offer carrying ``history`` points of
    {timestamp, price, currency, availability} (data-documentation.md "Example
    Response"; refinery's offerHistory handler).

    Points arrive newest first; ``availability`` is omitted when it was not
    observed and ``currency`` is null on an archived point with no recorded
    currency. shopsavvy-sdk 1.1.0-1.3.0 read ``data`` as List[OfferWithHistory]
    (offers at the top level, ``id`` required), so every real 200 raised a
    ValidationError; 1.4.0 models the real shape, hence the >=1.4.0 floor.
    """
    tool = ShopSavvyPriceHistory(shopsavvy_api_key=SecretStr(API_KEY))
    offer = _offer("of_1", "Amazon", 298.0)
    offer["history"] = [
        {
            "availability": "in",
            "price": 298.0,
            "currency": "USD",
            "timestamp": "2026-08-20T00:00:00Z",
        },
        {
            "availability": "out",
            "price": 318.0,
            "currency": "USD",
            "timestamp": "2026-08-10T00:00:00Z",
        },
        {
            "price": 348.0,
            "currency": None,
            "timestamp": "2026-08-01T00:00:00Z",
        },
    ]
    ebay = _offer("of_2", "eBay", 250.0)
    ebay["history"] = []
    seen = _wire(
        tool,
        {
            "success": True,
            "data": [{**PRODUCT, "offers": [offer, ebay]}],
            "meta": {
                "request_id": "req-7f3c9a",
                "credits_used": 2,
                "credits_remaining": 998,
                "rate_limit_remaining": 999,
            },
        },
    )

    out = json.loads(tool.invoke({"identifier": "B09XS7JWHH", "days_back": 30}))

    assert seen[0].url.path == "/v1/products/offers/history"
    assert seen[0].url.params["ids"] == "B09XS7JWHH"
    assert set(seen[0].url.params) == {"ids", "start", "end"}
    assert out == [
        {
            "product_title": PRODUCT["title"],
            "retailer": "Amazon",
            "data_points": 3,
            "currency": "USD",
            "min_price": 298.0,
            "max_price": 348.0,
            "avg_price": 321.33,
            "latest_price": 298.0,
            "latest_timestamp": "2026-08-20T00:00:00Z",
            "oldest_timestamp": "2026-08-01T00:00:00Z",
        },
        {
            "product_title": PRODUCT["title"],
            "retailer": "eBay",
            "data_points": 0,
        },
    ]


def test_api_error_becomes_error_tool_message() -> None:
    tool = ShopSavvyPriceComparison(shopsavvy_api_key=SecretStr(API_KEY))
    _wire(tool, lambda request: httpx.Response(401, json={"error": "bad key"}))

    msg = tool.invoke(
        {
            "args": {"identifier": "B09XS7JWHH"},
            "id": "call_1",
            "name": tool.name,
            "type": "tool_call",
        }
    )

    assert isinstance(msg, ToolMessage)
    assert msg.status == "error"
    assert "AuthenticationError" in msg.content


def test_api_error_raises_when_handling_disabled() -> None:
    tool = ShopSavvyProductSearch(
        shopsavvy_api_key=SecretStr(API_KEY), handle_tool_error=False
    )
    _wire(tool, lambda request: httpx.Response(404, json={"error": "nope"}))

    with pytest.raises(ToolException, match="NotFoundError"):
        tool.invoke({"query": "does not exist"})


def test_retriever() -> None:
    retriever = ShopSavvyRetriever(shopsavvy_api_key=SecretStr(API_KEY), k=2)
    seen = _wire(
        retriever,
        {
            "success": True,
            "data": [PRODUCT],
            "pagination": {"total": 1, "limit": 2, "offset": 0, "returned": 1},
        },
    )

    docs = retriever.invoke("sony headphones")

    assert seen[0].url.params["limit"] == "2"
    assert len(docs) == 1
    assert json.loads(docs[0].page_content)["description"] == PRODUCT["description"]
    assert docs[0].metadata["asin"] == "B09XS7JWHH"
    assert docs[0].metadata["shopsavvy_id"] == "sp_456"
