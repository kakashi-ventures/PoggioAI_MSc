"""Config + diagnostics tools."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from ..workspace import resolve_workspace


def _msc_cmd(args: list[str]) -> list[str]:
    found = shutil.which("msc")
    if found:
        return [found, *args]
    return ["python", "-m", "consortium.cli.main", *args]


def _user_config_path() -> Path:
    return Path.home() / ".msc" / "config.yaml"


def register(mcp) -> None:

    @mcp.tool()
    def msc_doctor(workspace_dir: str | None = None) -> dict[str, Any]:
        """Run `msc doctor` — environment + API key + dependency check.

        Returns the doctor command's stdout/stderr and exit code.
        """
        workspace = resolve_workspace(workspace_dir)
        try:
            result = subprocess.run(
                _msc_cmd(["doctor"]),
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"error": "doctor timed out after 60s"}
        except FileNotFoundError as e:
            return {"error": f"msc CLI not found: {e}"}

    @mcp.tool()
    def msc_config_get(key: str | None = None) -> dict[str, Any]:
        """Read the user config at `~/.msc/config.yaml`.

        Args:
            key: Optional dot-path (e.g. "tier" or "notifications.telegram.enabled").
                 If omitted, returns the full config.
        """
        cfg_path = _user_config_path()
        if not cfg_path.exists():
            return {"error": "no config — run `msc setup` first", "path": str(cfg_path)}
        try:
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
        except (yaml.YAMLError, OSError) as e:
            return {"error": f"could not read config: {e}"}

        if not key:
            return {"path": str(cfg_path), "config": cfg}

        cur: Any = cfg
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return {"path": str(cfg_path), "key": key, "value": None, "found": False}
        return {"path": str(cfg_path), "key": key, "value": cur, "found": True}

    @mcp.tool()
    def msc_llm_config(workspace_dir: str | None = None) -> dict[str, Any]:
        """Read the project's `.llm_config.yaml` from the workspace."""
        workspace = resolve_workspace(workspace_dir)
        for name in (".llm_config.yaml", "llm_config.yaml"):
            p = workspace / name
            if p.exists():
                try:
                    return {"path": str(p), "config": yaml.safe_load(p.read_text())}
                except (yaml.YAMLError, OSError) as e:
                    return {"error": f"could not parse {p}: {e}"}
        return {"error": "no .llm_config.yaml in workspace", "workspace": str(workspace)}
