"""Run-management tools.

Exposes the `msc run` subcommand plus read-only inspection of past runs
(`results/consortium_<timestamp>_<task>/`).
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

from ..workspace import resolve_workspace, results_dir, run_dir


def _msc_binary() -> str:
    """Locate the `msc` CLI. Falls back to `python -m consortium.cli.main`."""
    found = shutil.which("msc")
    if found:
        return found
    return ""


def _spawn_msc(args: list[str], workspace: Path) -> dict[str, Any]:
    """Spawn the msc CLI in the background and return the PID + log path."""
    bin_path = _msc_binary()
    if bin_path:
        cmd = [bin_path, *args]
    else:
        cmd = ["python", "-m", "consortium.cli.main", *args]

    workspace.mkdir(parents=True, exist_ok=True)
    log_root = workspace / ".poggio_ai_mcp_logs"
    log_root.mkdir(exist_ok=True)

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout_path = log_root / f"msc_{stamp}.out"
    stderr_path = log_root / f"msc_{stamp}.err"

    stdout_f = open(stdout_path, "w")
    stderr_f = open(stderr_path, "w")

    proc = subprocess.Popen(
        cmd,
        cwd=str(workspace),
        stdout=stdout_f,
        stderr=stderr_f,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {
        "pid": proc.pid,
        "command": " ".join(cmd),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "workspace": str(workspace),
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _summarize_run(run_path: Path) -> dict[str, Any]:
    """Build a one-run summary dict from on-disk artifacts."""
    summary = _read_json(run_path / "run_summary.json") or {}
    budget = _read_json(run_path / "budget_state.json") or {}
    heartbeat = _read_json(run_path / ".progress_heartbeat") or {}

    manuscripts = []
    for ext in ("md", "tex", "pdf"):
        p = run_path / f"final_paper.{ext}"
        if p.exists():
            manuscripts.append(str(p))

    return {
        "run_id": run_path.name,
        "path": str(run_path),
        "task": summary.get("task"),
        "model": summary.get("model"),
        "completed": summary.get("completed", False),
        "total_cost_usd": summary.get("total_cost_usd") or budget.get("spent_usd"),
        "budget_limit_usd": budget.get("limit_usd"),
        "current_stage": heartbeat.get("stage"),
        "last_heartbeat": heartbeat.get("timestamp"),
        "manuscripts": manuscripts,
    }


def register(mcp) -> None:

    @mcp.tool()
    def msc_run(
        task: str,
        tier: str = "medium",
        model: str | None = None,
        budget_usd: float | None = None,
        output_format: str = "markdown",
        mode: str = "local",
        counsel: bool = False,
        math: bool = False,
        tree_search: bool = False,
        max_run_seconds: int | None = None,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Launch a research pipeline on a question.

        Returns immediately with the spawned PID and log paths — the run
        continues in the background. Poll with `msc_status`, `msc_get_logs`,
        and `msc_get_run`. Stop with `msc_stop_run`.

        Args:
            task: The research question or task prompt.
            tier: One of budget|light|medium|pro|max. Controls model choice
                  and budget defaults.
            model: Override the model (e.g. claude-opus-4-6).
            budget_usd: Override the hard budget cap in USD.
            output_format: markdown or latex.
            mode: local | tinker | hpc.
            counsel: Enable multi-model counsel oversight.
            math: Enable math agents.
            tree_search: Enable tree-search exploration.
            max_run_seconds: Hard timeout for the run.
            workspace_dir: Override the workspace root.
        """
        workspace = resolve_workspace(workspace_dir)
        args = ["run", task, "--tier", tier, "--output-format", output_format, "--mode", mode]
        if model:
            args += ["--model", model]
        if budget_usd is not None:
            args += ["--budget", str(int(budget_usd))]
        if counsel:
            args.append("--counsel")
        else:
            args.append("--no-counsel")
        if math:
            args.append("--math")
        else:
            args.append("--no-math")
        if tree_search:
            args.append("--tree-search")
        else:
            args.append("--no-tree-search")
        if max_run_seconds is not None:
            args += ["--max-run-seconds", str(max_run_seconds)]

        result = _spawn_msc(args, workspace)
        result["next_steps"] = [
            "Use msc_status to see when the run appears in results/",
            "Use msc_list_runs to find the run_id once the workspace is created",
            f"Tail stdout: msc_get_logs(run_id='...') or read {result['stdout_log']}",
        ]
        return result

    @mcp.tool()
    def msc_stop_run(pid: int) -> dict[str, Any]:
        """Stop a running MSc pipeline by PID (returned from msc_run).

        Sends SIGTERM to the process group; falls back to SIGKILL after a
        moment if the process is still alive.
        """
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            return {"stopped": True, "pid": pid, "signal": "SIGTERM"}
        except ProcessLookupError:
            return {"stopped": False, "pid": pid, "error": "process not found"}
        except PermissionError as e:
            return {"stopped": False, "pid": pid, "error": str(e)}

    @mcp.tool()
    def msc_list_runs(
        limit: int = 20,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """List past MSc runs in `results/`, newest first.

        Each entry contains run_id, task, model, cost, completion status,
        and the path to its final manuscript if any.
        """
        rd = results_dir(workspace_dir)
        if not rd.exists():
            return {"runs": [], "results_dir": str(rd), "note": "results/ does not exist yet"}

        run_paths = [p for p in rd.iterdir() if p.is_dir() and p.name.startswith("consortium_")]
        run_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        run_paths = run_paths[:limit]

        return {
            "results_dir": str(rd),
            "count": len(run_paths),
            "runs": [_summarize_run(p) for p in run_paths],
        }

    @mcp.tool()
    def msc_get_run(
        run_id: str,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the full summary, budget state, and artifact paths for one run.

        Args:
            run_id: Either the directory name (e.g. `consortium_2026...`) or
                    an absolute path to a run directory.
        """
        path = run_dir(run_id, workspace_dir)
        if not path.exists():
            return {"error": "run not found", "path": str(path)}

        summary = _summarize_run(path)
        summary["run_summary"] = _read_json(path / "run_summary.json")
        summary["budget_state"] = _read_json(path / "budget_state.json")
        summary["token_usage"] = _read_json(path / "run_token_usage.json")

        log_dir = path / "logs"
        if log_dir.exists():
            summary["log_files"] = sorted(str(p) for p in log_dir.glob("*.log"))
        return summary

    @mcp.tool()
    def msc_get_logs(
        run_id: str,
        lines: int = 100,
        stage: str | None = None,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Return the tail of a run's log file.

        Args:
            run_id: Run directory name or absolute path.
            lines: How many tail lines to return.
            stage: If given, return logs from logs/<stage>.log only.
                   Otherwise concatenate the newest consortium_*.out + logs/.
        """
        path = run_dir(run_id, workspace_dir)
        if not path.exists():
            return {"error": "run not found", "path": str(path)}

        log_files: list[Path] = []
        if stage:
            target = path / "logs" / f"{stage}.log"
            if target.exists():
                log_files.append(target)
        else:
            log_files = sorted(path.glob("consortium_*.out"))
            log_dir = path / "logs"
            if log_dir.exists():
                log_files += sorted(log_dir.glob("*.log"))

        if not log_files:
            return {"error": "no log files found", "path": str(path)}

        latest = log_files[-1]
        try:
            content = latest.read_text(errors="replace")
        except OSError as e:
            return {"error": str(e), "log_file": str(latest)}
        tail = content.splitlines()[-lines:]
        return {
            "log_file": str(latest),
            "lines_returned": len(tail),
            "content": "\n".join(tail),
        }

    @mcp.tool()
    def msc_status(workspace_dir: str | None = None) -> dict[str, Any]:
        """Show currently-running MSc pipelines and recent campaigns.

        Detects running pipelines via .pid files and heartbeat staleness.
        """
        rd = results_dir(workspace_dir)
        if not rd.exists():
            return {"running": [], "recent": [], "note": "results/ does not exist yet"}

        running = []
        recent = []
        from datetime import datetime, timezone

        for p in sorted(rd.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:30]:
            if not p.is_dir() or not p.name.startswith("consortium_"):
                continue
            heartbeat_path = p / ".progress_heartbeat"
            hb = _read_json(heartbeat_path) or {}
            entry = _summarize_run(p)
            ts = hb.get("timestamp")
            is_running = False
            if ts:
                try:
                    when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - when).total_seconds()
                    is_running = age < 300  # 5 min staleness threshold
                    entry["heartbeat_age_seconds"] = int(age)
                except ValueError:
                    pass
            if is_running:
                running.append(entry)
            else:
                recent.append(entry)
        return {"running": running, "recent": recent[:10]}

    @mcp.tool()
    def msc_budget(workspace_dir: str | None = None) -> dict[str, Any]:
        """Aggregate USD spending across all runs in `results/`."""
        rd = results_dir(workspace_dir)
        if not rd.exists():
            return {"total_spent_usd": 0.0, "runs": 0, "note": "results/ does not exist yet"}

        total = 0.0
        per_model: dict[str, float] = {}
        n = 0
        for p in rd.iterdir():
            if not p.is_dir() or not p.name.startswith("consortium_"):
                continue
            n += 1
            budget = _read_json(p / "budget_state.json") or {}
            summary = _read_json(p / "run_summary.json") or {}
            cost = budget.get("spent_usd") or summary.get("total_cost_usd") or 0.0
            total += float(cost)
            model = summary.get("model") or "unknown"
            per_model[model] = per_model.get(model, 0.0) + float(cost)
        return {
            "total_spent_usd": round(total, 4),
            "runs": n,
            "per_model_usd": {k: round(v, 4) for k, v in per_model.items()},
        }
