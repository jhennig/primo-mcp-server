"""Tests for the Primo HTTP client, with the API mocked by respx."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from primo_mcp_server.client import PrimoAPIError

from .conftest import BASE_URL

PNXS = f"{BASE_URL}/pnxs"
SUGGEST = f"{BASE_URL}/suggest"


def _params(route: respx.Route) -> httpx.QueryParams:
    return route.calls.last.request.url.params


# ---------------------------------------------------------------------------
# search: request parameters
# ---------------------------------------------------------------------------


@respx.mock
async def test_search_sends_core_params(client, search_results_data):
    route = respx.get(PNXS).respond(json=search_results_data)

    response = await client.search("climate change", field="title", sort_by="date")

    params = _params(route)
    assert params["vid"] == "TEST_INST:TEST"
    assert params["q"] == "title,contains,climate change"
    assert params["sortby"] == "date"
    assert params["tab"] == "Everything"
    assert params["scope"] == "MyInst_and_CI"
    assert params["limit"] == "10"
    assert params["offset"] == "0"
    assert "qInclude" not in params
    assert "mode" not in params
    assert len(response.records) == 3


@respx.mock
async def test_search_catalogue_scope(client, search_results_data):
    route = respx.get(PNXS).respond(json=search_results_data)

    await client.search("x", scope="catalogue")

    assert _params(route)["tab"] == "LibraryCatalog"
    assert _params(route)["scope"] == "MyInstitution"


@respx.mock
@pytest.mark.parametrize(
    ("limit", "offset", "expected_limit", "expected_offset"),
    [(0, -5, "1", "0"), (500, 20, "50", "20")],
)
async def test_search_clamps_limit_and_offset(
    client, empty_results_data, limit, offset, expected_limit, expected_offset
):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("x", limit=limit, offset=offset)

    assert _params(route)["limit"] == expected_limit
    assert _params(route)["offset"] == expected_offset


@respx.mock
async def test_search_facets_joined_in_qinclude(client, empty_results_data):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("x", resource_type="books", peer_reviewed=True)

    assert _params(route)["qInclude"] == (
        "facet_rtype,exact,books|,|facet_tlevel,exact,peer_reviewed"
    )


# ---------------------------------------------------------------------------
# search: year filters
# ---------------------------------------------------------------------------


NEXT_YEAR = date.today().year + 1


@respx.mock
@pytest.mark.parametrize(
    ("date_from", "date_to", "expected"),
    [
        ("2015", "2020", "dr_s,exact,201501,AND;dr_e,exact,202012"),
        ("2015", None, f"dr_s,exact,201501,AND;dr_e,exact,{NEXT_YEAR}12"),
        (None, "2020", "dr_s,exact,100001,AND;dr_e,exact,202012"),
        ("2020", "2020", "dr_s,exact,202001,AND;dr_e,exact,202012"),
        (" 2015 ", "", f"dr_s,exact,201501,AND;dr_e,exact,{NEXT_YEAR}12"),
    ],
)
async def test_search_year_range_is_one_query_clause(
    client, empty_results_data, date_from, date_to, expected
):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("water", date_from=date_from, date_to=date_to)

    params = _params(route)
    assert params["q"] == f"any,contains,water,AND;{expected}"
    assert params["mode"] == "advanced"
    # Years must no longer be expanded into per-year qInclude facets.
    assert "creationdate" not in params.get("qInclude", "")


@respx.mock
async def test_search_without_years_is_not_advanced(client, empty_results_data):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("water")

    assert _params(route)["q"] == "any,contains,water"
    assert "mode" not in _params(route)


@respx.mock
async def test_search_wide_year_range_stays_small(client, empty_results_data):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("x", date_from="1900", date_to="2025")

    assert len(str(route.calls.last.request.url)) < 500


@respx.mock
async def test_search_years_combine_with_other_facets(client, empty_results_data):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await client.search("x", resource_type="articles", date_to="2010")

    params = _params(route)
    assert params["qInclude"] == "facet_rtype,exact,articles"
    assert params["q"].endswith(",AND;dr_e,exact,201012")


@pytest.mark.parametrize(
    ("date_from", "date_to", "message"),
    [
        ("2020", "2015", "must not be later"),
        ("20x0", None, "date_from must be a year"),
        (None, "2020-01-01", "date_to must be a year"),
        ("12345", None, "date_from must be a year"),
    ],
)
@respx.mock
async def test_search_rejects_bad_years_without_calling_api(
    client, date_from, date_to, message
):
    route = respx.get(PNXS)

    with pytest.raises(ValueError, match=message):
        await client.search("x", date_from=date_from, date_to=date_to)

    assert not route.called


# ---------------------------------------------------------------------------
# get_record / get_records / suggest
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_record_returns_exact_match(client, search_results_data):
    route = respx.get(PNXS).respond(json=search_results_data)

    record = await client.get_record("cdi_jstor_primary_43553080")

    assert record is not None
    assert record.record_id == "cdi_jstor_primary_43553080"
    assert _params(route)["q"] == "any,contains,cdi_jstor_primary_43553080"


@respx.mock
async def test_get_record_none_when_no_results(client, empty_results_data):
    respx.get(PNXS).respond(json=empty_results_data)

    assert await client.get_record("missing") is None


@respx.mock
async def test_get_records_reports_missing(client, search_results_data, empty_results_data):
    respx.get(PNXS, params={"q": "any,contains,missing"}).respond(json=empty_results_data)
    respx.get(PNXS).respond(json=search_results_data)

    records, missing = await client.get_records(
        ["cdi_jstor_primary_43553080", "missing", "cdi_gale_incontextgauss__A649289798"]
    )

    assert [r.record_id for r in records] == [
        "cdi_jstor_primary_43553080",
        "cdi_gale_incontextgauss__A649289798",
    ]
    assert missing == ["missing"]


@respx.mock
async def test_suggest(client, suggest_results_data):
    route = respx.get(SUGGEST).respond(json=suggest_results_data)

    suggestions = await client.suggest("entrepre")

    assert _params(route)["q"] == "entrepre"
    assert suggestions[:2] == ["entrepreneur", "entrepreneurship"]
    assert len(suggestions) == 5


@respx.mock
async def test_suggest_tolerates_missing_response(client):
    respx.get(SUGGEST).respond(json={})

    assert await client.suggest("x") == []


# ---------------------------------------------------------------------------
# error handling
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.parametrize(
    ("status", "message"),
    [(400, "Bad request"), (503, "server error"), (404, "HTTP 404")],
)
async def test_http_errors_become_primo_api_error(client, status, message):
    respx.get(PNXS).respond(status_code=status)

    with pytest.raises(PrimoAPIError, match=message) as exc_info:
        await client.search("x")

    assert exc_info.value.status_code == status


@respx.mock
async def test_timeout_becomes_primo_api_error(client):
    respx.get(PNXS).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(PrimoAPIError, match="timed out"):
        await client.search("x")


@respx.mock
async def test_connect_error_becomes_primo_api_error(client):
    respx.get(PNXS).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(PrimoAPIError, match="Could not connect"):
        await client.search("x")


@respx.mock
async def test_invalid_json_becomes_primo_api_error(client):
    respx.get(PNXS).respond(text="<html>not json</html>")

    with pytest.raises(PrimoAPIError, match="Unexpected error"):
        await client.search("x")
