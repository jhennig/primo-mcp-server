"""Async HTTP client for the Primo REST API."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from primo_mcp_server.config import PrimoConfig
from primo_mcp_server.models import PrimoRecord, SearchResponse


class PrimoAPIError(Exception):
    """Raised when the Primo API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


# Open-ended bounds used when only one end of a year range is given.
# The upper bound allows for forthcoming items dated next year.
_MIN_YEAR = 1000


def _max_year() -> int:
    return date.today().year + 1


def _parse_year(value: str | None, name: str) -> int | None:
    """Parse a YYYY year string, treating blank values as absent."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    if not text.isdigit() or len(text) > 4:
        raise ValueError(f'{name} must be a year in YYYY format, got "{value}".')
    return int(text)


def _year_range(date_from: str | None, date_to: str | None) -> tuple[int, int] | None:
    """Resolve optional start and end years into an inclusive range.

    Returns None when neither end is given. A missing end is left open.
    """
    start = _parse_year(date_from, "date_from")
    end = _parse_year(date_to, "date_to")
    if start is None and end is None:
        return None
    if start is None:
        start = _MIN_YEAR if end is None else min(_MIN_YEAR, end)
    end = _max_year() if end is None else end
    if start > end:
        raise ValueError(
            f"date_from ({start}) must not be later than date_to ({end})."
        )
    return start, end


class PrimoClient:
    """Async client for the Ex Libris Primo public API."""

    def __init__(self, http_client: httpx.AsyncClient, config: PrimoConfig):
        self._http = http_client
        self._config = config

    async def search(
        self,
        query: str,
        field: str = "any",
        scope: str = "everything",
        sort_by: str = "rank",
        limit: int = 10,
        offset: int = 0,
        resource_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        peer_reviewed: bool | None = None,
    ) -> SearchResponse:
        """Search the Primo catalogue.

        Args:
            query: Search terms.
            field: Search field (any, title, creator, sub, isbn, oclcnum).
            scope: "everything" for local + PCI, "catalogue" for local only.
            sort_by: rank, date, or title.
            limit: Number of results (capped at max_results_per_request).
            offset: Pagination offset.
            resource_type: Filter by type (books, articles, journals, etc.).
            date_from: Start year (YYYY).
            date_to: End year (YYYY).
            peer_reviewed: Filter to peer-reviewed items only.

        Returns:
            SearchResponse with parsed records and pagination info.

        Raises:
            ValueError: If a year is not YYYY or the range is reversed.
            PrimoAPIError: If the API request fails.
        """
        cfg = self._config
        limit = min(max(1, limit), cfg.max_results_per_request)
        offset = max(0, offset)

        # Resolve scope to tab + scope params
        if scope == "catalogue":
            tab = cfg.tab_catalogue
            scope_param = cfg.scope_local
        else:
            tab = cfg.tab_everything
            scope_param = cfg.scope_combined

        params: dict[str, Any] = {
            "vid": cfg.vid,
            "tab": tab,
            "scope": scope_param,
            "q": f"{field},contains,{query}",
            "offset": str(offset),
            "limit": str(limit),
            "lang": cfg.language,
            "sortby": sort_by,
            "pcAvailability": "true",
        }

        # Facet filters
        q_include: list[str] = []
        if resource_type:
            q_include.append(f"facet_rtype,exact,{resource_type}")
        if peer_reviewed:
            q_include.append("facet_tlevel,exact,peer_reviewed")

        # Add all qInclude params
        if q_include:
            params["qInclude"] = "|,|".join(q_include)

        # Publication year range. Primo takes a date range as dr_s / dr_e
        # clauses in an advanced query, as YYYYMM values (the same form the
        # Primo VE advanced search sends), so either end may be given alone.
        year_range = _year_range(date_from, date_to)
        if year_range:
            start, end = year_range
            params["q"] += (
                f",AND;dr_s,exact,{start:04d}01,AND;dr_e,exact,{end:04d}12"
            )
            params["mode"] = "advanced"

        data = await self._get("/pnxs", params=params)
        return SearchResponse.from_api_response(data)

    async def get_record(self, record_id: str) -> PrimoRecord | None:
        """Fetch a single record by its Primo record ID.

        Searches by the record ID and returns the first matching result.
        Returns None if not found.
        """
        cfg = self._config
        params: dict[str, Any] = {
            "vid": cfg.vid,
            "tab": cfg.tab_everything,
            "scope": cfg.scope_combined,
            "q": f"any,contains,{record_id}",
            "offset": "0",
            "limit": "5",
            "lang": cfg.language,
        }
        data = await self._get("/pnxs", params=params)
        response = SearchResponse.from_api_response(data)

        # Find exact match by record_id
        for record in response.records:
            if record.record_id == record_id:
                return record

        # If no exact match, return the first result (may be a partial match)
        return response.records[0] if response.records else None

    async def suggest(self, query: str) -> list[str]:
        """Get autocomplete suggestions for a search term."""
        cfg = self._config
        params = {
            "vid": cfg.vid,
            "q": query,
            "lang": cfg.language,
        }
        data = await self._get("/suggest", params=params)

        # Extract suggestion texts
        response = data.get("response", {})
        docs = response.get("docs", [])
        return [doc.get("text", "") for doc in docs if doc.get("text")]

    async def get_records(self, record_ids: list[str]) -> list[PrimoRecord]:
        """Fetch multiple records by their IDs."""
        records = []
        for rid in record_ids:
            record = await self.get_record(rid)
            if record:
                records.append(record)
        return records

    async def _get(self, path: str, params: dict[str, Any]) -> dict:
        """Make a GET request to the Primo API."""
        try:
            response = await self._http.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise PrimoAPIError(
                f"Request timed out after {self._config.request_timeout}s. "
                "The Primo API may be slow or unavailable. Try again shortly.",
            ) from e
        except httpx.ConnectError as e:
            raise PrimoAPIError(
                f"Could not connect to {self._config.base_url}. "
                "Check your network connection and that the Primo API is available.",
            ) from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 400:
                raise PrimoAPIError(
                    f"Bad request (HTTP 400). Check your search query and parameters.",
                    status_code=400,
                ) from e
            elif status >= 500:
                raise PrimoAPIError(
                    f"Primo API server error (HTTP {status}). "
                    "The service may be experiencing issues. Try again later.",
                    status_code=status,
                ) from e
            else:
                raise PrimoAPIError(
                    f"Primo API returned HTTP {status}.",
                    status_code=status,
                ) from e
        except Exception as e:
            raise PrimoAPIError(
                f"Unexpected error querying Primo: {e}",
            ) from e
