# `msc` CLI reference

The `msc` command is the primary user-facing interface to the PoggioAI/MSc engine. Entry point: `consortium.cli.main:cli` (Click-based).

All commands accept these **global flags**: `--verbose/-v`, `--quiet/-q`, `--no-banner`, `--config-dir <dir>` (default `~/.msc`), `--version`.

---

## Setup & diagnostics (quick)

| Command | What it does | Notable flags |
|---|---|---|
| `msc setup` | Interactive setup: API keys, tier, notifications. Writes `~/.msc/config.yaml`, `~/.msc/.env`, and a reference copy of `.llm_config.yaml`. | `--non-interactive`, `--migrate` |
| `msc doctor` | Validates Python version, API keys, LaTeX, Playwright, SLURM, `.llm_config.yaml`. No artifacts. | — |
| `msc config list` / `get <key>` / `set <key> <value>` / `edit` / `path` | Read/write `~/.msc/config.yaml`. Dot-notation supported (`notifications.telegram.enabled`). | — |
| `msc install <extra>` | `pip install poggio-ai[<extra>]`. Extras: `docs`, `web`, `experiment`, `observability`, `latex`, `all`. | — |
| `msc notify setup` / `notify test --channel [telegram|slack]` | Configure & test notification channels. | — |

## Running a research pipeline

### `msc run <task>` — the workhorse

Executes the research pipeline on a single task. Long-running.

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `--tier/-t` | `budget` `light` `medium` `pro` `max` | `medium` | Sets model + budget defaults. See tier table below. |
| `--task-file/-f` | path | — | Read task from a file instead of CLI arg. |
| `--model/-m` | str | (from tier) | Override the main agent model. |
| `--budget/-b` | int (USD) | (from tier) | Override the hard budget cap. |
| `--output-format/-o` | `markdown` `latex` | `markdown` | Final manuscript format. |
| `--mode` | `local` `tinker` `hpc` | `local` | Local subprocess, Tinker-backed, or SLURM HPC. |
| `--dry-run` | bool | false | Validate config without spending. |
| `--counsel/--no-counsel` | bool | tier-dependent | Multi-model oversight. |
| `--math/--no-math` | bool | tier-dependent | Enable math agents (formalization, proof transcription). |
| `--tree-search/--no-tree-search` | bool | tier-dependent | Enable tree-search exploration. |
| `--max-run-seconds` | int | — | Hard wall-clock timeout. |
| `--stream/--no-stream` | bool | true | Display streaming progress. |

**Tier defaults** (rough; check `consortium/cli/core/tiers.py` for current values):
- `budget` — economy models, low budget, no counsel/math/tree-search.
- `light` — sonnet, moderate budget, no counsel.
- `medium` — sonnet, default budget, math on, no counsel.
- `pro` — opus, larger budget, counsel + math on.
- `max` — opus, large budget, everything on.

**Artifacts**: `results/consortium_<YYYYMMDD-HHMMSS>_<task_slug>/` containing `final_paper.{md|tex|pdf}`, `run_summary.json`, `budget_state.json`, `run_token_usage.json`, `logs/*.log`, `.progress_heartbeat`.

### `msc resume [run_id]`

Resume a checkpointed run.

- `--start-from <stage>` — override the resume point.
- `--task <text>` — override the task.

Resumes from any `results/consortium_*/` directory.

## Inspecting runs

| Command | What it shows |
|---|---|
| `msc runs [-n N]` | List the last N runs (default 10) — task, model, cost, completion. |
| `msc status [--all]` | Currently-running pipelines (local + SLURM) and recent campaigns. |
| `msc logs [run_id] [-f] [-n N] [--stage S]` | Tail logs from a run. `--follow` streams. `--stage` filters to one stage. |
| `msc budget` | Aggregate USD spending across all runs in `results/`. |

## Multi-stage campaigns

The `msc campaign` group manages YAML-defined campaigns with stage DAGs, heartbeat loops, autonomous repair, and dynamic planning.

| Command | What it does |
|---|---|
| `msc campaign init --name <n> --task <t> --budget <b> --output-dir <d>` | Generate a `<slug>_campaign.yaml`. |
| `msc campaign start <campaign_file>` | Launch the campaign (heartbeat loop, stage scheduler). |
| `msc campaign status <campaign_file>` | Print stage statuses, budget, total cost. Reads `campaign_state.json`. |
| `msc campaign repair <campaign_file> <stage_id>` | Trigger autonomous repair on a failed stage. |
| `msc campaign list` | List `*_campaign.yaml` files in the CWD. |

Campaign artifacts live under the `workspace_root` declared in the spec (default `results/<slug>/`). The state file is `campaign_state.json`.

## OpenClaw (autonomous oversight gateway)

| Command | What it does |
|---|---|
| `msc openclaw setup` | Interactive config wizard. Writes `~/.openclaw/openclaw.json`. |
| `msc openclaw start --background` / `--foreground` | Launch the gateway. |
| `msc openclaw stop` / `status` | Stop or check the gateway. |

## Artifact layout

```
~/.msc/
├── config.yaml          # tier, model, budget_usd, notifications, autonomous_mode
├── .env                 # API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...)
└── llm_config.yaml      # reference copy (real .llm_config.yaml lives in project root)

<project_root>/
├── .llm_config.yaml     # model, budget, counsel, persona_council, per_agent_models
├── *_campaign.yaml      # campaign specs
└── results/
    ├── consortium_<stamp>_<slug>/
    │   ├── final_paper.{md|tex|pdf}
    │   ├── run_summary.json
    │   ├── budget_state.json
    │   ├── run_token_usage.json
    │   ├── logs/*.log
    │   └── .progress_heartbeat
    └── <campaign_slug>/
        ├── campaign_state.json
        └── <stage_id>/...
```
