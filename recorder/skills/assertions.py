"""
Assertions Skill - All assertion types for workflow steps.

Always runs locally. No heavy ML dependencies.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class AssertionsSkill(SkillBase):
    name = "assertions"
    description = "Assertion engine for text, visibility, URL, storage, and more"
    local_capable = True
    server_capable = False

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run an assertion.

        kwargs:
            assert_type: str - "text", "visible", "url", "value", "attribute", etc.
            actual_value: str - the value obtained from the page/element
            expected_value: str - the expected value
            match_mode: str - "equals", "contains", "startsWith", "endsWith", "regex"
            case_sensitive: bool
            negate: bool - invert result
            custom_message: str
        """
        assert_type = kwargs.get("assert_type", "text")
        actual = kwargs.get("actual_value", "")
        expected = kwargs.get("expected_value", "")
        match_mode = kwargs.get("match_mode", "contains")
        case_sensitive = kwargs.get("case_sensitive", False)
        negate = kwargs.get("negate", False)
        custom_msg = kwargs.get("custom_message")

        passed = self._check_match(actual, expected, match_mode, case_sensitive)

        if negate:
            passed = not passed

        if passed:
            return SkillResult(
                success=True,
                data={
                    "assert_type": assert_type,
                    "passed": True,
                    "actual": actual,
                    "expected": expected,
                },
                run_location=SkillRunLocation.LOCAL,
            )

        error_msg = custom_msg or (
            f"Assertion failed: expected '{expected}' "
            f"({match_mode}) but got '{actual}'"
        )
        if negate:
            error_msg = custom_msg or (
                f"Negated assertion failed: did NOT expect '{expected}' "
                f"({match_mode}) in '{actual}'"
            )

        return SkillResult(
            success=False,
            data={
                "assert_type": assert_type,
                "passed": False,
                "actual": actual,
                "expected": expected,
            },
            error=error_msg,
            run_location=SkillRunLocation.LOCAL,
        )

    @staticmethod
    def _check_match(
        actual: str,
        expected: str,
        mode: str,
        case_sensitive: bool,
    ) -> bool:
        a = actual if case_sensitive else actual.lower()
        e = expected if case_sensitive else expected.lower()

        if mode == "equals":
            return a == e
        elif mode == "contains":
            return e in a
        elif mode == "startsWith":
            return a.startswith(e)
        elif mode == "endsWith":
            return a.endswith(e)
        elif mode == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            return bool(re.search(expected, actual, flags))

        return a == e
