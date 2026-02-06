"""
Variable Store for Test Execution

Stores and retrieves variables across test steps and test cases.
Supports:
- Step-level variables (within a test)
- Test-level variables (persist across steps)
- Suite-level variables (persist across tests)
- Environment variables
- Dynamic extraction from page elements
"""

from __future__ import annotations

import os
import re
import json
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class VariableStore:
    """
    Hierarchical variable storage for test execution.

    Variable scopes:
    - env: Environment variables (from system or .env file)
    - suite: Persist across all tests in a suite
    - test: Persist across steps in a single test
    - step: Temporary, cleared after each step

    Variable syntax in selectors/values:
    - ${varName} - Simple variable reference
    - ${scope.varName} - Scoped variable (e.g., ${env.BASE_URL})
    - ${varName:default} - With default value
    """

    def __init__(self):
        self._env_vars: Dict[str, Any] = {}
        self._suite_vars: Dict[str, Any] = {}
        self._test_vars: Dict[str, Any] = {}
        self._step_vars: Dict[str, Any] = {}

        # Load environment variables
        self._load_env_vars()

        # Variable pattern: ${varName} or ${scope.varName} or ${varName:default}
        self._var_pattern = re.compile(r'\$\{([^}]+)\}')

    def _load_env_vars(self):
        """Load environment variables from system and .env file."""
        # System environment
        self._env_vars = dict(os.environ)

        # Try to load .env file
        env_paths = [
            Path.cwd() / ".env",
            Path.cwd() / "data" / ".env",
            Path(__file__).parent.parent.parent.parent / ".env",
        ]

        for env_path in env_paths:
            if env_path.exists():
                try:
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                self._env_vars[key.strip()] = value.strip().strip('"\'')
                    logger.info(f"Loaded environment from {env_path}")
                except Exception as e:
                    logger.warning(f"Failed to load .env file: {e}")
                break

    def set(self, name: str, value: Any, scope: str = "test") -> None:
        """
        Set a variable in the specified scope.

        Args:
            name: Variable name
            value: Variable value
            scope: One of 'env', 'suite', 'test', 'step'
        """
        store = self._get_store(scope)
        store[name] = value
        logger.debug(f"Set variable {scope}.{name} = {value}")

    def get(self, name: str, default: Any = None, scope: Optional[str] = None) -> Any:
        """
        Get a variable, searching scopes from most specific to least.

        Search order: step -> test -> suite -> env

        Args:
            name: Variable name (can include scope prefix like "env.BASE_URL")
            default: Default value if not found
            scope: Specific scope to search (None = search all)
        """
        # Check if name includes scope prefix
        if "." in name and scope is None:
            parts = name.split(".", 1)
            if parts[0] in ("env", "suite", "test", "step"):
                scope = parts[0]
                name = parts[1]

        if scope:
            store = self._get_store(scope)
            return store.get(name, default)

        # Search all scopes
        for store in [self._step_vars, self._test_vars, self._suite_vars, self._env_vars]:
            if name in store:
                return store[name]

        return default

    def _get_store(self, scope: str) -> Dict[str, Any]:
        """Get the variable store for a scope."""
        stores = {
            "env": self._env_vars,
            "suite": self._suite_vars,
            "test": self._test_vars,
            "step": self._step_vars,
        }
        return stores.get(scope, self._test_vars)

    def resolve(self, text: str) -> str:
        """
        Resolve all variable references in a string.

        Syntax:
        - ${varName} - Simple reference
        - ${scope.varName} - Scoped reference
        - ${varName:defaultValue} - With default

        Args:
            text: String containing variable references

        Returns:
            String with variables resolved
        """
        if not text or "${" not in text:
            return text

        def replace_var(match):
            expr = match.group(1)

            # Check for default value
            if ":" in expr:
                var_part, default = expr.split(":", 1)
            else:
                var_part = expr
                default = match.group(0)  # Keep original if not found

            value = self.get(var_part)
            if value is None:
                return default

            return str(value)

        return self._var_pattern.sub(replace_var, text)

    def clear_step(self):
        """Clear step-level variables."""
        self._step_vars.clear()

    def clear_test(self):
        """Clear test-level variables (and step vars)."""
        self._step_vars.clear()
        self._test_vars.clear()

    def clear_suite(self):
        """Clear suite-level variables (and test/step vars)."""
        self._step_vars.clear()
        self._test_vars.clear()
        self._suite_vars.clear()

    def get_all(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Get all variables, optionally filtered by scope."""
        if scope:
            return dict(self._get_store(scope))

        # Merge all scopes (env -> suite -> test -> step priority)
        merged = {}
        merged.update(self._env_vars)
        merged.update(self._suite_vars)
        merged.update(self._test_vars)
        merged.update(self._step_vars)
        return merged

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Export all variables by scope."""
        return {
            "env": dict(self._env_vars),
            "suite": dict(self._suite_vars),
            "test": dict(self._test_vars),
            "step": dict(self._step_vars),
        }

    def load_from_dict(self, data: Dict[str, Dict[str, Any]]):
        """Load variables from a dictionary."""
        if "suite" in data:
            self._suite_vars.update(data["suite"])
        if "test" in data:
            self._test_vars.update(data["test"])


class ElementExtractor:
    """
    Extract values from page elements for variable storage.
    """

    @staticmethod
    async def extract_text(page, selector: str) -> Optional[str]:
        """Extract text content from an element."""
        try:
            element = page.locator(selector).first
            return await element.text_content()
        except Exception as e:
            logger.warning(f"Failed to extract text from {selector}: {e}")
            return None

    @staticmethod
    async def extract_value(page, selector: str) -> Optional[str]:
        """Extract input value from an element."""
        try:
            element = page.locator(selector).first
            return await element.input_value()
        except Exception as e:
            logger.warning(f"Failed to extract value from {selector}: {e}")
            return None

    @staticmethod
    async def extract_attribute(page, selector: str, attribute: str) -> Optional[str]:
        """Extract attribute value from an element."""
        try:
            element = page.locator(selector).first
            return await element.get_attribute(attribute)
        except Exception as e:
            logger.warning(f"Failed to extract {attribute} from {selector}: {e}")
            return None

    @staticmethod
    async def extract_count(page, selector: str) -> int:
        """Count matching elements."""
        try:
            return await page.locator(selector).count()
        except Exception as e:
            logger.warning(f"Failed to count {selector}: {e}")
            return 0

    @staticmethod
    async def extract_table_data(page, selector: str) -> List[List[str]]:
        """Extract table data as 2D array."""
        try:
            rows = page.locator(f"{selector} tr")
            count = await rows.count()

            data = []
            for i in range(count):
                row = rows.nth(i)
                cells = row.locator("td, th")
                cell_count = await cells.count()

                row_data = []
                for j in range(cell_count):
                    text = await cells.nth(j).text_content()
                    row_data.append(text.strip() if text else "")
                data.append(row_data)

            return data
        except Exception as e:
            logger.warning(f"Failed to extract table from {selector}: {e}")
            return []


# Global instance
_variable_store: Optional[VariableStore] = None


def get_variable_store() -> VariableStore:
    """Get or create the global variable store."""
    global _variable_store
    if _variable_store is None:
        _variable_store = VariableStore()
    return _variable_store
