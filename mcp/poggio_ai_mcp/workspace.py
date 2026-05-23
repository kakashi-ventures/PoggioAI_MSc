"""Workspace resolution for poggio-ai-mcp.

The MCP server runs as a subprocess of the MCP client and inherits its CWD.
This module centralises workspace path resolution so every tool agrees on:

  - where to find `results/`
  - where to find campaign YAML files
  - where to find `.llm_config.yaml`

Resolution order:
  1. explicit `workspace_dir` argument passed to a tool
  2. `POGGIO_AI_WORKSPACE` environment variable
  3. current working directory of the server process
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_workspace(workspace_dir: str | None = None) -> Path:
    if workspace_dir:
        return Path(workspace_dir).expanduser().resolve()
    env = os.environ.get("POGGIO_AI_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd().resolve()


def results_dir(workspace_dir: str | None = None) -> Path:
    return resolve_workspace(workspace_dir) / "results"


def run_dir(run_id: str, workspace_dir: str | None = None) -> Path:
    """Resolve a run_id to its on-disk directory.

    A run_id may be either the bare directory name (e.g. `consortium_2026...`)
    or an absolute path. Returns the absolute path either way.
    """
    p = Path(run_id).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (results_dir(workspace_dir) / run_id).resolve()
