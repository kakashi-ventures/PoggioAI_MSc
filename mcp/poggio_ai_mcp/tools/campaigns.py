"""Campaign-management tools.

Campaigns are multi-stage research workflows defined in YAML. The engine
provides a `consortium.campaign` package for spec loading and status reading;
campaign launches go through the `msc campaign` CLI (subprocess).
"""

from __future__ import annotations

import json
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


def _read_status(workspace_root: Path) -> dict[str, Any] | None:
    """Read campaign_state.json (or campaign_status.json) from a workspace."""
    for name in ("campaign_state.json", "campaign_status.json"):
        p = workspace_root / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                return None
    return None


def register(mcp) -> None:

    @mcp.tool()
    def msc_campaign_init(
        name: str,
        task: str,
        budget_usd: float = 50.0,
        workspace_root: str | None = None,
        output_dir: str | None = None,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Create a new campaign YAML spec with planner-driven stage discovery.

        Writes a `<slug>_campaign.yaml` next to the workspace and returns its
        path. The spec uses dynamic planning by default (planner generates the
        stage DAG from the task file).

        Args:
            name: Human-readable campaign name.
            task: The research task description. Will be written to a task
                  file referenced by the campaign spec.
            budget_usd: Campaign-wide hard budget cap.
            workspace_root: Path for campaign outputs (default: results/<slug>).
            output_dir: Where to write the YAML file (default: workspace).
            workspace_dir: Override the workspace root.
        """
        workspace = resolve_workspace(workspace_dir)
        slug = name.lower().replace(" ", "_")[:60]
        ws_root = workspace_root or f"results/{slug}"
        out_root = Path(output_dir).resolve() if output_dir else workspace
        out_root.mkdir(parents=True, exist_ok=True)

        task_dir = out_root / "automation_tasks"
        task_dir.mkdir(exist_ok=True)
        task_file = task_dir / f"{slug}_task.txt"
        task_file.write_text(task)

        spec = {
            "name": name,
            "workspace_root": ws_root,
            "heartbeat_interval_minutes": 15,
            "max_idle_ticks": 6,
            "max_campaign_hours": 96,
            "counsel_model_timeout_seconds": 3600,
            "budget_usd": budget_usd,
            "planning": {
                "enabled": True,
                "base_task_file": str(task_file.relative_to(out_root)),
                "max_stages": 6,
                "max_parallel": 2,
                "human_review": True,
                "planning_budget_usd": 5.0,
                "planning_timeout_seconds": 600,
            },
            "stages": [],
            "repair": {
                "enabled": True,
                "max_attempts": 2,
                "launcher": "local",
                "model": "claude-sonnet-4-6",
                "effort": "max",
                "budget_usd": 10.0,
                "timeout_seconds": 600,
                "two_phase": True,
                "min_review_score": 7,
            },
            "notification": {
                "telegram_bot_token": "${TELEGRAM_BOT_TOKEN}",
                "telegram_chat_id": "${TELEGRAM_CHAT_ID}",
                "on_stage_complete": True,
                "on_failure": True,
                "on_heartbeat": False,
            },
        }

        yaml_path = out_root / f"{slug}_campaign.yaml"
        yaml_path.write_text(yaml.safe_dump(spec, sort_keys=False))

        return {
            "campaign_file": str(yaml_path),
            "task_file": str(task_file),
            "workspace_root": ws_root,
            "next_steps": [
                f"Edit {yaml_path} to refine the spec",
                f"Edit {task_file} to refine the research task",
                f"Launch with msc_campaign_start(campaign_file='{yaml_path}')",
            ],
        }

    @mcp.tool()
    def msc_campaign_start(
        campaign_file: str,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Launch a campaign defined by a YAML spec.

        Runs in the foreground briefly to initialize, then detaches into the
        heartbeat loop. Use msc_campaign_status to track progress.
        """
        workspace = resolve_workspace(workspace_dir)
        cf = Path(campaign_file)
        if not cf.is_absolute():
            cf = workspace / cf
        if not cf.exists():
            return {"error": "campaign file not found", "path": str(cf)}

        cmd = _msc_cmd(["campaign", "start", str(cf)])
        log_root = workspace / ".poggio_ai_mcp_logs"
        log_root.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stdout_log = log_root / f"campaign_start_{stamp}.out"
        stderr_log = log_root / f"campaign_start_{stamp}.err"

        with open(stdout_log, "w") as out, open(stderr_log, "w") as err:
            proc = subprocess.Popen(
                cmd,
                cwd=str(workspace),
                stdout=out,
                stderr=err,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return {
            "pid": proc.pid,
            "campaign_file": str(cf),
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
        }

    @mcp.tool()
    def msc_campaign_status(
        campaign_file: str | None = None,
        workspace_root: str | None = None,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Read the current state of a campaign.

        Provide either `campaign_file` (the YAML spec — we resolve its
        workspace_root) or `workspace_root` directly.
        """
        workspace = resolve_workspace(workspace_dir)
        ws_root: Path | None = None
        if workspace_root:
            ws_root = Path(workspace_root)
            if not ws_root.is_absolute():
                ws_root = workspace / ws_root
        elif campaign_file:
            cf = Path(campaign_file)
            if not cf.is_absolute():
                cf = workspace / cf
            if not cf.exists():
                return {"error": "campaign file not found", "path": str(cf)}
            try:
                spec = yaml.safe_load(cf.read_text())
                raw_ws = spec.get("workspace_root", "")
                ws_root = Path(raw_ws)
                if not ws_root.is_absolute():
                    ws_root = cf.parent / ws_root
            except (yaml.YAMLError, OSError) as e:
                return {"error": f"could not read campaign file: {e}"}
        else:
            return {"error": "must provide campaign_file or workspace_root"}

        status = _read_status(ws_root)
        if status is None:
            return {
                "workspace_root": str(ws_root),
                "exists": ws_root.exists(),
                "status": None,
                "note": "no campaign_state.json yet — campaign may not have started",
            }

        stages = status.get("stages") or status.get("stage_states") or {}
        stage_summary = []
        if isinstance(stages, dict):
            for sid, s in stages.items():
                stage_summary.append({
                    "id": sid,
                    "status": s.get("status"),
                    "pid": s.get("pid"),
                    "artifacts": s.get("artifacts"),
                })
        elif isinstance(stages, list):
            stage_summary = stages

        return {
            "workspace_root": str(ws_root),
            "campaign_status": status.get("status"),
            "total_cost_usd": status.get("total_cost_usd"),
            "budget_usd": status.get("budget_usd"),
            "stages": stage_summary,
            "raw": status,
        }

    @mcp.tool()
    def msc_campaign_repair(
        campaign_file: str,
        stage_id: str,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Trigger autonomous repair on a failed campaign stage.

        Invokes `msc campaign repair <campaign_file> <stage_id>` synchronously
        and returns its exit code + tail of output.
        """
        workspace = resolve_workspace(workspace_dir)
        cf = Path(campaign_file)
        if not cf.is_absolute():
            cf = workspace / cf
        if not cf.exists():
            return {"error": "campaign file not found", "path": str(cf)}

        cmd = _msc_cmd(["campaign", "repair", str(cf), stage_id])
        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-2000:],
            }
        except subprocess.TimeoutExpired:
            return {"error": "repair launch timed out after 60s", "note": "repair may still be running in background"}

    @mcp.tool()
    def msc_campaign_list(workspace_dir: str | None = None) -> dict[str, Any]:
        """List campaign YAML files in the workspace."""
        workspace = resolve_workspace(workspace_dir)
        files = sorted(workspace.glob("*_campaign.yaml")) + sorted(workspace.glob("*.campaign.yaml"))
        out = []
        for f in files:
            try:
                spec = yaml.safe_load(f.read_text())
                out.append({
                    "campaign_file": str(f),
                    "name": spec.get("name"),
                    "workspace_root": spec.get("workspace_root"),
                    "budget_usd": spec.get("budget_usd"),
                    "planning_enabled": (spec.get("planning") or {}).get("enabled", False),
                })
            except (yaml.YAMLError, OSError):
                out.append({"campaign_file": str(f), "error": "could not parse"})
        return {"workspace": str(workspace), "campaigns": out}
