# langchain-shopsavvy

[![PyPI - Version](https://img.shields.io/pypi/v/langchain-shopsavvy?label=%20)](https://pypi.org/project/langchain-shopsavvy/#history)
[![PyPI - License](https://img.shields.io/pypi/l/langchain-shopsavvy)](https://opensource.org/licenses/MIT)

## Quick Install

```bash
pip install langchain-shopsavvy
```

## What is this?

This package contains the LangChain integration with [ShopSavvy](https://shopsavvy.com), a price comparison platform with product and pricing data from thousands of retailers. It provides tools for product search, real-time price comparison, and price history analysis.

## Setup

Get an API key at [shopsavvy.com/data](https://shopsavvy.com/data) and set it as an environment variable:

```bash
export SHOPSAVVY_API_KEY="ss_live_your_api_key"
```

## Tools

- **`ShopSavvyProductSearch`** — Search for products by keyword
- **`ShopSavvyPriceComparison`** — Get current prices from all retailers for a product
- **`ShopSavvyPriceHistory`** — Get historical price data to evaluate deals

`ShopSavvyPriceHistory` returns one summary per retailer offer:

```python
from langchain_shopsavvy import ShopSavvyPriceHistory

ShopSavvyPriceHistory().invoke({"identifier": "B09XS7JWHH", "days_back": 30})
```

```json
[
  {
    "product_title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
    "retailer": "Amazon",
    "data_points": 3,
    "currency": "USD",
    "min_price": 298.0,
    "max_price": 348.0,
    "avg_price": 321.33,
    "latest_price": 298.0,
    "latest_timestamp": "2026-08-20T00:00:00Z",
    "oldest_timestamp": "2026-08-01T00:00:00Z"
  }
]
```

An offer with no recorded history has only `product_title`, `retailer` and `data_points: 0`. `currency` is `null` when the recorded points disagree or none recorded one.

## Retriever

- **`ShopSavvyRetriever`** — Retrieve product documents for use in RAG chains

## Documentation

- [ShopSavvy Data API docs](https://shopsavvy.com/data/documentation)
- [LangChain docs](https://docs.langchain.com)
