"""
Analytics Skill - Dashboard stats, execution history, reports.

Server-only. Fetches aggregated data from the central portal.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class AnalyticsSkill(SkillBase):
    name = "analytics"
    description = "Dashboard statistics, execution history, and reports from central server"
    local_capable = False
    server_capable = True

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Fetch analytics from central server.

        kwargs:
            action: "dashboard" | "executions" | "ml_status" | "training_stats"
            workflow_id: str (for filtered executions)
            page: int
            page_size: int
        """
        action = kwargs.get("action", "dashboard")

        if action == "dashboard":
            status, data = ctx.portal_client.get_dashboard_stats()
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._error(data)

        elif action == "executions":
            workflow_id = kwargs.get("workflow_id")
            page = kwargs.get("page", 1)
            page_size = kwargs.get("page_size", 50)
            status, data = ctx.portal_client.list_executions(workflow_id, page, page_size)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._error(data)

        elif action == "ml_status":
            status, data = ctx.portal_client.get("/api/ml/status")
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._error(data)

        elif action == "training_stats":
            status, data = ctx.portal_client.get("/api/ml/training-data/stats")
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._error(data)

        return SkillResult(success=False, error=f"Unknown analytics action: {action}")

    @staticmethod
    def _error(data: Any) -> SkillResult:
        error = data.get("detail", "Analytics server error") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)
