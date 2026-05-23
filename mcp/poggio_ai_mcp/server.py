"""poggio-ai-mcp server — FastMCP entry point.

Registers all tool groups and resources, then runs over stdio. Spawn via
the `poggio-ai-mcp` console script or `python -m poggio_ai_mcp`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import resources, tools

mcp = FastMCP(
    name="poggio-ai",
    instructions=(
        "PoggioAI/MSc research-automation engine. Tools are grouped by purpose:\n"
        "  • msc_run / msc_status / msc_list_runs / msc_get_run / msc_get_logs — "
        "drive and inspect research pipelines.\n"
        "  • msc_campaign_init / start / status / repair / list — multi-stage campaigns.\n"
        "  • msc_search_papers — Semantic Scholar literature search.\n"
        "  • msc_counsel_debate — multi-model expert debate on an arbitrary question.\n"
        "  • msc_doctor / msc_config_get / msc_llm_config — diagnostics + config.\n"
        "\n"
        "Long-running ops (msc_run, msc_campaign_start) return a PID immediately and "
        "continue in the background — poll with msc_status / msc_get_logs.\n"
        "\n"
        "All tools resolve paths against the workspace, which defaults to the "
        "POGGIO_AI_WORKSPACE env var or the server's CWD. Override per-call with "
        "the workspace_dir argument."
    ),
)

tools.runs.register(mcp)
tools.campaigns.register(mcp)
tools.lit_search.register(mcp)
tools.counsel.register(mcp)
tools.config.register(mcp)
resources.register(mcp)


def main() -> None:
    """Console-script entry point: runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
