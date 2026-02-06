"""
Test Suite Runner - Execute multiple workflows with shared variables

Supports:
- Sequential workflow execution
- Variable sharing between workflows via global registry
- Dependency resolution based on variable requirements
- Suite-level reporting
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
from enum import Enum

from .global_variable_registry import get_global_registry, GlobalVariableRegistry
from .stable_replay import StableReplayer, StepResult
from ..schema.workflow import Workflow

logger = logging.getLogger(__name__)


class SuiteExecutionMode(str, Enum):
    """How to execute workflows in a suite."""
    SEQUENTIAL = "sequential"  # Run in order provided
    DEPENDENCY = "dependency"  # Respect variable dependencies
    PARALLEL = "parallel"  # Run independent workflows in parallel (future)


@dataclass
class WorkflowResult:
    """Result of a single workflow execution."""
    workflow_id: str
    workflow_name: str
    success: bool
    step_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    duration_ms: int
    error: Optional[str] = None
    imported_variables: Dict[str, Any] = field(default_factory=dict)
    exported_variables: Dict[str, Any] = field(default_factory=dict)
    step_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SuiteResult:
    """Result of suite execution."""
    suite_name: str
    success: bool
    total_workflows: int
    passed_workflows: int
    failed_workflows: int
    total_steps: int
    passed_steps: int
    failed_steps: int
    duration_ms: int
    workflow_results: List[WorkflowResult] = field(default_factory=list)
    global_variables: Dict[str, Any] = field(default_factory=dict)


class SuiteRunner:
    """
    Runs multiple workflows as a test suite with shared variables.

    Variable Flow:
    1. Clear runtime variables at suite start
    2. For each workflow:
       a. Import required global variables
       b. Execute workflow steps
       c. Export variables to global registry
    3. Report suite results with all shared variables
    """

    def __init__(self):
        self._replayer: Optional[StableReplayer] = None
        self._registry: GlobalVariableRegistry = get_global_registry()

        # Callbacks
        self._on_workflow_start: Optional[Callable] = None
        self._on_workflow_complete: Optional[Callable] = None
        self._on_suite_complete: Optional[Callable] = None
        self._on_step_result: Optional[Callable] = None

        # Configuration
        self._stop_on_failure = True
        self._clear_variables_before_run = True

    def set_stop_on_failure(self, stop: bool):
        """Configure whether to stop suite on first workflow failure."""
        self._stop_on_failure = stop

    def set_clear_variables(self, clear: bool):
        """Configure whether to clear runtime variables before suite run."""
        self._clear_variables_before_run = clear

    def on_workflow_start(self, callback: Callable):
        """Set callback for workflow start."""
        self._on_workflow_start = callback

    def on_workflow_complete(self, callback: Callable):
        """Set callback for workflow completion."""
        self._on_workflow_complete = callback

    def on_suite_complete(self, callback: Callable):
        """Set callback for suite completion."""
        self._on_suite_complete = callback

    def on_step_result(self, callback: Callable):
        """Set callback for step results."""
        self._on_step_result = callback

    def set_replayer_engines(
        self,
        healing_engine=None,
        llm_engine=None,
        cv_engine=None,
        selector_engine=None
    ):
        """Configure ML engines for the replayer."""
        self._healing_engine = healing_engine
        self._llm_engine = llm_engine
        self._cv_engine = cv_engine
        self._selector_engine = selector_engine

    async def run_suite(
        self,
        workflow_paths: List[str],
        suite_name: str = "Test Suite",
        mode: SuiteExecutionMode = SuiteExecutionMode.SEQUENTIAL
    ) -> SuiteResult:
        """
        Execute multiple workflows as a test suite.

        Args:
            workflow_paths: List of workflow file paths to execute
            suite_name: Name for the suite (for reporting)
            mode: Execution mode (sequential, dependency-based)

        Returns:
            SuiteResult with aggregated results
        """
        suite_start = time.perf_counter()

        # Clear runtime variables if configured
        if self._clear_variables_before_run:
            self._registry.clear_runtime()
            logger.info("Cleared runtime variables for suite run")

        workflow_results: List[WorkflowResult] = []
        total_steps = 0
        passed_steps = 0
        failed_steps = 0

        # Resolve execution order if using dependency mode
        if mode == SuiteExecutionMode.DEPENDENCY:
            workflow_paths = await self._resolve_dependencies(workflow_paths)

        for i, workflow_path in enumerate(workflow_paths):
            logger.info(f"\n{'='*60}")
            logger.info(f"Workflow {i+1}/{len(workflow_paths)}: {Path(workflow_path).stem}")
            logger.info(f"{'='*60}")

            if self._on_workflow_start:
                self._on_workflow_start(i, workflow_path)

            # Execute workflow
            result = await self._run_single_workflow(workflow_path, i)
            workflow_results.append(result)

            # Update totals
            total_steps += result.step_count
            passed_steps += result.passed_count
            failed_steps += result.failed_count

            if self._on_workflow_complete:
                self._on_workflow_complete(i, result)

            # Check for failure
            if not result.success and self._stop_on_failure:
                logger.warning(f"Stopping suite due to workflow failure: {result.workflow_name}")
                break

        # Calculate suite results
        suite_duration = int((time.perf_counter() - suite_start) * 1000)
        passed_workflows = sum(1 for r in workflow_results if r.success)
        failed_workflows = len(workflow_results) - passed_workflows

        suite_result = SuiteResult(
            suite_name=suite_name,
            success=failed_workflows == 0,
            total_workflows=len(workflow_paths),
            passed_workflows=passed_workflows,
            failed_workflows=failed_workflows,
            total_steps=total_steps,
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            duration_ms=suite_duration,
            workflow_results=workflow_results,
            global_variables=self._registry.export_to_dict()
        )

        if self._on_suite_complete:
            self._on_suite_complete(suite_result)

        self._print_suite_summary(suite_result)
        return suite_result

    async def _run_single_workflow(
        self,
        workflow_path: str,
        index: int
    ) -> WorkflowResult:
        """Execute a single workflow and return results."""
        import json

        workflow_start = time.perf_counter()
        step_results: List[Dict[str, Any]] = []
        passed = 0
        failed = 0
        skipped = 0
        error_msg = None
        imported_vars: Dict[str, Any] = {}
        exported_vars: Dict[str, Any] = {}

        try:
            # Load workflow
            with open(workflow_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workflow = Workflow(**data)

            workflow_name = self._get_workflow_name(workflow, workflow_path)

            # Check variable dependencies
            if workflow.variables and workflow.variables.imports:
                for imp in workflow.variables.imports:
                    if imp.required and self._registry.get(imp.globalName) is None:
                        raise ValueError(
                            f"Required variable '{imp.globalName}' not available. "
                            f"Ensure dependent workflow runs first."
                        )

            # Create replayer for this workflow
            replayer = StableReplayer()

            # Configure engines if available
            if hasattr(self, '_healing_engine'):
                replayer.set_healing_engine(self._healing_engine)
            if hasattr(self, '_llm_engine'):
                replayer.set_llm_engine(self._llm_engine)
            if hasattr(self, '_cv_engine'):
                replayer.set_cv_engine(self._cv_engine)
            if hasattr(self, '_selector_engine'):
                replayer.set_selector_engine(self._selector_engine)

            # Track step results
            def on_step_result(result: StepResult):
                step_results.append(result.to_dict())
                if self._on_step_result:
                    self._on_step_result(index, result)

            replayer.on_step_result(on_step_result)

            # Run synchronously using threading
            success = False
            complete_event = asyncio.Event()
            loop = asyncio.get_event_loop()

            def on_complete(success_flag, error, duration):
                nonlocal success, error_msg
                success = success_flag
                error_msg = error
                # Thread-safe: schedule set() on the correct event loop
                loop.call_soon_threadsafe(complete_event.set)

            replayer.on_complete(on_complete)
            replayer.replay(workflow_path)

            # Wait for completion
            await complete_event.wait()

            # Count results
            for sr in step_results:
                if sr["status"] == "passed":
                    passed += 1
                elif sr["status"] == "failed":
                    failed += 1
                elif sr["status"] == "skipped":
                    skipped += 1

            # Get imported/exported variables from replayer
            # Note: These are tracked in the replayer's internal state

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            error_msg = str(e)
            success = False
            workflow_name = Path(workflow_path).stem

        duration = int((time.perf_counter() - workflow_start) * 1000)

        return WorkflowResult(
            workflow_id=Path(workflow_path).stem,
            workflow_name=workflow_name if 'workflow_name' in dir() else Path(workflow_path).stem,
            success=error_msg is None and failed == 0,
            step_count=len(step_results),
            passed_count=passed,
            failed_count=failed,
            skipped_count=skipped,
            duration_ms=duration,
            error=error_msg,
            imported_variables=imported_vars,
            exported_variables=exported_vars,
            step_results=step_results
        )

    async def _resolve_dependencies(self, workflow_paths: List[str]) -> List[str]:
        """
        Resolve workflow execution order based on variable dependencies.

        Workflows that export variables should run before those that import them.
        """
        import json

        # Build dependency graph
        workflows = {}
        for path in workflow_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                workflow = Workflow(**data)
                workflows[path] = workflow
            except Exception as e:
                logger.warning(f"Could not parse workflow {path}: {e}")

        # Track what each workflow exports and imports
        exports: Dict[str, str] = {}  # variable -> workflow path
        imports: Dict[str, List[str]] = {}  # workflow path -> [required variables]

        for path, workflow in workflows.items():
            if workflow.variables:
                for exp in workflow.variables.exports:
                    global_name = exp.globalName or exp.variableName
                    exports[global_name] = path

                required = []
                for imp in workflow.variables.imports:
                    if imp.required:
                        required.append(imp.globalName)
                imports[path] = required

        # Topological sort
        sorted_paths = []
        remaining = set(workflow_paths)

        while remaining:
            # Find workflows with no unmet dependencies
            ready = []
            for path in remaining:
                unmet = []
                for var in imports.get(path, []):
                    if var in exports and exports[var] in remaining:
                        unmet.append(var)
                if not unmet:
                    ready.append(path)

            if not ready:
                # Circular dependency or unresolvable - use original order
                logger.warning("Could not fully resolve dependencies, using original order")
                sorted_paths.extend(remaining)
                break

            # Add ready workflows in original order
            for path in workflow_paths:
                if path in ready and path in remaining:
                    sorted_paths.append(path)
                    remaining.remove(path)

        return sorted_paths

    def _get_workflow_name(self, workflow: Workflow, path: str) -> str:
        """Extract workflow name for reporting."""
        if workflow.metadata and workflow.metadata.get("name"):
            return workflow.metadata["name"]
        if workflow.meta and workflow.meta.get("name"):
            return workflow.meta["name"]
        return Path(path).stem

    def _print_suite_summary(self, result: SuiteResult):
        """Print suite execution summary."""
        logger.info(f"\n{'='*60}")
        logger.info(f"SUITE SUMMARY: {result.suite_name}")
        logger.info(f"{'='*60}")
        logger.info(f"Status: {'PASSED' if result.success else 'FAILED'}")
        logger.info(f"Workflows: {result.passed_workflows}/{result.total_workflows} passed")
        logger.info(f"Steps: {result.passed_steps}/{result.total_steps} passed")
        logger.info(f"Duration: {result.duration_ms}ms")

        if result.global_variables:
            logger.info(f"\nShared Variables ({len(result.global_variables)}):")
            for name, value in result.global_variables.items():
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else value
                logger.info(f"  {name} = {display_value}")

        if not result.success:
            logger.info("\nFailed Workflows:")
            for wr in result.workflow_results:
                if not wr.success:
                    logger.info(f"  - {wr.workflow_name}: {wr.error}")

        logger.info(f"{'='*60}\n")


def run_suite_sync(
    workflow_paths: List[str],
    suite_name: str = "Test Suite",
    stop_on_failure: bool = True
) -> SuiteResult:
    """
    Synchronous helper to run a test suite.

    Args:
        workflow_paths: List of workflow file paths
        suite_name: Name for the suite
        stop_on_failure: Stop on first failure

    Returns:
        SuiteResult
    """
    runner = SuiteRunner()
    runner.set_stop_on_failure(stop_on_failure)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            runner.run_suite(workflow_paths, suite_name)
        )
    finally:
        loop.close()
