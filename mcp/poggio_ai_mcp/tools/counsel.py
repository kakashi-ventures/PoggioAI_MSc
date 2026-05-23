"""Multi-model counsel-debate tool.

Wraps `consortium.counsel.run_counsel_stage` — runs N debate models on an
arbitrary question and synthesises a consensus answer.

Heads-up: counsel requires API keys for every model spec listed in
`.llm_config.yaml` (or the override passed in). Disabled by default in
the upstream config.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ..workspace import resolve_workspace


def register(mcp) -> None:

    @mcp.tool()
    def msc_counsel_debate(
        question: str,
        system_prompt: str | None = None,
        max_debate_rounds: int = 3,
        model_specs: list[dict] | None = None,
        budget_usd: float = 5.0,
        model_timeout_seconds: int = 600,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Run multi-model counsel debate on an arbitrary question.

        Spins up the configured counsel models (or `model_specs` override),
        has them debate for `max_debate_rounds`, and returns the synthesized
        consensus.

        Args:
            question: The question / task to debate.
            system_prompt: System prompt for each model. Defaults to a generic
                           "provide your best answer with reasoning" prompt.
            max_debate_rounds: How many rounds of cross-critique (default 3).
            model_specs: Override the default counsel models. Each spec is a
                         dict with keys: model (required), reasoning_effort,
                         verbosity, thinking_budget.
            budget_usd: Hard cost cap for this debate.
            model_timeout_seconds: Per-model timeout.
            workspace_dir: Workspace for the sandboxes (counsel writes
                           scratch artifacts here). Defaults to a temp dir.

        Returns the consensus string and the sandbox directory.
        """
        try:
            from consortium.counsel import create_counsel_models, run_counsel_stage
        except ImportError as e:
            return {"error": f"PoggioAI engine not installed: {e}"}

        if workspace_dir:
            ws = resolve_workspace(workspace_dir)
            ws.mkdir(parents=True, exist_ok=True)
            sandbox_root = ws / "counsel_debates"
            sandbox_root.mkdir(exist_ok=True)
            tmp = tempfile.mkdtemp(prefix="counsel_", dir=str(sandbox_root))
        else:
            tmp = tempfile.mkdtemp(prefix="poggio_counsel_")

        budget_config = {"usd_limit": budget_usd, "hard_stop": True, "fail_closed": True}

        try:
            models = create_counsel_models(
                budget_config=budget_config,
                budget_dir=tmp,
                model_specs=model_specs,
            )
        except Exception as e:
            return {"error": f"could not create counsel models: {e}", "sandbox": tmp}

        prompt = system_prompt or (
            "You are part of a multi-model expert counsel. Provide your best "
            "answer to the question, with reasoning. In later rounds you will "
            "critique other models' answers — be rigorous and honest."
        )

        try:
            consensus = run_counsel_stage(
                task=question,
                system_prompt=prompt,
                tools=[],
                workspace_dir=tmp,
                counsel_models=models,
                agent_name="mcp_debate",
                max_debate_rounds=max_debate_rounds,
                model_specs=model_specs,
                model_timeout_seconds=model_timeout_seconds,
            )
        except Exception as e:
            return {"error": f"counsel debate failed: {e}", "sandbox": tmp}

        return {
            "consensus": consensus,
            "sandbox": tmp,
            "rounds": max_debate_rounds,
            "models_used": [s.get("model") for s in (model_specs or [])] or "default",
        }
