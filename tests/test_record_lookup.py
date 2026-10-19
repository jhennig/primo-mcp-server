"""Tests for record lookup by ID (client and the cite/export/get_record tools)."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
import respx

from primo_mcp_server import server
from primo_mcp_server.client import PrimoClient
from primo_mcp_server.config import PrimoConfig

BASE_URL = "https://primo.example.edu/primaws/rest/pub"
KNOWN_ID = "cdi_jstor_primary_43553080"
OTHER_IDS = {
    "cdi_gale_incontextgauss__A649289798",
    "cdi_crossref_primary_10_1007_s11365_017_0461_8",
}
UNKNOWN_ID = "alma991234567890"


@pytest.fixture
def config() -> PrimoConfig:
    return PrimoConfig(base_url=BASE_URL)


@pytest.fixture
async def client(config: PrimoConfig):
    async with httpx.AsyncClient(base_url=BASE_URL) as http:
        yield PrimoClient(http, config)


@pytest.fixture
def ctx(client: PrimoClient):
    """Minimal stand-in for the FastMCP Context used by the tools."""
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"client": client})
    )


@pytest.fixture
def mock_api(search_results_data, empty_results_data):
    """Mock /pnxs: the known ID returns the fixture (3 hits); anything else
    that is not in the fixture still returns the same 3 non-matching hits,
    mimicking a fuzzy "contains" search."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:

        def handler(request: httpx.Request) -> httpx.Response:
            q = request.url.params.get("q", "")
            if q.endswith(",nohits"):
                return httpx.Response(200, json=empty_results_data)
            return httpx.Response(200, json=search_results_data)

        router.get("/pnxs").mock(side_effect=handler)
        yield router


# ---------------------------------------------------------------------------
# PrimoClient.get_record
# ---------------------------------------------------------------------------


async def test_get_record_returns_exact_match(client, mock_api):
    record = await client.get_record(KNOWN_ID)
    assert record is not None
    assert record.record_id == KNOWN_ID


async def test_get_record_ignores_surrounding_whitespace(client, mock_api):
    record = await client.get_record(f"  {KNOWN_ID}\n")
    assert record is not None
    assert record.record_id == KNOWN_ID


async def test_get_record_does_not_fall_back_to_first_hit(client, mock_api):
    # The API returns three hits, none of which has this ID.
    record = await client.get_record(UNKNOWN_ID)
    assert record is None


async def test_get_record_no_hits(client, mock_api):
    assert await client.get_record("nohits") is None


async def test_get_record_blank_id_skips_request(client, mock_api):
    assert await client.get_record("   ") is None
    assert not mock_api.calls


async def test_get_records_reports_missing_ids(client, mock_api):
    records, missing = await client.get_records([KNOWN_ID, UNKNOWN_ID])
    assert [r.record_id for r in records] == [KNOWN_ID]
    assert missing == [UNKNOWN_ID]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def test_primo_get_record_not_found(ctx, mock_api):
    out = await server.primo_get_record(ctx, UNKNOWN_ID)
    assert "not found" in out
    assert UNKNOWN_ID in out
    for other in OTHER_IDS:
        assert other not in out


async def test_primo_cite_refuses_when_an_id_is_missing(ctx, mock_api):
    out = await server.primo_cite(ctx, [KNOWN_ID, UNKNOWN_ID])
    assert out.startswith("Record not found:")
    assert UNKNOWN_ID in out
    assert "No output was generated" in out


async def test_primo_cite_lists_all_missing_ids(ctx, mock_api):
    out = await server.primo_cite(ctx, [UNKNOWN_ID, "alma990000000000"])
    assert out.startswith("Records not found:")
    assert UNKNOWN_ID in out
    assert "alma990000000000" in out


async def test_primo_cite_succeeds_for_known_id(ctx, mock_api):
    out = await server.primo_cite(ctx, [KNOWN_ID])
    assert "not found" not in out
    assert "verify citations" in out


async def test_primo_cite_empty_list(ctx, mock_api):
    out = await server.primo_cite(ctx, [])
    assert out == "No record IDs were provided."


@pytest.mark.parametrize("fmt", ["bibtex", "ris", "csv"])
async def test_primo_export_refuses_when_an_id_is_missing(ctx, mock_api, fmt):
    out = await server.primo_export(ctx, [UNKNOWN_ID], format=fmt)
    assert out.startswith("Record not found:")
    assert UNKNOWN_ID in out


async def test_primo_export_succeeds_for_known_id(ctx, mock_api):
    out = await server.primo_export(ctx, [KNOWN_ID], format="ris")
    assert "not found" not in out
    assert "TY  -" in out
