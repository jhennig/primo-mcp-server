"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def search_results_data() -> dict:
    """Load the search results fixture."""
    with open(FIXTURES_DIR / "search_results.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def empty_results_data() -> dict:
    """Load the empty results fixture."""
    with open(FIXTURES_DIR / "empty_results.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def suggest_results_data() -> dict:
    """Load the suggest results fixture."""
    with open(FIXTURES_DIR / "suggest_results.json", encoding="utf-8") as f:
        return json.load(f)


BASE_URL = "https://primo.test/primaws/rest/pub"


@pytest.fixture
def config():
    """A Primo config pointing at a fake host so no real request can escape."""
    from primo_mcp_server.config import PrimoConfig

    return PrimoConfig(base_url=BASE_URL, vid="TEST_INST:TEST", _env_file=None)


@pytest.fixture
async def client(config):
    """A PrimoClient backed by a real httpx client (mocked with respx)."""
    import httpx

    from primo_mcp_server.client import PrimoClient

    async with httpx.AsyncClient(base_url=config.base_url, timeout=5) as http:
        yield PrimoClient(http, config)
