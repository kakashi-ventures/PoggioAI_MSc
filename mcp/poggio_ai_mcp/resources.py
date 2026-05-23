"""Read-only MCP resources for run artifacts.

Exposes paths under `msc://...` URIs so clients can browse them without
calling a tool. Resources are good for things an LLM wants to *read*; tools
are for *actions*.
"""

from __future__ import annotations

from pathlib import Path

from .workspace import resolve_workspace, run_dir


def register(mcp) -> None:

    @mcp.resource("msc://runs/{run_id}/summary")
    def run_summary(run_id: str) -> str:
        """Return run_summary.json for a run as a string."""
        path = run_dir(run_id) / "run_summary.json"
        if not path.exists():
            return f'{{"error": "not found", "path": "{path}"}}'
        return path.read_text()

    @mcp.resource("msc://runs/{run_id}/budget")
    def run_budget(run_id: str) -> str:
        """Return budget_state.json for a run as a string."""
        path = run_dir(run_id) / "budget_state.json"
        if not path.exists():
            return f'{{"error": "not found", "path": "{path}"}}'
        return path.read_text()

    @mcp.resource("msc://runs/{run_id}/manuscript")
    def run_manuscript(run_id: str) -> str:
        """Return the final manuscript content (markdown preferred, then latex)."""
        base = run_dir(run_id)
        for ext in ("md", "tex"):
            p = base / f"final_paper.{ext}"
            if p.exists():
                return p.read_text()
        return f"# Not found\n\nNo final_paper.md or .tex in {base}\n"

    @mcp.resource("msc://config/llm")
    def llm_config() -> str:
        """Return the workspace's .llm_config.yaml."""
        for name in (".llm_config.yaml", "llm_config.yaml"):
            p = resolve_workspace() / name
            if p.exists():
                return p.read_text()
        return "# No .llm_config.yaml in workspace\n"
