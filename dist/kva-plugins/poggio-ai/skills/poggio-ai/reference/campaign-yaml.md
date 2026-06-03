# Campaign YAML schema

Campaigns are multi-stage research workflows. The spec is parsed by `consortium.campaign.spec.CampaignSpec`. Either declare stages explicitly or let the planner generate them dynamically via `planning.enabled: true`.

A campaign must have **stages OR `planning.enabled: true`** — empty stages with planning disabled is a hard error.

---

## Top level

| Key | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `name` | string | yes | inferred from dir | Human-readable campaign title. |
| `workspace_root` | path | yes | `results/campaign` | Output directory. **Must be unique per campaign.** Resolved relative to the YAML's dir. |
| `stages` | list[Stage] | conditional | `[]` | Ordered stage definitions. Empty OK if `planning.enabled: true`. |
| `heartbeat_interval_minutes` | int | no | 30 | Polling interval for stage status. |
| `max_idle_ticks` | int | no | 6 | Auto-exit after N consecutive no-op heartbeats. Prevents zombie campaigns. |
| `max_campaign_hours` | float | no | 0 (unlimited) | Wall-clock cap. `0` means no limit. |
| `counsel_model_timeout_seconds` | int | no | 600 | Per-model timeout for counsel agents within stages. |
| `budget_usd` | float | no | 0 (unlimited) | Campaign-wide USD cap. `0` means no limit. |
| `planning` | PlanningConfig | no | null | See below. |
| `repair` | RepairConfig | no | `{}` | See below. |
| `notification` | NotificationConfig | no | `{}` | See below. |

## `Stage`

| Key | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | string | yes | — | Unique stage identifier (used in `depends_on` / `context_from`). |
| `task_file` | string | yes | `""` | Path to the task text file. Resolved relative to YAML dir. |
| `args` | list[string] | no | `[]` | Extra CLI args passed to `launch_multiagent.py`. |
| `depends_on` | string \| list[string] | no | `[]` | Stage IDs that must complete first. |
| `context_from` | string \| list[string] | no | `[]` | Stage IDs whose memory dirs are inherited. |
| `memory_dirs` | list[string] | no | `[]` | Specific dirs to preserve from previous stages. |
| `success_artifacts` | dict \| list[string] | no | `{}` | Required/optional output files for completion check. |
| `artifact_validators` | dict | no | `{}` | Per-file validation rules (`min_size`, `must_contain`, etc.). |
| `launcher_script` | string | no | null | Override the launcher (default `launch_multiagent.py`). |

## `PlanningConfig`

Set `planning.enabled: true` to let the planner generate stages from a single base task via multi-model counsel debate. Auto-injects two pre-stages: `discovery_plan` and `planning_counsel`.

| Key | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `enabled` | bool | no | false | Turn on dynamic planning. |
| `base_task_file` | string | **yes if enabled** | `""` | Task file for the discovery stage. |
| `max_stages` | int | no | 6 | Hard cap on non-paper stages. |
| `max_parallel` | int | no | 2 | Max concurrent stage executions. |
| `human_review` | bool | no | true | Pause for approval before executing the plan. |
| `planning_budget_usd` | float | no | 5.0 | Budget for planning counsel debate. |
| `planning_timeout_seconds` | int | no | 600 | Timeout for planning phase. |
| `counsel_models` | list[dict] | no | null | Override default counsel models for planning. |
| `stage_type_constraints` | dict | no | `{}` | Override args per stage type. |

## `RepairConfig`

Autonomous repair attempts to fix failed stages by spawning a Claude CLI subprocess with a constrained action set.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | false | Turn on repair. |
| `max_attempts` | int | 2 | Repair tries per failed stage. |
| `launcher` | string | `local` | `local` (blocking) or `slurm` (async HPC). |
| `claude_binary` | string | `auto` | `auto` or explicit path to `claude` CLI. |
| `model` | string | `claude-opus-4-6` | Model for repair execution. |
| `effort` | string | `max` | Effort level: `low` / `medium` / `high` / `max`. |
| `budget_usd` | float | 10.0 | Per-attempt USD cap. |
| `timeout_seconds` | int | 600 | Hard timeout per attempt. |
| `allowed_actions` | list[string] | `[edit_code, fix_config, generate_missing_artifacts, install_dependencies]` | Action whitelist. |
| `two_phase` | bool | true | Plan → review → execute. Disable only if you trust the model fully. |
| `plan_model` | string | null | Planning-phase model (defaults to `model`). |
| `plan_budget_usd` | float | 5.0 | Budget for read-only planning phase. |
| `min_review_score` | int | 7 | Plan must score ≥ this (1–10) to proceed. |
| `review_model` | string | `claude-opus-4-6` | Model for judging the repair plan. |
| `review_temperature` | float | 0.2 | Low temp for deterministic review. |
| `auto_retry_on_timeout` | bool | true | Retry on escalation timeout vs. halt. |

## `NotificationConfig`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `telegram_bot_token` | string | null | Use `${TELEGRAM_BOT_TOKEN}` env reference. |
| `telegram_chat_id` | string | null | Use `${TELEGRAM_CHAT_ID}`. |
| `slack_webhook` | string | null | Slack incoming webhook URL. |
| `ntfy_topic` / `ntfy_server` | string | null / `https://ntfy.sh` | ntfy.sh push notifications. |
| `twilio_account_sid` / `auth_token` / `from_number` / `sms_to_number` | string | null | SMS via Twilio. |
| `on_stage_complete` | bool | true | Notify on stage completion. |
| `on_failure` | bool | true | Notify on failure. |
| `on_heartbeat` | bool | false | Notify on every heartbeat (verbose). |

---

## Validation rules

These are enforced at load time — get them wrong and the campaign won't start.

1. **Stages or planning required**: `len(stages) > 0` or `planning.enabled is True`. Otherwise `ValueError`.
2. **Dependency graph validity**: every `depends_on` and `context_from` reference must point to a valid stage ID. Typos caught early.
3. **Planning gate**: `planning.enabled: true` requires `planning.base_task_file` (non-empty).
4. **Workspace paths**: relative `workspace_root` is resolved against the YAML's parent directory, **not** CWD.
5. **Env var expansion**: notification secrets use `${VAR_NAME}` syntax. Strings not matching this pattern are passed through verbatim.

## Common pitfalls

- **Reusing `workspace_root` across campaigns** corrupts `campaign_state.json` and mixes outputs. Always make it unique.
- **`max_campaign_hours: 0` means no limit**, not "zero hours allowed". Set explicitly for production.
- **Pricing table must cover all models used**, otherwise cost tracking silently fails for unknown models. Cross-check against `.llm_config.yaml` → `budget.pricing`.
- **`planning.enabled: true` with `stages: []`** auto-generates `discovery_plan` and `planning_counsel` — don't define those manually.
- **Repair `model: claude-opus-4-6`** is expensive. Switch to `claude-sonnet-4-6` for YAML-edit-style repairs to save 5×.
