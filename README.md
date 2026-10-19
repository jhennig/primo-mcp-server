# primo-mcp-server

MCP server for Ex Libris Primo library discovery -- search university catalogues and subscribed databases (ProQuest, Elsevier, Crossref, Gale, Springer, IEEE, etc.) via the Model Context Protocol.

## Features

- **Search** the full university catalogue and Primo Central Index (millions of records)
- **Get record details** including abstract, authors, identifiers, and availability
- **Autocomplete** search suggestions
- **Generate citations** in APA 7th, Harvard, Chicago, IEEE, and Vancouver styles
- **Export** to BibTeX, RIS, or CSV for import into reference managers

## Installation

```bash
git clone https://github.com/jhennig/primo-mcp-server.git
cd primo-mcp-server
pip install -e .
```

## Register in Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "primo": {
      "command": "python",
      "args": ["-m", "primo_mcp_server"]
    }
  }
}
```

Restart Claude Code. The tools will appear as `mcp__primo__primo_search`, etc.

## Tools

| Tool | Description |
|------|-------------|
| `primo_search` | Search the library catalogue with filters (type, date, peer-reviewed) |
| `primo_get_record` | Get full details for a record by ID |
| `primo_suggest` | Autocomplete search suggestions |
| `primo_cite` | Generate formatted citations (APA7, Harvard, Chicago, IEEE, Vancouver) |
| `primo_export` | Export records as BibTeX, RIS, or CSV |

## Usage Examples

From a Claude Code conversation:

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

The defaults point at the University of Alberta Library Search (`https://search.library.ualberta.ca/discovery/search?vid=01UOA_INST:UOA`), so no configuration is needed there. The tab and scope codes are the Primo VE out-of-the-box values (`Everything` / `MyInst_and_CI` and `LibraryCatalog` / `MyInstitution`). If a search fails with HTTP 400, check them against the address bar using the steps above.

### Other institutions

Set the values in the `env` block of the server registration:

```json
{
  "mcpServers": {
    "primo": {
      "command": "python",
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
