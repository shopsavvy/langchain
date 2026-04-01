#!/bin/bash
set -e

echo "🧪 ShopSavvy LangChain Partner Tests"
echo "======================================"

if [ "$1" = "--integration" ]; then
  if [ -z "$SHOPSAVVY_API_KEY" ]; then
    echo "❌ Set SHOPSAVVY_API_KEY env var to run integration tests"
    echo "   Get a key at https://shopsavvy.com/data"
    exit 1
  fi
  echo "Running integration tests (live API)..."
  make integration_tests
else
  echo "Running unit tests (mocked API)..."
  make test
fi

echo ""
echo "✅ All tests passed"
