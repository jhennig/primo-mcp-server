"""Tests that institution settings are read from the environment and sent to Primo."""

from __future__ import annotations

import httpx
import pytest
import respx

from primo_mcp_server.client import PrimoClient
from primo_mcp_server.config import PrimoConfig

BASE_URL = "https://example.primo.exlibrisgroup.com/primaws/rest/pub"


@pytest.fixture
def institution_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the server at a non-default institution via PRIMO_ variables."""
    monkeypatch.setenv("PRIMO_BASE_URL", BASE_URL)
    monkeypatch.setenv("PRIMO_VID", "01TEST_INST:TEST")
    monkeypatch.setenv("PRIMO_INSTITUTION_NAME", "Test University")
    monkeypatch.setenv("PRIMO_TAB_EVERYTHING", "Everything_Tab")
    monkeypatch.setenv("PRIMO_TAB_CATALOGUE", "Local_Tab")
    monkeypatch.setenv("PRIMO_SCOPE_COMBINED", "Combined_Scope")
    monkeypatch.setenv("PRIMO_SCOPE_LOCAL", "Local_Scope")


def test_defaults_are_ualberta(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("BASE_URL", "VID", "INSTITUTION_NAME"):
        monkeypatch.delenv(f"PRIMO_{name}", raising=False)
    cfg = PrimoConfig(_env_file=None)
    assert cfg.base_url == "https://search.library.ualberta.ca/primaws/rest/pub"
    assert cfg.vid == "01UOA_INST:UOA"
    assert cfg.institution_name == "University of Alberta"


def test_env_overrides_defaults(institution_env: None) -> None:
    cfg = PrimoConfig(_env_file=None)
    assert cfg.base_url == BASE_URL
    assert cfg.vid == "01TEST_INST:TEST"
    assert cfg.institution_name == "Test University"
    assert cfg.tab_everything == "Everything_Tab"
    assert cfg.tab_catalogue == "Local_Tab"
    assert cfg.scope_combined == "Combined_Scope"
    assert cfg.scope_local == "Local_Scope"


@pytest.mark.parametrize(
    ("scope", "tab", "scope_param"),
    [
        ("everything", "Everything_Tab", "Combined_Scope"),
        ("catalogue", "Local_Tab", "Local_Scope"),
    ],
)
@respx.mock
async def test_search_sends_configured_values(
    institution_env: None,
    empty_results_data: dict,
    scope: str,
    tab: str,
    scope_param: str,
) -> None:
    route = respx.get(f"{BASE_URL}/pnxs").mock(
        return_value=httpx.Response(200, json=empty_results_data)
    )
    cfg = PrimoConfig(_env_file=None)
    async with httpx.AsyncClient(base_url=cfg.base_url) as http:
        await PrimoClient(http, cfg).search("test", scope=scope)

    assert route.called
    params = route.calls.last.request.url.params
    assert params["vid"] == "01TEST_INST:TEST"
    assert params["tab"] == tab
    assert params["scope"] == scope_param
