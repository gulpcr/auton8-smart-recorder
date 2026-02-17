"""
Suite Runner Skill - Execute multiple workflows in sequence or parallel.

Runs locally. Can optionally report results to central server.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class SuiteRunnerSkill(SkillBase):
    name = "suite_runner"
    description = "Run multiple workflows in sequence or parallel"
    local_capable = True
    server_capable = True

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run a suite of workflows.

        kwargs:
            workflows: list of workflow paths
            mode: "sequential" | "parallel" (default: sequential)
            replayer_factory: callable that returns a StableReplayer
            stop_on_failure: bool
            on_workflow_result: callable(path, success, duration_ms)
        """
        workflows = kwargs.get("workflows", [])
        if not workflows:
            return SkillResult(success=False, error="No workflows provided")

        mode = kwargs.get("mode", "sequential")
        stop_on_fail = kwargs.get("stop_on_failure", False)
        replayer_factory = kwargs.get("replayer_factory")
        on_result = kwargs.get("on_workflow_result")

        if not replayer_factory:
            return SkillResult(success=False, error="replayer_factory required")

        results: List[Dict[str, Any]] = []
        total_passed = 0
        total_failed = 0

        if mode == "sequential":
            for wf_path in workflows:
                start = time.perf_counter_ns()
                replayer = replayer_factory()

                # Simple blocking replay
                success = False
                error_msg = ""

                def _on_complete(s: bool, e: str, d: int = 0):
                    nonlocal success, error_msg
                    success = s
                    error_msg = e

                replayer.on_complete(_on_complete)
                replayer.replay(wf_path)

                # Wait for completion (replayer runs in its own thread)
                import threading
                timeout = ctx.settings.get("suiteTimeout", 300)
                deadline = time.monotonic() + timeout
                while replayer._running and time.monotonic() < deadline:
                    time.sleep(0.5)

                elapsed_ms = int((time.perf_counter_ns() - start) / 1_000_000)

                result_entry = {
                    "workflow": wf_path,
                    "success": success,
                    "error": error_msg,
                    "duration_ms": elapsed_ms,
                }
                results.append(result_entry)

                if success:
                    total_passed += 1
                else:
                    total_failed += 1

                if on_result:
                    on_result(wf_path, success, elapsed_ms)

                if not success and stop_on_fail:
                    logger.info(f"[suite_runner] Stopping on failure: {wf_path}")
                    break

        suite_success = total_failed == 0

        # Report to server if connected
        if ctx.portal_client and ctx.portal_client.is_connected:
            try:
                ctx.portal_client.upload_training_data([{
                    "type": "suite_execution",
                    "total": len(workflows),
                    "passed": total_passed,
                    "failed": total_failed,
                    "results": results,
                }])
            except Exception as e:
                logger.debug(f"[suite_runner] Could not report to server: {e}")

        return SkillResult(
            success=suite_success,
            data={
                "total": len(workflows),
                "passed": total_passed,
                "failed": total_failed,
                "results": results,
            },
            run_location=SkillRunLocation.LOCAL,
        )

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Submit suite for server-side execution."""
        workflows = kwargs.get("workflows", [])
        if not workflows:
            return SkillResult(success=False, error="No workflows provided")

        from pathlib import Path
        workflow_ids = [Path(w).name for w in workflows]

        status, data = ctx.portal_client.post("/api/suite/run", {
            "workflows": workflow_ids,
            "mode": kwargs.get("mode", "sequential"),
            "stop_on_failure": kwargs.get("stop_on_failure", False),
        })

        if status in (200, 201):
            return SkillResult(
                success=True,
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        return SkillResult(success=False, error=f"Server suite run failed: {data}")
