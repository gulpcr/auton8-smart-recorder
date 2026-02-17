"""
Workflow Management Skill - CRUD + sync to central server.

Always runs locally for basic operations.
Server sync available when portal is connected.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class WorkflowMgmtSkill(SkillBase):
    name = "workflow_mgmt"
    description = "Workflow CRUD operations and sync to central server"
    local_capable = True
    server_capable = True

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Local workflow operations.

        kwargs:
            action: "list" | "load" | "save" | "delete" | "export" | "sync"
            workflow_path: str
            workflow: Workflow object (for save)
            filename: str (for save)
        """
        action = kwargs.get("action", "list")

        from recorder.services import workflow_store

        if action == "list":
            workflows = workflow_store.list_workflows()
            return SkillResult(success=True, data=workflows)

        elif action == "load":
            filename = kwargs.get("filename")
            if not filename:
                path = kwargs.get("workflow_path", "")
                filename = os.path.basename(path) if path else ""
            if not filename:
                return SkillResult(success=False, error="filename or workflow_path required")

            workflow = workflow_store.load_workflow(filename)
            if workflow:
                return SkillResult(success=True, data=workflow)
            return SkillResult(success=False, error=f"Workflow not found: {filename}")

        elif action == "save":
            workflow = kwargs.get("workflow")
            filename = kwargs.get("filename")
            if not workflow:
                return SkillResult(success=False, error="workflow object required")
            if not filename:
                import uuid
                filename = f"test-{uuid.uuid4()}.json"

            path = workflow_store.save_workflow(workflow, filename)
            return SkillResult(success=True, data={"path": path, "filename": filename})

        elif action == "delete":
            path = kwargs.get("workflow_path", "")
            if not path or not os.path.exists(path):
                return SkillResult(success=False, error="Workflow file not found")
            os.remove(path)
            return SkillResult(success=True, data={"deleted": path})

        elif action == "sync":
            return self._sync_to_server(ctx, kwargs)

        elif action == "export":
            return self._export_workflow(ctx, kwargs)

        return SkillResult(success=False, error=f"Unknown action: {action}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Server-side workflow operations (fetch from server)."""
        action = kwargs.get("action", "list")

        if action == "list":
            status, data = ctx.portal_client.get("/api/workflows")
            if status == 200:
                return SkillResult(success=True, data=data.get("workflows", []),
                                   run_location=SkillRunLocation.SERVER)
            return SkillResult(success=False, error=f"Server error: {data}")

        elif action == "sync":
            return self._sync_to_server(ctx, kwargs)

        return SkillResult(success=False, error=f"Server action not supported: {action}")

    def _sync_to_server(self, ctx: SkillContext, kwargs: Dict) -> SkillResult:
        """Sync a local workflow to the central server."""
        if not ctx.portal_client or not ctx.portal_client.is_connected:
            return SkillResult(success=False, error="Portal not connected")

        workflow_path = kwargs.get("workflow_path", "")
        if not workflow_path:
            return SkillResult(success=False, error="workflow_path required")

        from recorder.services import workflow_store

        filename = os.path.basename(workflow_path)
        workflow = workflow_store.load_workflow(filename)
        if not workflow:
            return SkillResult(success=False, error=f"Cannot load: {filename}")

        # Build sync payload
        metadata = workflow.metadata or {}
        sync_data = {
            "name": metadata.get("name", filename),
            "description": metadata.get("description", ""),
            "url": metadata.get("baseUrl", ""),
            "steps": [s.model_dump() for s in workflow.steps],
            "tags": metadata.get("tags", []),
            "local_file_path": workflow_path,
        }

        status, data = ctx.portal_client.sync_workflow(sync_data)
        if status in (200, 201):
            logger.info(f"[workflow_mgmt] Synced workflow to server: {filename}")
            return SkillResult(
                success=True,
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        return SkillResult(success=False, error=f"Sync failed: {data}")

    def _export_workflow(self, ctx: SkillContext, kwargs: Dict) -> SkillResult:
        """Export workflow to a standalone JSON file."""
        workflow_path = kwargs.get("workflow_path", "")
        export_path = kwargs.get("export_path", "")

        if not workflow_path:
            return SkillResult(success=False, error="workflow_path required")
        if not export_path:
            return SkillResult(success=False, error="export_path required")

        from recorder.services import workflow_store

        filename = os.path.basename(workflow_path)
        workflow = workflow_store.load_workflow(filename)
        if not workflow:
            return SkillResult(success=False, error=f"Cannot load: {filename}")

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(workflow.model_dump(), f, indent=2, default=str)

        return SkillResult(success=True, data={"exported": export_path})
