#!/usr/bin/env bash
# Re-sync the packaged plugin from the canonical sources in this repo's .claude/.
#
# The source of truth is .claude/skills/* and .claude/commands/* (used directly by
# sessions working *inside* this repo). This script copies them into the distributable
# plugin under dist/kva-plugins/poggio-ai/ so the published KVA marketplace stays in
# step. Run it whenever you edit a skill or command, then commit dist/.
#
# Usage:  bash dist/kva-plugins/sync_from_repo.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_SKILLS="$REPO_ROOT/.claude/skills"
SRC_CMDS="$REPO_ROOT/.claude/commands"
PLUG="$REPO_ROOT/dist/kva-plugins/poggio-ai"

echo "Repo root: $REPO_ROOT"

# Skills bundled in the plugin (add new ones here).
SKILLS=(poggio-ai final-review)
# Commands bundled in the plugin.
COMMANDS=(analyze_agent_context.md refine_agent_prompt.md)

rm -rf "$PLUG/skills" "$PLUG/commands"
mkdir -p "$PLUG/skills" "$PLUG/commands"

for s in "${SKILLS[@]}"; do
  echo "  skill  -> $s"
  cp -R "$SRC_SKILLS/$s" "$PLUG/skills/"
done
for c in "${COMMANDS[@]}"; do
  echo "  command-> $c"
  cp "$SRC_CMDS/$c" "$PLUG/commands/"
done

# Keep the bundled MCP config aligned with the repo's .mcp.json.
cp "$REPO_ROOT/.mcp.json" "$PLUG/.mcp.json"

# Ensure scripts stay executable.
find "$PLUG/skills" -name '*.py' -exec chmod +x {} +

echo "Done. Review changes under dist/kva-plugins/ and commit."
