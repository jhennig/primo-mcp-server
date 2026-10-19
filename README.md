# primo-mcp-server

MCP server for Ex Libris Primo library discovery -- search university catalogues and subscribed databases (ProQuest, Elsevier, Crossref, Gale, Springer, IEEE, etc.) via the Model Context Protocol.

## Features

- **Search** the full university catalogue and Primo Central Index (millions of records)
- **Get record details** including abstract, authors, identifiers, and availability
- **Autocomplete** search suggestions
- **Generate citations** in APA 7th, Harvard, Chicago, IEEE, and Vancouver styles
- **Export** to BibTeX, RIS, or CSV for import into reference managers

## Installation

Requires Python 3.11 or later. Install into a virtual environment so the server has its own dependencies:

```bash
git clone https://github.com/jhennig/primo-mcp-server.git
cd primo-mcp-server
python3 -m venv .venv
.venv/bin/pip install -e .
```

On Windows, use `.venv\Scripts\pip install -e .` instead.

Then note the full path to the virtual environment's Python, which the registration steps below need:

```bash
echo "$PWD/.venv/bin/python"
```

On Windows the path is `<repo folder>\.venv\Scripts\python.exe`.

Use this full path rather than a bare `python` command. Claude Desktop and Claude Code start the server without your shell's `PATH` or an activated virtual environment, so a bare `python` usually resolves to a different interpreter that does not have the server installed.

## Register in Claude Desktop

Open Claude Desktop, go to Settings > Developer > Edit Config, and add the server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "primo": {
      "command": "/full/path/to/primo-mcp-server/.venv/bin/python",
      "args": ["-m", "primo_mcp_server"]
    }
  }
}
```

Fully quit and reopen Claude Desktop. The Primo tools then appear in the tools menu of a new chat.

## Register in Claude Code

Run:

```bash
claude mcp add primo -- /full/path/to/primo-mcp-server/.venv/bin/python -m primo_mcp_server
```

Add `--scope user` to make the server available in every project rather than only the current directory. Check it with `claude mcp list`. The tools appear as `mcp__primo__primo_search`, etc.

## Hosting one shared copy

Instead of each person installing the server, an institution can run one copy on a web server and let people add it to Claude as a connector, with nothing to install on their own computer.

Start the server in HTTP mode:

```bash
primo-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000
```

The tools are then served at `http://<server>:8000/mcp`. The same settings are available as environment variables (`PRIMO_TRANSPORT`, `PRIMO_HTTP_HOST`, `PRIMO_HTTP_PORT`), which is easier in a service file or container.

For a public deployment:

- Put the server behind a reverse proxy (for example nginx) that provides HTTPS, so the address people add is `https://<public hostname>/mcp`.
- If the server binds to `127.0.0.1` behind that proxy, set `PRIMO_HTTP_ALLOWED_HOSTS` to the public hostname (comma-separated for several). The server rejects requests whose `Host` header is not on that list, which protects it from DNS rebinding.
- Consider rate limiting at the proxy. Every search runs against your Primo instance on behalf of whoever uses the connector.

The server runs statelessly and answers with plain JSON, so several copies can run behind a load balancer. It has no login of its own: anyone who can reach the address can search, with the same guest access as the public Library Search page.

To use a hosted copy, add the `https://.../mcp` address in Claude under Settings > Connectors > Add custom connector.

## Tools

| Tool | Description |
|------|-------------|
| `primo_search` | Search the library catalogue with filters (type, date, peer-reviewed) |
| `primo_get_record` | Get full details for a record by ID |
| `primo_suggest` | Autocomplete search suggestions |
| `primo_cite` | Generate formatted citations (APA7, Harvard, Chicago, IEEE, Vancouver) |
| `primo_export` | Export records as BibTeX, RIS, or CSV |

## Usage Examples

From a Claude Desktop or Claude Code conversation:

- "Search the library for articles about machine learning in entrepreneurship published after 2020"
- "Get the full details for record cdi_crossref_primary_10_1234"
- "Generate APA7 citations for these records"
- "Export the search results as BibTeX"

## Configuration

Defaults are set for the University of Alberta. Override via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIMO_BASE_URL` | `https://search.library.ualberta.ca/primaws/rest/pub` | Primo API base URL |
| `PRIMO_VID` | `01UOA_INST:UOA` | Primo View ID |
| `PRIMO_INSTITUTION_NAME` | `University of Alberta` | Display name |
| `PRIMO_REQUEST_TIMEOUT` | `30.0` | HTTP timeout in seconds |
| `PRIMO_MAX_RESULTS_PER_REQUEST` | `50` | Maximum results per search |
| `PRIMO_DEFAULT_RESULTS` | `10` | Default results per search |
| `PRIMO_TAB_EVERYTHING` | `Everything` | Primo tab for local catalogue plus subscribed databases |
| `PRIMO_TAB_CATALOGUE` | `LibraryCatalog` | Primo tab for the local catalogue only |
| `PRIMO_SCOPE_COMBINED` | `MyInst_and_CI` | Search scope used with the "everything" tab |
| `PRIMO_SCOPE_LOCAL` | `MyInstitution` | Search scope used with the "catalogue" tab |

See `.env.example` for the full list. Values can also go in a `.env` file in the directory the server is started from.

### Finding the values for your institution

Run any search in your library's Primo interface and look at the address bar. A Primo VE search URL looks like this:

```
https://<host>/discovery/search?query=any,contains,test&tab=<TAB>&search_scope=<SCOPE>&vid=<VID>
```

- `PRIMO_BASE_URL` is `https://<host>/primaws/rest/pub`
- `PRIMO_VID` is the `vid` value (for example `01ABC_INST:MAIN`)
- `PRIMO_TAB_EVERYTHING` and `PRIMO_SCOPE_COMBINED` are the `tab` and `search_scope` values when searching everything
- `PRIMO_TAB_CATALOGUE` and `PRIMO_SCOPE_LOCAL` are the same values after switching the interface to the local catalogue only

### University of Alberta

The defaults point at the University of Alberta Library Search (`https://search.library.ualberta.ca/discovery/search?vid=01UOA_INST:UOA`), so no configuration is needed there. The tab and scope codes (`Everything` / `MyInst_and_CI` for everything, `LibraryCatalog` / `MyInstitution` for the catalogue) match the UAlberta search URLs as of October 2026. If a search fails with HTTP 400, check them against the address bar using the steps above.

### Other institutions

Set the values in the `env` block of the Claude Desktop registration (with Claude Code, pass each one as `--env NAME=value` to `claude mcp add`):

```json
{
  "mcpServers": {
    "primo": {
      "command": "/full/path/to/primo-mcp-server/.venv/bin/python",
      "args": ["-m", "primo_mcp_server"],
      "env": {
        "PRIMO_BASE_URL": "https://<primo-host>/primaws/rest/pub",
        "PRIMO_VID": "<vid>",
        "PRIMO_INSTITUTION_NAME": "<institution name>",
        "PRIMO_TAB_EVERYTHING": "<everything-tab>",
        "PRIMO_TAB_CATALOGUE": "<catalogue-tab>",
        "PRIMO_SCOPE_COMBINED": "<everything-scope>",
        "PRIMO_SCOPE_LOCAL": "<catalogue-scope>"
      }
    }
  }
}
```

The server uses the public Primo API (`primaws/rest/pub`), so no API key is needed, but results from subscribed databases depend on the view allowing guest access.

For example, the original University of Western Australia values were `PRIMO_BASE_URL=https://onesearch.library.uwa.edu.au/primaws/rest/pub`, `PRIMO_VID=61UWA_INST:NDE_UWA` and `PRIMO_TAB_CATALOGUE=Catalogue`.

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Credits

Originally written by Gehe Haridas ([geheharidas/primo-mcp-server](https://github.com/geheharidas/primo-mcp-server)). This fork adds University of Alberta setup.

## Licence

MIT. See `LICENSE`.
