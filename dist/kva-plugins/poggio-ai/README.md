# PoggioAI Toolkit (Claude Code plugin)

The complete PoggioAI/MSc toolkit, packaged for installation into any Claude Code
session via the KVA marketplace.

## Contents

- **`skills/poggio-ai`** — drive the MSc multi-agent research engine: launch & monitor
  runs and campaigns, author `campaign.yaml` / `.llm_config.yaml`, interpret run
  outputs. Reference docs + starter templates included.
- **`skills/final-review`** — pre-submission integrity audit. Catches the
  Generative-AI failure modes that get papers desk-rejected or retracted: fabricated
  references, citation↔claim mismatches, captions for not-reported figures, fabricated
  statistics, missing AI-disclosure. Ships two stdlib-only scripts:
  - `scripts/verify_references.py` — verify every reference against Crossref + OpenAlex.
  - `scripts/check_figures.py` — figure/table/label/ref integrity for LaTeX.
- **`commands/`** — `analyze_agent_context`, `refine_agent_prompt` for tuning MSc agents.
- **`.mcp.json`** — registers the `poggio-ai` MCP server (needs `poggio-ai-mcp` on PATH).

## Install

```text
/plugin marketplace add kakashi-ventures/poggioai_msc
/plugin install poggio-ai@kva
```

Then invoke `/poggio-ai:final-review`, `/poggio-ai:poggio-ai`, etc.

See `../README.md` (the marketplace README) for org-wide auto-enablement and publishing
to a dedicated repo.

## Quick start: audit a paper before submitting

```bash
# 1. references (the highest-value, fully-automated check)
python skills/final-review/scripts/verify_references.py path/to/refs.bib \
    --mailto you@kakashi.ventures --out references_audit.md

# 2. figures / captions / labels
python skills/final-review/scripts/check_figures.py path/to/paper.tex --figdir figures/
```

A `NOT FOUND` reference is treated as fabricated until a manual search proves otherwise.
