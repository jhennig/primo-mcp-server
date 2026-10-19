"""Tests for the MCP tool functions, with the Primo API mocked by respx."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import respx

from primo_mcp_server import server

from .conftest import BASE_URL

PNXS = f"{BASE_URL}/pnxs"
SUGGEST = f"{BASE_URL}/suggest"


@pytest.fixture
def ctx(client):
    """A stand-in for the MCP Context exposing the lifespan client."""
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"client": client})
    )


@respx.mock
async def test_primo_search_formats_results(ctx, search_results_data):
    respx.get(PNXS).respond(json=search_results_data)

    out = await server.primo_search(ctx, "entrepreneurship")

    assert "cdi_jstor_primary_43553080" in out
    assert "Error" not in out


@respx.mock
async def test_primo_search_passes_date_to_alone(ctx, empty_results_data):
    route = respx.get(PNXS).respond(json=empty_results_data)

    await server.primo_search(ctx, "x", date_to="1999")

    params = route.calls.last.request.url.params
    assert params["q"] == "any,contains,x,AND;dr_s,exact,100001,AND;dr_e,exact,199912"


@respx.mock
async def test_primo_search_reports_bad_years(ctx):
    route = respx.get(PNXS)

    out = await server.primo_search(ctx, "x", date_from="2020", date_to="2010")

    assert out.startswith("Invalid search parameters:")
    assert not route.called


@respx.mock
async def test_primo_search_reports_api_error(ctx):
    respx.get(PNXS).respond(status_code=500)

    out = await server.primo_search(ctx, "x")

    assert out.startswith("Error searching Primo:")
    assert "HTTP 500" in out


@respx.mock
async def test_primo_get_record(ctx, search_results_data):
    respx.get(PNXS).respond(json=search_results_data)

    out = await server.primo_get_record(ctx, "cdi_jstor_primary_43553080")

    assert "cdi_jstor_primary_43553080" in out


@respx.mock
async def test_primo_get_record_not_found(ctx, empty_results_data):
    respx.get(PNXS).respond(json=empty_results_data)

    out = await server.primo_get_record(ctx, "missing")

    assert 'Record "missing" not found' in out


@respx.mock
async def test_primo_suggest(ctx, suggest_results_data):
    respx.get(SUGGEST).respond(json=suggest_results_data)

    out = await server.primo_suggest(ctx, "entrepre")

    assert "entrepreneurship" in out


@respx.mock
async def test_primo_cite(ctx, search_results_data):
    respx.get(PNXS).respond(json=search_results_data)

    out = await server.primo_cite(ctx, ["cdi_jstor_primary_43553080"], style="apa7")

    assert "verify citations" in out


async def test_primo_cite_rejects_unknown_style(ctx):
    out = await server.primo_cite(ctx, ["x"], style="mla")

    assert out.startswith('Invalid citation style "mla"')


@respx.mock
async def test_primo_cite_no_records(ctx, empty_results_data):
    respx.get(PNXS).respond(json=empty_results_data)

    out = await server.primo_cite(ctx, ["missing"])

    assert out.startswith('Record not found: "missing".')


@respx.mock
@pytest.mark.parametrize(("fmt", "marker"), [("bibtex", "@"), ("ris", "TY  -")])
async def test_primo_export(ctx, search_results_data, fmt, marker):
    respx.get(PNXS).respond(json=search_results_data)

    out = await server.primo_export(ctx, ["cdi_jstor_primary_43553080"], format=fmt)

    assert marker in out


@respx.mock
async def test_primo_export_csv(ctx, search_results_data):
    respx.get(PNXS).respond(json=search_results_data)

    out = await server.primo_export(ctx, ["cdi_jstor_primary_43553080"], format="csv")

    assert out.splitlines()[0].lstrip("﻿")  # header row present
    assert len(out.strip().splitlines()) == 2


async def test_primo_export_rejects_unknown_format(ctx):
    out = await server.primo_export(ctx, ["x"], format="endnote")

    assert out.startswith('Invalid format "endnote"')


async def test_tools_are_registered():
    names = {tool.name for tool in await server.mcp.list_tools()}

    assert names == {
        "primo_search",
        "primo_get_record",
        "primo_suggest",
        "primo_cite",
        "primo_export",
    }
