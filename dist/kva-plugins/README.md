# KVA Claude Code marketplace

This directory is a self-contained **Claude Code plugin marketplace** for Kakashi
Ventures. It packages the complete **PoggioAI toolkit** so any KVA member can install
it into Claude Code with two commands — no copy-pasting skill folders.

```
dist/kva-plugins/
├── .claude-plugin/
│   └── marketplace.json        # makes this dir a marketplace named "kva"
├── poggio-ai/                  # the plugin
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json               # registers the poggio-ai MCP server on install
│   ├── skills/
│   │   ├── poggio-ai/          # drive the MSc research engine
│   │   └── final-review/       # pre-submission anti-hallucination audit (+ scripts)
│   └── commands/
│       ├── analyze_agent_context.md
│       └── refine_agent_prompt.md
├── sync_from_repo.sh           # re-sync from the canonical .claude/ sources
└── README.md                   # this file
```

## What's in the plugin

| Component | Type | What it does |
|-----------|------|--------------|
| `poggio-ai` | skill | Launch/monitor MSc research runs & campaigns, author `campaign.yaml` / `.llm_config.yaml`, read run outputs. |
| `final-review` | skill | The "last gate before submission": verifies every reference against Crossref/OpenAlex, checks figure/caption/label integrity, sweeps for fabricated stats & placeholders, checks AI-disclosure compliance. Includes runnable scripts. |
| `analyze_agent_context` | command | Analyse an MSc agent's instructions for sufficiency/clarity. |
| `refine_agent_prompt` | command | Iteratively improve MSc agent instructions. |
| `poggio-ai` MCP server | mcp | `msc_run`, `msc_search_papers`, `msc_campaign_*`, etc. (requires `poggio-ai-mcp` on PATH — see prerequisites). |

## Install (each KVA member, once)

This marketplace currently lives inside the `poggioai_msc` repo. Point Claude Code at
it either from the published repo or a local checkout:

```text
# From the GitHub repo (recommended once this branch is merged):
/plugin marketplace add kakashi-ventures/poggioai_msc
/plugin install poggio-ai@kva

# Or from a local checkout of this repo:
/plugin marketplace add ./dist/kva-plugins
/plugin install poggio-ai@kva
```

> If you publish to a dedicated org repo (see below), the marketplace source becomes
> `kakashi-ventures/<that-repo>` and the install line is unchanged.

After install, skills are invoked as `/poggio-ai:final-review`, `/poggio-ai:poggio-ai`,
and the commands as `/poggio-ai:analyze_agent_context` etc. Run `/reload-plugins` if you
just changed the files.

## Make it available to ALL of KVA automatically

Add the marketplace and force-enable the plugin via **managed (organization) settings**
or a **shared project `.claude/settings.json`**. Exact keys:

```jsonc
{
  "extraKnownMarketplaces": {
    "kva": {
      "source": { "source": "github", "repo": "kakashi-ventures/poggioai_msc" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "poggio-ai@kva": true
  }
}
```

- Put this in the org-level `managed-settings.json` to apply to every KVA member
  (enterprise/managed scope), **or** in a repo's `.claude/settings.json` to apply to
  everyone working in that repo.
- `strictKnownMarketplaces` (managed scope only) can lock installs to the KVA
  marketplace if you want an allowlist.

## Publishing to a dedicated org repo (optional, cleaner)

If you'd rather host the marketplace in its own repo (e.g.
`kakashi-ventures/claude-plugins`) instead of inside `poggioai_msc`:

1. Create the repo and copy the **contents** of this `dist/kva-plugins/` directory to
   its root (so `.claude-plugin/marketplace.json` sits at the repo root).
2. Push.
3. Members run `/plugin marketplace add kakashi-ventures/claude-plugins` then
   `/plugin install poggio-ai@kva`, and the managed-settings `source.repo` above points
   to that repo instead.

## Prerequisites for the MCP server

The bundled `poggio-ai` MCP server runs the `poggio-ai-mcp` command, which ships with
this repo's Python package. Members who want the MCP tools (not just the skills) must
have it installed and on PATH:

```bash
pip install -e .        # from a checkout of poggioai_msc, or
pip install poggio-ai   # if/when published to an index
```

The skills themselves work without the MCP server; the `final-review` scripts use only
the Python standard library.

## Keeping the package in sync

The canonical sources are `.claude/skills/*` and `.claude/commands/*` in the repo root
(used directly by sessions working inside `poggioai_msc`). After editing any of them,
re-sync the packaged copy and commit:

```bash
bash dist/kva-plugins/sync_from_repo.sh
```
