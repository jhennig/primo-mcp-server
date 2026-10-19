"""Configuration for the Primo MCP server."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class PrimoConfig(BaseSettings):
    """Primo API configuration.

    Defaults are set for the University of Alberta (Primo VE view 01UOA_INST:UOA).
    Tab and scope codes match the UAlberta search URLs as of October 2026.
    Override via environment variables with the PRIMO_ prefix,
    or via a .env file in the working directory.
    """

    model_config = SettingsConfigDict(env_prefix="PRIMO_", env_file=".env")

    # Institution-specific
    base_url: str = "https://search.library.ualberta.ca/primaws/rest/pub"
    vid: str = "01UOA_INST:UOA"
    institution_name: str = "University of Alberta"
    tab_everything: str = "Everything"
    tab_catalogue: str = "LibraryCatalog"
    scope_combined: str = "MyInst_and_CI"
    scope_local: str = "MyInstitution"

    # Operational
    request_timeout: float = 30.0
    max_results_per_request: int = 50
    default_results: int = 10
    language: str = "en"
    user_agent: str = "primo-mcp-server/0.1.0"

    # How MCP clients connect. "stdio" (default) is for a client that starts
    # the server itself, such as Claude Desktop. "streamable-http" serves the
    # tools over the web so one hosted copy can be shared as a connector.
    transport: Literal["stdio", "streamable-http"] = "stdio"
    http_host: str = "127.0.0.1"
    http_port: int = 8000
    # Comma-separated public hostnames the HTTP server answers to, for example
    # "mcp.library.example.edu". Needed when binding to localhost behind a
    # reverse proxy that passes the public Host header.
    http_allowed_hosts: str = ""
