"""Shared pytest fixtures for TradeLens backend tests."""
from __future__ import annotations

import pytest

from routers import market as market_router


@pytest.fixture(autouse=True)
def _reset_opportunities_response_cache():
    """Prevent cross-test pollution from the opportunities endpoint cache."""
    market_router.clear_opportunities_cache()
    yield
    market_router.clear_opportunities_cache()
