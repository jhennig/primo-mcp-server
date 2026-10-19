"""Configuration for the Primo MCP server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PrimoConfig(BaseSettings):
    """Primo API configuration.

    Defaults are set for the University of Alberta (Primo VE view 01UOA_INST:UOA).
    The tab and scope codes are the Primo VE out-of-the-box values and may need
    adjusting if the library has customised them.
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
