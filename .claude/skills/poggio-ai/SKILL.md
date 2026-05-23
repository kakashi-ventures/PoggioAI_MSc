---
name: poggio-ai
description: Drive the PoggioAI/MSc research-automation engine — launch and monitor research runs and campaigns via the `msc` CLI or the `poggio-ai` MCP server, author and edit `campaign_template.yaml` / `.llm_config.yaml` files, and interpret run outputs (manuscripts, validation gate failures, counsel transcripts, budget states). Use this when the user mentions PoggioAI, MSc, "research campaign", "campaign.yaml", `msc run`, multi-agent research pipelines, literature review automation, counsel debate, or working inside this repo's `results/` directory.
allowed-tools: Bash Read Edit Write Grep Glob
---

# PoggioAI / MSc

**MSc** (Multi-agent Scientific Collaboration) is an open-source research-automation system that turns a research question into a submission-ready manuscript. It orchestrates ~22 specialist agent nodes through a LangGraph pipeline with stage-level validation gates, multi-model counsel debate, tree-search exploration, and multi-stage campaign orchestration.

This skill teaches you how to drive MSc effectively — through the `msc` CLI, the `poggio-ai` MCP server, or by directly editing the YAML configs.

## When to apply

Apply this skill whenever you're:
- Running, monitoring, or debugging an MSc pipeline (`msc run`, `msc status`, `msc logs`)
- Authoring or editing `*_campaign.yaml` (multi-stage research campaigns)
- Authoring or editing `.llm_config.yaml` (model, budget, counsel, persona-council settings)
- Reading run outputs in `results/consortium_<timestamp>_<task>/`
- Interpreting counsel-debate transcripts or validation-gate failures
- Using the `poggio-ai` MCP server tools (`msc_run`, `msc_campaign_*`, `msc_search_papers`, etc.)

## The two operating surfaces

**CLI (`msc`)** — for human-driven and shell-driven workflows. See `${CLAUDE_SKILL_DIR}/reference/cli-reference.md` for the full subcommand surface.

**MCP server (`poggio-ai`)** — for Claude / LLM-driven workflows. Tools mirror the CLI but return structured JSON instead of Rich-formatted terminal output. See `${CLAUDE_SKILL_DIR}/reference/mcp-tools.md` for the full tool list and `when-to-use-which` guidance.

Both surfaces resolve paths against the same workspace. Default workspace is the project root (where `.llm_config.yaml` and `results/` live). The MCP server can be redirected with the `POGGIO_AI_WORKSPACE` env var.

## Workflow shortcuts

**"Run a research pipeline on question X"** — Most common request.
1. Verify environment: `msc doctor` (or `msc_doctor` MCP tool). Check API keys, Python version, optional deps.
2. Confirm budget: read `.llm_config.yaml` `budget.usd_limit` and `~/.msc/config.yaml`. Don't proceed if the limit looks misconfigured for the task size.
3. Launch: `msc run "<question>" --tier medium` (or `msc_run` MCP tool). The tier sets model + budget defaults — see CLI reference for the tier table.
4. Monitor: `msc status`, `msc logs --follow`, or `msc_get_logs`. The run writes to `results/consortium_<stamp>_<slug>/`.
5. Read result: `final_paper.md` or `.tex` in the run directory. The `run_summary.json` records total cost and completion status.

**"Set up a multi-stage research campaign"** — Use a campaign when the work needs multiple coordinated pipeline runs (e.g., discovery → theory → experiments → writeup), or when you want planner-driven stage generation.
1. Author the YAML: copy `${CLAUDE_SKILL_DIR}/templates/campaign-starter.yaml` or use `msc campaign init`. The schema is in `${CLAUDE_SKILL_DIR}/reference/campaign-yaml.md`.
2. Validate: `msc campaign status <file>` won't run anything but parses the spec — use it as a syntax check before launch.
3. Launch: `msc campaign start <file>`. This kicks off a heartbeat loop that orchestrates stages.
4. Monitor: `msc campaign status <file>` returns the stage DAG and per-stage status. Failed stages can be repaired with `msc campaign repair <file> <stage_id>` if `repair.enabled: true` in the spec.

**"Tune the model / budget / counsel config"** — Edit `.llm_config.yaml`. Schema in `${CLAUDE_SKILL_DIR}/reference/llm-config-yaml.md`. Common changes:
- Switch the main model: `main_agents.model: claude-opus-4-6` (best quality) or `claude-sonnet-4-6` (balanced).
- Raise/lower budget: `budget.usd_limit` in USD.
- Enable counsel debate: `counsel.enabled: true` — but counsel requires API keys for *every* listed provider. If keys are missing, counsel will hard-fail.
- Use per-agent tiers: `per_agent_models.enabled: true` — assigns cheaper models to simpler agents (e.g., proofreading uses an economy tier).

**"Read this run's outputs"** — See `${CLAUDE_SKILL_DIR}/reference/run-outputs.md` for the artifact layout. Key files in each run directory:
- `final_paper.{md|tex|pdf}` — the manuscript.
- `run_summary.json` — task, model, total cost, completion flag.
- `budget_state.json` — token + USD spend per model.
- `logs/<stage>.log` — per-stage transcripts.
- `.progress_heartbeat` — live status when running.

## Hard rules

- **Never edit files inside `results/<run_id>/` while a run is in progress.** The heartbeat-staleness threshold is 5 minutes — check `.progress_heartbeat` timestamp before assuming a run is dead.
- **Never raise `budget.usd_limit` without telling the user.** Budgets are intentional cost caps; quietly bumping them surprises the user with bills.
- **Counsel requires every provider's API key.** Before enabling `counsel.enabled: true`, verify the user has keys for all models listed under `counsel.models`. If any are missing, counsel will halt the pipeline.
- **Campaign `workspace_root` must be unique per campaign.** Reusing a workspace mixes outputs across campaigns and corrupts `campaign_state.json`.
- **Don't fabricate run IDs or campaign names.** When the user asks about a specific run, list runs first (`msc runs` or `msc_list_runs`) to confirm it exists.

## Reference docs

Load these when you need precision:

- `reference/cli-reference.md` — every `msc` subcommand, flag, and artifact location.
- `reference/campaign-yaml.md` — full campaign YAML schema, validation rules, common pitfalls.
- `reference/llm-config-yaml.md` — `.llm_config.yaml` schema, model registry, budget enforcement model.
- `reference/run-outputs.md` — what each artifact file means and how to read it.
- `reference/mcp-tools.md` — the `poggio-ai` MCP server's tool catalog and when to prefer each one.

Templates:
- `templates/campaign-starter.yaml` — minimal campaign with dynamic planning and autonomous repair.
- `templates/llm-config-starter.yaml` — safe-defaults `.llm_config.yaml`.
