"""
Global Variable Registry - Cross-workflow variable sharing

Supports:
- Persistent variables across workflow runs
- Import/export between workflows
- Variable groups (organize by feature/module)
- Variable versioning and history
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

if TYPE_CHECKING:
    from recorder.services.execution.variable_store import VariableStore

logger = logging.getLogger(__name__)


class VariableType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    SECRET = "secret"  # For sensitive data


class GlobalVariable(BaseModel):
    """A variable in the global registry."""
    name: str
    value: Any
    type: VariableType = VariableType.STRING
    group: str = "default"
    description: Optional[str] = None

    # Metadata
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    createdBy: Optional[str] = None  # Workflow that created it

    # Options
    readonly: bool = False  # Cannot be modified by workflows
    persistent: bool = True  # Survives application restart
    masked: bool = False  # Hide in logs/UI


class VariableImportConfig(BaseModel):
    """Import a variable from global registry into workflow."""
    globalName: str  # Name in global registry
    localName: Optional[str] = None  # Local variable name (defaults to globalName)
    required: bool = True  # Fail if not found
    defaultValue: Optional[Any] = None  # Use if not found and not required


class VariableExportConfig(BaseModel):
    """Export a variable from workflow to global registry."""
    variableName: str  # Local variable name in workflow
    globalName: Optional[str] = None  # Name in registry (defaults to variableName)
    group: str = "default"  # Variable group for organization
    overwrite: bool = True  # Overwrite if exists
    condition: Optional[str] = None  # Only export if condition is true
    persistent: bool = True  # Persist to disk
    masked: bool = False  # Hide sensitive values


class WorkflowVariables(BaseModel):
    """Variable configuration for a workflow."""
    imports: List[VariableImportConfig] = Field(default_factory=list)
    exports: List[VariableExportConfig] = Field(default_factory=list)


class GlobalVariableRegistry:
    """
    Manages global variables shared across workflows.

    Storage: data/variables.json (persistent)
    Runtime: In-memory with auto-save

    Variable Resolution Order:
    1. Runtime-only variables (non-persistent)
    2. Persistent variables from storage

    Usage:
        registry = get_global_registry()
        registry.set("authToken", "abc123", group="auth")
        token = registry.get("authToken")
    """

    def __init__(self, storage_path: Optional[Path] = None):
        import threading
        self._lock = threading.Lock()
        self._storage_path = storage_path or Path("data/variables.json")
        self._variables: Dict[str, GlobalVariable] = {}
        self._runtime_only: Dict[str, Any] = {}  # Non-persistent runtime vars
        self._load()

    def _load(self):
        """Load variables from persistent storage."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, var_data in data.get("variables", {}).items():
                    self._variables[name] = GlobalVariable(**var_data)
                logger.info(f"Loaded {len(self._variables)} global variables from {self._storage_path}")
            except Exception as e:
                logger.error(f"Failed to load global variables: {e}")
        else:
            logger.info(f"No existing variables file at {self._storage_path}")

    def _save(self):
        """Persist variables to storage."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "updatedAt": datetime.utcnow().isoformat(),
                "variables": {
                    name: var.model_dump()
                    for name, var in self._variables.items()
                    if var.persistent
                }
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(data['variables'])} variables to {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to save global variables: {e}")

    # ==================== CRUD Operations ====================

    def set(
        self,
        name: str,
        value: Any,
        var_type: Optional[VariableType] = None,
        group: str = "default",
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        persistent: bool = True,
        masked: bool = False,
        readonly: bool = False
    ) -> GlobalVariable:
        """
        Set a global variable.

        Args:
            name: Variable name
            value: Variable value
            var_type: Type hint (auto-detected if None)
            group: Group for organization
            description: Human-readable description
            created_by: Workflow/source that created it
            persistent: Whether to save to disk
            masked: Hide value in logs
            readonly: Prevent modification

        Returns:
            The created/updated GlobalVariable
        """
        with self._lock:
            existing = self._variables.get(name)
            if existing and existing.readonly:
                raise ValueError(f"Variable '{name}' is readonly and cannot be modified")

            # Auto-detect type if not specified
            if var_type is None:
                var_type = self._detect_type(value)

            var = GlobalVariable(
                name=name,
                value=value,
                type=var_type,
                group=group,
                description=description,
                createdBy=created_by,
                persistent=persistent,
                masked=masked,
                readonly=readonly,
                createdAt=existing.createdAt if existing else datetime.utcnow().isoformat(),
                updatedAt=datetime.utcnow().isoformat()
            )
            self._variables[name] = var

            if persistent:
                self._save()

        log_value = "***" if masked else value
        logger.info(f"Set global variable: {group}.{name} = {log_value}")
        return var

    def _detect_type(self, value: Any) -> VariableType:
        """Auto-detect variable type from value."""
        if isinstance(value, bool):
            return VariableType.BOOLEAN
        elif isinstance(value, (int, float)):
            return VariableType.NUMBER
        elif isinstance(value, (dict, list)):
            return VariableType.JSON
        else:
            return VariableType.STRING

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a global variable value.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        with self._lock:
            # Check runtime-only first
            if name in self._runtime_only:
                return self._runtime_only[name]

            var = self._variables.get(name)
            if var:
                return var.value
            return default

    def get_variable(self, name: str) -> Optional[GlobalVariable]:
        """Get full variable object with metadata."""
        with self._lock:
            return self._variables.get(name)

    def exists(self, name: str) -> bool:
        """Check if a variable exists."""
        with self._lock:
            return name in self._variables or name in self._runtime_only

    def delete(self, name: str) -> bool:
        """
        Delete a global variable.

        Returns:
            True if deleted, False if not found
        """
        if name in self._variables:
            var = self._variables[name]
            if var.readonly:
                raise ValueError(f"Variable '{name}' is readonly and cannot be deleted")
            del self._variables[name]
            self._save()
            logger.info(f"Deleted global variable: {name}")
            return True
        if name in self._runtime_only:
            del self._runtime_only[name]
            return True
        return False

    def list_all(self, group: Optional[str] = None) -> List[GlobalVariable]:
        """
        List all variables, optionally filtered by group.

        Args:
            group: Filter by group name (None = all)

        Returns:
            List of GlobalVariable objects
        """
        vars_list = list(self._variables.values())
        if group:
            vars_list = [v for v in vars_list if v.group == group]
        return sorted(vars_list, key=lambda v: (v.group, v.name))

    def list_groups(self) -> List[str]:
        """List all unique variable groups."""
        groups = set(v.group for v in self._variables.values())
        return sorted(groups)

    def search(self, query: str) -> List[GlobalVariable]:
        """Search variables by name or description."""
        query_lower = query.lower()
        results = []
        for var in self._variables.values():
            if query_lower in var.name.lower():
                results.append(var)
            elif var.description and query_lower in var.description.lower():
                results.append(var)
        return results

    # ==================== Runtime Variables ====================

    def set_runtime(self, name: str, value: Any):
        """Set a runtime-only variable (not persisted)."""
        self._runtime_only[name] = value
        logger.debug(f"Set runtime variable: {name}")

    def clear_runtime(self):
        """Clear all non-persistent runtime variables."""
        count = len(self._runtime_only)
        self._runtime_only.clear()
        logger.info(f"Cleared {count} runtime variables")

    # ==================== Workflow Integration ====================

    def import_for_workflow(
        self,
        imports: List[VariableImportConfig],
        target_store: "VariableStore",
        workflow_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Import global variables into a workflow's variable store.

        Args:
            imports: List of import configurations
            target_store: The workflow's VariableStore instance
            workflow_name: Name of the workflow (for logging)

        Returns:
            Dict of imported variable names and values

        Raises:
            ValueError: If a required variable is not found
        """
        imported = {}

        for imp in imports:
            value = self.get(imp.globalName)

            if value is None:
                if imp.required:
                    raise ValueError(
                        f"Required global variable '{imp.globalName}' not found. "
                        f"Workflow '{workflow_name}' cannot start without it."
                    )
                value = imp.defaultValue

            if value is not None:
                local_name = imp.localName or imp.globalName
                target_store.set(local_name, value, scope="test")
                imported[local_name] = value
                logger.info(f"[{workflow_name}] Imported global.{imp.globalName} -> ${{{local_name}}}")

        return imported

    def export_from_workflow(
        self,
        exports: List[VariableExportConfig],
        source_store: "VariableStore",
        workflow_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Export workflow variables to global registry.

        Args:
            exports: List of export configurations
            source_store: The workflow's VariableStore instance
            workflow_name: Name of the workflow (for logging/tracking)

        Returns:
            Dict of exported variable names and values
        """
        exported = {}

        for exp in exports:
            value = source_store.get(exp.variableName)

            if value is None:
                logger.warning(
                    f"[{workflow_name}] Export variable '{exp.variableName}' not found in workflow"
                )
                continue

            global_name = exp.globalName or exp.variableName

            # Check if exists and overwrite setting
            existing = self.get_variable(global_name)
            if existing and not exp.overwrite:
                logger.info(
                    f"[{workflow_name}] Skipping export '{global_name}' - already exists"
                )
                continue

            if existing and existing.readonly:
                logger.warning(
                    f"[{workflow_name}] Cannot export to readonly variable '{global_name}'"
                )
                continue

            self.set(
                name=global_name,
                value=value,
                group=exp.group,
                created_by=workflow_name,
                persistent=exp.persistent,
                masked=exp.masked
            )
            exported[global_name] = value
            logger.info(f"[{workflow_name}] Exported ${{{exp.variableName}}} -> global.{global_name}")

        return exported

    # ==================== Bulk Operations ====================

    def clear_group(self, group: str) -> int:
        """
        Clear all variables in a group.

        Returns:
            Number of variables deleted
        """
        to_delete = [
            name for name, var in self._variables.items()
            if var.group == group and not var.readonly
        ]
        for name in to_delete:
            del self._variables[name]

        if to_delete:
            self._save()
            logger.info(f"Cleared {len(to_delete)} variables from group '{group}'")

        return len(to_delete)

    def clear_all(self, include_readonly: bool = False) -> int:
        """
        Clear all variables.

        Args:
            include_readonly: Also delete readonly variables

        Returns:
            Number of variables deleted
        """
        if include_readonly:
            count = len(self._variables)
            self._variables.clear()
        else:
            to_delete = [n for n, v in self._variables.items() if not v.readonly]
            count = len(to_delete)
            for name in to_delete:
                del self._variables[name]

        self._runtime_only.clear()
        self._save()
        logger.info(f"Cleared {count} global variables")
        return count

    def export_to_dict(self, include_masked: bool = False) -> Dict[str, Any]:
        """
        Export all variables as simple dict.

        Args:
            include_masked: Include masked variable values

        Returns:
            Dict of name -> value
        """
        result = {}
        for name, var in self._variables.items():
            if var.masked and not include_masked:
                result[name] = "***"
            else:
                result[name] = var.value
        return result

    def import_from_dict(
        self,
        data: Dict[str, Any],
        group: str = "imported",
        overwrite: bool = False
    ) -> int:
        """
        Import variables from a simple dict.

        Args:
            data: Dict of name -> value
            group: Group to assign to imported variables
            overwrite: Overwrite existing variables

        Returns:
            Number of variables imported
        """
        count = 0
        for name, value in data.items():
            if not overwrite and self.exists(name):
                continue
            self.set(name, value, group=group)
            count += 1
        return count

    def to_json(self) -> str:
        """Export registry to JSON string."""
        return json.dumps({
            "version": "1.0",
            "exportedAt": datetime.utcnow().isoformat(),
            "variables": {
                name: var.model_dump()
                for name, var in self._variables.items()
            }
        }, indent=2)

    def from_json(self, json_str: str, overwrite: bool = False) -> int:
        """
        Import registry from JSON string.

        Returns:
            Number of variables imported
        """
        data = json.loads(json_str)
        count = 0
        for name, var_data in data.get("variables", {}).items():
            if not overwrite and self.exists(name):
                continue
            var = GlobalVariable(**var_data)
            self._variables[name] = var
            count += 1
        self._save()
        return count


# Singleton instance
import threading
_registry: Optional[GlobalVariableRegistry] = None
_registry_lock = threading.Lock()


def get_global_registry(storage_path: Optional[Path] = None) -> GlobalVariableRegistry:
    """
    Get the global variable registry singleton.

    Args:
        storage_path: Custom path for variable storage (only used on first call)

    Returns:
        GlobalVariableRegistry instance
    """
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = GlobalVariableRegistry(storage_path)
    return _registry


def reset_global_registry():
    """Reset the global registry (mainly for testing)."""
    global _registry
    _registry = None
