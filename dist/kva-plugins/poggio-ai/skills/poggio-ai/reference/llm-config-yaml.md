# `.llm_config.yaml` schema

`.llm_config.yaml` lives in the project root (gitignored). It controls model selection, budgets, multi-model counsel, persona council, and per-agent model tiering. Parsed by `consortium.config.load_llm_config()`.

A reference copy of safe defaults is at `.llm_config.yaml.example`.

---

## `main_agents`

The default model for every agent unless overridden by `per_agent_models`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `model` | string | `claude-sonnet-4-6` | Must be in the model registry (`consortium/models.py`). Common: `claude-opus-4-6`, `claude-sonnet-4-6`, `gpt-5`, `gpt-5.4`, `gemini-3-pro-preview`. |
| `reasoning_effort` | string | `high` | Claude only. `low` / `medium` / `high` / `max`. |
| `budget_tokens` | int | 128000 | Max extended-thinking tokens. Engine auto-bumps `max_tokens` to satisfy `max_tokens > budget_tokens + 2048`. |

## `budget`

Hard cost cap enforced via a monkey-patched `litellm.completion`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `usd_limit` | float | 25 | Hard USD cap. Pipeline halts when reached. |
| `hard_stop` | bool | true | If false, log a warning instead of halting. |
| `fail_closed` | bool | true | Treat corrupted budget state as over-budget. Safe default. |
| `pricing` | dict | (see below) | Per-model input/output cost per 1K tokens. Empty disables cost enforcement. |

**Pricing format**:
```yaml
budget:
  pricing:
    claude-opus-4-6:
      input_per_1k: 0.005
      output_per_1k: 0.025
    claude-sonnet-4-6:
      input_per_1k: 0.003
      output_per_1k: 0.015
    # ... one entry per model used anywhere in the config
```

Missing a model from `pricing` makes cost tracking fail silently for that model.

## `counsel`

Multi-model debate. **Disabled by default**. Requires API keys for *every* listed provider.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | false | Master switch. |
| `max_debate_rounds` | int | 3 | Rounds of cross-critique. |
| `synthesis_model` | string | `claude-sonnet-4-6` | Final consensus model. |
| `models` | list[dict] | (see below) | Each entry: `{model, reasoning_effort?, verbosity?, thinking_budget?}`. |

Sample:
```yaml
counsel:
  enabled: true
  max_debate_rounds: 3
  synthesis_model: claude-sonnet-4-6
  models:
    - model: claude-sonnet-4-6
      reasoning_effort: high
    - model: gpt-5.4
      reasoning_effort: high
      verbosity: high
    - model: gemini-3-pro-preview
      thinking_budget: 131072
```

## `persona_council`

V2-pipeline persona-council node settings.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `max_debate_rounds` | int | 3 | Persona debate rounds. |
| `synthesis_model` | string | `claude-sonnet-4-6` | Synthesis model. |

## `duality_check`

| Key | Type | Default |
|---|---|---|
| `model` | string | `claude-sonnet-4-6` |

## `per_agent_models`

Assign different models to different agents (cost optimization).

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | false | When false, all agents use `main_agents.model`. |
| `tiers` | dict | (see below) | Named tiers, each with `{model, reasoning_effort, budget_tokens?}`. |
| `agent_tiers` | dict | (see below) | Map agent name → tier name. |

Sample:
```yaml
per_agent_models:
  enabled: true
  tiers:
    opus:
      model: claude-opus-4-6
      reasoning_effort: high
      budget_tokens: 128000
    sonnet:
      model: claude-sonnet-4-6
      reasoning_effort: high
      budget_tokens: 128000
    economy:
      model: claude-sonnet-4-6
      reasoning_effort: low
  agent_tiers:
    literature_review_agent: sonnet
    writeup_agent: sonnet
    proofreading_agent: economy
    # ... agent name → tier
```

Common agent names: `literature_review_agent`, `math_literature_agent`, `experiment_literature_agent`, `formalize_results_agent`, `writeup_agent`, `reviewer_agent`, `experimentation_agent`, `proofreading_agent`, `proof_transcription_agent`, `experiment_transcription_agent`, `resource_preparation_agent`, `followup_lit_review`.

## `run_experiment_tool`

Per-role models inside the experiment-execution subsystem (AI-Scientist-v2 integration).

```yaml
run_experiment_tool:
  code_model: claude-sonnet-4-6
  feedback_model: claude-sonnet-4-6
  vlm_model: claude-sonnet-4-6
  report_model: claude-sonnet-4-6
```

---

## Validation rules

1. **`main_agents` required**: must be a dict with a `model` key. Missing → warning, fallback to defaults.
2. **`budget.usd_limit`** required for cost enforcement. Missing → enforcement disabled (no halt on overspend).
3. **`budget.pricing`** must include every model used. Missing entries → cost tracking fails silently for those models.
4. **Claude thinking invariant**: `max_tokens` must exceed `budget_tokens + 2048`. Engine auto-bumps `max_tokens` to satisfy this.
5. **Counsel API keys**: enabling counsel requires keys for every listed provider. Missing keys → hard fail at first counsel call.

## Common edits, quick recipes

**Switch to Opus for quality, sonnet was too weak**:
```yaml
main_agents:
  model: claude-opus-4-6
  reasoning_effort: high
```

**Raise budget for a real run**:
```yaml
budget:
  usd_limit: 100   # was 25
```

**Enable counsel** (verify keys first):
```yaml
counsel:
  enabled: true
```

**Cheap pass on a draft** — keep main as opus, downgrade simple agents:
```yaml
per_agent_models:
  enabled: true
  agent_tiers:
    proofreading_agent: economy
    proof_transcription_agent: economy
    experiment_transcription_agent: economy
    resource_preparation_agent: economy
```
