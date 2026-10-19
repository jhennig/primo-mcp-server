"""Primo MCP Server -- search university library catalogues via MCP."""

from __future__ import annotations

import argparse

__version__ = "0.1.0"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="primo-mcp-server",
        description="MCP server for Ex Libris Primo library search.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        help="How clients connect (default: PRIMO_TRANSPORT, or stdio).",
    )
    parser.add_argument("--host", help="HTTP bind address (default: PRIMO_HTTP_HOST, or 127.0.0.1).")
    parser.add_argument("--port", type=int, help="HTTP port (default: PRIMO_HTTP_PORT, or 8000).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the primo-mcp-server command."""
    from primo_mcp_server.config import PrimoConfig
    from primo_mcp_server.server import configure_http, mcp

    args = _parse_args(argv)
    config = PrimoConfig()
    transport = args.transport or config.transport

    if transport == "streamable-http":
        configure_http(
            mcp,
            host=args.host or config.http_host,
            port=args.port or config.http_port,
            allowed_hosts=config.http_allowed_hosts,
        )

    mcp.run(transport=transport)
