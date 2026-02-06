"""
Stable Replay System

Uses the tiered execution approach for reliable test replay:
- Deterministic first (80% of actions)
- Heuristics for fallback (15%)
- AI as last resort only (5%)

Every action is verified. No fire-and-forget.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any
from urllib.parse import urlparse
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..schema.workflow import Workflow, Step, Locator as WorkflowLocator
from .execution import (
    TieredExecutor, ExecutionContext, ExecutionResult, ExecutionTier,
    LocatorCandidate, PageStabilityDetector
)
from .global_variable_registry import get_global_registry, VariableImportConfig, VariableExportConfig

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a single step execution."""
    index: int
    step_id: str
    name: str
    step_type: str
    status: str  # "passed", "failed", "skipped", "running"
    duration_ms: int
    tier_used: Optional[str] = None
    locator_used: str = ""
    error: Optional[str] = None
    timestamp: str = ""
    verification_details: Optional[dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for QML/UI consumption."""
        return {
            "stepIndex": self.index,
            "id": self.step_id,
            "name": self.name,
            "type": self.step_type,
            "status": self.status,
            "duration": self.duration_ms,
            "error": self.error or "",
            "locator": self.locator_used,
            "timestamp": self.timestamp,
            "tier": self.tier_used,
            "verification": self.verification_details,
        }


class StableReplayer:
    """
    Stable workflow replay using tiered execution.

    Key principles:
    1. Wait for page stability before every action
    2. Verify every action achieved its intent
    3. Use AI only as last resort
    4. Fail fast with clear diagnostics
    """

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._executor: Optional[TieredExecutor] = None
        self._page: Optional[Page] = None
        self._context = None

        # Threading support
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False

        # External engines (optional)
        self._healing_engine = None
        self._llm_engine = None
        self._cv_engine = None
        self._selector_engine = None

        # Callbacks
        self._on_step: Optional[Callable] = None
        self._on_step_result: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None
        self._on_workflow_loaded: Optional[Callable] = None

        # Configuration
        self._max_consecutive_failures = 3
        self._page_load_timeout_ms = 60000
        self._max_tier = ExecutionTier.TIER_3_LLM
        self._base_domain: Optional[str] = None
        self._context_listeners_attached = False

    @property
    def is_running(self) -> bool:
        return self._running

    def set_healing_engine(self, engine):
        self._healing_engine = engine
        logger.info("Healing engine configured")

    def set_llm_engine(self, engine):
        self._llm_engine = engine
        if engine and engine.available:
            logger.info("LLM engine configured (Tier 3 recovery)")

    def set_cv_engine(self, engine):
        self._cv_engine = engine
        logger.info("CV engine configured (Tier 2)")

    def set_selector_engine(self, engine):
        self._selector_engine = engine
        logger.info("Selector engine configured (ML ranking)")

    def set_max_tier(self, tier: ExecutionTier):
        """Limit maximum execution tier (for testing determinism)."""
        self._max_tier = tier
        logger.info(f"Max execution tier set to: {tier.name}")

    def on_step(self, callback: Callable):
        self._on_step = callback

    def on_step_result(self, callback: Callable):
        self._on_step_result = callback

    def on_complete(self, callback: Callable):
        self._on_complete = callback

    def on_workflow_loaded(self, callback: Callable):
        self._on_workflow_loaded = callback

    def replay(self, workflow_path: str):
        """Start replay in a background thread."""
        if self._running:
            logger.warning("Replay already running")
            return

        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._replay(workflow_path))

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        logger.info(f"Replay started for {workflow_path}")

    def stop(self):
        """Stop the current replay."""
        if self._loop and self._running:
            async def close():
                if self._browser:
                    await self._browser.close()
            asyncio.run_coroutine_threadsafe(close(), self._loop)
            self._running = False

    async def _replay(self, workflow_path: str):
        """Internal async replay implementation."""
        self._running = True
        replay_start = time.perf_counter()
        total_duration_ms = 0
        success = True
        error_msg = None

        # Load workflow
        import json
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workflow = Workflow(**data)
        except Exception as e:
            logger.error(f"Failed to load workflow: {e}")
            if self._on_complete:
                self._on_complete(False, f"Failed to load: {e}", 0)
            self._running = False
            return

        logger.info(f"Workflow loaded with {len(workflow.steps)} steps for replay")

        if self._on_workflow_loaded:
            self._on_workflow_loaded(workflow.steps)

        pw = None
        try:
            # Initialize browser
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(headless=False)
            self._page = await self._browser.new_page()
            self._context = self._page.context
            self._attach_page_events(self._page)

            # Initialize tiered executor
            self._executor = TieredExecutor(
                page=self._page,
                healing_engine=self._healing_engine,
                llm_engine=self._llm_engine,
                cv_engine=self._cv_engine,
                selector_engine=self._selector_engine,
                context=self._context
            )
            self._executor.set_max_tier(self._max_tier)

            # Import global variables before workflow execution
            workflow_name = self._get_workflow_name(workflow)
            imported_vars = await self._import_global_variables(workflow, workflow_name)
            if imported_vars:
                logger.info(f"Imported {len(imported_vars)} global variables: {list(imported_vars.keys())}")

            # Navigate to base URL
            base_url = self._get_base_url(workflow)
            if base_url:
                self._base_domain = urlparse(base_url).netloc
            if base_url:
                logger.info(f"Navigating to {base_url}")
                await self._navigate_with_stability(self._page, base_url)
            else:
                raise ValueError("No base URL found in workflow")

            # Execute steps
            consecutive_failures = 0
            last_input_value = ""  # Track for autocomplete context

            for i, step in enumerate(workflow.steps):
                page = self._page
                if not page or page.is_closed():
                    result = self._create_failure_result(i, step, "Page closed during replay")
                    self._emit_result(result)
                    success = False
                    error_msg = result.error
                    self._skip_remaining_steps(i + 1, workflow.steps)
                    break

                # Skip phantom input steps
                if step.type in ["input", "change", "type"]:
                    value = step.input.get("value", "") if step.input else ""
                    if not value:
                        result = self._create_skip_result(i, step, "Empty input value (phantom)")
                        self._emit_result(result)
                        continue

                # Check page context
                if self._should_skip_step(page, step):
                    result = self._create_skip_result(i, step, "Different page context")
                    self._emit_result(result)
                    continue

                # Build execution context
                context = self._build_context(i, step, last_input_value, workflow.steps)

                # Emit running status
                if self._on_step:
                    self._on_step(i, step.type)

                self._emit_running(i, step)

                # Execute with tiered approach
                exec_result = await self._executor.execute_step(context)

                # Build step result
                step_result = self._build_step_result(i, step, exec_result)
                self._emit_result(step_result)

                total_duration_ms += step_result.duration_ms

                # Track input values for autocomplete context
                if step.type in ["input", "change", "type"] and step_result.status == "passed":
                    value = step.input.get("value", "") if step.input else ""
                    if value:
                        last_input_value = value

                # Handle failures
                if step_result.status == "failed":
                    consecutive_failures += 1
                    if step_result.error and "Page closed" in step_result.error:
                        success = False
                        error_msg = step_result.error
                        self._skip_remaining_steps(i + 1, workflow.steps)
                        break
                    if consecutive_failures >= self._max_consecutive_failures:
                        success = False
                        error_msg = step_result.error
                        logger.error(f"Stopping after {consecutive_failures} consecutive failures")
                        self._skip_remaining_steps(i + 1, workflow.steps)
                        break
                else:
                    consecutive_failures = 0

            # Export global variables after workflow execution
            exported_vars = await self._export_global_variables(workflow, workflow_name)
            if exported_vars:
                logger.info(f"Exported {len(exported_vars)} global variables: {list(exported_vars.keys())}")

            # Brief pause to see result
            await asyncio.sleep(2)

        except Exception as e:
            logger.exception(f"Replay failed: {e}")
            success = False
            error_msg = str(e)

            # Still try to export variables even on failure
            try:
                exported_vars = await self._export_global_variables(workflow, workflow_name)
                if exported_vars:
                    logger.info(f"Exported {len(exported_vars)} variables after failure")
            except Exception as export_error:
                logger.warning(f"Failed to export variables: {export_error}")

        finally:
            self._running = False

            # Print healing report showing what changed
            if self._executor:
                self._executor.print_healing_report()

            if self._browser:
                await self._browser.close()
            if pw:
                await pw.stop()

            total_duration_ms = int((time.perf_counter() - replay_start) * 1000)
            if self._on_complete:
                self._on_complete(success, error_msg, total_duration_ms)

    async def _navigate_with_stability(self, page: Page, url: str):
        """Navigate and wait for page stability."""
        stability = PageStabilityDetector(page)

        try:
            nav_start = time.perf_counter()
            await page.goto(url, timeout=self._page_load_timeout_ms, wait_until="domcontentloaded")

            # Wait for additional stability
            await stability.wait_for_stability(timeout_ms=10000)

            nav_duration = int((time.perf_counter() - nav_start) * 1000)
            logger.info(f"Page loaded and stable in {nav_duration}ms")

        except PlaywrightTimeoutError:
            raise TimeoutError(f"Page load timeout: {url}")

    def _get_base_url(self, workflow: Workflow) -> Optional[str]:
        """Extract base URL from workflow."""
        if workflow.meta and workflow.meta.get("baseUrl"):
            return workflow.meta["baseUrl"]
        if workflow.metadata and workflow.metadata.get("baseUrl"):
            return workflow.metadata["baseUrl"]
        if workflow.steps and workflow.steps[0].page:
            return workflow.steps[0].page.get("url")
        return None

    def _should_skip_step(self, page: Page, step: Step) -> bool:
        """Check if step should be skipped due to page context mismatch."""
        if not step.page:
            return False

        step_url = step.page.get("url", "")
        current_url = page.url

        if not step_url:
            return False

        step_parsed = urlparse(step_url)
        current_parsed = urlparse(current_url)

        # Different domain = skip
        if step_parsed.netloc != current_parsed.netloc:
            return True

        # Checkout vs non-checkout = skip
        step_is_checkout = 'checkout' in step_parsed.path.lower()
        current_is_checkout = 'checkout' in current_parsed.path.lower()
        if step_is_checkout != current_is_checkout:
            return True

        return False

    def _attach_page_events(self, page: Page):
        """Attach popup/close handlers to keep active page current."""
        if not self._context_listeners_attached and self._context:
            self._context.on(
                "page",
                lambda new_page: asyncio.create_task(self._handle_new_page(new_page, "context"))
            )
            self._context_listeners_attached = True

        page.on(
            "popup",
            lambda new_page: asyncio.create_task(self._handle_new_page(new_page, "popup"))
        )
        page.on(
            "close",
            lambda: asyncio.create_task(self._handle_page_closed(page))
        )

    async def _handle_new_page(self, new_page: Page, reason: str):
        """Switch to a new page when it represents the main flow."""
        if new_page == self._page:
            return

        try:
            await new_page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        # Always switch if the current page is closed
        if not self._page or self._page.is_closed():
            self._switch_active_page(new_page, f"{reason}:current_closed")
            return

        # Otherwise, only switch if the new page matches base domain
        try:
            new_domain = urlparse(new_page.url).netloc
        except Exception:
            new_domain = ""

        if self._base_domain and new_domain == self._base_domain:
            self._switch_active_page(new_page, f"{reason}:domain_match")

    async def _handle_page_closed(self, closed_page: Page):
        """When a page closes, switch to another open page if available."""
        if closed_page != self._page or not self._context:
            return

        for candidate in self._context.pages:
            if not candidate.is_closed():
                self._switch_active_page(candidate, "page_closed")
                return

    def _switch_active_page(self, new_page: Page, reason: str):
        """Update active page and executor when switching tabs."""
        if new_page == self._page:
            return

        logger.info(f"Switching active page ({reason}): {new_page.url}")
        self._page = new_page
        self._attach_page_events(new_page)
        if self._executor:
            self._executor.set_page(new_page)

    def _build_context(
        self,
        index: int,
        step: Step,
        last_input: str,
        all_steps: List[Step]
    ) -> ExecutionContext:
        """Build execution context for a step."""
        # Convert workflow locators to candidates
        locators = []
        if step.target and step.target.locators:
            for loc in step.target.locators:
                locators.append(LocatorCandidate(
                    type=loc.type,
                    value=loc.value,
                    confidence=loc.score or 0.5,
                    source="primary"
                ))

        # Sort by confidence
        locators.sort(key=lambda x: x.confidence, reverse=True)

        # Get input value
        input_value = None
        if step.input:
            input_value = step.input.get("value", "")

        # Determine expected navigation
        expected_navigation = None
        if step.type in ["click", "dblclick"]:
            expected_navigation = self._get_expected_navigation(index, step, all_steps)

        return ExecutionContext(
            step_index=index,
            step_type=step.type,
            step_name=step.name,
            locators=locators,
            input_value=input_value,
            expected_navigation=expected_navigation,
            search_context=last_input if step.type == "click" else None,
            dom_context=step.domContext,
            step_config=step.config  # Pass step configuration for command overrides
        )

    def _get_expected_navigation(
        self,
        index: int,
        step: Step,
        all_steps: List[Step]
    ) -> Optional[str]:
        """Look ahead to determine expected navigation URL."""
        step_url = step.page.get("url", "") if step.page else ""

        for future_step in all_steps[index + 1:]:
            future_url = future_step.page.get("url", "") if future_step.page else ""
            if future_url and future_url != step_url:
                # Extract meaningful part of URL
                path = future_url.split('/')[-1].split('.')[0]
                if path and len(path) > 3:
                    return path
                break

        return None

    def _build_step_result(
        self,
        index: int,
        step: Step,
        exec_result: ExecutionResult
    ) -> StepResult:
        """Build step result from execution result."""
        return StepResult(
            index=index,
            step_id=step.id,
            name=step.name,
            step_type=step.type,
            status="passed" if exec_result.success else "failed",
            duration_ms=exec_result.duration_ms,
            tier_used=exec_result.tier_used.name if exec_result.tier_used else None,
            locator_used=exec_result.locator_used.value[:80] if exec_result.locator_used else "",
            error=exec_result.error,
            timestamp=time.strftime("%H:%M:%S"),
            verification_details=exec_result.verification.details if exec_result.verification else None
        )

    def _create_skip_result(self, index: int, step: Step, reason: str) -> StepResult:
        """Create a skip result."""
        return StepResult(
            index=index,
            step_id=step.id,
            name=step.name,
            step_type=step.type,
            status="skipped",
            duration_ms=0,
            error=f"Skipped: {reason}",
            timestamp=time.strftime("%H:%M:%S")
        )

    def _create_failure_result(self, index: int, step: Step, reason: str) -> StepResult:
        """Create a failure result without execution."""
        return StepResult(
            index=index,
            step_id=step.id,
            name=step.name,
            step_type=step.type,
            status="failed",
            duration_ms=0,
            error=reason,
            timestamp=time.strftime("%H:%M:%S")
        )

    def _emit_running(self, index: int, step: Step):
        """Emit running status."""
        if self._on_step_result:
            running = StepResult(
                index=index,
                step_id=step.id,
                name=step.name,
                step_type=step.type,
                status="running",
                duration_ms=0,
                timestamp=time.strftime("%H:%M:%S")
            )
            self._on_step_result(running)

    def _emit_result(self, result: StepResult):
        """Emit step result."""
        status_icon = {"passed": "✓", "failed": "✗", "skipped": "○"}.get(result.status, "?")
        tier_info = f" [{result.tier_used}]" if result.tier_used else ""

        logger.info(
            f"Step {result.index + 1} ({result.step_type}): "
            f"{status_icon} {result.status}{tier_info} in {result.duration_ms}ms"
            + (f" - {result.error}" if result.error else "")
        )

        if self._on_step_result:
            self._on_step_result(result)

    def _skip_remaining_steps(self, start_index: int, steps: List[Step]):
        """Skip remaining steps after failure."""
        for i in range(start_index, len(steps)):
            step = steps[i]
            result = self._create_skip_result(i, step, "Skipped due to previous failures")
            self._emit_result(result)

    def _get_workflow_name(self, workflow: Workflow) -> str:
        """Extract workflow name for variable tracking."""
        if workflow.metadata and workflow.metadata.get("name"):
            return workflow.metadata["name"]
        if workflow.meta and workflow.meta.get("name"):
            return workflow.meta["name"]
        return "unknown"

    async def _import_global_variables(
        self,
        workflow: Workflow,
        workflow_name: str
    ) -> Dict[str, Any]:
        """
        Import global variables into workflow's variable store before execution.

        Args:
            workflow: The workflow to execute
            workflow_name: Name for logging/tracking

        Returns:
            Dict of imported variable names and values

        Raises:
            ValueError: If a required variable is not found
        """
        if not workflow.variables or not workflow.variables.imports:
            return {}

        registry = get_global_registry()
        variable_store = self._executor.variable_store if self._executor else None

        if not variable_store:
            logger.warning("No variable store available for import")
            return {}

        # Convert schema imports to registry format
        imports = []
        for imp in workflow.variables.imports:
            imports.append(VariableImportConfig(
                globalName=imp.globalName,
                localName=imp.localName,
                required=imp.required,
                defaultValue=imp.defaultValue
            ))

        try:
            return registry.import_for_workflow(imports, variable_store, workflow_name)
        except ValueError as e:
            # Re-raise with context
            raise ValueError(f"Variable import failed for '{workflow_name}': {e}")

    async def _export_global_variables(
        self,
        workflow: Workflow,
        workflow_name: str
    ) -> Dict[str, Any]:
        """
        Export workflow variables to global registry after execution.

        Args:
            workflow: The executed workflow
            workflow_name: Name for logging/tracking

        Returns:
            Dict of exported variable names and values
        """
        if not workflow.variables or not workflow.variables.exports:
            return {}

        registry = get_global_registry()
        variable_store = self._executor.variable_store if self._executor else None

        if not variable_store:
            logger.warning("No variable store available for export")
            return {}

        # Convert schema exports to registry format
        exports = []
        for exp in workflow.variables.exports:
            exports.append(VariableExportConfig(
                variableName=exp.variableName,
                globalName=exp.globalName,
                group=exp.group,
                overwrite=exp.overwrite,
                persistent=exp.persistent,
                masked=exp.masked
            ))

        return registry.export_from_workflow(exports, variable_store, workflow_name)
