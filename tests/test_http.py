"""Tests for serving the tools over streamable HTTP."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

import primo_mcp_server
from primo_mcp_server import server
from primo_mcp_server.config import PrimoConfig

INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}
HEADERS = {"Accept": "application/json, text/event-stream"}


def _fresh_server() -> FastMCP:
    app = FastMCP("test")

    @app.tool()
    def ping() -> str:
        return "pong"

    return app


def test_transport_defaults_to_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TRANSPORT", "HTTP_HOST", "HTTP_PORT", "HTTP_ALLOWED_HOSTS"):
        monkeypatch.delenv(f"PRIMO_{name}", raising=False)
    cfg = PrimoConfig(_env_file=None)
    assert cfg.transport == "stdio"
    assert cfg.http_host == "127.0.0.1"
    assert cfg.http_port == 8000
    assert cfg.http_allowed_hosts == ""


def test_configure_http_localhost_keeps_host_checking() -> None:
    app = _fresh_server()
    server.configure_http(app, host="127.0.0.1", port=9001)
    assert app.settings.port == 9001
    assert app.settings.stateless_http is True
    assert app.settings.json_response is True
    sec = app.settings.transport_security
    assert sec is not None and sec.enable_dns_rebinding_protection
    assert "localhost:*" in sec.allowed_hosts


def test_configure_http_public_bind_without_names_disables_host_checking() -> None:
    app = _fresh_server()
    server.configure_http(app, host="0.0.0.0", port=8000)
    assert app.settings.host == "0.0.0.0"
    assert app.settings.transport_security is None


def test_configure_http_allowed_hosts() -> None:
    app = _fresh_server()
    server.configure_http(app, host="0.0.0.0", port=8000, allowed_hosts=" mcp.example.edu , ")
    sec = app.settings.transport_security
    assert sec is not None and sec.enable_dns_rebinding_protection
    assert "mcp.example.edu" in sec.allowed_hosts
    assert "mcp.example.edu:*" in sec.allowed_hosts
    assert "https://mcp.example.edu" in sec.allowed_origins


def test_http_app_answers_initialize_and_rejects_unknown_host() -> None:
    app = _fresh_server()
    server.configure_http(app, host="0.0.0.0", port=8000, allowed_hosts="mcp.example.edu")
    with TestClient(app.streamable_http_app(), base_url="https://mcp.example.edu") as client:
        ok = client.post("/mcp", json=INIT, headers=HEADERS)
        assert ok.status_code == 200
        assert ok.json()["result"]["serverInfo"]["name"] == "test"

        tools = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=HEADERS,
        )
        assert [t["name"] for t in tools.json()["result"]["tools"]] == ["ping"]

        bad = client.post("/mcp", json=INIT, headers={**HEADERS, "Host": "evil.example.com"})
        assert bad.status_code == 421


@pytest.mark.parametrize(
    ("argv", "env", "expected"),
    [
        ([], {}, ("stdio", None)),
        (["--transport", "streamable-http", "--port", "9100"], {}, ("streamable-http", ("127.0.0.1", 9100, ""))),
        (
            [],
            {"PRIMO_TRANSPORT": "streamable-http", "PRIMO_HTTP_HOST": "0.0.0.0", "PRIMO_HTTP_ALLOWED_HOSTS": "a.edu"},
            ("streamable-http", ("0.0.0.0", 8000, "a.edu")),
        ),
    ],
)
def test_main_picks_transport(monkeypatch: pytest.MonkeyPatch, argv, env, expected) -> None:
    for name in ("TRANSPORT", "HTTP_HOST", "HTTP_PORT", "HTTP_ALLOWED_HOSTS"):
        monkeypatch.delenv(f"PRIMO_{name}", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    calls: dict = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.setdefault("transport", transport))
    monkeypatch.setattr(
        server,
        "configure_http",
        lambda app, host, port, allowed_hosts: calls.setdefault("http", (host, port, allowed_hosts)),
    )

    primo_mcp_server.main(argv)

    assert (calls["transport"], calls.get("http")) == expected
