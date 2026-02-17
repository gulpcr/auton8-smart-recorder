"""
Variables Skill - Store, extract, import/export workflow variables.

Always runs locally. Wraps expression_engine + global_variable_registry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class VariablesSkill(SkillBase):
    name = "variables"
    description = "Variable store, extract, evaluate expressions, import/export"
    local_capable = True
    server_capable = False

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Variable operations.

        kwargs:
            action: "store" | "get" | "evaluate" | "import" | "export" | "list"
            variable_name: str
            value: Any
            expression: str (for evaluate)
            scope: "step" | "test" | "suite" | "global"
            variables: dict - current variable store
        """
        action = kwargs.get("action", "store")
        variables = kwargs.get("variables", {})

        if action == "store":
            name = kwargs.get("variable_name", "")
            value = kwargs.get("value", "")
            if not name:
                return SkillResult(success=False, error="variable_name required")
            variables[name] = value
            return SkillResult(
                success=True,
                data={"name": name, "value": value, "variables": variables},
            )

        elif action == "get":
            name = kwargs.get("variable_name", "")
            if name in variables:
                return SkillResult(success=True, data={"name": name, "value": variables[name]})
            return SkillResult(success=False, error=f"Variable not found: {name}")

        elif action == "evaluate":
            expression = kwargs.get("expression", "")
            return self._evaluate_expression(expression, variables)

        elif action == "list":
            return SkillResult(success=True, data={"variables": variables})

        elif action == "import":
            return self._import_globals(kwargs)

        elif action == "export":
            return self._export_globals(kwargs, variables)

        return SkillResult(success=False, error=f"Unknown action: {action}")

    def _evaluate_expression(self, expression: str, variables: Dict) -> SkillResult:
        """Evaluate an expression with variable substitution."""
        try:
            from recorder.services.expression_engine import ExpressionEngine
            engine = ExpressionEngine(variables)
            result = engine.evaluate(expression)
            return SkillResult(success=True, data={"expression": expression, "result": result})
        except ImportError:
            # Fallback: simple ${var} substitution
            import re
            result = expression
            for match in re.finditer(r"\$\{(\w+)\}", expression):
                var_name = match.group(1)
                if var_name in variables:
                    result = result.replace(match.group(0), str(variables[var_name]))
            return SkillResult(success=True, data={"expression": expression, "result": result})
        except Exception as e:
            return SkillResult(success=False, error=f"Expression eval failed: {e}")

    def _import_globals(self, kwargs: Dict) -> SkillResult:
        """Import variables from global registry."""
        try:
            from recorder.services.global_variable_registry import get_global_registry
            registry = get_global_registry()
            imports = kwargs.get("imports", [])
            imported = {}
            for imp in imports:
                global_name = imp.get("globalName", "")
                local_name = imp.get("localName", global_name)
                value = registry.get(global_name)
                if value is not None:
                    imported[local_name] = value
                elif imp.get("required", True):
                    return SkillResult(
                        success=False,
                        error=f"Required global variable not found: {global_name}",
                    )
                else:
                    default = imp.get("defaultValue")
                    if default is not None:
                        imported[local_name] = default
            return SkillResult(success=True, data={"imported": imported})
        except ImportError:
            return SkillResult(success=False, error="Global variable registry not available")

    def _export_globals(self, kwargs: Dict, variables: Dict) -> SkillResult:
        """Export variables to global registry."""
        try:
            from recorder.services.global_variable_registry import get_global_registry
            registry = get_global_registry()
            exports = kwargs.get("exports", [])
            exported = []
            for exp in exports:
                var_name = exp.get("variableName", "")
                global_name = exp.get("globalName", var_name)
                if var_name in variables:
                    registry.set(global_name, variables[var_name],
                                 group=exp.get("group", "default"))
                    exported.append(global_name)
            return SkillResult(success=True, data={"exported": exported})
        except ImportError:
            return SkillResult(success=False, error="Global variable registry not available")
