# Reading MSc run outputs

Every `msc run` invocation creates a directory under `results/`:

```
results/consortium_<YYYYMMDD-HHMMSS>_<task_slug>/
├── final_paper.md           # primary manuscript output
├── final_paper.tex          # if --output-format latex
├── final_paper.pdf          # if LaTeX was installed and compilation succeeded
├── run_summary.json         # task, model, completion status, total cost
├── budget_state.json        # token + USD spend per model
├── run_token_usage.json     # raw token counts per agent call
├── .progress_heartbeat      # live status JSON, updated by the runner
├── consortium_*.out         # combined stdout/stderr from the pipeline driver
├── logs/                    # per-stage transcripts
│   ├── persona_council.log
│   ├── literature_review_agent.log
│   ├── brainstorm_agent.log
│   ├── formalize_goals_agent.log
│   ├── theory_track/...
│   ├── experiment_track/...
│   ├── synthesis_agent.log
│   ├── writeup_agent.log
│   └── reviewer_agent.log
├── persona_council/...      # persona council artifacts (debate transcripts, synthesis)
├── counsel_sandboxes/...    # if counsel was enabled: per-model sandboxes for each stage
├── tree_search/...          # if --tree-search: search tree, pruning logs
└── repair_log.json          # if any stage was auto-repaired
```

---

## `run_summary.json`

Most useful first-look file. Shape:

```json
{
  "task": "Original research question",
  "model": "claude-sonnet-4-6",
  "tier": "medium",
  "completed": true,
  "started_at": "2026-05-23T10:14:22Z",
  "finished_at": "2026-05-23T11:47:08Z",
  "total_cost_usd": 12.41,
  "stages_completed": ["persona_council", "literature_review_agent", "brainstorm_agent", "..."],
  "final_paper": "final_paper.md",
  "manuscript_format": "markdown"
}
```

**`completed: false`** means the pipeline halted early — check `.progress_heartbeat.stage` for where, and `logs/<that_stage>.log` for why.

## `budget_state.json`

Authoritative cost record:

```json
{
  "spent_usd": 12.41,
  "limit_usd": 25.0,
  "hard_stop": true,
  "per_model": {
    "claude-sonnet-4-6": {
      "input_tokens": 145000,
      "output_tokens": 38000,
      "cost_usd": 12.41
    }
  },
  "exceeded": false
}
```

If `exceeded: true`, the budget cap was hit and the run halted mid-pipeline.

## `.progress_heartbeat`

Live status — updated every few seconds while the pipeline runs:

```json
{
  "stage": "writeup_agent",
  "stage_index": 14,
  "total_stages": 22,
  "timestamp": "2026-05-23T11:43:09Z",
  "elapsed_seconds": 5327
}
```

**Heartbeat staleness threshold is 5 minutes**. Timestamp older than that means the runner likely crashed. Look for an `*.err` file or the tail of `consortium_*.out`.

## `logs/<stage>.log`

Per-stage transcript. Each agent's prompts + responses, tool calls + results, validation checks. Format is plain text — `grep` works fine.

To find why a stage failed, tail its log:
```bash
tail -200 results/consortium_*/logs/<failing_stage>.log
```

## `counsel_sandboxes/`

If counsel was enabled, each stage that used it has a subdirectory:

```
counsel_sandboxes/
└── literature_review_agent/
    ├── model_0_claude-sonnet-4-6/
    │   └── (full sandbox: this model's working copy)
    ├── model_1_gpt-5.4/
    ├── model_2_gemini-3-pro-preview/
    ├── debate_round_1.json
    ├── debate_round_2.json
    ├── debate_round_3.json
    └── synthesis.json
```

`synthesis.json` is the final consensus that was promoted back to the main workspace. Individual model outputs are useful for debugging when consensus quality is suspect.

## Validation-gate failures

Each stage has success criteria. Failures show up as:

1. A non-completion marker in `run_summary.json` (`completed: false`, last stage = the failing one).
2. A `validation_failures` list in the stage's log, or in `repair_log.json` if repair was enabled.
3. For campaigns: `campaign_state.json` shows the stage as `failed` with a `failure_reason`.

Common failure modes:
- **Missing artifacts**: the stage didn't produce a file declared in `success_artifacts`.
- **Artifact validator failed**: file existed but was too small or missing required content (`must_contain` rule).
- **Budget exceeded**: `budget_state.exceeded: true`. Pipeline halts cleanly mid-stage.
- **Counsel hard fail**: an API key was missing for one of the counsel models. Fix in `.llm_config.yaml` or `~/.msc/.env`.

## Cleaning up

Old runs accumulate. Safe to delete:
- Entire `results/consortium_*/` directories you no longer need (after copying out `final_paper.*`).
- `counsel_sandboxes/` within a completed run (the consensus is already in the stage outputs).

Do **not** delete:
- `~/.msc/` (your API keys + tier config).
- Active campaign workspaces (where `campaign_state.json` is being updated).
