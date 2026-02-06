from __future__ import annotations

import json
import os
import logging
from typing import Optional
from datetime import datetime

from recorder.schema.workflow import Workflow, Step
from recorder.services.migration import migrate_workflow, ensure_workflow_compatibility

logger = logging.getLogger(__name__)


WORKFLOW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "workflows")


def ensure_dir():
    os.makedirs(WORKFLOW_DIR, exist_ok=True)


def save_workflow(workflow: Workflow, filename: str) -> str:
    ensure_dir()
    path = os.path.join(WORKFLOW_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        # Use exclude_none=False to ensure all fields are saved, including None metadata
        data = workflow.model_dump(exclude_none=False)
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_workflow(filename: str) -> Optional[Workflow]:
    """Load workflow with automatic migration."""
    path = os.path.join(WORKFLOW_DIR, filename)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Migrate if needed
        data = migrate_workflow(data)
        
        # Create workflow object
        workflow = Workflow(**data)
        
        # Ensure compatibility
        workflow = ensure_workflow_compatibility(workflow)
        
        logger.info(f"Loaded workflow: {filename}")
        return workflow
    
    except Exception as e:
        logger.error(f"Failed to load workflow {filename}: {e}")
        return None


def append_step(workflow: Workflow, step: Step):
    workflow.steps.append(step)


def list_workflows() -> list[dict]:
    """Return list of saved workflows with enhanced metadata."""
    ensure_dir()
    workflows = []
    for filename in os.listdir(WORKFLOW_DIR):
        if filename.endswith(".json"):
            path = os.path.join(WORKFLOW_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Get metadata (try new format first, fall back to old)
                metadata = data.get("metadata", data.get("meta", {}))
                
                workflows.append({
                    "filename": filename,
                    "path": path,
                    "name": metadata.get("name", filename),
                    "description": metadata.get("description", ""),
                    "status": metadata.get("status", "draft"),
                    "tags": metadata.get("tags", []),
                    "stepCount": len(data.get("steps", [])),
                    "baseUrl": metadata.get("baseUrl", ""),
                    "updatedAt": metadata.get("updatedAt", ""),
                    "lastRunAt": metadata.get("lastRunAt", ""),
                    "version": metadata.get("version", 1),
                    "author": metadata.get("author", ""),
                    "successRate": metadata.get("successRate", 0.0),
                    "successProjection": metadata.get("successProjection", "unknown"),
                })
            except Exception as e:
                logger.warning(f"Failed to read workflow {filename}: {e}")
                pass
    
    # Sort by updated time (most recent first)
    return sorted(workflows, key=lambda x: x.get("updatedAt", ""), reverse=True)

