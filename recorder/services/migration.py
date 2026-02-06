"""
Workflow migration system for backward compatibility.
Ensures old workflows load correctly with new schema.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from recorder.schema.workflow import Workflow, Step
from recorder.schema.enhanced import WorkflowMetadata

logger = logging.getLogger(__name__)


def get_workflow_version(data: Dict[str, Any]) -> int:
    """Extract version from workflow data."""
    # Check metadata first (new format)
    if "metadata" in data and isinstance(data["metadata"], dict):
        return data["metadata"].get("version", 1)
    
    # Check old meta dict
    if "meta" in data and isinstance(data["meta"], dict):
        return data["meta"].get("version", 1)
    
    # No version field = v1 (original)
    return 1


def migrate_workflow(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate workflow data to latest version.
    
    Migration chain:
    v1 (original) → v2 (enhanced metadata)
    """
    # #region agent log
    import json
    try:
        with open(r"f:\auton8\recorder\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "migration.py:migrate_workflow", "message": "Migration check", "data": {"has_metadata": "metadata" in data, "has_meta": "meta" in data}, "hypothesisId": "H4", "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session"}) + "\n")
    except Exception:
        pass  # Debug logging - non-critical
    # #endregion
    version = get_workflow_version(data)
    # #region agent log
    try:
        with open(r"f:\auton8\recorder\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "migration.py:migrate_workflow", "message": "Version detected", "data": {"version": version}, "hypothesisId": "H4", "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session"}) + "\n")
    except Exception:
        pass  # Debug logging - non-critical
    # #endregion
    
    if version == 1:
        logger.info("Migrating workflow from v1 to v2")
        data = migrate_v1_to_v2(data)
    
    # Future migrations would go here:
    # if version == 2:
    #     data = migrate_v2_to_v3(data)
    
    return data


def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate v1 workflow to v2 (add enhanced metadata).
    
    Changes:
    - Extract old meta dict values → new metadata object
    - Add default values for new fields
    - Preserve all existing data
    """
    # Create new data structure
    migrated = data.copy()
    
    # Extract old meta
    old_meta = data.get("meta", {})
    
    # Build enhanced metadata
    metadata = {
        "name": old_meta.get("name"),
        "description": old_meta.get("description"),
        "status": old_meta.get("status", "draft"),
        "tags": old_meta.get("tags", []),
        "createdAt": old_meta.get("createdAt"),
        "updatedAt": old_meta.get("updatedAt"),
        "lastRunAt": old_meta.get("lastRunAt"),
        "version": 2,  # New version
        "baseUrl": old_meta.get("baseUrl"),
        "author": old_meta.get("author"),
        "totalRuns": old_meta.get("totalRuns", 0),
        "successfulRuns": old_meta.get("successfulRuns", 0),
        "failedRuns": old_meta.get("failedRuns", 0),
        "avgDuration": old_meta.get("avgDuration", 0.0),
        "portalId": old_meta.get("portalId"),
        "portalUrl": old_meta.get("portalUrl"),
        "lastPublishedAt": old_meta.get("lastPublishedAt"),
    }
    
    # Remove None values for cleaner JSON
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    # Update structure
    migrated["metadata"] = metadata
    
    # Keep old meta for backward compatibility reading (some tools might expect it)
    # But mark as deprecated
    migrated["meta"] = old_meta
    migrated["meta"]["_deprecated"] = "Use 'metadata' field instead"
    
    # Migrate steps (add enhancements field if missing)
    if "steps" in migrated:
        for step in migrated["steps"]:
            if "enhancements" not in step:
                step["enhancements"] = {}
            
            # Migrate old metadata field to enhancements if exists
            if "metadata" in step:
                old_step_meta = step.pop("metadata")
                if old_step_meta and "comment" in old_step_meta:
                    step["enhancements"]["comment"] = old_step_meta["comment"]
    
    logger.info(f"Successfully migrated workflow to v2: {metadata.get('name', 'Unnamed')}")
    
    return migrated


def create_default_metadata(workflow_data: Dict[str, Any]) -> WorkflowMetadata:
    """
    Create default metadata for a new workflow.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Try to extract name from old meta or use default
    name = None
    if "meta" in workflow_data:
        name = workflow_data["meta"].get("name")
    if "metadata" in workflow_data:
        name = workflow_data["metadata"].get("name")
    
    if not name:
        # Generate name from base URL or timestamp
        base_url = workflow_data.get("meta", {}).get("baseUrl", "")
        if base_url:
            from urllib.parse import urlparse
            domain = urlparse(base_url).netloc or "unknown"
            name = f"Test on {domain}"
        else:
            name = f"Test {now[:10]}"  # Use date
    
    return WorkflowMetadata(
        name=name,
        status="draft",
        createdAt=now,
        updatedAt=now,
        version=2,
        baseUrl=workflow_data.get("meta", {}).get("baseUrl")
    )


def ensure_workflow_compatibility(workflow: Workflow) -> Workflow:
    """
    Ensure workflow object has all required fields for new features.
    Called after loading from JSON.
    """
    # Ensure metadata exists
    if not hasattr(workflow, "metadata") or workflow.metadata is None:
        # Try to extract from meta dict
        meta_dict = workflow.meta or {}
        workflow.metadata = create_default_metadata({"meta": meta_dict})
    
    # Ensure all steps have enhancements field
    for step in workflow.steps:
        if not hasattr(step, "enhancements") or step.enhancements is None:
            step.enhancements = {}
    
    return workflow


def downgrade_workflow(workflow: Workflow) -> Dict[str, Any]:
    """
    Downgrade workflow to v1 format for compatibility with older tools.
    (Rarely needed, but good for export)
    """
    data = workflow.model_dump()
    
    # Move metadata back to meta
    if "metadata" in data and data["metadata"]:
        meta = data.get("meta", {})
        metadata = data["metadata"]
        
        # Copy fields back
        meta.update({
            "name": metadata.get("name"),
            "baseUrl": metadata.get("baseUrl"),
            "status": metadata.get("status"),
            "tags": metadata.get("tags", []),
        })
        
        data["meta"] = meta
        
        # Remove new fields
        data.pop("metadata", None)
    
    # Remove enhancements from steps
    if "steps" in data:
        for step in data["steps"]:
            step.pop("enhancements", None)
    
    # Set version to 1
    data["version"] = "1.0"
    
    logger.info("Downgraded workflow to v1 format")
    
    return data


def validate_migrated_workflow(data: Dict[str, Any]) -> bool:
    """
    Validate that migration was successful.
    """
    try:
        # Check required fields exist
        assert "version" in data
        assert "steps" in data
        
        # Check metadata or meta exists
        assert "metadata" in data or "meta" in data
        
        # Validate steps structure
        for step in data["steps"]:
            assert "id" in step
            assert "type" in step
        
        return True
    
    except (AssertionError, KeyError, TypeError) as e:
        logger.error(f"Migration validation failed: {e}")
        return False
