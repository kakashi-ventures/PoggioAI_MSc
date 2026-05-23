"""Literature search tool.

Wraps `consortium.toolkits.ideation.paper_search_tool.PaperSearchTool` —
Semantic Scholar query, no pipeline overhead.

Requires the `S2_API_KEY` environment variable.
"""

from __future__ import annotations

import json
from typing import Any


def register(mcp) -> None:

    @mcp.tool()
    def msc_search_papers(
        query: str,
        result_limit: int = 10,
        fields_of_study: str | None = None,
    ) -> dict[str, Any]:
        """Search Semantic Scholar for academic papers.

        Direct call into the literature-search subsystem MSc uses for its
        own lit-review stage — no pipeline runs, no budget consumption.

        Args:
            query: Free-text search query.
            result_limit: Max papers to return (default 10).
            fields_of_study: Comma-separated list, e.g. "Computer Science,Physics".

        Requires the `S2_API_KEY` environment variable.
        """
        try:
            from consortium.toolkits.ideation.paper_search_tool import PaperSearchTool
        except ImportError as e:
            return {"error": f"PoggioAI engine not installed: {e}"}

        tool = PaperSearchTool()
        raw = tool._run(query=query, result_limit=result_limit, fields_of_study=fields_of_study)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_response": raw}
