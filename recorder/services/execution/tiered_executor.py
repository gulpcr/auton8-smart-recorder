"""
Tiered Execution Engine

Implements the layered execution strategy:
- Tier 0: Deterministic (Playwright native, no AI)
- Tier 1: Heuristic (fallback selectors, patterns)
- Tier 2: Computer Vision (visual location, verification)
- Tier 3: LLM (recovery planning only, last resort)

80% of actions should complete at Tier 0.
AI is a safety net, not a crutch.
"""

import asyncio
import logging
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Callable, Any, Dict
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

import numpy as np
import cv2

from .page_stability import PageStabilityDetector, ElementStabilityChecker
from .action_verifier import ActionVerifier, ActionOutcome, VerificationResult
from .variable_store import VariableStore, ElementExtractor, get_variable_store
from .frame_handler import FrameHandler, WindowHandler, DialogHandler
from ..global_variable_registry import get_global_registry

logger = logging.getLogger(__name__)


class ExecutionTier(Enum):
    TIER_0_DETERMINISTIC = 0
    TIER_1_HEURISTIC = 1
    TIER_2_VISION = 2
    TIER_3_LLM = 3


@dataclass
class LocatorCandidate:
    """A potential element locator with confidence score."""
    type: str  # css, xpath, aria, id, etc.
    value: str
    confidence: float
    source: str  # "primary", "fallback", "healed", "ai"


@dataclass
class ExecutionContext:
    """Context for step execution."""
    step_index: int
    step_type: str
    step_name: str
    locators: List[LocatorCandidate]
    input_value: Optional[str] = None
    expected_navigation: Optional[str] = None
    search_context: Optional[str] = None  # From previous input steps
    dom_context: Optional[dict] = None
    step_config: Optional[Any] = None  # StepConfig from schema - Optional for backward compat


@dataclass
class HealingChange:
    """Record of a healed/changed selector."""
    step_index: int
    original_selector: str
    healed_selector: str
    strategy: str
    confidence: float
    element_text: Optional[str] = None
    reason: str = ""


@dataclass
class ExecutionResult:
    """Result of step execution."""
    success: bool
    tier_used: ExecutionTier
    locator_used: Optional[LocatorCandidate]
    verification: Optional[ActionOutcome]
    duration_ms: int
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    healing_change: Optional[HealingChange] = None
    skipped: bool = False  # NEW: Step was skipped due to condition
    skip_reason: Optional[str] = None  # NEW: Why step was skipped
    tier_attempts: List[Dict[str, Any]] = field(default_factory=list)  # Per-tier attempt history


class TieredExecutor:
    """
    Executes actions using a tiered approach.

    The execution pyramid:
    - Tier 0 (80%): Direct Playwright with stability checks
    - Tier 1 (15%): Fallback locators with heuristics
    - Tier 2 (4%): Computer vision assistance
    - Tier 3 (1%): LLM recovery (constrained)
    """

    def __init__(
        self,
        page: Page,
        healing_engine=None,
        llm_engine=None,
        cv_engine=None,
        selector_engine=None,
        context=None  # BrowserContext for window handling
    ):
        self.page = page
        self._context = context
        self._healing_engine = healing_engine
        self._llm_engine = llm_engine
        self._cv_engine = cv_engine
        self._selector_engine = selector_engine

        # Stability components
        self._page_stability = PageStabilityDetector(page)
        self._element_stability = ElementStabilityChecker(page)
        self._verifier = ActionVerifier(page)

        # Frame, window, dialog handlers
        self._frame_handler = FrameHandler(page)
        self._window_handler = WindowHandler(context, page) if context else None
        self._dialog_handler = DialogHandler(page)

        # Variable store
        self._variable_store = get_variable_store()

        # Configuration
        self._tier_0_timeout_ms = 5000
        self._tier_1_timeout_ms = 3000
        self._stability_timeout_ms = 3000  # Reduced from 10s for faster execution
        self._max_tier = ExecutionTier.TIER_3_LLM

        # Change tracking
        self._healing_report: List[HealingChange] = []

    def set_max_tier(self, tier: ExecutionTier):
        """Limit maximum tier (for testing determinism)."""
        self._max_tier = tier

    def get_healing_report(self) -> List[HealingChange]:
        """Get the list of all selector changes/healings."""
        return self._healing_report

    def print_healing_report(self):
        """Print a summary of all selector changes."""
        if not self._healing_report:
            logger.info("No selector changes were needed.")
            return

        logger.info(f"\n{'='*60}")
        logger.info(f"HEALING REPORT: {len(self._healing_report)} selectors changed")
        logger.info(f"{'='*60}")

        for change in self._healing_report:
            logger.info(f"\nStep {change.step_index + 1}:")
            logger.info(f"  Original: {change.original_selector[:60]}...")
            logger.info(f"  Healed:   {change.healed_selector}")
            logger.info(f"  Strategy: {change.strategy} (confidence: {change.confidence:.2f})")
            if change.element_text:
                logger.info(f"  Text:     \"{change.element_text[:40]}\"")
            logger.info(f"  Reason:   {change.reason}")

        logger.info(f"\n{'='*60}\n")

    def set_page(self, page: Page):
        """Switch the active page (e.g., after popup/new tab)."""
        self.page = page
        self._page_stability = PageStabilityDetector(page)
        self._element_stability = ElementStabilityChecker(page)
        self._verifier = ActionVerifier(page)
        self._frame_handler.set_page(page)
        self._dialog_handler.set_page(page)
        if self._window_handler:
            self._window_handler.set_page(page)

    def set_context(self, context):
        """Set the browser context for window handling."""
        self._context = context
        if context and not self._window_handler:
            self._window_handler = WindowHandler(context, self.page)

    @property
    def variable_store(self) -> VariableStore:
        """Get the variable store."""
        return self._variable_store

    @property
    def frame_handler(self) -> FrameHandler:
        """Get the frame handler."""
        return self._frame_handler

    @property
    def window_handler(self) -> Optional[WindowHandler]:
        """Get the window handler."""
        return self._window_handler

    @property
    def dialog_handler(self) -> DialogHandler:
        """Get the dialog handler."""
        return self._dialog_handler

    def set_selector_engine(self, selector_engine):
        """Set the selector engine for ML training."""
        self._selector_engine = selector_engine

    # =========================================================================
    # STEP CONFIG HELPERS
    # =========================================================================

    def _get_execution_config(self, context: ExecutionContext):
        """Get execution config with defaults."""
        from recorder.schema.workflow import ExecutionConfig
        if context.step_config and hasattr(context.step_config, 'execution') and context.step_config.execution:
            return context.step_config.execution
        return ExecutionConfig()

    def _get_click_config(self, context: ExecutionContext):
        """Get click config with defaults."""
        from recorder.schema.workflow import ClickConfig
        if context.step_config and hasattr(context.step_config, 'click') and context.step_config.click:
            return context.step_config.click
        return ClickConfig()

    def _get_input_config(self, context: ExecutionContext):
        """Get input config with defaults."""
        from recorder.schema.workflow import InputConfig
        if context.step_config and hasattr(context.step_config, 'inputConfig') and context.step_config.inputConfig:
            return context.step_config.inputConfig
        return InputConfig()

    def _get_hover_config(self, context: ExecutionContext):
        """Get hover config with defaults."""
        from recorder.schema.workflow import HoverConfig
        if context.step_config and hasattr(context.step_config, 'hover') and context.step_config.hover:
            return context.step_config.hover
        return HoverConfig()

    def _get_select_config(self, context: ExecutionContext):
        """Get select config with defaults."""
        from recorder.schema.workflow import SelectConfig
        if context.step_config and hasattr(context.step_config, 'select') and context.step_config.select:
            return context.step_config.select
        return SelectConfig()

    def _get_stability_config(self, context: ExecutionContext):
        """Get stability config - returns None values for executor defaults."""
        from recorder.schema.workflow import StabilityConfig
        if context.step_config and hasattr(context.step_config, 'stability') and context.step_config.stability:
            return context.step_config.stability
        return StabilityConfig()

    def _get_conditions_config(self, context: ExecutionContext):
        """Get conditions config with defaults."""
        from recorder.schema.workflow import ConditionConfig
        if context.step_config and hasattr(context.step_config, 'conditions') and context.step_config.conditions:
            return context.step_config.conditions
        return ConditionConfig()

    def _get_healing_hints(self, context: ExecutionContext):
        """Get healing hints with defaults."""
        from recorder.schema.workflow import HealingHints
        if context.step_config and hasattr(context.step_config, 'healingHints') and context.step_config.healingHints:
            return context.step_config.healingHints
        return HealingHints()

    def _get_assert_config(self, context: ExecutionContext):
        """Get assert config with defaults."""
        from recorder.schema.workflow import AssertConfig
        if context.step_config and hasattr(context.step_config, 'assertConfig') and context.step_config.assertConfig:
            return context.step_config.assertConfig
        return AssertConfig()

    def _match_text(self, actual: str, expected: str, config) -> bool:
        """
        Match text based on config settings.
        Returns True if match succeeds, False otherwise.

        Match Modes:
        - equals: Exact match (after normalization)
        - contains: Expected text is found anywhere in actual
        - startsWith: Actual text starts with expected
        - endsWith: Actual text ends with expected
        - regex: Expected is a regular expression pattern
        """
        import re

        # Handle None values
        if actual is None:
            actual = ""
        if expected is None:
            expected = ""

        # Normalize whitespace if configured
        if config.normalizeWhitespace:
            actual = ' '.join(actual.split())
            expected = ' '.join(expected.split())

        # Handle case sensitivity
        if not config.caseSensitive:
            actual = actual.lower()
            expected = expected.lower()

        # Match based on mode
        if config.matchMode == "equals":
            return actual == expected
        elif config.matchMode == "contains":
            return expected in actual
        elif config.matchMode == "startsWith":
            return actual.startswith(expected)
        elif config.matchMode == "endsWith":
            return actual.endswith(expected)
        elif config.matchMode == "regex":
            try:
                flags = 0 if config.caseSensitive else re.IGNORECASE
                return bool(re.search(expected, actual, flags))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{expected}': {e}")
                return False
        else:
            return expected in actual

    def _compare_count(self, actual: int, expected: int, comparison: str) -> bool:
        """Compare count based on comparison type."""
        if comparison == "equals":
            return actual == expected
        elif comparison == "greaterThan":
            return actual > expected
        elif comparison == "lessThan":
            return actual < expected
        elif comparison == "atLeast":
            return actual >= expected
        elif comparison == "atMost":
            return actual <= expected
        else:
            return actual == expected

    def _compare_numeric_with_tolerance(
        self,
        actual: str,
        expected: str,
        tolerance: float,
        tolerance_type: str
    ) -> tuple:
        """
        Compare numeric values with tolerance.
        Returns (success: bool, message: str)

        Tolerance Types:
        - absolute: The difference must be <= tolerance (e.g., tolerance=5 means ±5)
        - percent: The difference must be <= tolerance% of expected (e.g., tolerance=10 means ±10%)
        """
        try:
            # Extract numeric values (remove currency symbols, commas, etc.)
            import re
            actual_clean = re.sub(r'[^\d.\-]', '', actual)
            expected_clean = re.sub(r'[^\d.\-]', '', expected)

            actual_num = float(actual_clean) if actual_clean else 0.0
            expected_num = float(expected_clean) if expected_clean else 0.0

            if tolerance_type == "percent":
                # Calculate percentage difference
                if expected_num == 0:
                    # Avoid division by zero
                    diff_percent = 100 if actual_num != 0 else 0
                else:
                    diff_percent = abs((actual_num - expected_num) / expected_num) * 100
                success = diff_percent <= tolerance
                return success, f"Numeric comparison: {actual_num} vs {expected_num} (diff: {diff_percent:.2f}%, tolerance: {tolerance}%)"
            else:  # absolute
                diff = abs(actual_num - expected_num)
                success = diff <= tolerance
                return success, f"Numeric comparison: {actual_num} vs {expected_num} (diff: {diff:.2f}, tolerance: ±{tolerance})"

        except (ValueError, TypeError) as e:
            return False, f"Failed to parse numeric values: actual='{actual}', expected='{expected}' - {e}"

    async def _get_storage_value(self, storage_type: str, key: str) -> tuple:
        """
        Get value from browser storage.
        Returns (success: bool, value: str, message: str)

        Storage Types:
        - localStorage: Browser's localStorage
        - sessionStorage: Browser's sessionStorage
        - cookie: Browser cookies
        """
        try:
            if storage_type == "localStorage":
                value = await self.page.evaluate("(k) => localStorage.getItem(k)", key)
                if value is None:
                    return False, "", f"localStorage key '{key}' not found"
                return True, str(value), f"localStorage['{key}'] = '{value}'"

            elif storage_type == "sessionStorage":
                value = await self.page.evaluate("(k) => sessionStorage.getItem(k)", key)
                if value is None:
                    return False, "", f"sessionStorage key '{key}' not found"
                return True, str(value), f"sessionStorage['{key}'] = '{value}'"

            elif storage_type == "cookie":
                cookies = await self.page.context.cookies()
                for cookie in cookies:
                    if cookie.get('name') == key:
                        return True, str(cookie.get('value', '')), f"cookie['{key}'] = '{cookie.get('value')}'"
                return False, "", f"Cookie '{key}' not found"

            else:
                return False, "", f"Unknown storage type: {storage_type}"

        except Exception as e:
            return False, "", f"Failed to get {storage_type} value: {e}"

    async def _get_console_messages(self, message_type: str) -> list:
        """
        Get console messages of a specific type.
        Note: Console messages must be captured by setting up a listener before page actions.

        This returns messages from the internal console buffer if available.
        """
        # Check if we have a console message buffer
        if not hasattr(self, '_console_messages'):
            self._console_messages = []

        type_map = {
            "consoleError": "error",
            "consoleWarning": "warning",
            "consoleLog": "log"
        }
        target_type = type_map.get(message_type, "log")

        return [msg for msg in self._console_messages if msg.get('type') == target_type]

    def _setup_console_listener(self):
        """Set up console message listener for the page."""
        if not hasattr(self, '_console_messages'):
            self._console_messages = []

        def on_console(msg):
            self._console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': str(msg.location) if msg.location else None
            })

        self.page.on('console', on_console)

    # =========================================================================
    # VARIABLE OPERATIONS HELPERS
    # =========================================================================

    def _get_variable_config(self, context: ExecutionContext):
        """Get variable config with defaults."""
        from recorder.schema.workflow import VariableConfig
        if context.step_config and hasattr(context.step_config, 'variable') and context.step_config.variable:
            return context.step_config.variable
        return None

    async def _store_variable_with_scope(
        self,
        name: str,
        value: Any,
        scope: str,
        context: ExecutionContext,
        masked: bool = False
    ):
        """
        Store a variable with the specified scope.
        Handles both local (test/suite) and global scope.
        """
        if scope == "global":
            # Store in global registry for cross-workflow access
            registry = get_global_registry()
            var_config = self._get_variable_config(context)
            group = "default"
            persistent = True

            if var_config:
                persistent = var_config.persistent if hasattr(var_config, 'persistent') else True
                masked = var_config.masked if hasattr(var_config, 'masked') else masked

            registry.set(
                name=name,
                value=value,
                group=group,
                persistent=persistent,
                masked=masked,
                created_by=context.step_name
            )
            log_value = "***" if masked else value
            logger.info(f"Stored global variable: global.{name} = {log_value}")
        else:
            # Store in local variable store
            self._variable_store.set(name, value, scope)
            log_value = "***" if masked else value
            logger.info(f"Stored variable: {scope}.{name} = {log_value}")

    async def _execute_store_variable(self, context: ExecutionContext, locator):
        """
        Execute storeVariable action with full VariableConfig support.

        Supports:
        - Manual value assignment
        - Element text/value/attribute extraction
        - Element count
        - Page URL/title
        - Expression evaluation
        - Regex extraction
        """
        import re
        from ..expression_engine import SafeExpressionEvaluator, VariableStore as ExprVarStore

        var_config = self._get_variable_config(context)

        # Use new config if available, otherwise fall back to legacy format
        if var_config and var_config.variableName:
            var_name = var_config.variableName
            scope = var_config.scope if var_config.scope != "env" else "test"
            source = var_config.source
            masked = var_config.masked

            var_value = None

            # Determine value based on source
            if source == "manual":
                var_value = var_config.manualValue
                # Type conversion
                if var_config.valueType == "number" and var_value:
                    try:
                        var_value = float(var_value) if '.' in str(var_value) else int(var_value)
                    except ValueError:
                        pass
                elif var_config.valueType == "boolean" and var_value:
                    var_value = var_value.lower() in ("true", "1", "yes")

            elif source == "element_text":
                selector = context.locators[0].value if context.locators else None
                if selector:
                    var_value = await ElementExtractor.extract_text(self.page, selector)

            elif source == "element_value":
                selector = context.locators[0].value if context.locators else None
                if selector:
                    var_value = await ElementExtractor.extract_value(self.page, selector)

            elif source == "element_attribute":
                selector = context.locators[0].value if context.locators else None
                attr_name = var_config.attributeName or "href"
                if selector:
                    var_value = await ElementExtractor.extract_attribute(self.page, selector, attr_name)

            elif source == "element_count":
                selector = context.locators[0].value if context.locators else None
                if selector:
                    var_value = await ElementExtractor.extract_count(self.page, selector)

            elif source == "page_url":
                var_value = self.page.url

            elif source == "page_title":
                var_value = await self.page.title()

            elif source == "expression":
                # Evaluate expression with variable substitution
                if var_config.expression:
                    # Create expression evaluator with current variables
                    expr_store = ExprVarStore()
                    for name, val in self._variable_store.get_all().items():
                        expr_store.set(name, val)

                    evaluator = SafeExpressionEvaluator(expr_store)
                    var_value, _ = evaluator.evaluate(var_config.expression)

            elif source == "regex":
                # Extract using regex from element text
                selector = context.locators[0].value if context.locators else None
                if selector and var_config.regexPattern:
                    text = await ElementExtractor.extract_text(self.page, selector)
                    if text:
                        match = re.search(var_config.regexPattern, text)
                        if match:
                            group = var_config.regexGroup or 0
                            var_value = match.group(group) if group <= len(match.groups()) else match.group(0)

            # Store the variable
            await self._store_variable_with_scope(var_name, var_value, scope, context, masked)

        else:
            # Legacy format: input_value = "varName=value" or just "varName"
            if context.input_value and "=" in context.input_value:
                parts = context.input_value.split("=", 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()
            else:
                var_name = context.input_value or "extractedValue"
                # Extract from element
                if context.locators:
                    var_value = await ElementExtractor.extract_text(self.page, context.locators[0].value)
                else:
                    var_value = None

            scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
            await self._store_variable_with_scope(var_name, var_value, scope, context)

    async def _perform_single_element_assertion(
        self,
        element,
        assert_type: str,
        config,
        expected: str,
        selector: str
    ) -> tuple:
        """
        Perform assertion on a single element.
        Returns (success: bool, message: str, actual_value: str)
        """
        actual_value = ""

        try:
            if assert_type == "text":
                actual_value = await element.text_content() or ""
                # Check for numeric tolerance
                if config.numericTolerance is not None:
                    success, msg = self._compare_numeric_with_tolerance(
                        actual_value, expected,
                        config.numericTolerance, config.numericToleranceType
                    )
                    return success, msg, actual_value
                # Standard text matching
                if not self._match_text(actual_value, expected, config):
                    return False, f"expected '{expected}' ({config.matchMode}) in '{actual_value[:100]}'", actual_value
                return True, "text matches", actual_value

            elif assert_type == "visible":
                is_visible = await element.is_visible()
                return is_visible, "visible" if is_visible else "not visible", str(is_visible)

            elif assert_type == "hidden":
                is_visible = await element.is_visible()
                return not is_visible, "hidden" if not is_visible else "still visible", str(not is_visible)

            elif assert_type == "enabled":
                is_enabled = await element.is_enabled()
                return is_enabled, "enabled" if is_enabled else "disabled", str(is_enabled)

            elif assert_type == "disabled":
                is_enabled = await element.is_enabled()
                return not is_enabled, "disabled" if not is_enabled else "enabled", str(not is_enabled)

            elif assert_type == "value":
                actual_value = await element.input_value() or ""
                # Check for numeric tolerance
                if config.numericTolerance is not None:
                    success, msg = self._compare_numeric_with_tolerance(
                        actual_value, expected,
                        config.numericTolerance, config.numericToleranceType
                    )
                    return success, msg, actual_value
                if not self._match_text(actual_value, expected, config):
                    return False, f"expected '{expected}' ({config.matchMode}) in '{actual_value}'", actual_value
                return True, "value matches", actual_value

            elif assert_type == "attribute":
                if not config.attributeName:
                    return False, "no attribute name specified", ""
                actual_value = await element.get_attribute(config.attributeName) or ""
                if not self._match_text(actual_value, expected, config):
                    return False, f"attribute '{config.attributeName}' = '{actual_value}', expected '{expected}'", actual_value
                return True, f"attribute '{config.attributeName}' matches", actual_value

            elif assert_type == "checked":
                is_checked = await element.is_checked()
                return is_checked, "checked" if is_checked else "not checked", str(is_checked)

            else:
                return False, f"unsupported element assertion type: {assert_type}", ""

        except Exception as e:
            return False, f"error: {str(e)}", ""

    async def _take_assertion_screenshot(self, context: ExecutionContext, message: str):
        """Take screenshot for assertion failure evidence."""
        try:
            import os
            from datetime import datetime

            # Create screenshots directory if needed
            screenshots_dir = os.path.join(os.getcwd(), "screenshots", "assertions")
            os.makedirs(screenshots_dir, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            step_name = context.step_name.replace(" ", "_")[:30] if context.step_name else "unknown"
            filename = f"assert_fail_{step_name}_{timestamp}.png"
            filepath = os.path.join(screenshots_dir, filename)

            await self.page.screenshot(path=filepath, full_page=False)
            logger.info(f"Assertion failure screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            logger.warning(f"Failed to take assertion screenshot: {e}")
            return None

    async def _perform_assertion(
        self,
        locator: Optional[Locator],
        context: ExecutionContext,
        assert_type_override: Optional[str] = None
    ) -> tuple:
        """
        Perform assertion based on config with full feature support.
        Returns (success: bool, message: str)

        Features:
        - Multiple assertion types (text, visible, hidden, enabled, disabled, value, attribute, url, count, checked)
        - Storage assertions (localStorage, sessionStorage, cookie)
        - Console assertions (consoleError, consoleWarning, consoleLog)
        - Match modes (equals, contains, startsWith, endsWith, regex)
        - Negation support (negate=True inverts the result)
        - Custom error messages
        - Retry/polling for dynamic content
        - Collection modes (first, last, all, any, none)
        - Numeric tolerance for value comparisons
        - Screenshot on failure
        """
        import asyncio

        config = self._get_assert_config(context)
        assert_type = assert_type_override if assert_type_override else config.assertType
        expected = config.expectedValue or context.input_value or ""
        selector = context.locators[0].value if context.locators else "unknown"

        # Retry wrapper function
        async def do_assertion() -> tuple:
            return await self._execute_assertion_logic(
                locator, context, assert_type, config, expected, selector
            )

        # Handle retry logic
        if config.retryUntilPass:
            last_result = (False, "No assertion attempted")
            for attempt in range(config.maxRetries + 1):
                success, message = await do_assertion()

                # Apply negation
                if config.negate:
                    success = not success
                    if success:
                        message = f"Negated assertion passed: {message}"
                    else:
                        message = f"Negated assertion failed: {message}"

                if success:
                    return True, message

                last_result = (False, message)
                if attempt < config.maxRetries:
                    logger.debug(f"Assertion retry {attempt + 1}/{config.maxRetries}: {message}")
                    await asyncio.sleep(config.retryIntervalMs / 1000.0)

            # All retries exhausted
            success, message = last_result
        else:
            # Single attempt
            success, message = await do_assertion()

            # Apply negation
            if config.negate:
                success = not success
                if success:
                    message = f"Negated assertion passed: {message}"
                else:
                    message = f"Negated assertion failed: {message}"

        # Apply custom message if provided and assertion failed
        if not success and config.customMessage:
            message = f"{config.customMessage} (Details: {message})"

        # Take screenshot on failure if configured
        if not success and config.screenshotOnFail:
            screenshot_path = await self._take_assertion_screenshot(context, message)
            if screenshot_path:
                message = f"{message} [Screenshot: {screenshot_path}]"

        return success, message

    async def _execute_assertion_logic(
        self,
        locator: Optional[Locator],
        context: ExecutionContext,
        assert_type: str,
        config,
        expected: str,
        selector: str
    ) -> tuple:
        """
        Core assertion logic - executes the actual assertion.
        Returns (success: bool, message: str)
        """
        try:
            # Wait for condition if configured (for element assertions)
            if config.waitForCondition and locator:
                try:
                    await locator.first.wait_for(
                        state="attached",
                        timeout=config.assertTimeoutMs
                    )
                except Exception:
                    pass  # Continue with assertion even if wait fails

            # ========== PAGE-LEVEL ASSERTIONS ==========
            if assert_type == "url":
                actual_url = self.page.url
                if not self._match_text(actual_url, expected, config):
                    return False, f"URL assertion failed: expected '{expected}' ({config.matchMode}) in '{actual_url}'"
                return True, f"URL assertion passed: {actual_url}"

            elif assert_type == "title":
                actual_title = await self.page.title()
                if not self._match_text(actual_title, expected, config):
                    return False, f"Title assertion failed: expected '{expected}' ({config.matchMode}) in '{actual_title}'"
                return True, f"Title assertion passed: {actual_title}"

            # ========== STORAGE ASSERTIONS ==========
            elif assert_type in ["localStorage", "sessionStorage", "cookie"]:
                if not config.storageKey:
                    return False, f"{assert_type} assertion requires storageKey"

                found, actual_value, msg = await self._get_storage_value(assert_type, config.storageKey)
                if not found:
                    return False, msg

                if expected and not self._match_text(actual_value, expected, config):
                    return False, f"{assert_type}['{config.storageKey}'] = '{actual_value}', expected '{expected}' ({config.matchMode})"
                return True, f"{assert_type} assertion passed: {msg}"

            # ========== CONSOLE ASSERTIONS ==========
            elif assert_type in ["consoleError", "consoleWarning", "consoleLog"]:
                messages = await self._get_console_messages(assert_type)
                type_name = assert_type.replace("console", "").lower()

                if expected:
                    # Check if any message matches the expected pattern
                    for msg in messages:
                        if self._match_text(msg.get('text', ''), expected, config):
                            return True, f"Found {type_name} message matching '{expected}': {msg.get('text', '')[:100]}"
                    return False, f"No {type_name} message found matching '{expected}'. Found {len(messages)} {type_name}(s)"
                else:
                    # Just check if any messages of this type exist
                    if messages:
                        return True, f"Found {len(messages)} {type_name} message(s)"
                    return False, f"No {type_name} messages found"

            # ========== COUNT ASSERTION ==========
            elif assert_type == "count":
                if not locator:
                    return False, "No element selector for count assertion"
                actual_count = await locator.count()
                expected_count = config.expectedCount if config.expectedCount is not None else 0
                if not self._compare_count(actual_count, expected_count, config.countComparison):
                    return False, f"Count assertion failed: found {actual_count}, expected {config.countComparison} {expected_count}"
                return True, f"Count assertion passed: {actual_count} elements"

            # ========== ELEMENT ASSERTIONS WITH COLLECTION MODE ==========
            else:
                if not locator:
                    if assert_type == "hidden":
                        return True, "Element not found (considered hidden)"
                    return False, f"No element to assert on for {assert_type}"

                element_count = await locator.count()
                if element_count == 0:
                    if assert_type == "hidden":
                        return True, "No elements found (considered hidden)"
                    return False, f"No elements found for selector: {selector}"

                # Handle collection modes
                collection_mode = config.collectionMode

                if collection_mode == "first":
                    success, msg, _ = await self._perform_single_element_assertion(
                        locator.first, assert_type, config, expected, selector
                    )
                    return success, f"[first of {element_count}] {msg}"

                elif collection_mode == "last":
                    success, msg, _ = await self._perform_single_element_assertion(
                        locator.last, assert_type, config, expected, selector
                    )
                    return success, f"[last of {element_count}] {msg}"

                elif collection_mode == "all":
                    # ALL elements must pass
                    failed_indices = []
                    for i in range(element_count):
                        success, msg, _ = await self._perform_single_element_assertion(
                            locator.nth(i), assert_type, config, expected, selector
                        )
                        if not success:
                            failed_indices.append((i, msg))

                    if failed_indices:
                        failures = "; ".join([f"[{i}]: {m}" for i, m in failed_indices[:3]])
                        if len(failed_indices) > 3:
                            failures += f" ... and {len(failed_indices) - 3} more"
                        return False, f"ALL mode failed ({len(failed_indices)}/{element_count}): {failures}"
                    return True, f"ALL {element_count} elements passed assertion"

                elif collection_mode == "any":
                    # At least ONE element must pass
                    for i in range(element_count):
                        success, msg, _ = await self._perform_single_element_assertion(
                            locator.nth(i), assert_type, config, expected, selector
                        )
                        if success:
                            return True, f"ANY mode passed: element [{i}] of {element_count} matched"
                    return False, f"ANY mode failed: none of {element_count} elements matched"

                elif collection_mode == "none":
                    # NO elements should pass (all must fail)
                    for i in range(element_count):
                        success, msg, _ = await self._perform_single_element_assertion(
                            locator.nth(i), assert_type, config, expected, selector
                        )
                        if success:
                            return False, f"NONE mode failed: element [{i}] of {element_count} unexpectedly matched"
                    return True, f"NONE mode passed: no elements matched (as expected)"

                else:
                    # Default to first
                    success, msg, _ = await self._perform_single_element_assertion(
                        locator.first, assert_type, config, expected, selector
                    )
                    return success, msg

        except Exception as e:
            return False, f"Assertion error: {str(e)}"

    def _evaluate_condition(self, expression: str) -> bool:
        """
        Evaluate a simple condition expression.

        Supports:
        - ${var} - truthy check (non-empty, non-null)
        - ${var} == "value" - equality
        - ${var} != "value" - inequality
        - ${var} > 5 - numeric comparison
        - ${var} < 5 - numeric comparison
        - !${var} - negation

        Returns True if condition is met, False otherwise.
        """
        if not expression:
            return True

        expression = expression.strip()

        # Negation check
        negated = False
        if expression.startswith("!"):
            negated = True
            expression = expression[1:].strip()

        # Resolve variables in the expression
        resolved = self._variable_store.resolve(expression)

        # Handle comparison operators
        # Note: >= and <= must be checked BEFORE > and < to avoid substring match
        if " == " in resolved:
            parts = resolved.split(" == ", 1)
            left = parts[0].strip().strip('"\'')
            right = parts[1].strip().strip('"\'')
            result = left == right
        elif " != " in resolved:
            parts = resolved.split(" != ", 1)
            left = parts[0].strip().strip('"\'')
            right = parts[1].strip().strip('"\'')
            result = left != right
        elif " >= " in resolved:
            parts = resolved.split(" >= ", 1)
            try:
                left = float(parts[0].strip())
                right = float(parts[1].strip())
                result = left >= right
            except (ValueError, TypeError):
                result = False
        elif " <= " in resolved:
            parts = resolved.split(" <= ", 1)
            try:
                left = float(parts[0].strip())
                right = float(parts[1].strip())
                result = left <= right
            except (ValueError, TypeError):
                result = False
        elif " > " in resolved:
            parts = resolved.split(" > ", 1)
            try:
                left = float(parts[0].strip())
                right = float(parts[1].strip())
                result = left > right
            except (ValueError, TypeError):
                result = False
        elif " < " in resolved:
            parts = resolved.split(" < ", 1)
            try:
                left = float(parts[0].strip())
                right = float(parts[1].strip())
                result = left < right
            except (ValueError, TypeError):
                result = False
        else:
            # Simple truthy check
            result = bool(resolved) and resolved.lower() not in ("false", "0", "null", "none", "")

        return not result if negated else result

    def _check_step_conditions(self, context: ExecutionContext) -> tuple:
        """
        Check if step should be executed based on conditions.

        Returns:
            (should_execute: bool, skip_reason: Optional[str])
        """
        conditions = self._get_conditions_config(context)

        # Check skipIf first (if condition is TRUE, skip the step)
        if conditions.skipIf:
            if self._evaluate_condition(conditions.skipIf):
                return False, f"skipIf condition met: {conditions.skipIf}"

        # Check runIf (if condition is FALSE, skip the step)
        if conditions.runIf:
            if not self._evaluate_condition(conditions.runIf):
                return False, f"runIf condition not met: {conditions.runIf}"

        return True, None

    def _record_selector_attempt(
        self,
        candidate: LocatorCandidate,
        context: ExecutionContext,
        success: bool,
        duration_ms: float
    ):
        """Record selector success/failure for ML training."""
        if not self._selector_engine:
            return

        try:
            # Convert LocatorCandidate to SelectorStrategy format
            from recorder.ml.selector_engine import SelectorStrategy, SelectorType, ElementFingerprint

            # Map candidate type to SelectorType
            type_map = {
                "css": SelectorType.CSS,
                "xpath": SelectorType.XPATH_RELATIVE,
                "xpath-relative": SelectorType.XPATH_RELATIVE,
                "xpath-absolute": SelectorType.XPATH_ABSOLUTE,
                "id": SelectorType.ID,
                "data-testid": SelectorType.DATA_TESTID,
                "aria": SelectorType.ARIA_LABEL,
                "aria-label": SelectorType.ARIA_LABEL,
                "text": SelectorType.TEXT,
            }
            selector_type = type_map.get(candidate.type, SelectorType.CSS)

            selector = SelectorStrategy(
                type=selector_type,
                value=candidate.value,
                score=candidate.confidence,
                metadata={"source": candidate.source}
            )

            # Create fingerprint from dom_context if available
            fingerprint = ElementFingerprint(tag_name="unknown")
            if context.dom_context:
                from recorder.ml.selector_engine import create_fingerprint_from_dom
                try:
                    fingerprint = create_fingerprint_from_dom(context.dom_context)
                except Exception:
                    pass  # Use default fingerprint

            # Record the result
            self._selector_engine.record_selector_result(
                selector=selector,
                fingerprint=fingerprint,
                success=success,
                execution_time_ms=duration_ms
            )

        except Exception as e:
            logger.debug(f"Failed to record selector result: {e}")

    # Action types that don't require element locators
    NO_LOCATOR_ACTIONS = {
        # Frame operations
        "switchFrame", "switchFrameByName", "switchFrameByIndex",
        "switchMainFrame", "switchParentFrame",
        # Window operations
        "switchWindow", "switchWindowByIndex", "switchNewWindow", "closeWindow",
        # Dialog operations
        "handleAlert", "handleConfirm", "handlePrompt", "setDialogHandler",
        # Variable operations (without element extraction)
        "storeVariable", "assertVariable", "setVariable", "evaluate",
        # Wait operations (without element)
        "wait", "waitForNavigation", "waitForUrl",
        # Screenshot
        "screenshot",
    }

    async def execute_step(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute a step using tiered approach.

        Flow:
        0. Check step conditions (runIf/skipIf)
        1. Wait for page stability
        2. Try Tier 0 (deterministic)
        3. If failed, try Tier 1 (heuristic)
        4. If failed, try Tier 2 (vision)
        5. If failed, try Tier 3 (LLM)
        6. Verify outcome at each tier
        """
        start_time = time.time()

        if self.page.is_closed():
            return ExecutionResult(
                success=False,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=0,
                error="Page closed before step"
            )

        # Step 0: Check conditions (runIf/skipIf)
        should_execute, skip_reason = self._check_step_conditions(context)
        if not should_execute:
            logger.info(f"Step {context.step_index + 1}: SKIPPED - {skip_reason}")
            return ExecutionResult(
                success=True,  # Skipped steps are considered successful
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=int((time.time() - start_time) * 1000),
                skipped=True,
                skip_reason=skip_reason
            )

        # Handle actions that don't require element locators
        if context.step_type in self.NO_LOCATOR_ACTIONS:
            return await self._execute_no_locator_action(context, start_time)

        # Step 1: Ensure page stability before any action
        logger.debug(f"Step {context.step_index + 1}: Waiting for page stability...")
        stability = await self._page_stability.wait_for_stability(
            timeout_ms=self._stability_timeout_ms
        )

        if self.page.is_closed():
            return ExecutionResult(
                success=False,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=0,
                error="Page closed during stability check"
            )

        if not stability.is_stable:
            logger.warning(f"Step {context.step_index + 1}: Page not fully stable, proceeding with caution")

        # Step 2: Try each tier in order
        tier_attempts = []
        for tier in ExecutionTier:
            if tier.value > self._max_tier.value:
                break

            result = await self._execute_at_tier(tier, context)

            tier_attempts.append({
                "tier": tier.name,
                "success": result.success,
                "error": result.error or "",
                "locator_tried": result.locator_used.value if result.locator_used else "",
            })

            if result.success:
                result.tier_attempts = tier_attempts
                result.duration_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Step {context.step_index + 1}: SUCCESS at {tier.name} "
                    f"in {result.duration_ms}ms"
                )
                return result

            logger.debug(f"Step {context.step_index + 1}: {tier.name} failed, trying next tier")

        # All tiers failed
        duration_ms = int((time.time() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            tier_used=self._max_tier,
            locator_used=None,
            verification=None,
            duration_ms=duration_ms,
            error="All execution tiers failed",
            tier_attempts=tier_attempts
        )

    async def _execute_no_locator_action(
        self,
        context: ExecutionContext,
        start_time: float
    ) -> ExecutionResult:
        """
        Execute actions that don't require element locators.
        These are typically page-level or context-level operations.
        """
        action_type = context.step_type

        try:
            # Frame operations
            if action_type == "switchFrame":
                selector = context.input_value or (context.locators[0].value if context.locators else None)
                if selector:
                    success = await self._frame_handler.switch_to_frame(selector)
                    if not success:
                        raise Exception(f"Failed to switch to frame: {selector}")
                else:
                    raise Exception("No selector provided for switchFrame")

            elif action_type == "switchFrameByName":
                name = context.input_value
                if name:
                    success = await self._frame_handler.switch_to_frame_by_name(name)
                    if not success:
                        raise Exception(f"Failed to switch to frame by name: {name}")
                else:
                    raise Exception("No name provided for switchFrameByName")

            elif action_type == "switchFrameByIndex":
                index = int(context.input_value or "0")
                success = await self._frame_handler.switch_to_frame_by_index(index)
                if not success:
                    raise Exception(f"Failed to switch to frame by index: {index}")

            elif action_type == "switchMainFrame":
                self._frame_handler.switch_to_main_frame()

            elif action_type == "switchParentFrame":
                self._frame_handler.switch_to_parent_frame()

            # Window operations
            elif action_type == "switchWindow":
                if not self._window_handler:
                    raise Exception("Window handler not available (no browser context)")
                identifier = context.input_value
                if identifier:
                    success = await self._window_handler.switch_to_window(identifier)
                    if success:
                        self.set_page(self._window_handler.current_page)
                    else:
                        raise Exception(f"Failed to switch to window: {identifier}")
                else:
                    raise Exception("No identifier provided for switchWindow")

            elif action_type == "switchWindowByIndex":
                if not self._window_handler:
                    raise Exception("Window handler not available (no browser context)")
                index = int(context.input_value or "0")
                success = await self._window_handler.switch_to_window_by_index(index)
                if success:
                    self.set_page(self._window_handler.current_page)
                else:
                    raise Exception(f"Failed to switch to window by index: {index}")

            elif action_type == "switchNewWindow":
                if not self._window_handler:
                    raise Exception("Window handler not available (no browser context)")
                timeout = int(context.dom_context.get("timeout", 30000)) if context.dom_context else 30000
                success = await self._window_handler.switch_to_new_window(timeout)
                if success:
                    self.set_page(self._window_handler.current_page)
                else:
                    raise Exception("No new window appeared")

            elif action_type == "closeWindow":
                if not self._window_handler:
                    raise Exception("Window handler not available (no browser context)")
                success = await self._window_handler.close_current_window()
                if success:
                    self.set_page(self._window_handler.current_page)
                else:
                    raise Exception("Failed to close window")

            # Dialog operations
            elif action_type == "handleAlert":
                action = context.input_value or "accept"
                await self._dialog_handler.handle_alert(action)

            elif action_type == "handleConfirm":
                accept = (context.input_value or "true").lower() == "true"
                await self._dialog_handler.handle_confirm(accept)

            elif action_type == "handlePrompt":
                text = context.input_value or ""
                accept = True
                if context.dom_context:
                    accept = context.dom_context.get("accept", True)
                await self._dialog_handler.handle_prompt(text, accept)

            elif action_type == "setDialogHandler":
                action = context.input_value or "accept"
                text = context.dom_context.get("text", "") if context.dom_context else ""
                enabled = context.dom_context.get("enabled", True) if context.dom_context else True
                self._dialog_handler.set_auto_handle(enabled, action, text)

            # Variable operations
            elif action_type == "storeVariable":
                # Try full VariableConfig-based handling first
                var_config = self._get_variable_config(context)
                if var_config and var_config.variableName:
                    await self._execute_store_variable(context, None)
                elif context.input_value and "=" in context.input_value:
                    # Legacy format: "name=value"
                    parts = context.input_value.split("=", 1)
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                    await self._store_variable_with_scope(var_name, var_value, scope, context)
                else:
                    raise Exception("storeVariable requires either a VariableConfig or input_value in format 'name=value'")

            elif action_type == "assertVariable":
                if not context.input_value:
                    raise Exception("No assertion provided")

                if "==" in context.input_value:
                    var_name, expected = context.input_value.split("==", 1)
                    actual = self._variable_store.get(var_name.strip())
                    if str(actual) != expected.strip():
                        raise Exception(f"Assertion failed: {var_name}=={expected}, actual={actual}")
                elif "!=" in context.input_value:
                    var_name, expected = context.input_value.split("!=", 1)
                    actual = self._variable_store.get(var_name.strip())
                    if str(actual) == expected.strip():
                        raise Exception(f"Assertion failed: {var_name}!={expected}, actual={actual}")
                else:
                    actual = self._variable_store.get(context.input_value)
                    if not actual:
                        raise Exception(f"Variable not set or empty: {context.input_value}")

            # Wait operations
            elif action_type == "wait":
                delay_ms = int(context.input_value or "1000")
                await asyncio.sleep(delay_ms / 1000)

            elif action_type == "waitForNavigation":
                timeout = int(context.input_value or "30000")
                await self.page.wait_for_load_state("networkidle", timeout=timeout)

            elif action_type == "waitForUrl":
                url_pattern = context.input_value
                timeout = int(context.dom_context.get("timeout", 30000)) if context.dom_context else 30000
                if url_pattern:
                    await self.page.wait_for_url(f"**{url_pattern}**", timeout=timeout)

            # Screenshot
            elif action_type == "screenshot":
                filename = context.input_value or f"screenshot_{context.step_index}.png"
                await self.page.screenshot(path=filename)
                logger.info(f"Screenshot saved: {filename}")

            else:
                raise Exception(f"Unknown no-locator action type: {action_type}")

            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=True,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=ActionOutcome(
                    result=VerificationResult.SUCCESS,
                    confidence=1.0,
                    details={"action": action_type},
                    duration_ms=duration_ms
                ),
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"No-locator action failed: {action_type} - {e}")
            return ExecutionResult(
                success=False,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _execute_at_tier(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute step at a specific tier."""

        if tier == ExecutionTier.TIER_0_DETERMINISTIC:
            return await self._tier_0_deterministic(context)
        elif tier == ExecutionTier.TIER_1_HEURISTIC:
            return await self._tier_1_heuristic(context)
        elif tier == ExecutionTier.TIER_2_VISION:
            return await self._tier_2_vision(context)
        elif tier == ExecutionTier.TIER_3_LLM:
            return await self._tier_3_llm(context)

        return ExecutionResult(
            success=False,
            tier_used=tier,
            locator_used=None,
            verification=None,
            duration_ms=0,
            error=f"Unknown tier: {tier}"
        )

    async def _tier_0_deterministic(self, context: ExecutionContext) -> ExecutionResult:
        """
        Tier 0: Pure deterministic execution.

        - Use primary locator only
        - Playwright's built-in waiting
        - No AI, no heuristics
        - Should handle 80% of cases
        """
        tier = ExecutionTier.TIER_0_DETERMINISTIC

        if not context.locators:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0, error="No locators provided"
            )

        # Use only primary (highest confidence) locator
        primary = context.locators[0]
        locator = self._create_locator(primary)

        try:
            # Wait for element with stability check
            await locator.first.wait_for(state="visible", timeout=self._tier_0_timeout_ms)

            # Check element stability
            is_stable, stability_details = await self._element_stability.is_element_stable(
                locator, stability_ms=150
            )

            if not is_stable:
                return ExecutionResult(
                    success=False, tier_used=tier, locator_used=primary,
                    verification=None, duration_ms=0,
                    error="Element not stable",
                    details=stability_details
                )

            # Capture state before action
            before_state = await self._verifier.capture_state(locator)

            # Execute action
            await self._perform_action(locator, context)

            # Verify outcome
            verification = await self._verify_action(locator, context, before_state)

            return ExecutionResult(
                success=verification.success,
                tier_used=tier,
                locator_used=primary,
                verification=verification,
                duration_ms=0,
                details={"stability": stability_details}
            )

        except PlaywrightTimeoutError:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=primary,
                verification=None, duration_ms=0,
                error="Element not found (timeout)"
            )
        except Exception as e:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=primary,
                verification=None, duration_ms=0,
                error=str(e)
            )

    async def _tier_1_heuristic(self, context: ExecutionContext) -> ExecutionResult:
        """
        Tier 1: Heuristic self-healing.

        - Try fallback locators in order
        - Apply pattern-specific strategies
        - Use ML scoring for candidates
        - Should handle 15% of cases
        """
        tier = ExecutionTier.TIER_1_HEURISTIC

        # Strategy 1: Try fallback locators
        for candidate in context.locators[1:]:  # Skip primary (tried in Tier 0)
            result = await self._try_locator(tier, candidate, context)
            if result.success:
                return result

        # Strategy 2: Apply pattern-specific heuristics
        pattern_result = await self._apply_pattern_heuristics(tier, context)
        if pattern_result and pattern_result.success:
            return pattern_result

        # Strategy 3: Use healing engine for similar elements
        if self._healing_engine:
            healed_result = await self._try_healed_locators(tier, context)
            if healed_result and healed_result.success:
                return healed_result

        return ExecutionResult(
            success=False, tier_used=tier, locator_used=None,
            verification=None, duration_ms=0,
            error="No fallback locators succeeded"
        )

    async def _tier_2_vision(self, context: ExecutionContext) -> ExecutionResult:
        """
        Tier 2: Computer Vision assistance.

        - Visual element location via template matching
        - OCR for text-based element finding
        - Color histogram matching
        - Should handle 4% of cases
        """
        tier = ExecutionTier.TIER_2_VISION

        if not self._cv_engine:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0,
                error="CV engine not available"
            )

        try:
            # Take current page screenshot
            screenshot_bytes = await self.page.screenshot(type="png")
            screenshot_np = cv2.imdecode(
                np.frombuffer(screenshot_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )

            # Strategy 1: If we have element fingerprint with visual hash, use template matching
            if context.dom_context and context.dom_context.get("visual_hash"):
                result = await self._cv_visual_hash_match(tier, context, screenshot_np)
                if result and result.success:
                    return result

            # Strategy 2: If we have element screenshot stored, use template matching
            if context.dom_context and context.dom_context.get("screenshot_path"):
                result = await self._cv_template_match(tier, context, screenshot_np)
                if result and result.success:
                    return result

            # Strategy 3: Use OCR to find text-based elements
            if context.dom_context and context.dom_context.get("text_content"):
                result = await self._cv_ocr_match(tier, context, screenshot_np)
                if result and result.success:
                    return result

            # Strategy 4: Find element by approximate position and appearance
            if context.dom_context and context.dom_context.get("bounding_box"):
                result = await self._cv_position_match(tier, context, screenshot_np)
                if result and result.success:
                    return result

            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0,
                error="CV strategies exhausted"
            )

        except Exception as e:
            logger.error(f"Tier 2 CV failed: {e}")
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0,
                error=f"CV error: {str(e)}"
            )

    async def _cv_visual_hash_match(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        screenshot: np.ndarray
    ) -> Optional[ExecutionResult]:
        """Find element using perceptual hash matching."""
        try:
            visual_hash = context.dom_context.get("visual_hash")
            bbox = context.dom_context.get("bounding_box", (0, 0, 100, 100))

            position = self._cv_engine.find_element_by_visual_similarity(
                screenshot, visual_hash, bbox, tolerance=80
            )

            if position:
                x, y = position
                return await self._click_at_position(tier, context, x, y)

            return None
        except Exception as e:
            logger.debug(f"CV visual hash match failed: {e}")
            return None

    async def _cv_template_match(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        screenshot: np.ndarray
    ) -> Optional[ExecutionResult]:
        """Find element using template matching."""
        try:
            screenshot_path = context.dom_context.get("screenshot_path")
            if not screenshot_path:
                return None

            # Load template image
            template = cv2.imread(screenshot_path)
            if template is None:
                return None

            match = self._cv_engine.template_match(screenshot, template, threshold=0.75)
            if match:
                x, y, confidence = match
                # Click at center of matched region
                center_x = x + template.shape[1] // 2
                center_y = y + template.shape[0] // 2
                logger.info(f"CV template match found at ({center_x}, {center_y}) with confidence {confidence:.2f}")
                return await self._click_at_position(tier, context, center_x, center_y)

            return None
        except Exception as e:
            logger.debug(f"CV template match failed: {e}")
            return None

    async def _cv_ocr_match(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        screenshot: np.ndarray
    ) -> Optional[ExecutionResult]:
        """Find element using OCR text matching."""
        try:
            target_text = context.dom_context.get("text_content", "").strip()
            if not target_text or len(target_text) < 2:
                return None

            # Use Playwright's text locator as fallback with OCR-detected regions
            text_locator = self.page.get_by_text(target_text, exact=False)
            count = await text_locator.count()

            if count > 0:
                candidate = LocatorCandidate(
                    type="text", value=target_text,
                    confidence=0.7, source="cv_ocr"
                )
                return await self._try_locator(tier, candidate, context)

            return None
        except Exception as e:
            logger.debug(f"CV OCR match failed: {e}")
            return None

    async def _cv_position_match(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        screenshot: np.ndarray
    ) -> Optional[ExecutionResult]:
        """Find element by approximate position with visual verification."""
        try:
            bbox = context.dom_context.get("bounding_box")
            if not bbox or bbox == (0, 0, 0, 0):
                return None

            x, y, w, h = bbox
            center_x = x + w // 2
            center_y = y + h // 2

            # Get element at this position
            element_at_point = await self.page.evaluate(
                "(coords) => document.elementFromPoint(coords[0], coords[1])",
                [int(center_x), int(center_y)]
            )

            if element_at_point:
                # Try to click at the stored position
                return await self._click_at_position(tier, context, center_x, center_y)

            return None
        except Exception as e:
            logger.debug(f"CV position match failed: {e}")
            return None

    async def _click_at_position(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        x: int,
        y: int
    ) -> ExecutionResult:
        """Click at specific screen coordinates."""
        try:
            # Capture before state
            before_url = self.page.url

            # Perform click at coordinates
            await self.page.mouse.click(x, y)
            await asyncio.sleep(0.3)  # Brief wait for response

            # Simple verification: check if page changed or element responded
            after_url = self.page.url
            navigation_occurred = after_url != before_url

            candidate = LocatorCandidate(
                type="coordinates", value=f"({x}, {y})",
                confidence=0.6, source="cv_position"
            )

            return ExecutionResult(
                success=True,
                tier_used=tier,
                locator_used=candidate,
                verification=ActionOutcome(
                    result=VerificationResult.SUCCESS,
                    confidence=0.7,
                    details={"coordinates": (x, y), "navigation": navigation_occurred},
                    duration_ms=0
                ),
                duration_ms=0,
                details={"method": "cv_position_click", "x": x, "y": y}
            )

        except Exception as e:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0,
                error=f"Position click failed: {e}"
            )

    async def _tier_3_llm(self, context: ExecutionContext) -> ExecutionResult:
        """
        Tier 3: LLM Recovery (LAST RESORT ONLY).

        - Constrained to recovery planning
        - Must validate all suggestions
        - Should handle only 1% of cases
        """
        tier = ExecutionTier.TIER_3_LLM

        if not self._llm_engine or not self._llm_engine.available:
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=None,
                verification=None, duration_ms=0,
                error="LLM engine not available"
            )

        # LLM is used ONLY for:
        # 1. Recovery planning (what to do next)
        # 2. Candidate disambiguation (which element to choose)
        # NOT for direct element finding

        # Get page state for LLM context
        page_info = await self._get_page_info_for_llm()

        # Ask LLM for recovery strategy
        recovery = await self._llm_recovery_plan(context, page_info)

        if recovery.get("action") == "retry_with_selector":
            suggested_selector = recovery.get("selector")
            if suggested_selector:
                # MUST validate before using
                validated = await self._validate_llm_suggestion(suggested_selector)
                if validated:
                    candidate = LocatorCandidate(
                        type="css", value=suggested_selector,
                        confidence=0.5, source="llm"
                    )
                    return await self._try_locator(tier, candidate, context)
                else:
                    # LLM suggestion invalid - try smart element matching from page info
                    fallback_result = await self._try_smart_element_match(tier, context, page_info)
                    if fallback_result and fallback_result.success:
                        return fallback_result

        elif recovery.get("action") == "scroll_and_retry":
            # Scroll to suggested position and retry Tier 1
            scroll_y = int(recovery.get('scroll_y', 500))
            await self.page.evaluate("(y) => window.scrollTo(0, y)", scroll_y)
            await asyncio.sleep(0.5)
            return await self._tier_1_heuristic(context)

        elif recovery.get("action") == "wait_and_retry":
            # Wait for suggested condition
            await asyncio.sleep(recovery.get("wait_seconds", 2))
            return await self._tier_1_heuristic(context)

        return ExecutionResult(
            success=False, tier_used=tier, locator_used=None,
            verification=None, duration_ms=0,
            error="LLM recovery failed",
            details={"recovery_plan": recovery}
        )

    def _create_locator(self, candidate: LocatorCandidate) -> Locator:
        """Create Playwright locator from candidate."""
        value = (candidate.value or "").strip()
        if candidate.type == "css":
            return self.page.locator(value)
        elif candidate.type == "xpath":
            return self.page.locator(f"xpath={value}")
        elif candidate.type == "id":
            return self.page.locator(f"#{value.lstrip('#')}")
        elif candidate.type == "name":
            if value.startswith("[name"):
                return self.page.locator(value)
            return self.page.locator(f'[name="{value}"]')
        elif candidate.type == "data":
            if value.startswith("["):
                return self.page.locator(value)
            return self.page.locator(f'[data-testid="{value}"]')
        elif candidate.type == "aria":
            if value.startswith("[aria-"):
                return self.page.locator(value)
            return self.page.get_by_label(value)
        elif candidate.type == "label":
            if value.startswith("label:") or value.startswith("["):
                return self.page.locator(value)
            return self.page.get_by_label(value)
        elif candidate.type == "text":
            return self.page.get_by_text(value)
        elif candidate.type == "role":
            return self.page.get_by_role(value)
        else:
            return self.page.locator(value)

    async def _try_locator(
        self,
        tier: ExecutionTier,
        candidate: LocatorCandidate,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Try a single locator candidate."""
        locator = self._create_locator(candidate)
        start_time = time.time()

        try:
            await locator.first.wait_for(state="visible", timeout=self._tier_1_timeout_ms)

            # Check element stability
            is_stable, _ = await self._element_stability.is_element_stable(locator, stability_ms=100)
            if not is_stable:
                duration_ms = (time.time() - start_time) * 1000
                self._record_selector_attempt(candidate, context, False, duration_ms)
                return ExecutionResult(
                    success=False, tier_used=tier, locator_used=candidate,
                    verification=None, duration_ms=int(duration_ms), error="Element not stable"
                )

            # Capture state and execute
            before_state = await self._verifier.capture_state(locator)
            await self._perform_action(locator, context)
            verification = await self._verify_action(locator, context, before_state)

            duration_ms = (time.time() - start_time) * 1000
            self._record_selector_attempt(candidate, context, verification.success, duration_ms)

            return ExecutionResult(
                success=verification.success,
                tier_used=tier,
                locator_used=candidate,
                verification=verification,
                duration_ms=int(duration_ms)
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._record_selector_attempt(candidate, context, False, duration_ms)
            return ExecutionResult(
                success=False, tier_used=tier, locator_used=candidate,
                verification=None, duration_ms=int(duration_ms), error=str(e)
            )

    async def _perform_action(self, locator: Locator, context: ExecutionContext):
        """Perform the actual action on the element."""
        action_type = context.step_type

        if action_type in ["click", "dblclick"]:
            click_config = self._get_click_config(context)

            # Build click kwargs from config
            click_kwargs = {}
            if click_config.button != "left":
                click_kwargs["button"] = click_config.button
            if click_config.modifiers:
                click_kwargs["modifiers"] = click_config.modifiers
            if click_config.position:
                click_kwargs["position"] = click_config.position
            if click_config.force:
                click_kwargs["force"] = True
            if click_config.noWaitAfter:
                click_kwargs["no_wait_after"] = True

            # Execute click with appropriate count
            if action_type == "dblclick" or click_config.clickCount == 2:
                await locator.first.dblclick(**click_kwargs)
            else:
                await locator.first.click(click_count=click_config.clickCount, **click_kwargs)

        elif action_type in ["input", "type", "change"]:
            input_config = self._get_input_config(context)
            value = context.input_value or ""

            # Check if it's a select element
            tag = await locator.first.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                select_config = self._get_select_config(context)
                if select_config.selectBy == "label":
                    await locator.first.select_option(label=value)
                elif select_config.selectBy == "index":
                    await locator.first.select_option(index=int(value))
                else:
                    await locator.first.select_option(value=value)
            else:
                # Clear first if configured
                if input_config.clearFirst:
                    await locator.first.fill("")

                # Type based on mode
                if input_config.typeMode == "type":
                    # Keystroke-by-keystroke typing
                    await locator.first.type(value, delay=input_config.typeDelayMs)
                else:
                    # Instant fill (default)
                    await locator.first.fill(value)

                # Press Enter after if configured
                if input_config.pressEnterAfter:
                    await locator.first.press("Enter")

        elif action_type == "hover":
            hover_config = self._get_hover_config(context)

            hover_kwargs = {}
            if hover_config.position:
                hover_kwargs["position"] = hover_config.position
            if hover_config.force:
                hover_kwargs["force"] = True

            await locator.first.hover(**hover_kwargs)

            # Hold hover if duration specified
            if hover_config.hoverDurationMs > 0:
                await asyncio.sleep(hover_config.hoverDurationMs / 1000)

        elif action_type == "contextmenu":
            await locator.first.click(button="right")

        elif action_type == "scroll":
            await locator.first.scroll_into_view_if_needed()

        elif action_type == "check":
            # Check a checkbox or radio button
            await locator.first.check()

        elif action_type == "uncheck":
            # Uncheck a checkbox
            await locator.first.uncheck()

        elif action_type == "submit":
            try:
                tag = await locator.first.evaluate("el => el.tagName.toLowerCase()")
                if tag == "form":
                    await locator.first.evaluate(
                        "el => (el.requestSubmit ? el.requestSubmit() : el.submit())"
                    )
                else:
                    await locator.first.evaluate(
                        """el => {
                            const form = el.form || el.closest('form');
                            if (form) {
                                if (form.requestSubmit) { form.requestSubmit(el); }
                                else { form.submit(); }
                            } else {
                                el.click();
                            }
                        }"""
                    )
            except Exception:
                await locator.first.click()

        elif action_type == "press":
            # Handle keyboard press (special keys like Enter, Tab, etc.)
            key = context.input_value or "Enter"
            # Focus the element first, then press the key
            await locator.first.focus()
            await locator.first.press(key)

        elif action_type in ["keydown", "keyup"]:
            # Legacy keydown/keyup - treat as press
            key = context.input_value or context.dom_context.get("key", "Enter") if context.dom_context else "Enter"
            await locator.first.focus()
            await locator.first.press(key)

        # ==================== FRAME OPERATIONS ====================
        elif action_type == "switchFrame":
            # Switch to iframe/frame by selector
            selector = context.input_value or (context.locators[0].value if context.locators else None)
            if selector:
                success = await self._frame_handler.switch_to_frame(selector)
                if not success:
                    raise Exception(f"Failed to switch to frame: {selector}")
            else:
                raise Exception("No selector provided for switchFrame")

        elif action_type == "switchFrameByName":
            # Switch to frame by name or id
            name = context.input_value
            if name:
                success = await self._frame_handler.switch_to_frame_by_name(name)
                if not success:
                    raise Exception(f"Failed to switch to frame by name: {name}")
            else:
                raise Exception("No name provided for switchFrameByName")

        elif action_type == "switchFrameByIndex":
            # Switch to frame by index
            index = int(context.input_value or "0")
            success = await self._frame_handler.switch_to_frame_by_index(index)
            if not success:
                raise Exception(f"Failed to switch to frame by index: {index}")

        elif action_type == "switchMainFrame":
            # Switch back to main/top frame
            self._frame_handler.switch_to_main_frame()

        elif action_type == "switchParentFrame":
            # Switch to parent frame
            self._frame_handler.switch_to_parent_frame()

        # ==================== WINDOW OPERATIONS ====================
        elif action_type == "switchWindow":
            # Switch to window by URL, title, or handle
            if not self._window_handler:
                raise Exception("Window handler not available (no browser context)")
            identifier = context.input_value
            if identifier:
                success = await self._window_handler.switch_to_window(identifier)
                if success:
                    self.set_page(self._window_handler.current_page)
                else:
                    raise Exception(f"Failed to switch to window: {identifier}")
            else:
                raise Exception("No identifier provided for switchWindow")

        elif action_type == "switchWindowByIndex":
            # Switch to window by index
            if not self._window_handler:
                raise Exception("Window handler not available (no browser context)")
            index = int(context.input_value or "0")
            success = await self._window_handler.switch_to_window_by_index(index)
            if success:
                self.set_page(self._window_handler.current_page)
            else:
                raise Exception(f"Failed to switch to window by index: {index}")

        elif action_type == "switchNewWindow":
            # Wait for and switch to new window/popup
            if not self._window_handler:
                raise Exception("Window handler not available (no browser context)")
            timeout = int(context.dom_context.get("timeout", 30000)) if context.dom_context else 30000
            success = await self._window_handler.switch_to_new_window(timeout)
            if success:
                self.set_page(self._window_handler.current_page)
            else:
                raise Exception("No new window appeared")

        elif action_type == "closeWindow":
            # Close current window and switch to another
            if not self._window_handler:
                raise Exception("Window handler not available (no browser context)")
            success = await self._window_handler.close_current_window()
            if success:
                self.set_page(self._window_handler.current_page)
            else:
                raise Exception("Failed to close window")

        # ==================== DIALOG OPERATIONS ====================
        elif action_type == "handleAlert":
            # Handle alert dialog (accept or dismiss)
            action = context.input_value or "accept"
            await self._dialog_handler.handle_alert(action)

        elif action_type == "handleConfirm":
            # Handle confirm dialog
            accept = (context.input_value or "true").lower() == "true"
            await self._dialog_handler.handle_confirm(accept)

        elif action_type == "handlePrompt":
            # Handle prompt dialog with text input
            text = context.input_value or ""
            accept = True
            if context.dom_context:
                accept = context.dom_context.get("accept", True)
            await self._dialog_handler.handle_prompt(text, accept)

        elif action_type == "setDialogHandler":
            # Configure automatic dialog handling
            action = context.input_value or "accept"
            text = context.dom_context.get("text", "") if context.dom_context else ""
            enabled = context.dom_context.get("enabled", True) if context.dom_context else True
            self._dialog_handler.set_auto_handle(enabled, action, text)

        # ==================== VARIABLE OPERATIONS ====================
        elif action_type == "storeVariable":
            # Store a value in variable store (enhanced with VariableConfig support)
            await self._execute_store_variable(context, locator)

        elif action_type == "storeText":
            # Extract text from element and store in variable
            var_name = context.input_value or "extractedText"
            selector = context.locators[0].value if context.locators else None
            if selector:
                text = await ElementExtractor.extract_text(self.page, selector)
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(var_name, text, scope, context)
                logger.info(f"Stored text: {scope}.{var_name} = {text}")

        elif action_type == "storeValue":
            # Extract input value and store in variable
            var_name = context.input_value or "extractedValue"
            selector = context.locators[0].value if context.locators else None
            if selector:
                value = await ElementExtractor.extract_value(self.page, selector)
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(var_name, value, scope, context)
                logger.info(f"Stored value: {scope}.{var_name} = {value}")

        elif action_type == "storeAttribute":
            # Extract attribute value and store in variable
            var_name = context.input_value or "extractedAttr"
            attribute = context.dom_context.get("attribute", "href") if context.dom_context else "href"
            selector = context.locators[0].value if context.locators else None
            if selector:
                value = await ElementExtractor.extract_attribute(self.page, selector, attribute)
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(var_name, value, scope, context)
                logger.info(f"Stored attribute: {scope}.{var_name} = {value}")

        elif action_type == "storeCount":
            # Count matching elements and store in variable
            var_name = context.input_value or "elementCount"
            selector = context.locators[0].value if context.locators else None
            if selector:
                count = await ElementExtractor.extract_count(self.page, selector)
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(var_name, count, scope, context)
                logger.info(f"Stored count: {scope}.{var_name} = {count}")

        elif action_type == "assertVariable":
            # Assert variable has expected value
            # input_value format: "varName==expectedValue" or "varName!=expectedValue"
            if not context.input_value:
                raise Exception("No assertion provided")

            if "==" in context.input_value:
                var_name, expected = context.input_value.split("==", 1)
                actual = self._variable_store.get(var_name.strip())
                if str(actual) != expected.strip():
                    raise Exception(f"Assertion failed: {var_name}=={expected}, actual={actual}")
            elif "!=" in context.input_value:
                var_name, expected = context.input_value.split("!=", 1)
                actual = self._variable_store.get(var_name.strip())
                if str(actual) == expected.strip():
                    raise Exception(f"Assertion failed: {var_name}!={expected}, actual={actual}")
            else:
                # Just check variable exists and is truthy
                actual = self._variable_store.get(context.input_value)
                if not actual:
                    raise Exception(f"Variable not set or empty: {context.input_value}")

        elif action_type == "setVariable":
            # Set a variable directly (simpler than storeVariable)
            # input_value format: "varName=value"
            if context.input_value and "=" in context.input_value:
                parts = context.input_value.split("=", 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()
                # Resolve any variable references in the value
                var_value = self._variable_store.resolve(var_value)
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(var_name, var_value, scope, context)
            else:
                raise Exception("setVariable requires input_value in format 'name=value'")

        elif action_type == "extractVariable":
            # Extract variable using regex pattern
            # Similar to storeVariable with regex source
            var_name = context.input_value or "extractedValue"
            selector = context.locators[0].value if context.locators else None
            pattern = context.dom_context.get("pattern", r"(.+)") if context.dom_context else r"(.+)"
            group = context.dom_context.get("group", 1) if context.dom_context else 1

            if selector:
                import re
                text = await ElementExtractor.extract_text(self.page, selector)
                if text:
                    match = re.search(pattern, text)
                    if match:
                        var_value = match.group(group) if group <= len(match.groups()) else match.group(0)
                        scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                        await self._store_variable_with_scope(var_name, var_value, scope, context)
                        logger.info(f"Extracted variable: {scope}.{var_name} = {var_value}")
                    else:
                        logger.warning(f"Pattern '{pattern}' did not match text: {text[:50]}...")

        elif action_type == "evaluate":
            # Evaluate an expression and optionally store result
            # Uses CalculateConfig if available, otherwise input_value as expression
            from ..expression_engine import SafeExpressionEvaluator, VariableStore as ExprVarStore

            calc_config = None
            if context.step_config and hasattr(context.step_config, 'calculate') and context.step_config.calculate:
                calc_config = context.step_config.calculate

            expression = calc_config.expression if calc_config else context.input_value
            if not expression:
                raise Exception("No expression provided for evaluate")

            # Create expression evaluator with current variables
            expr_store = ExprVarStore()
            for name, val in self._variable_store.get_all().items():
                expr_store.set(name, val)

            evaluator = SafeExpressionEvaluator(expr_store)
            result, used_vars = evaluator.evaluate(expression)

            logger.info(f"Evaluated: {expression} = {result}")
            logger.debug(f"Variables used: {used_vars}")

            # Store result if configured
            store_as = calc_config.storeResultAs if calc_config else None
            if not store_as and context.dom_context:
                store_as = context.dom_context.get("storeAs")

            if store_as:
                scope = context.dom_context.get("scope", "test") if context.dom_context else "test"
                await self._store_variable_with_scope(store_as, result, scope, context)
                logger.info(f"Stored evaluation result: {scope}.{store_as} = {result}")

        # ==================== WAIT OPERATIONS ====================
        elif action_type == "wait":
            # Fixed delay (use sparingly)
            delay_ms = int(context.input_value or "1000")
            await asyncio.sleep(delay_ms / 1000)

        elif action_type == "waitForElement":
            # Wait for element to appear
            timeout = int(context.dom_context.get("timeout", 30000)) if context.dom_context else 30000
            state = context.dom_context.get("state", "visible") if context.dom_context else "visible"
            await locator.first.wait_for(state=state, timeout=timeout)

        elif action_type == "waitForNavigation":
            # Wait for navigation to complete
            timeout = int(context.input_value or "30000")
            await self.page.wait_for_load_state("networkidle", timeout=timeout)

        elif action_type == "waitForUrl":
            # Wait for URL to match pattern
            url_pattern = context.input_value
            timeout = int(context.dom_context.get("timeout", 30000)) if context.dom_context else 30000
            if url_pattern:
                await self.page.wait_for_url(f"**{url_pattern}**", timeout=timeout)

        # ==================== DRAG AND DROP ====================
        elif action_type == "dragTo":
            # Drag element to target
            target_selector = context.input_value
            if target_selector:
                target = self.page.locator(target_selector).first
                await locator.first.drag_to(target)
            else:
                raise Exception("No target selector for dragTo")

        elif action_type == "dragByOffset":
            # Drag element by x,y offset
            if context.input_value:
                parts = context.input_value.split(",")
                x_offset = int(parts[0].strip())
                y_offset = int(parts[1].strip()) if len(parts) > 1 else 0
                box = await locator.first.bounding_box()
                if box:
                    await self.page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    await self.page.mouse.down()
                    await self.page.mouse.move(box["x"] + box["width"]/2 + x_offset, box["y"] + box["height"]/2 + y_offset)
                    await self.page.mouse.up()

        # ==================== SCREENSHOT AND ASSERTIONS ====================
        elif action_type == "screenshot":
            # Take screenshot
            filename = context.input_value or f"screenshot_{context.step_index}.png"
            await self.page.screenshot(path=filename)
            logger.info(f"Screenshot saved: {filename}")

        elif action_type == "assert":
            # Generic assert - uses config to determine assertion type
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context)
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertText":
            # Assert element text content
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "text")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertVisible":
            # Assert element is visible
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "visible")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertNotVisible":
            # Assert element is not visible (hidden)
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "hidden")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertEnabled":
            # Assert element is enabled
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "enabled")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertChecked":
            # Assert checkbox/radio is checked
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "checked")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertDisabled":
            # Assert element is disabled
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "disabled")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertValue":
            # Assert input element value
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "value")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertAttribute":
            # Assert element attribute value
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "attribute")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertUrl":
            # Assert current page URL
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "url")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "assertCount":
            # Assert element count
            config = self._get_assert_config(context)
            success, message = await self._perform_assertion(locator, context, "count")
            if not success:
                if config.softAssert:
                    logger.warning(f"Soft assertion failed: {message}")
                else:
                    raise Exception(message)
            else:
                logger.info(message)

        elif action_type == "selectOption":
            # Handle select dropdown option
            select_config = self._get_select_config(context)
            value = context.input_value or ""
            if select_config.selectBy == "label":
                await locator.first.select_option(label=value)
            elif select_config.selectBy == "index":
                await locator.first.select_option(index=int(value))
            else:
                await locator.first.select_option(value=value)

        else:
            logger.warning(f"Unknown action type: {action_type}, skipping")
            # Don't default to click - just skip unknown actions

    async def _verify_action(
        self,
        locator: Locator,
        context: ExecutionContext,
        before_state: dict
    ) -> ActionOutcome:
        """Verify the action achieved its intended outcome."""
        action_type = context.step_type

        if action_type in ["click", "dblclick"]:
            return await self._verifier.verify_click(
                locator, before_state,
                expected_navigation=context.expected_navigation
            )

        elif action_type in ["input", "type", "change"]:
            tag = await locator.first.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                return await self._verifier.verify_select(
                    locator, context.input_value or ""
                )
            else:
                return await self._verifier.verify_input(
                    locator, context.input_value or ""
                )

        elif action_type == "hover":
            return await self._verifier.verify_hover(locator)

        elif action_type == "submit":
            return await self._verifier.verify_click(
                locator, before_state,
                expected_navigation=context.expected_navigation
            )

        else:
            # For other actions, just check element still exists
            return ActionOutcome(
                result=VerificationResult.SUCCESS,
                confidence=0.7,
                details={"action": action_type},
                duration_ms=0
            )

    async def _apply_pattern_heuristics(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Apply pattern-specific heuristics."""

        # Pattern: Filter dropdown (Brand, Series, Model selectors)
        if self._is_filter_dropdown_pattern(context):
            result = await self._handle_filter_dropdown_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Add to cart button
        if self._is_add_to_cart_pattern(context):
            result = await self._handle_add_to_cart_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Checkout button
        if self._is_checkout_pattern(context):
            result = await self._handle_checkout_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Submit button (malformed selectors, form submits)
        if self._is_submit_pattern(context):
            result = await self._handle_submit_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Dropdown menu (needs hover on parent)
        if self._is_dropdown_pattern(context):
            result = await self._handle_dropdown_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Search autocomplete (needs text match)
        if self._is_autocomplete_pattern(context):
            result = await self._handle_autocomplete_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Select option by value (robust dropdown handling)
        if self._is_select_value_pattern(context):
            result = await self._handle_select_value_pattern(tier, context)
            if result and result.success:
                return result

        # Pattern: Modal/dialog (wait for animation)
        if self._is_modal_pattern(context):
            result = await self._handle_modal_pattern(tier, context)
            if result and result.success:
                return result

        return None

    # ==================== NEW HEURISTIC PATTERNS ====================

    def _is_filter_dropdown_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is a filter dropdown (Brand, Series, Model, etc.)."""
        # Check semantic intent from domContext first
        if context.dom_context:
            intent = (context.dom_context.get("semantic_intent") or "").lower()
            if any(x in intent for x in ['brand', 'series', 'model', 'category', 'filter', 'dropdown']):
                return True

            # Check aria_label from domContext
            aria = (context.dom_context.get("aria_label") or "").lower()
            if any(x in aria for x in ['brand', 'series', 'model', 'category', 'filter']):
                return True

        # Fallback: check locators
        for loc in context.locators:
            selector = loc.value.lower()
            # Check for aria-label patterns like "Brand", "Series", "Model"
            if 'aria-label=' in selector:
                if any(x in selector for x in ['brand', 'series', 'model', 'category', 'filter']):
                    return True
            # Check for dropdown IDs
            if '#dropdown-' in selector or 'dropdown' in selector:
                return True
        return False

    async def _handle_filter_dropdown_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle filter dropdowns by semantic discovery - finding elements by text content."""
        try:
            # Extract filter type from domContext (preferred) or locators
            filter_type = None
            original_selector = ""
            original_text = ""

            # First check domContext for richer data
            if context.dom_context:
                intent = (context.dom_context.get("semantic_intent") or "").lower()
                aria = (context.dom_context.get("aria_label") or "").lower()
                text = (context.dom_context.get("text_content") or "").lower()
                original_text = context.dom_context.get("text_content") or ""

                for kw in ['brand', 'series', 'model', 'category', 'type', 'color', 'size']:
                    if kw in intent or kw in aria or kw in text:
                        filter_type = kw
                        break

            # Fallback: extract from locators
            if not filter_type:
                for loc in context.locators:
                    val_lower = loc.value.lower()
                    if 'brand' in val_lower:
                        filter_type = 'brand'
                        original_selector = loc.value
                        break
                    elif 'series' in val_lower:
                        filter_type = 'series'
                        original_selector = loc.value
                        break
                    elif 'model' in val_lower:
                        filter_type = 'model'
                        original_selector = loc.value
                        break

            if not filter_type:
                return None

            if not original_selector and context.locators:
                original_selector = context.locators[0].value

            logger.info(f"Semantic discovery: searching for '{filter_type}' filter on page")

            # Strategy 1: Find by exact text match (case-insensitive)
            text_patterns = [
                filter_type.capitalize(),  # "Brand"
                filter_type.upper(),        # "BRAND"
                filter_type.lower(),        # "brand"
                f"Select {filter_type}",    # "Select Brand"
                f"Choose {filter_type}",    # "Choose Brand"
                f"Filter by {filter_type}", # "Filter by Brand"
            ]

            for pattern in text_patterns:
                # Try button/link with text
                for tag in ['button', 'a', 'div', 'span', 'label']:
                    try:
                        locator = self.page.locator(f'{tag}:has-text("{pattern}")')
                        count = await locator.count()
                        if count > 0:
                            for i in range(min(count, 3)):
                                elem = locator.nth(i)
                                try:
                                    if await elem.is_visible(timeout=500):
                                        elem_text = await elem.inner_text(timeout=500)
                                        selector = f'{tag}:has-text("{pattern}")'

                                        candidate = LocatorCandidate(
                                            type="css", value=selector,
                                            confidence=0.8, source="semantic_discovery"
                                        )
                                        before_state = await self._verifier.capture_state(elem)
                                        await elem.click()
                                        verification = await self._verifier.verify_click(
                                            elem, before_state, context.expected_navigation
                                        )

                                        if verification.success:
                                            # Record the healing change
                                            healing = HealingChange(
                                                step_index=context.step_index,
                                                original_selector=original_selector,
                                                healed_selector=selector,
                                                strategy="semantic_text_match",
                                                confidence=0.8,
                                                element_text=elem_text[:50] if elem_text else None,
                                                reason=f"Found '{filter_type}' by text content"
                                            )
                                            self._healing_report.append(healing)
                                            logger.info(f"Semantic discovery SUCCESS: '{selector}' (text: '{elem_text[:30]}')")

                                            return ExecutionResult(
                                                success=True, tier_used=tier,
                                                locator_used=candidate, verification=verification,
                                                duration_ms=0,
                                                healing_change=healing
                                            )
                                except Exception:
                                    continue
                    except Exception:
                        continue

            # Strategy 2: Find select elements with matching options
            try:
                selects = self.page.locator('select')
                select_count = await selects.count()
                for i in range(min(select_count, 10)):
                    select = selects.nth(i)
                    try:
                        # Check if this select has an option/label matching filter_type
                        html = await select.evaluate("el => el.outerHTML")
                        if filter_type.lower() in html.lower():
                            if await select.is_visible(timeout=500):
                                selector = f'select:nth-of-type({i+1})'
                                candidate = LocatorCandidate(
                                    type="css", value=selector,
                                    confidence=0.7, source="semantic_select"
                                )
                                before_state = await self._verifier.capture_state(select)
                                await select.click()
                                verification = await self._verifier.verify_click(
                                    select, before_state, context.expected_navigation
                                )

                                if verification.success:
                                    healing = HealingChange(
                                        step_index=context.step_index,
                                        original_selector=original_selector,
                                        healed_selector=selector,
                                        strategy="semantic_select_match",
                                        confidence=0.7,
                                        element_text=f"select containing '{filter_type}'",
                                        reason=f"Found select element for '{filter_type}'"
                                    )
                                    self._healing_report.append(healing)
                                    logger.info(f"Semantic select discovery SUCCESS: {selector}")

                                    return ExecutionResult(
                                        success=True, tier_used=tier,
                                        locator_used=candidate, verification=verification,
                                        duration_ms=0,
                                        healing_change=healing
                                    )
                    except Exception:
                        continue
            except Exception:
                pass

            # Strategy 3: Find elements with aria-label or data attributes
            try:
                aria_patterns = [
                    f'[aria-label*="{filter_type}" i]',
                    f'[data-filter*="{filter_type}" i]',
                    f'[data-type*="{filter_type}" i]',
                    f'[name*="{filter_type}" i]',
                    f'[placeholder*="{filter_type}" i]',
                ]
                for aria_sel in aria_patterns:
                    locator = self.page.locator(aria_sel)
                    if await locator.count() > 0:
                        elem = locator.first
                        if await elem.is_visible(timeout=500):
                            elem_text = await elem.inner_text(timeout=500) if await elem.count() > 0 else ""
                            candidate = LocatorCandidate(
                                type="css", value=aria_sel,
                                confidence=0.85, source="semantic_aria"
                            )
                            before_state = await self._verifier.capture_state(elem)
                            await elem.click()
                            verification = await self._verifier.verify_click(
                                elem, before_state, context.expected_navigation
                            )

                            if verification.success:
                                healing = HealingChange(
                                    step_index=context.step_index,
                                    original_selector=original_selector,
                                    healed_selector=aria_sel,
                                    strategy="semantic_aria_match",
                                    confidence=0.85,
                                    element_text=elem_text[:50] if elem_text else None,
                                    reason=f"Found '{filter_type}' by aria/data attribute"
                                )
                                self._healing_report.append(healing)
                                logger.info(f"Semantic aria discovery SUCCESS: {aria_sel}")

                                return ExecutionResult(
                                    success=True, tier_used=tier,
                                    locator_used=candidate, verification=verification,
                                    duration_ms=0,
                                    healing_change=healing
                                )
            except Exception:
                pass

            logger.warning(f"Semantic discovery: could not find '{filter_type}' filter on page")
            return None

        except Exception as e:
            logger.debug(f"Filter dropdown pattern failed: {e}")
            return None

    def _is_add_to_cart_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is an add-to-cart action."""
        for loc in context.locators:
            selector = loc.value.lower()
            if any(x in selector for x in ['name="add"', 'add-to-cart', 'addtocart', 'add_to_cart']):
                return True
        # Check step name
        if context.step_name and 'cart' in context.step_name.lower():
            return True
        return False

    async def _handle_add_to_cart_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle add-to-cart buttons."""
        try:
            logger.info("Add to cart heuristic: searching for add-to-cart button")

            # Common add-to-cart selectors
            cart_selectors = [
                'button[name="add"], input[name="add"]',
                'button:has-text("Add to Cart")',
                'button:has-text("Add to Bag")',
                '[data-action="add-to-cart"]',
                '.add-to-cart, .add-to-cart-button',
                'form[action*="cart"] button[type="submit"]',
                '.product-form button[type="submit"]',
                'button.btn-addtocart, .addtocart-btn',
            ]

            for selector in cart_selectors:
                try:
                    locator = self.page.locator(selector)
                    if await locator.count() > 0:
                        elem = locator.first
                        if await elem.is_visible(timeout=1000):
                            candidate = LocatorCandidate(
                                type="css", value=selector,
                                confidence=0.8, source="cart_heuristic"
                            )
                            before_state = await self._verifier.capture_state(elem)
                            await elem.click()
                            verification = await self._verifier.verify_click(
                                elem, before_state, context.expected_navigation
                            )
                            if verification.success:
                                logger.info(f"Add to cart: found via '{selector}'")
                                return ExecutionResult(
                                    success=True, tier_used=tier,
                                    locator_used=candidate, verification=verification,
                                    duration_ms=0
                                )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Add to cart pattern failed: {e}")
            return None

    def _is_checkout_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is a checkout action."""
        for loc in context.locators:
            selector = loc.value.lower()
            if any(x in selector for x in ['checkout', 'cart-drawer', 'name="checkout"']):
                return True
        return False

    async def _handle_checkout_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle checkout buttons."""
        try:
            logger.info("Checkout heuristic: searching for checkout button")

            # Common checkout selectors
            checkout_selectors = [
                'button[name="checkout"], a[name="checkout"]',
                'button:has-text("Checkout")',
                'button:has-text("Check Out")',
                'a:has-text("Checkout")',
                '[data-action="checkout"]',
                '.checkout-button, .btn-checkout',
                'cart-drawer button[name="checkout"]',
                '.cart-drawer__checkout, .cart-summary button',
                'form[action*="checkout"] button',
            ]

            for selector in checkout_selectors:
                try:
                    locator = self.page.locator(selector)
                    if await locator.count() > 0:
                        elem = locator.first
                        if await elem.is_visible(timeout=1000):
                            candidate = LocatorCandidate(
                                type="css", value=selector,
                                confidence=0.8, source="checkout_heuristic"
                            )
                            before_state = await self._verifier.capture_state(elem)
                            await elem.click()
                            verification = await self._verifier.verify_click(
                                elem, before_state, context.expected_navigation
                            )
                            if verification.success:
                                logger.info(f"Checkout: found via '{selector}'")
                                return ExecutionResult(
                                    success=True, tier_used=tier,
                                    locator_used=candidate, verification=verification,
                                    duration_ms=0
                                )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Checkout pattern failed: {e}")
            return None

    def _is_submit_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is a submit action with potentially malformed selector."""
        if context.step_type == 'submit':
            return True
        for loc in context.locators:
            selector = loc.value.lower()
            # Malformed selectors like #[object HTMLInputElement]
            if 'object' in selector and 'html' in selector:
                return True
            if 'type="submit"' in selector or 'type=submit' in selector:
                return True
        return False

    async def _handle_submit_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle submit buttons with malformed or broken selectors."""
        try:
            logger.info("Submit heuristic: searching for submit button")

            # Common submit selectors
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'form button:not([type="button"])',
                '.submit-button, .btn-submit',
                'button:has-text("Submit")',
                'button:has-text("Continue")',
                'button:has-text("Place Order")',
                'button.primary, .btn-primary[type="submit"]',
            ]

            for selector in submit_selectors:
                try:
                    locator = self.page.locator(selector)
                    if await locator.count() > 0:
                        elem = locator.first
                        if await elem.is_visible(timeout=1000):
                            candidate = LocatorCandidate(
                                type="css", value=selector,
                                confidence=0.75, source="submit_heuristic"
                            )
                            before_state = await self._verifier.capture_state(elem)
                            await elem.click()
                            verification = await self._verifier.verify_click(
                                elem, before_state, context.expected_navigation
                            )
                            if verification.success:
                                logger.info(f"Submit: found via '{selector}'")
                                return ExecutionResult(
                                    success=True, tier_used=tier,
                                    locator_used=candidate, verification=verification,
                                    duration_ms=0
                                )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Submit pattern failed: {e}")
            return None

    # ==================== EXISTING PATTERNS ====================

    def _is_dropdown_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is a dropdown menu pattern."""
        for loc in context.locators:
            selector = loc.value.lower()
            if any(x in selector for x in ['dropdown', 'menu', 'submenu', 'level0', 'nav-']):
                return True
        return False

    async def _handle_dropdown_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle dropdown menu by hovering parent first."""
        try:
            # Find and hover parent menu items
            menu_items = self.page.locator('li.ui-menu-item.level0, nav li, .menu > li')
            count = await menu_items.count()

            for i in range(min(count, 10)):
                item = menu_items.nth(i)
                await item.hover()
                await asyncio.sleep(0.3)

                # Try to find target within this menu
                for candidate in context.locators:
                    try:
                        locator = self._create_locator(candidate)
                        if await locator.first.is_visible(timeout=500):
                            return await self._try_locator(tier, candidate, context)
                    except Exception:
                        continue

            return None

        except Exception as e:
            logger.debug(f"Dropdown pattern failed: {e}")
            return None

    def _is_autocomplete_pattern(self, context: ExecutionContext) -> bool:
        """Check if this is an autocomplete/search pattern."""
        return bool(context.search_context)

    async def _handle_autocomplete_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle autocomplete by matching search text."""
        if not context.search_context:
            return None

        try:
            # Extract key term from search
            search_terms = context.search_context.lower().replace('-', ' ').split()
            key_terms = [t for t in search_terms if len(t) > 2 and t not in ['ink', 'toner', 'the', 'a']]
            key_term = key_terms[-1] if key_terms else context.search_context

            # Find suggestions containing the key term
            suggestions = self.page.locator(
                '[role="option"], [role="listbox"] li, .autocomplete-suggestion, '
                '.search-autocomplete li, .ui-autocomplete li, ul li a'
            )

            count = await suggestions.count()
            for i in range(min(count, 20)):
                item = suggestions.nth(i)
                try:
                    text = await item.inner_text(timeout=500)
                    if key_term.lower() in text.lower():
                        # Found matching suggestion
                        candidate = LocatorCandidate(
                            type="css", value=f":nth-match(li, {i+1})",
                            confidence=0.8, source="autocomplete_match"
                        )

                        before_state = await self._verifier.capture_state(item)
                        await item.click()
                        verification = await self._verifier.verify_click(
                            item, before_state, context.expected_navigation
                        )

                        logger.info(f"Autocomplete: found '{key_term}' in '{text[:30]}'")
                        return ExecutionResult(
                            success=verification.success,
                            tier_used=tier,
                            locator_used=candidate,
                            verification=verification,
                            duration_ms=0
                        )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Autocomplete pattern failed: {e}")
            return None

    def _is_select_value_pattern(self, context: ExecutionContext) -> bool:
        return context.step_type in ["input", "change", "type"] and bool(context.input_value)

    async def _handle_select_value_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle select elements by matching option values directly."""
        value = (context.input_value or "").strip()
        if not value or '"' in value:
            return None

        selectors = [
            f'select:has(option[value="{value}"])',
            f'select:has(option[value*="{value}"])'
        ]

        for selector in selectors:
            try:
                locator = self.page.locator(selector)
                if await locator.count() == 0:
                    continue

                elem = locator.first
                try:
                    await elem.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass

                if await elem.is_visible(timeout=1000):
                    candidate = LocatorCandidate(
                        type="css", value=selector,
                        confidence=0.8, source="select_value_heuristic"
                    )
                    before_state = await self._verifier.capture_state(elem)
                    await elem.select_option(value=value)
                    verification = await self._verifier.verify_select(elem, value)
                    return ExecutionResult(
                        success=verification.success,
                        tier_used=tier,
                        locator_used=candidate,
                        verification=verification,
                        duration_ms=0
                    )
            except Exception:
                continue

        return None

    def _is_modal_pattern(self, context: ExecutionContext) -> bool:
        """Check if this might be a modal interaction."""
        for loc in context.locators:
            selector = loc.value.lower()
            if any(x in selector for x in ['modal', 'dialog', 'overlay', 'popup']):
                return True
        return False

    async def _handle_modal_pattern(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Handle modal by waiting for animation."""
        try:
            # Wait for modal animation to complete
            await asyncio.sleep(0.5)

            # Try locators again
            for candidate in context.locators:
                result = await self._try_locator(tier, candidate, context)
                if result.success:
                    return result

            return None

        except Exception as e:
            logger.debug(f"Modal pattern failed: {e}")
            return None

    async def _try_healed_locators(
        self,
        tier: ExecutionTier,
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Try healed locators from the healing engine using proper heal_selector API."""
        if not self._healing_engine:
            return None

        try:
            # Build ElementFingerprint from context
            fingerprint = await self._build_fingerprint_from_context(context)
            if not fingerprint:
                return None

            # Build selector strategies from context locators
            selector_strategies = self._build_selector_strategies(context)

            # Get current page state (elements on page)
            page_state = await self._get_current_page_state()

            # Optionally capture screenshot for visual healing
            screenshot = None
            if self._cv_engine:
                try:
                    screenshot_bytes = await self.page.screenshot(type="png")
                    screenshot = cv2.imdecode(
                        np.frombuffer(screenshot_bytes, np.uint8),
                        cv2.IMREAD_COLOR
                    )
                except Exception:
                    pass

            # Call the healing engine with proper API
            healing_result = self._healing_engine.heal_selector(
                original_fingerprint=fingerprint,
                selector_strategies=selector_strategies,
                current_page_state=page_state,
                screenshot=screenshot
            )

            if healing_result.success:
                logger.info(
                    f"Healing succeeded via {healing_result.strategy.value} "
                    f"(confidence: {healing_result.confidence:.2f})"
                )

                # If healed by selector fallback, use that selector
                if healing_result.fallback_selector:
                    candidate = LocatorCandidate(
                        type="css", value=healing_result.fallback_selector,
                        confidence=healing_result.confidence, source="healed"
                    )
                    return await self._try_locator(tier, candidate, context)

                # If healed by visual/position match, click at position
                elif healing_result.element_data and "position" in healing_result.element_data:
                    x, y = healing_result.element_data["position"]
                    return await self._click_at_position(tier, context, x, y)

                # If healed by text match, use text locator
                elif healing_result.element_data and healing_result.element_data.get("textContent"):
                    text = healing_result.element_data["textContent"]
                    candidate = LocatorCandidate(
                        type="text", value=text,
                        confidence=healing_result.confidence, source="healed_text"
                    )
                    return await self._try_locator(tier, candidate, context)

            return None

        except Exception as e:
            logger.debug(f"Healed locators failed: {e}")
            return None

    async def _build_fingerprint_from_context(self, context: ExecutionContext):
        """Build ElementFingerprint from execution context."""
        try:
            from recorder.ml.selector_engine import ElementFingerprint

            dom_ctx = context.dom_context or {}

            return ElementFingerprint(
                tag_name=dom_ctx.get("tag_name", "div"),
                id=dom_ctx.get("id"),
                classes=dom_ctx.get("classes", []),
                attributes=dom_ctx.get("attributes", {}),
                text_content=dom_ctx.get("text_content"),
                aria_label=dom_ctx.get("aria_label"),
                bounding_box=tuple(dom_ctx.get("bounding_box", (0, 0, 0, 0))),
                visual_hash=dom_ctx.get("visual_hash"),
                parent_path=dom_ctx.get("parent_path", ""),
                sibling_count=dom_ctx.get("sibling_count", 0),
                depth=dom_ctx.get("depth", 0),
                is_in_iframe=dom_ctx.get("is_in_iframe", False),
                has_stable_attributes=dom_ctx.get("has_stable_attributes", False)
            )
        except Exception as e:
            logger.debug(f"Failed to build fingerprint: {e}")
            return None

    def _build_selector_strategies(self, context: ExecutionContext) -> list:
        """Build SelectorStrategy list from context locators."""
        try:
            from recorder.ml.selector_engine import SelectorStrategy, SelectorType

            strategies = []
            for loc in context.locators:
                # Map locator type to SelectorType
                type_map = {
                    "css": SelectorType.CSS,
                    "xpath": SelectorType.XPATH,
                    "id": SelectorType.ID,
                    "data": SelectorType.DATA_TESTID,
                    "aria": SelectorType.ARIA_LABEL,
                    "text": SelectorType.TEXT,
                    "name": SelectorType.NAME,
                }
                selector_type = type_map.get(loc.type, SelectorType.CSS)

                strategies.append(SelectorStrategy(
                    type=selector_type,
                    value=loc.value,
                    score=loc.confidence,
                    specificity=0.5
                ))

            return strategies
        except Exception as e:
            logger.debug(f"Failed to build selector strategies: {e}")
            return []

    async def _get_current_page_state(self) -> Dict[str, Any]:
        """Get current page DOM state for healing engine."""
        try:
            elements = await self.page.evaluate('''() => {
                const elements = [];
                const allElements = document.querySelectorAll('a, button, input, select, textarea, [onclick], [role="button"], [role="link"]');

                for (let i = 0; i < Math.min(allElements.length, 100); i++) {
                    const el = allElements[i];
                    const rect = el.getBoundingClientRect();

                    elements.push({
                        tagName: el.tagName.toLowerCase(),
                        id: el.id || null,
                        className: el.className || '',
                        textContent: (el.textContent || '').substring(0, 100).trim(),
                        ariaLabel: el.getAttribute('aria-label'),
                        name: el.getAttribute('name'),
                        type: el.getAttribute('type'),
                        href: el.href || null,
                        boundingBox: [
                            Math.round(rect.x),
                            Math.round(rect.y),
                            Math.round(rect.width),
                            Math.round(rect.height)
                        ],
                        attributes: {
                            'data-testid': el.getAttribute('data-testid'),
                            'role': el.getAttribute('role'),
                            'placeholder': el.getAttribute('placeholder')
                        }
                    });
                }

                return elements;
            }''')

            return {"elements": elements, "url": self.page.url}
        except Exception as e:
            logger.debug(f"Failed to get page state: {e}")
            return {"elements": []}

    async def _get_page_info_for_llm(self) -> dict:
        """Get detailed page info for LLM context."""
        try:
            return await self.page.evaluate('''() => {
                const getVisibleElements = (selector) => {
                    return Array.from(document.querySelectorAll(selector))
                        .filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0 &&
                                   rect.top < window.innerHeight && rect.bottom > 0;
                        })
                        .slice(0, 30);
                };

                const formatElement = (el) => {
                    const text = (el.innerText || '').trim().substring(0, 60);
                    const attrs = [];
                    if (el.id) attrs.push(`id="${el.id}"`);
                    if (el.name) attrs.push(`name="${el.name}"`);
                    if (el.getAttribute('aria-label')) attrs.push(`aria-label="${el.getAttribute('aria-label')}"`);
                    if (el.getAttribute('data-testid')) attrs.push(`data-testid="${el.getAttribute('data-testid')}"`);
                    if (el.type) attrs.push(`type="${el.type}"`);
                    if (el.placeholder) attrs.push(`placeholder="${el.placeholder}"`);

                    return {
                        tag: el.tagName.toLowerCase(),
                        text: text || null,
                        attrs: attrs.join(' '),
                        classes: (el.className || '').substring(0, 80)
                    };
                };

                const buttons = getVisibleElements('button, [role="button"], input[type="submit"]').map(formatElement);
                const links = getVisibleElements('a[href]').map(formatElement);
                const inputs = getVisibleElements('input, select, textarea').map(formatElement);
                const dropdowns = getVisibleElements('[aria-haspopup], .dropdown, select, [data-dropdown]').map(formatElement);

                return {
                    url: location.href,
                    title: document.title,
                    buttons: buttons,
                    links: links,
                    inputs: inputs,
                    dropdowns: dropdowns,
                    pageText: document.body.innerText.substring(0, 500)
                };
            }''')
        except Exception:
            return {"url": self.page.url}

    async def _llm_recovery_plan(self, context: ExecutionContext, page_info: dict) -> dict:
        """Get recovery plan from LLM with enhanced context."""
        if not self._llm_engine:
            return {"action": "fail"}

        # Build detailed context about what we're trying to do
        step_intent = self._describe_step_intent(context)
        failed_selectors = [l.value for l in context.locators[:3]]

        # Format visible elements for LLM
        buttons_str = self._format_elements_for_llm(page_info.get("buttons", []), "buttons")
        dropdowns_str = self._format_elements_for_llm(page_info.get("dropdowns", []), "dropdowns")
        inputs_str = self._format_elements_for_llm(page_info.get("inputs", []), "inputs")

        system_prompt = """You are a web automation selector expert. Your ONLY job is to pick an element from the visible elements list below.

CRITICAL RULES - YOU MUST FOLLOW:
1. You can ONLY suggest selectors built from the EXACT elements listed in VISIBLE BUTTONS/DROPDOWNS/INPUTS sections
2. DO NOT invent or guess selectors - use ONLY what you see in the lists
3. If no matching element exists in the lists, use action "fail"
4. Build selectors using: #id, [name="x"], [aria-label="x"], button:has-text("x")
5. Reply with valid JSON ONLY - no other text"""

        prompt = f"""FAILED STEP: {context.step_type}
INTENT: {step_intent}
INPUT VALUE: {context.input_value or 'N/A'}

TRIED SELECTORS (all failed):
{json.dumps(failed_selectors, indent=2)}

PAGE URL: {page_info.get('url', 'unknown')}
PAGE TITLE: {page_info.get('title', 'unknown')}

VISIBLE BUTTONS:
{buttons_str}

VISIBLE DROPDOWNS/SELECTS:
{dropdowns_str}

VISIBLE INPUTS:
{inputs_str}

Based on the intent "{step_intent}" and the visible elements above, suggest recovery:

{{
  "action": "retry_with_selector" | "scroll_and_retry" | "wait_and_retry" | "fail",
  "selector": "<exact CSS selector from visible elements>",
  "scroll_y": <pixels to scroll if action is scroll_and_retry>,
  "wait_seconds": <seconds to wait if action is wait_and_retry>,
  "reason": "<brief explanation>"
}}"""

        try:
            response = self._llm_engine.generate(
                prompt,
                system_prompt=system_prompt,
                format_json=True,
                max_tokens=200,
                temperature=0.2  # Lower temperature for more precise suggestions
            )

            if response:
                result = json.loads(response)
                logger.info(f"LLM suggested: {result.get('action')} - {result.get('reason', 'no reason')}")
                return result
        except Exception as e:
            logger.debug(f"LLM recovery failed: {e}")

        return {"action": "fail"}

    def _describe_step_intent(self, context: ExecutionContext) -> str:
        """Generate human-readable description of step intent."""
        step_type = context.step_type
        input_val = context.input_value

        # Extract hints from locators
        hints = []
        for loc in context.locators[:2]:
            val = loc.value.lower()
            if 'brand' in val:
                hints.append("brand filter/dropdown")
            elif 'series' in val:
                hints.append("series filter/dropdown")
            elif 'model' in val:
                hints.append("model filter/dropdown")
            elif 'cart' in val:
                hints.append("add to cart button")
            elif 'checkout' in val:
                hints.append("checkout button")
            elif 'submit' in val:
                hints.append("submit button")
            elif 'search' in val:
                hints.append("search input")

        if hints:
            element_desc = hints[0]
        else:
            element_desc = context.step_name or "element"

        if step_type == "click":
            return f"Click on {element_desc}"
        elif step_type in ["input", "type"]:
            return f"Enter '{input_val}' into {element_desc}"
        elif step_type == "select":
            return f"Select '{input_val}' from {element_desc}"
        elif step_type == "hover":
            return f"Hover over {element_desc}"
        else:
            return f"Perform {step_type} on {element_desc}"

    def _format_elements_for_llm(self, elements: list, element_type: str) -> str:
        """Format elements list for LLM prompt."""
        if not elements:
            return f"  (no visible {element_type})"

        lines = []
        for i, el in enumerate(elements[:10]):
            tag = el.get("tag", "?")
            text = el.get("text", "")
            attrs = el.get("attrs", "")
            classes = el.get("classes", "")

            desc_parts = [f"<{tag}"]
            if attrs:
                desc_parts.append(f" {attrs}")
            desc_parts.append(">")
            if text:
                desc_parts.append(f" \"{text[:40]}\"")
            if classes:
                desc_parts.append(f" class=\"{classes[:50]}\"")

            lines.append(f"  {i+1}. {''.join(desc_parts)}")

        return "\n".join(lines)

    async def _validate_llm_suggestion(self, selector: str) -> bool:
        """Validate LLM-suggested selector before using."""
        try:
            locator = self.page.locator(selector)
            count = await locator.count()
            if count == 0:
                logger.warning(f"LLM suggestion invalid: {selector} (no matches)")
                return False
            if count > 5:
                logger.warning(f"LLM suggestion ambiguous: {selector} ({count} matches)")
                return False
            return True
        except Exception:
            return False

    async def _try_smart_element_match(
        self,
        tier: ExecutionTier,
        context: ExecutionContext,
        page_info: dict
    ) -> Optional[ExecutionResult]:
        """Try to find element by matching intent to visible elements."""
        try:
            step_intent = self._describe_step_intent(context).lower()

            # Extract keywords from intent
            keywords = []
            if 'brand' in step_intent:
                keywords.extend(['brand', 'manufacturer', 'make'])
            if 'series' in step_intent:
                keywords.extend(['series', 'line', 'product line'])
            if 'model' in step_intent:
                keywords.extend(['model', 'product', 'item'])
            if 'cart' in step_intent:
                keywords.extend(['cart', 'add', 'buy', 'purchase'])
            if 'checkout' in step_intent:
                keywords.extend(['checkout', 'check out', 'proceed', 'pay'])
            if 'search' in step_intent:
                keywords.extend(['search', 'find', 'lookup'])

            # Search in dropdowns first
            for dropdown in page_info.get("dropdowns", []):
                text = (dropdown.get("text") or "").lower()
                attrs = (dropdown.get("attrs") or "").lower()
                for keyword in keywords:
                    if keyword in text or keyword in attrs:
                        # Found a match - build selector
                        selector = await self._build_selector_for_element(dropdown)
                        if selector:
                            candidate = LocatorCandidate(
                                type="css", value=selector,
                                confidence=0.6, source="smart_match"
                            )
                            result = await self._try_locator(tier, candidate, context)
                            if result.success:
                                logger.info(f"Smart match found: '{selector}' for intent '{step_intent}'")
                                return result

            # Search in buttons
            for button in page_info.get("buttons", []):
                text = (button.get("text") or "").lower()
                attrs = (button.get("attrs") or "").lower()
                for keyword in keywords:
                    if keyword in text or keyword in attrs:
                        selector = await self._build_selector_for_element(button)
                        if selector:
                            candidate = LocatorCandidate(
                                type="css", value=selector,
                                confidence=0.6, source="smart_match"
                            )
                            result = await self._try_locator(tier, candidate, context)
                            if result.success:
                                logger.info(f"Smart match found: '{selector}' for intent '{step_intent}'")
                                return result

            # Search in inputs for input actions
            if context.step_type in ["input", "type", "change"]:
                for inp in page_info.get("inputs", []):
                    text = (inp.get("text") or "").lower()
                    attrs = (inp.get("attrs") or "").lower()
                    for keyword in keywords:
                        if keyword in text or keyword in attrs:
                            selector = await self._build_selector_for_element(inp)
                            if selector:
                                candidate = LocatorCandidate(
                                    type="css", value=selector,
                                    confidence=0.6, source="smart_match"
                                )
                                result = await self._try_locator(tier, candidate, context)
                                if result.success:
                                    logger.info(f"Smart match found: '{selector}' for intent '{step_intent}'")
                                    return result

            return None
        except Exception as e:
            logger.debug(f"Smart element match failed: {e}")
            return None

    async def _build_selector_for_element(self, element: dict) -> Optional[str]:
        """Build a CSS selector from element info."""
        try:
            attrs = element.get("attrs", "")
            tag = element.get("tag", "")
            text = element.get("text", "")

            # Try id first
            if 'id="' in attrs:
                import re
                match = re.search(r'id="([^"]+)"', attrs)
                if match:
                    selector = f"#{match.group(1)}"
                    if await self._validate_llm_suggestion(selector):
                        return selector

            # Try name
            if 'name="' in attrs:
                import re
                match = re.search(r'name="([^"]+)"', attrs)
                if match:
                    selector = f'[name="{match.group(1)}"]'
                    if await self._validate_llm_suggestion(selector):
                        return selector

            # Try aria-label
            if 'aria-label="' in attrs:
                import re
                match = re.search(r'aria-label="([^"]+)"', attrs)
                if match:
                    selector = f'[aria-label="{match.group(1)}"]'
                    if await self._validate_llm_suggestion(selector):
                        return selector

            # Try data-testid
            if 'data-testid="' in attrs:
                import re
                match = re.search(r'data-testid="([^"]+)"', attrs)
                if match:
                    selector = f'[data-testid="{match.group(1)}"]'
                    if await self._validate_llm_suggestion(selector):
                        return selector

            # Try text content for buttons
            if text and tag in ["button", "a"]:
                selector = f'{tag}:has-text("{text[:30]}")'
                if await self._validate_llm_suggestion(selector):
                    return selector

            return None
        except Exception:
            return None
