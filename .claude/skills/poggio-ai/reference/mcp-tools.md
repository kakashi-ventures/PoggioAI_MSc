# `poggio-ai` MCP server — tool catalog

The `poggio-ai` MCP server lives in `mcp/` in this repo. Each tool returns structured JSON (a dict in Python terms). All path-resolving tools accept an optional `workspace_dir` argument; without it they use `POGGIO_AI_WORKSPACE` or the server's CWD.

---

## Run tools

### `msc_run(task, tier='medium', model=None, budget_usd=None, output_format='markdown', mode='local', counsel=False, math=False, tree_search=False, max_run_seconds=None, workspace_dir=None)`

Launches a pipeline. **Non-blocking** — returns immediately with `{"pid", "command", "stdout_log", "stderr_log", "workspace", "next_steps"}`. The run proceeds in the background.

Use when: the user wants to start a research pipeline and you'll monitor it asynchronously.

### `msc_stop_run(pid)`

SIGTERM the process group of a run launched by `msc_run`. Returns `{"stopped", "pid", "signal"|"error"}`.

### `msc_list_runs(limit=20, workspace_dir=None)`

Returns `{"results_dir", "count", "runs": [...]}`. Each run entry: `{"run_id", "path", "task", "model", "completed", "total_cost_usd", "budget_limit_usd", "current_stage", "last_heartbeat", "manuscripts"}`.

Use when: the user asks "what runs do I have", "show me past runs", or you need a run ID before calling another tool.

### `msc_get_run(run_id, workspace_dir=None)`

Returns the full summary, budget state, token usage, and log file list for one run.

Use when: drilling into a specific run.

### `msc_get_logs(run_id, lines=100, stage=None, workspace_dir=None)`

Returns `{"log_file", "lines_returned", "content"}` — the tail of the newest log. With `stage="..."`, returns that stage's log only.

Use when: investigating why a run failed or what it's doing now.

### `msc_status(workspace_dir=None)`

Returns `{"running": [...], "recent": [...]}`. A run is "running" if its heartbeat is < 5 minutes old.

Use when: the user wants a dashboard view.

### `msc_budget(workspace_dir=None)`

Returns `{"total_spent_usd", "runs", "per_model_usd"}`.

Use when: the user asks about spending.

---

## Campaign tools

### `msc_campaign_init(name, task, budget_usd=50.0, workspace_root=None, output_dir=None, workspace_dir=None)`

Creates a `<slug>_campaign.yaml` with dynamic planning enabled and a task file beside it. Returns `{"campaign_file", "task_file", "workspace_root", "next_steps"}`.

Use when: the user wants to start a multi-stage campaign and hasn't authored a YAML yet.

### `msc_campaign_start(campaign_file, workspace_dir=None)`

Launches a campaign in the background. Returns `{"pid", "campaign_file", "stdout_log", "stderr_log"}`.

### `msc_campaign_status(campaign_file=None, workspace_root=None, workspace_dir=None)`

Pass either `campaign_file` (we'll resolve its workspace) or `workspace_root` directly. Returns stage list, budget, total cost.

Use when: monitoring a campaign.

### `msc_campaign_repair(campaign_file, stage_id, workspace_dir=None)`

Invokes `msc campaign repair <file> <stage_id>` synchronously. Returns `{"returncode", "stdout", "stderr"}` (output tails).

Use when: a stage has failed and the user wants to attempt autonomous repair. Requires `repair.enabled: true` in the spec.

### `msc_campaign_list(workspace_dir=None)`

Returns all `*_campaign.yaml` files in the workspace with their headers.

---

## Standalone subsystems

### `msc_search_papers(query, result_limit=10, fields_of_study=None)`

Direct call into the literature-search subsystem (Semantic Scholar). Returns the parsed JSON response — list of papers with title, authors, venue, year, abstract, citation count.

Requires the `S2_API_KEY` environment variable. **No pipeline runs, no budget consumed.**

Use when: the user wants to find relevant papers without committing to a full pipeline run, or to verify literature coverage before/after a run.

### `msc_counsel_debate(question, system_prompt=None, max_debate_rounds=3, model_specs=None, budget_usd=5.0, model_timeout_seconds=600, workspace_dir=None)`

Run multi-model counsel debate on an arbitrary question. Returns `{"consensus", "sandbox", "rounds", "models_used"}`.

Requires API keys for every provider in `model_specs` (or the default counsel models).

Use when: the user wants a multi-model second opinion on a tricky question, or to test which counsel config works before enabling it in a full pipeline.

**Cost warning**: defaults to a `$5` cap. For longer debates raise `budget_usd` explicitly.

---

## Diagnostics & config

### `msc_doctor(workspace_dir=None)`

Runs `msc doctor`. Returns `{"returncode", "stdout", "stderr"}`. Use this before any first run to verify API keys and dependencies.

### `msc_config_get(key=None)`

Read from `~/.msc/config.yaml`. Pass a dot-path like `"notifications.telegram.enabled"`, or omit to get the full config.

### `msc_llm_config(workspace_dir=None)`

Returns the parsed `.llm_config.yaml` from the workspace.

---

## Resources (read-only)

URIs the client can fetch without calling a tool:

| URI | What it returns |
|---|---|
| `msc://runs/{run_id}/summary` | `run_summary.json` for a run. |
| `msc://runs/{run_id}/budget` | `budget_state.json` for a run. |
| `msc://runs/{run_id}/manuscript` | `final_paper.md` content (or `.tex` if no `.md`). |
| `msc://config/llm` | Workspace `.llm_config.yaml`. |

---

## When to prefer which

| Goal | Tool / approach |
|---|---|
| Run a research pipeline | `msc_run` (non-blocking) → `msc_status` / `msc_get_logs` to monitor |
| Read just the manuscript | `msc://runs/<id>/manuscript` resource |
| Find papers without spending budget | `msc_search_papers` |
| Multi-model second opinion on a question | `msc_counsel_debate` |
| Multi-stage research project | `msc_campaign_init` → `msc_campaign_start` → `msc_campaign_status` |
| Diagnose "is everything wired up" | `msc_doctor` |
| Get total spend so far | `msc_budget` |
| Edit campaign / llm config | Use the `Edit` tool on the YAML file directly — the Skill reference docs describe the schema |
