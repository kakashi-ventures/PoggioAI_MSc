# poggio-ai-mcp

MCP (Model Context Protocol) server for [PoggioAI/MSc](https://github.com/PoggioAI/PoggioAI_MSc). Exposes the research-automation engine as a set of tools any MCP client can call — Claude Code, Claude Desktop, Cursor, Zed, etc.

## What it gives you

A command-palette of MSc operations, callable from any LLM client:

**Runs**
- `msc_run` — kick off a research pipeline on a question (long-running, non-blocking)
- `msc_list_runs` — enumerate past runs in `results/`
- `msc_get_run` — fetch run summary, budget, manuscript path for one run
- `msc_get_logs` — tail logs from a run
- `msc_status` — show what's currently running
- `msc_budget` — view aggregate spending across all runs

**Campaigns**
- `msc_campaign_init` — create a campaign YAML from a task description
- `msc_campaign_start` — launch a campaign
- `msc_campaign_status` — read `campaign_state.json` for a campaign
- `msc_campaign_repair` — trigger autonomous repair on a failed stage
- `msc_campaign_list` — list campaign YAML files in the workspace

**Standalone subsystems**
- `msc_search_papers` — invoke the literature-search subsystem directly
- `msc_counsel_debate` — run multi-model counsel debate on an arbitrary question

**Diagnostics**
- `msc_doctor` — environment + API key + dependency check
- `msc_config_get` — read a value from `~/.msc/config.yaml`

**Resources** (read-only)
- `msc://runs/{run_id}/summary` — `run_summary.json` for a run
- `msc://runs/{run_id}/manuscript` — final paper (markdown or latex)
- `msc://runs/{run_id}/budget` — `budget_state.json`
- `msc://config/llm` — current `.llm_config.yaml`

## Install

The server lives inside the main PoggioAI/MSc repo. Install in editable mode alongside the engine:

```bash
pip install -e .          # installs poggio-ai (the engine + msc CLI)
pip install -e ./mcp      # installs poggio-ai-mcp (this server)
```

This gives you the `poggio-ai-mcp` console script.

## Add to Claude Code

The repo ships with a `.mcp.json` at the root, so the server is automatically available whenever Claude Code runs in this repo. To add it manually elsewhere:

```bash
claude mcp add --transport stdio poggio-ai -- poggio-ai-mcp
```

## Add to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add:

```json
{
  "mcpServers": {
    "poggio-ai": {
      "command": "poggio-ai-mcp"
    }
  }
}
```

## Workspace

All tools resolve paths relative to a workspace. By default this is the current working directory of the MCP server process. Override with the `POGGIO_AI_WORKSPACE` environment variable:

```bash
POGGIO_AI_WORKSPACE=/path/to/my/research poggio-ai-mcp
```

## How long-running operations work

`msc_run` and `msc_campaign_start` spawn the `msc` / `consortium` CLI as a subprocess and return immediately with a `run_id`. Use `msc_status`, `msc_get_logs`, and `msc_get_run` to poll progress. Cancel a run with `msc_stop_run`.

## License

MIT — same as the parent project.
