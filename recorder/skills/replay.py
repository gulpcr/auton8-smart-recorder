"""
Replay Skill - Workflow execution with tiered healing.

Tier 0-1 always run locally (deterministic + heuristic).
Tier 2-3 (vision + LLM) delegate to server when in hybrid/server mode.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import SkillBase, SkillContext, SkillMode, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class ReplaySkill(SkillBase):
    name = "replay"
    description = "Execute workflow replay with tiered healing (local Tier 0-1, server Tier 2-3)"
    local_capable = True
    server_capable = True

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Replay a workflow locally.

        kwargs:
            workflow_path: str - path to workflow JSON
            replayer: StableReplayer instance (pre-configured)
            max_tier: int - max healing tier (0-3), defaults from settings
            headless: bool
            on_step: callable
            on_step_result: callable
            on_complete: callable
        """
        workflow_path = kwargs.get("workflow_path")
        replayer = kwargs.get("replayer")

        if not workflow_path:
            return SkillResult(success=False, error="workflow_path required")
        if not replayer:
            return SkillResult(success=False, error="replayer instance required")

        # Configure max tier based on mode
        max_tier = kwargs.get("max_tier")
        if max_tier is None:
            if ctx.skill_mode == SkillMode.LOCAL:
                # Local only: limit to Tier 1 (no CV/LLM)
                max_tier = 1
            else:
                max_tier = ctx.settings.get("maxTier", 3)

        # Wire optional callbacks
        on_step = kwargs.get("on_step")
        on_step_result = kwargs.get("on_step_result")
        on_complete = kwargs.get("on_complete")

        if on_step:
            replayer.on_step(on_step)
        if on_step_result:
            replayer.on_step_result(on_step_result)
        if on_complete:
            replayer.on_complete(on_complete)

        # Inject server-backed engines for Tier 2-3 when in hybrid mode
        if ctx.skill_mode != SkillMode.LOCAL and ctx.portal_client and ctx.portal_client.is_connected:
            self._attach_server_engines(replayer, ctx)

        replayer.replay(workflow_path)
        logger.info(f"[replay] Started local replay: {workflow_path} (maxTier={max_tier})")

        return SkillResult(
            success=True,
            data={"workflow_path": workflow_path, "max_tier": max_tier},
            run_location=SkillRunLocation.LOCAL,
        )

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Submit workflow for server-side replay (batch/CI mode).

        Returns a job_id that can be polled for status.
        """
        workflow_path = kwargs.get("workflow_path")
        if not workflow_path:
            return SkillResult(success=False, error="workflow_path required")

        headless = kwargs.get("headless", True)

        # Extract workflow_id from path
        from pathlib import Path
        workflow_id = Path(workflow_path).name

        status, data = ctx.portal_client.post("/api/replay", {
            "workflow_id": workflow_id,
            "headless": headless,
            "record_video": kwargs.get("record_video", False),
        })

        if status in (200, 201):
            return SkillResult(
                success=True,
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        return SkillResult(
            success=False,
            error=f"Server replay failed: {data}",
            run_location=SkillRunLocation.SERVER,
        )

    def _attach_server_engines(self, replayer: Any, ctx: SkillContext) -> None:
        """Attach server-backed engine proxies for higher healing tiers."""
        # These are lightweight proxy objects that call the portal API
        # instead of running heavy ML locally
        try:
            from .healing import ServerHealingProxy
            proxy = ServerHealingProxy(ctx.portal_client)
            replayer.set_healing_engine(proxy)
            logger.debug("[replay] Attached server healing proxy")
        except Exception as e:
            logger.debug(f"[replay] Could not attach server healing proxy: {e}")
