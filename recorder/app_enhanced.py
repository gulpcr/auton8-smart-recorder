"""
Enhanced Recording Controller - Integrates new UI components
This is the entry point for the enhanced UI with Test Library
"""

from __future__ import annotations

import os
import sys
import uuid
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Slot, Signal, QUrl, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from recorder.models.timeline_model import TimelineModel
from recorder.models.workflow_list_model import WorkflowListModel
from recorder.models.test_library_model import TestLibraryModel
from recorder.models.replay_results_model import ReplayResultsModel
from recorder.models.step_detail_model import StepDetailModel
from recorder.models.settings_model import SettingsModel
from recorder.models.execution_history_model import ExecutionHistoryModel, MLStatsModel
from recorder.schema.workflow import Workflow, Step, Target, Locator
from recorder.schema.enhanced import WorkflowMetadata
from recorder.services import workflow_store
from recorder.services.ws_server import WebSocketIngestServer
from recorder.services.browser_launcher import BrowserLauncher
from recorder.services.stable_replay import StableReplayer, StepResult


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recorder")

# Skills system (client-server architecture)
from recorder.skills import create_default_registry, create_context, SkillRegistry, SkillMode

# ML/AI Components - loaded via skills, direct imports only for type hints
try:
    from recorder.ml.selector_engine import (
        MultiDimensionalSelectorEngine,
        create_fingerprint_from_dom
    )
    from recorder.ml.healing_engine import SelectorHealingEngine
    from recorder.ml.vision_engine import VisualElementMatcher, ScreenshotManager
    from recorder.ml.nlp_engine import NLPEngine
    ML_AVAILABLE = True
except Exception as e:
    logger.warning(f"ML engines not available: {e}")
    ML_AVAILABLE = False

# Ollama LLM integration (optional)
try:
    from recorder.ml.ollama_engine import OllamaLLMEngine, OllamaConfig
    OLLAMA_AVAILABLE = True
except Exception as e:
    logger.debug(f"Ollama engine not available: {e}")
    OLLAMA_AVAILABLE = False

# Playwright auto-install check
def _ensure_playwright_browsers():
    """Check if Playwright browsers are installed, install if missing."""
    try:
        from pathlib import Path
        import subprocess
        # Quick check: see if chromium exists in the expected location
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True, timeout=10
        )
        if "chromium" in result.stdout and "already installed" in result.stdout.lower():
            return  # Already installed
    except Exception:
        pass  # dry-run not supported or failed, try install anyway

    try:
        logger.info("Installing Playwright browsers (first run)...")
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, timeout=120
        )
        logger.info("Playwright browsers installed")
    except Exception as e:
        logger.warning(f"Could not auto-install Playwright browsers: {e}")
        logger.warning("Run manually: python -m playwright install chromium")


class EnhancedRecordingController(QObject):
    """
    Enhanced recording controller with Test Library integration.
    """

    # Signals
    timelineChanged = Signal()
    statusMessage = Signal(str)
    recordingStateChanged = Signal(bool)
    replayStateChanged = Signal(bool)
    replayProgress = Signal(int, str)
    replayStepResult = Signal(dict)  # New: detailed step result with timing
    replayCompleted = Signal(bool, str, int)  # New: success, error, total_duration_ms
    mlStatusChanged = Signal(dict)
    workflowCreated = Signal(str)  # New: emits workflow path when created
    workflowLoadedForEdit = Signal(str, str, int)  # path, baseUrl, stepCount - for editing mode

    # Portal signals
    portalLoginResult = Signal(bool, str)  # success flag + message

    # Internal signals for thread-safe updates
    _stepResultReady = Signal()
    _workflowLoadedReady = Signal()

    def __init__(self):
        super().__init__()

        # Core components
        self.timeline_model = TimelineModel()
        self.workflow_list_model = WorkflowListModel()
        self.test_library_model = TestLibraryModel()  # NEW
        self.replay_results_model = ReplayResultsModel()  # NEW: for step execution results
        self.step_detail_model = StepDetailModel()  # NEW: for step viewer/editor
        self.settings_model = SettingsModel()  # Application settings
        self.execution_history_model = ExecutionHistoryModel()  # Execution history for Runs tab
        self.ml_stats_model = MLStatsModel()  # ML statistics for ML Insights tab
        self.workflow = Workflow()
        self.current_workflow_path: Optional[str] = None
        self.server = WebSocketIngestServer()
        self.browser = BrowserLauncher()
        self.replayer = StableReplayer()

        # Current execution tracking
        self._current_execution_id: Optional[str] = None

        # Thread-safe queue for step results
        from queue import Queue
        self._step_result_queue = Queue()
        self._pending_steps = None

        # Skills system - centralized capability registry
        self.skill_registry: SkillRegistry = create_default_registry()
        self.skill_ctx = create_context(
            settings=self.settings_model.to_dict(),
            portal_url=self.settings_model.portalUrl,
            portal_token=self.settings_model.portalAccessToken,
            skill_mode=self.settings_model.get("skillMode", "hybrid"),
        )
        logger.info(
            f"Skills: {len(self.skill_registry.skill_names)} registered, "
            f"mode={self.skill_ctx.skill_mode.value}"
        )

        # ML/AI components (optional) - loaded via skills or directly
        self.selector_engine = None
        self.healing_engine = None
        self.vision_matcher = None
        self.nlp_engine: Optional[Any] = None
        self.llm_engine: Optional[Any] = None

        # Initialize ML (direct local engines) + attach to replayer
        self._initialize_ml_components()
        self._setup_connections()
        self._attach_engines_to_replayer()

        self.refresh_workflow_list()

        logger.info("Enhanced recording controller initialized")
    
    def _initialize_ml_components(self):
        """
        Initialize ML/AI components.

        Strategy:
        - If ML libs are installed locally, use them directly (fastest).
        - If not, skills will delegate to the central server automatically
          when execute() is called in hybrid mode.
        """
        if not ML_AVAILABLE:
            logger.info("ML libs not installed locally - will use server via skills")
            return

        try:
            self.selector_engine = MultiDimensionalSelectorEngine()
            self.healing_engine = SelectorHealingEngine()
            logger.info("Selector and healing engines initialized (local)")

            self.vision_matcher = VisualElementMatcher()
            logger.info("Computer vision engine initialized (local)")

            self.nlp_engine = NLPEngine()
            logger.info("NLP engine initialized (local)")

        except Exception as e:
            logger.error(f"ML component initialization error: {e}")

        # Initialize Ollama LLM engine (optional)
        if OLLAMA_AVAILABLE:
            try:
                model_name = self.settings_model.get("ollamaModel", "ministral-3:latest")
                config = OllamaConfig(
                    model_name=model_name,
                    base_url="http://localhost:11434",
                    temperature=0.7,
                    max_tokens=512
                )
                self.llm_engine = OllamaLLMEngine(config)
                if self.llm_engine.available:
                    logger.info(f"Ollama LLM initialized (local: {model_name})")
                    self.mlStatusChanged.emit({
                        "llm_available": True,
                        "llm_model": model_name
                    })
                else:
                    logger.warning("Ollama server running but model not available")
                    self.llm_engine = None
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama LLM: {e}")
                self.llm_engine = None

        # Initial ML stats update
        self.update_ml_stats()

    def _attach_engines_to_replayer(self):
        """
        Connect ML engines to the replayer for tiered execution.

        If local engines exist, use them directly.
        If not but portal is connected, attach server-backed proxies via skills.
        """
        # Direct local engines (fastest path)
        if self.healing_engine:
            self.replayer.set_healing_engine(self.healing_engine)
            logger.info("Healing engine -> replayer (local, Tier 1)")
        elif self.skill_ctx.skill_mode != SkillMode.LOCAL:
            # Attach server proxy via healing skill
            healing_skill = self.skill_registry.get("healing")
            if healing_skill:
                try:
                    from recorder.skills.healing import ServerHealingProxy
                    if self.skill_ctx.portal_client and self.skill_ctx.portal_client.is_connected:
                        proxy = ServerHealingProxy(self.skill_ctx.portal_client)
                        self.replayer.set_healing_engine(proxy)
                        logger.info("Healing engine -> replayer (server proxy, Tier 1)")
                except Exception as e:
                    logger.debug(f"Could not attach server healing proxy: {e}")

        if self.llm_engine and self.llm_engine.available:
            self.replayer.set_llm_engine(self.llm_engine)
            logger.info("LLM engine -> replayer (local, Tier 3)")

        if self.vision_matcher:
            self.replayer.set_cv_engine(self.vision_matcher)
            logger.info("CV engine -> replayer (local, Tier 2)")

        if self.selector_engine:
            self.replayer.set_selector_engine(self.selector_engine)
            logger.info("Selector engine -> replayer (local, ML ranking)")

    @Slot()
    def update_ml_stats(self):
        """Update ML statistics model from engines."""
        self.ml_stats_model.update_from_engines(
            selector_engine=self.selector_engine,
            healing_engine=self.healing_engine,
            vision_engine=self.vision_matcher,
            llm_engine=self.llm_engine
        )
        logger.debug("ML stats updated")

    def _setup_connections(self):
        """Setup signal connections."""
        self.server.set_callback(self.ingest_event)
        self.server.start()

        self.replayer.on_step(self._on_replay_step)
        self.replayer.on_step_result(self._on_replay_step_result)
        self.replayer.on_complete(self._on_replay_complete)
        self.replayer.on_workflow_loaded(self._on_workflow_loaded)

        # Connect internal signals for thread-safe updates
        self._stepResultReady.connect(self._process_step_result)
        self._workflowLoadedReady.connect(self._process_workflow_loaded)
    
    def _on_replay_step(self, index: int, step_type: str):
        self.replayProgress.emit(index, step_type)

    def _on_replay_step_result(self, result: StepResult):
        """Handle step execution result from replay (called from replay thread)."""
        from PySide6.QtCore import QMetaObject, Qt
        # Queue the result and marshal signal to main thread
        self._step_result_queue.put(result)
        QMetaObject.invokeMethod(
            self, "_process_step_result",
            Qt.QueuedConnection
        )
        logger.debug(f"Queued step result: {result.index} - {result.status}")

    @Slot()
    def _process_step_result(self):
        """Process step result on main thread."""
        # Process all queued results
        while not self._step_result_queue.empty():
            try:
                result = self._step_result_queue.get_nowait()

                # Convert tier name to numeric value for UI
                tier_value = 0
                if result.tier_used:
                    tier_map = {
                        "TIER_0_DETERMINISTIC": 0,
                        "TIER_1_HEURISTIC": 1,
                        "TIER_2_VISION": 2,
                        "TIER_3_LLM": 3,
                    }
                    tier_value = tier_map.get(result.tier_used, 0)

                # Serialize tier attempts and healing details as JSON strings for QML
                tier_attempts_json = json.dumps(result.tier_attempts) if result.tier_attempts else ""
                healing_details_json = json.dumps(result.healing_details) if result.healing_details else ""

                # Update the model with full result data including recovery tier
                self.replay_results_model.update_status(
                    result.index,
                    result.status,
                    result.duration_ms,
                    result.error,
                    result.locator_used,
                    result.timestamp,
                    tier_value,
                    result.original_selector,
                    tier_attempts_json,
                    healing_details_json
                )

                # Emit signal for QML
                result_dict = result.to_dict()
                self.replayStepResult.emit(result_dict)

                # Add step result to execution history
                if self._current_execution_id:
                    try:
                        # Determine if healed based on tier used
                        was_healed = tier_value > 0 and result.status == "passed"

                        step_result_data = {
                            "step_index": result.index,
                            "step_name": result.name if hasattr(result, 'name') else f"Step {result.index + 1}",
                            "step_type": result.step_type if hasattr(result, 'step_type') else "unknown",
                            "status": result.status,
                            "duration_ms": result.duration_ms,
                            "tier_used": tier_value,
                            "tier_name": result.tier_used if result.tier_used else "Tier 0",
                            "was_healed": was_healed,
                            "healing_strategy": result.tier_used if was_healed else None,
                            "original_selector": result.original_selector or None,
                            "healed_selector": result.locator_used if was_healed else None,
                            "error_message": result.error if result.error else None,
                        }
                        self.execution_history_model.add_step_result(
                            self._current_execution_id, step_result_data
                        )
                    except Exception as ex:
                        logger.warning(f"Failed to add step result to history: {ex}")

                status_msg = f"Step {result.index + 1}: {result.status} in {result.duration_ms}ms"
                if result.error:
                    status_msg += f" - {result.error}"
                logger.info(status_msg)

            except Exception as e:
                logger.error(f"Error processing step result: {e}")
                import traceback
                traceback.print_exc()
                break

    def _on_workflow_loaded(self, steps):
        """Pre-populate replay results model with workflow steps (called from replay thread)."""
        self._pending_steps = steps
        self._workflowLoadedReady.emit()

    @Slot()
    def _process_workflow_loaded(self):
        """Process workflow loaded on main thread."""
        if self._pending_steps:
            steps = self._pending_steps
            self._pending_steps = None
            self.replay_results_model.populate_from_workflow(steps)
            logger.info(f"Workflow loaded with {len(steps)} steps for replay")
        else:
            logger.warning("_process_workflow_loaded called but no pending steps")

    def _on_replay_complete(self, success: bool, error: str, total_duration_ms: int = 0):
        self.replayStateChanged.emit(False)
        self.replayCompleted.emit(success, error, total_duration_ms)

        # Complete the execution record
        if self._current_execution_id:
            try:
                status = "completed" if success else "failed"
                self.execution_history_model.complete_execution(
                    self._current_execution_id, status, error if not success else ""
                )
                logger.info(f"Completed execution {self._current_execution_id} with status {status}")
            except Exception as ex:
                logger.warning(f"Failed to complete execution record: {ex}")
            finally:
                self._current_execution_id = None

        # Update ML stats after execution (may have new training data)
        self.update_ml_stats()

        summary = self.replay_results_model.get_summary()
        if success:
            self.statusMessage.emit(f"Replay completed: {summary}")
        else:
            self.statusMessage.emit(f"Replay failed: {error}")
    
    @Slot(str, str)
    def create_new_test(self, name: str, url: str):
        """
        Create a new test workflow with metadata.
        Called from NewTestWizard.
        """
        try:
            # Create new workflow with enhanced metadata
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            metadata = WorkflowMetadata(
                name=name,
                status="draft",
                createdAt=now,
                updatedAt=now,
                version=2,
                baseUrl=url
            )
            
            
            self.workflow = Workflow(
                version="1.0",
                metadata=metadata.model_dump(),
                meta={"name": name, "baseUrl": url},  # Backward compat
                steps=[],
                assets={},
                replay={}
            )
            
            
            logger.info(f"Created workflow with metadata: {self.workflow.metadata}")
            
            # Clear timeline
            self.timeline_model.beginResetModel()
            self.timeline_model._items.clear()
            self.timeline_model.endResetModel()
            
            # Save immediately to create file
            filename = f"test-{uuid.uuid4()}.json"
            path = workflow_store.save_workflow(self.workflow, filename)
            self.current_workflow_path = path
            
            
            self.statusMessage.emit(f"Created new test: {name}")
            self.workflowCreated.emit(path)
            logger.info(f"Created new test: {name} at {path}")
            
            # Start recording
            self.start_recording(url)
            
        except Exception as e:
            logger.error(f"Failed to create test: {e}")
            self.statusMessage.emit(f"Failed to create test: {str(e)}")
    
    def _extract_domain_name(self, url: str) -> str:
        """Extract a friendly name from URL (domain without extension)."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            # Get name before first dot (e.g., "daraz" from "daraz.pk")
            name_part = domain.split('.')[0] if '.' in domain else domain
            # Capitalize first letter
            return name_part.capitalize() if name_part else "Recording"
        except:
            return "Recording"

    @Slot(str)
    def start_recording(self, url: str):
        """Start recording session."""
        if not url.strip():
            url = "https://example.com"
        if not url.startswith("http"):
            url = "https://" + url

        # Initialize metadata if not set (direct recording without wizard)
        if self.workflow.metadata is None or not self.workflow.metadata:
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            # Use domain name for better identification
            domain_name = self._extract_domain_name(url)
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
            self.workflow.metadata = {
                "name": f"{domain_name} - {timestamp}",
                "baseUrl": url,
                "status": "draft",
                "createdAt": now,
                "updatedAt": now,
                "version": 2
            }
            logger.info(f"Initialized metadata for direct recording: {self.workflow.metadata.get('name')}")
        
        self.browser.launch(url)
        self.statusMessage.emit(f"Recording browser opened: {url}")
        self.recordingStateChanged.emit(True)
        logger.info(f"Started recording session for {url}")
    
    @Slot()
    def stop_recording(self):
        """Stop recording session and auto-save workflow."""
        self.browser.stop()
        self.recordingStateChanged.emit(False)
        
        # Auto-save if we have steps
        if len(self.workflow.steps) > 0:
            self.save_workflow()
            self.statusMessage.emit(f"Recording stopped - {len(self.workflow.steps)} steps saved")
        else:
            self.statusMessage.emit("Recording stopped - no steps captured")
        
        logger.info(f"Stopped recording session - {len(self.workflow.steps)} steps")
    
    @Slot()
    def save_workflow(self):
        """Save current workflow with updated metadata."""
        try:
            
            # Ensure metadata is a dict (don't overwrite existing!)
            logger.info(f"Before save - metadata type: {type(self.workflow.metadata)}, value: {self.workflow.metadata}")
            
            if self.workflow.metadata is None:
                self.workflow.metadata = {}
                logger.warning("Metadata was None, created empty dict")
            elif not isinstance(self.workflow.metadata, dict):
                # If it's a Pydantic model, convert to dict
                self.workflow.metadata = dict(self.workflow.metadata)
                logger.info("Converted metadata to dict")
            
            # Update metadata with current stats (preserving existing fields)
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            self.workflow.metadata["updatedAt"] = now
            self.workflow.metadata["stepCount"] = len(self.workflow.steps)
            
            # Initialize success metrics if not present
            if "successRate" not in self.workflow.metadata:
                self.workflow.metadata["successRate"] = 0.0  # Will be updated after first replay
            if "successProjection" not in self.workflow.metadata:
                self.workflow.metadata["successProjection"] = "unknown"  # "excellent", "good", "fair", "poor"
            
            # Set status to "ready" if we have steps, keep existing status otherwise
            if len(self.workflow.steps) > 0 and self.workflow.metadata.get("status", "draft") == "draft":
                self.workflow.metadata["status"] = "ready"
            elif "status" not in self.workflow.metadata:
                self.workflow.metadata["status"] = "draft"
            
            
            logger.info(f"After updates - metadata: {self.workflow.metadata}")
            
            if self.current_workflow_path:
                # Update existing
                filename = os.path.basename(self.current_workflow_path)
                path = workflow_store.save_workflow(self.workflow, filename)
            else:
                # Save new
                filename = f"test-{uuid.uuid4()}.json"
                path = workflow_store.save_workflow(self.workflow, filename)
                self.current_workflow_path = path
            
            
            self.statusMessage.emit(f"Saved {len(self.workflow.steps)} steps")
            self.refresh_workflow_list()
            self.timeline_model.saveSnapshot()  # Save snapshot for undo functionality
            logger.info(f"Workflow saved: {path} ({len(self.workflow.steps)} steps)")
            
            # #region agent log
            # Debug: Log workflow save details
            try:
                with open(r"f:\auton8\recorder\.cursor\debug.log", "a") as f:
                    import json as _json
                    steps_with_locators = sum(1 for s in self.workflow.steps if s.target and s.target.locators)
                    f.write(_json.dumps({"location":"app_enhanced.py:save_workflow","message":"workflow_saved","data":{"path":str(path),"total_steps":len(self.workflow.steps),"steps_with_locators":steps_with_locators,"name":self.workflow.metadata.get("name","unnamed")},"hypothesisId":"H2_SAVE","timestamp":int(datetime.now(timezone.utc).timestamp()*1000)}) + "\n")
            except Exception:
                pass  # Debug logging - non-critical
            # #endregion
            
        except Exception as e:
            logger.error(f"Failed to save workflow: {e}")
            self.statusMessage.emit(f"Failed to save: {str(e)}")
    
    @Slot()
    def refresh_workflow_list(self):
        """Refresh workflow list in both models."""
        workflows = workflow_store.list_workflows()
        self.workflow_list_model.set_workflows(workflows)
        self.test_library_model.set_workflows(workflows)
        logger.info(f"Loaded {len(workflows)} workflows")
    
    @Slot(str)
    def load_workflow(self, workflow_path: str):
        """Load a workflow for editing."""
        try:
            filename = os.path.basename(workflow_path)
            self.workflow = workflow_store.load_workflow(filename)
            
            if not self.workflow:
                self.statusMessage.emit("Failed to load workflow")
                return
            
            self.current_workflow_path = workflow_path
            
            # Populate timeline
            self.timeline_model.beginResetModel()
            self.timeline_model._items.clear()
            for step in self.workflow.steps:
                target_desc = ""
                if step.target and step.target.locators:
                    target_desc = step.target.locators[0].value[:50]
                
                self.timeline_model._items.append({
                    "id": step.id,
                    "name": step.name,
                    "type": step.type,
                    "target": target_desc,
                    "status": "pending",
                    "timestamp": ""
                })
            self.timeline_model.endResetModel()
            self.timeline_model.countChanged.emit()  # Notify QML of count change
            self.timeline_model.saveSnapshot()  # Save as baseline for undo

            # Get baseUrl from metadata
            base_url = ""
            if self.workflow.metadata:
                base_url = self.workflow.metadata.get("baseUrl", "")

            workflow_name = self.workflow.metadata.get("name", filename) if self.workflow.metadata else filename
            self.statusMessage.emit(f"Loaded: {workflow_name}")
            logger.info(f"Loaded workflow: {workflow_path}")

            # Emit signal for UI to update edit mode
            self.workflowLoadedForEdit.emit(workflow_path, base_url, len(self.workflow.steps))

        except Exception as e:
            logger.error(f"Failed to load workflow: {e}")
            self.statusMessage.emit(f"Failed to load: {str(e)}")

    @Slot(str)
    def load_workflow_steps(self, workflow_path: str):
        """Load workflow steps into the step detail model for viewing."""
        try:
            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)

            if not workflow:
                self.statusMessage.emit("Failed to load workflow steps")
                self.step_detail_model.clear()
                return

            # Load into step detail model
            self.step_detail_model.load_from_workflow(workflow, workflow_path)

            workflow_name = workflow.metadata.get("name", filename) if workflow.metadata else filename
            step_count = len(workflow.steps) if workflow.steps else 0
            self.statusMessage.emit(f"Loaded {step_count} steps from {workflow_name}")
            logger.info(f"Loaded {step_count} steps for viewing: {workflow_path}")

        except Exception as e:
            logger.error(f"Failed to load workflow steps: {e}")
            self.statusMessage.emit(f"Failed to load steps: {str(e)}")
            self.step_detail_model.clear()

    @Slot()
    def clear_step_details(self):
        """Clear the step detail model."""
        self.step_detail_model.clear()

    @Slot(int)
    def delete_step(self, step_index: int):
        """Delete a step from the current workflow and save."""
        workflow_path = self.step_detail_model.getWorkflowPath()
        if not workflow_path:
            self.statusMessage.emit("No workflow loaded")
            return

        try:
            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)

            if not workflow or step_index >= len(workflow.steps):
                self.statusMessage.emit("Invalid step index")
                return

            # Delete from workflow
            del workflow.steps[step_index]

            # Update metadata
            if workflow.metadata:
                workflow.metadata["stepCount"] = len(workflow.steps)
                workflow.metadata["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Save workflow
            workflow_store.save_workflow(workflow, filename)

            # Reload model from saved file to ensure consistency
            self.step_detail_model.load_from_workflow(workflow, workflow_path)

            self.statusMessage.emit(f"Deleted step {step_index + 1}")
            logger.info(f"Deleted step {step_index} from {filename}")

        except Exception as e:
            logger.error(f"Failed to delete step: {e}")
            self.statusMessage.emit(f"Failed to delete step: {str(e)}")

    @Slot(int, str)
    def add_step(self, after_index: int, step_type: str):
        """Add a new step to the current workflow and save."""
        logger.info(f"add_step called: after_index={after_index}, step_type={step_type}")
        workflow_path = self.step_detail_model.getWorkflowPath()
        logger.info(f"add_step workflow_path={workflow_path}")
        if not workflow_path:
            self.statusMessage.emit("No workflow loaded")
            logger.warning("add_step: No workflow loaded")
            return

        try:
            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)

            if not workflow:
                self.statusMessage.emit("Failed to load workflow")
                return

            # Create new step
            from recorder.schema.workflow import Step, Target, Locator
            import uuid

            # Action types that don't need locators
            NO_LOCATOR_ACTIONS = {
                # Frame operations (some need selectors)
                "switchMainFrame", "switchParentFrame",
                # Window operations
                "switchWindow", "switchWindowByIndex", "switchNewWindow", "closeWindow",
                # Dialog operations
                "handleAlert", "handleConfirm", "handlePrompt", "setDialogHandler",
                # Variable operations (without element extraction)
                "storeVariable", "assertVariable",
                # Wait operations (without element)
                "wait", "waitForNavigation", "waitForUrl",
                # Screenshot
                "screenshot",
            }

            # Default input values for specific action types
            DEFAULT_INPUTS = {
                "storeVariable": {"value": "variableName=value"},
                "assertVariable": {"value": "variableName==expectedValue"},
                "wait": {"value": "1000"},
                "waitForNavigation": {"value": "30000"},
                "waitForUrl": {"value": "/expected-url"},
                "handleAlert": {"value": "accept"},
                "handleConfirm": {"value": "true"},
                "handlePrompt": {"value": "prompt text"},
                "switchWindow": {"value": "window-identifier"},
                "switchWindowByIndex": {"value": "0"},
                "switchFrameByName": {"value": "frame-name"},
                "switchFrameByIndex": {"value": "0"},
                "screenshot": {"value": "screenshot.png"},
            }

            # Create step with or without target based on action type
            if step_type in NO_LOCATOR_ACTIONS:
                new_step = Step(
                    id=str(uuid.uuid4()),
                    name=step_type,
                    type=step_type,
                    target=None,
                    input=DEFAULT_INPUTS.get(step_type, {}),
                    domContext={
                        "semantic_intent": f"New {step_type} step - edit to configure"
                    }
                )
            else:
                new_step = Step(
                    id=str(uuid.uuid4()),
                    name=step_type,
                    type=step_type,
                    target=Target(locators=[
                        Locator(type="css", value="[data-testid='EDIT_ME']", score=0.5)
                    ]),
                    input=DEFAULT_INPUTS.get(step_type, {}),
                    domContext={
                        "semantic_intent": f"New {step_type} step - edit to configure"
                    }
                )

            # Insert at position
            insert_index = after_index + 1 if after_index >= 0 else 0
            if insert_index > len(workflow.steps):
                insert_index = len(workflow.steps)

            workflow.steps.insert(insert_index, new_step)

            # Update metadata
            if workflow.metadata:
                workflow.metadata["stepCount"] = len(workflow.steps)
                workflow.metadata["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Save workflow
            workflow_store.save_workflow(workflow, filename)

            # Reload model from saved file to ensure consistency
            self.step_detail_model.load_from_workflow(workflow, workflow_path)

            self.statusMessage.emit(f"Added {step_type} step at position {insert_index + 1}")
            logger.info(f"Added {step_type} step at index {insert_index} in {filename}")

        except Exception as e:
            logger.error(f"Failed to add step: {e}")
            self.statusMessage.emit(f"Failed to add step: {str(e)}")

    @Slot(int, str)
    def add_step_full(self, after_index: int, step_data_json: str):
        """Add a new step with full configuration to the workflow."""
        logger.info(f"add_step_full called: after_index={after_index}, data={step_data_json}")
        workflow_path = self.step_detail_model.getWorkflowPath()
        if not workflow_path:
            self.statusMessage.emit("No workflow loaded")
            logger.warning("add_step_full: No workflow loaded")
            return

        try:
            import json as json_module
            step_data = json_module.loads(step_data_json)
            step_type = step_data.get("type", "click")

            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)

            if not workflow:
                self.statusMessage.emit("Failed to load workflow")
                return

            # Create new step with full configuration
            from recorder.schema.workflow import Step, Target, Locator

            # Build locator based on provided data
            selector_type = step_data.get("selectorType", "css")
            selector_value = step_data.get("selector", "")

            # For wait type with time, use special handling
            if step_type == "wait":
                wait_type = step_data.get("waitType", "Time (ms)")
                if wait_type == "Time (ms)":
                    selector_value = f"wait:{step_data.get('waitTime', '1000')}ms"
                    selector_type = "wait"
                elif wait_type == "Page load":
                    selector_value = "document:load"
                    selector_type = "wait"
                else:
                    selector_value = step_data.get("waitSelector", "")

            locators = [Locator(type=selector_type, value=selector_value, score=1.0)]

            # Build dom context with semantic intent
            dom_context = {}
            if step_type == "click":
                dom_context["semantic_intent"] = f"Click on element: {selector_value}"
            elif step_type == "input":
                input_value = step_data.get("value", "")
                dom_context["semantic_intent"] = f"Input '{input_value}' into element"
                dom_context["input_value"] = input_value
            elif step_type == "keydown":
                key = step_data.get("key", "Enter")
                dom_context["semantic_intent"] = f"Press key: {key}"
                dom_context["key"] = key
            elif step_type == "wait":
                wait_type = step_data.get("waitType", "Time (ms)")
                if wait_type == "Time (ms)":
                    dom_context["semantic_intent"] = f"Wait {step_data.get('waitTime', '1000')}ms"
                    dom_context["wait_time"] = int(step_data.get("waitTime", "1000"))
                else:
                    dom_context["semantic_intent"] = f"Wait for element: {wait_type}"
                    dom_context["wait_type"] = wait_type
            elif step_type == "assert":
                assert_type = step_data.get("assertType", "Element exists")
                dom_context["semantic_intent"] = f"Assert: {assert_type}"
                dom_context["assert_type"] = assert_type
                if step_data.get("assertValue"):
                    dom_context["assert_value"] = step_data.get("assertValue")

            new_step = Step(
                id=str(uuid.uuid4()),
                name=step_type,
                type=step_type,
                target=Target(locators=locators),
                domContext=dom_context,
                value=step_data.get("value", "") if step_type == "input" else None
            )

            # Insert at position
            insert_index = after_index + 1 if after_index >= 0 else 0
            if insert_index > len(workflow.steps):
                insert_index = len(workflow.steps)

            workflow.steps.insert(insert_index, new_step)

            # Update metadata
            if workflow.metadata:
                workflow.metadata["stepCount"] = len(workflow.steps)
                workflow.metadata["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Save workflow
            workflow_store.save_workflow(workflow, filename)

            # Reload model from saved file to ensure consistency
            self.step_detail_model.load_from_workflow(workflow, workflow_path)

            self.statusMessage.emit(f"Added {step_type} step at position {insert_index + 1}")
            logger.info(f"Added {step_type} step at index {insert_index} in {filename}")

        except Exception as e:
            logger.error(f"Failed to add step: {e}")
            self.statusMessage.emit(f"Failed to add step: {str(e)}")

    @Slot(int, str, str)
    def update_step_selector(self, step_index: int, selector_type: str, selector_value: str):
        """Update a step's primary selector."""
        workflow_path = self.step_detail_model.getWorkflowPath()
        if not workflow_path:
            self.statusMessage.emit("No workflow loaded")
            return

        try:
            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)

            if not workflow or step_index >= len(workflow.steps):
                self.statusMessage.emit("Invalid step index")
                return

            step = workflow.steps[step_index]

            # Update or add the selector
            from recorder.schema.workflow import Locator
            new_locator = Locator(type=selector_type, value=selector_value, score=0.9)

            if step.target and step.target.locators:
                # Insert at beginning as primary
                step.target.locators.insert(0, new_locator)
            else:
                from recorder.schema.workflow import Target
                step.target = Target(locators=[new_locator])

            # Update metadata
            if workflow.metadata:
                workflow.metadata["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Save workflow
            workflow_store.save_workflow(workflow, filename)

            # Reload model to reflect changes
            self.step_detail_model.load_from_workflow(workflow, workflow_path)

            self.statusMessage.emit(f"Updated selector for step {step_index + 1}")
            logger.info(f"Updated selector for step {step_index} in {filename}")

        except Exception as e:
            logger.error(f"Failed to update selector: {e}")
            self.statusMessage.emit(f"Failed to update selector: {str(e)}")

    @Slot(str, result=str)
    def analyze_workflow_with_llm(self, workflow_path: str) -> str:
        """Analyze a workflow using LLM and return insights."""
        if not self.llm_engine or not self.llm_engine.available:
            return "LLM not available. Make sure Ollama is running with ministral-3:latest model."
        
        try:
            filename = os.path.basename(workflow_path)
            workflow = workflow_store.load_workflow(filename)
            
            if not workflow or not workflow.steps:
                return "Workflow has no steps to analyze."
            
            # Convert steps to dict format
            steps = [
                {
                    "type": step.type,
                    "action": step.action if hasattr(step, 'action') else step.type,
                    "selector": step.target.locators[0].value if step.target and step.target.locators else ""
                }
                for step in workflow.steps
            ]
            
            # Get workflow metadata
            name = workflow.metadata.get("name", filename) if workflow.metadata else filename
            url = workflow.metadata.get("baseUrl", "") if workflow.metadata else ""
            
            # Analyze with LLM
            analysis = self.llm_engine.analyze_workflow(steps, name, url)
            
            # Format result
            result = f"""📊 Workflow Analysis
            
Name: {name}
Steps: {analysis.steps_count}
Complexity: {analysis.complexity.upper()}

📝 Summary:
{analysis.summary}

🎯 Purpose:
{analysis.purpose}

💡 Suggestions:
"""
            for i, suggestion in enumerate(analysis.suggestions, 1):
                result += f"{i}. {suggestion}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return f"Analysis failed: {str(e)}"
    
    @Slot(result=str)
    def get_llm_status(self) -> str:
        """Get LLM engine status for UI display."""
        if not self.llm_engine:
            return "❌ LLM not initialized"
        elif not self.llm_engine.available:
            return "⚠️ LLM unavailable (Ollama not running or model not found)"
        else:
            return f"✅ LLM ready: {self.llm_engine.config.model_name}"
    
    @Slot(str)
    def start_replay(self, workflow_path: str):
        """Start workflow replay."""
        if not workflow_path:
            self.statusMessage.emit("No workflow selected")
            return

        # Clear previous results
        self.replay_results_model.clear()

        # Create execution record
        try:
            workflow_name = os.path.basename(workflow_path).replace(".json", "")
            workflow_id = workflow_name  # Use name as ID for local files
            self._current_execution_id = self.execution_history_model.create_execution(
                workflow_id, workflow_name
            )
            logger.info(f"Created execution record: {self._current_execution_id}")
        except Exception as e:
            logger.warning(f"Failed to create execution record: {e}")
            self._current_execution_id = None

        self.replayer.replay(workflow_path)
        self.replayStateChanged.emit(True)
        self.statusMessage.emit("Replay started...")
        logger.info(f"Started replay for {workflow_path}")
    
    @Slot()
    def stop_replay(self):
        """Stop replay."""
        self.replayer.stop()
        self.replayStateChanged.emit(False)
        self.statusMessage.emit("Replay stopped")
        logger.info("Stopped replay")
    
    @Slot()
    def clear_timeline(self):
        """Clear timeline."""
        self.timeline_model.clear()
        self.workflow.steps.clear()
        self.current_workflow_path = None
        self.statusMessage.emit("Timeline cleared")
        import logging
        logging.getLogger("recorder").info("Timeline cleared by user")
    
    @Slot(str)
    def delete_workflow(self, workflow_path: str):
        """Delete a workflow file."""
        try:
            if os.path.exists(workflow_path):
                os.remove(workflow_path)
                self.statusMessage.emit("Workflow deleted")
                self.refresh_workflow_list()
                logger.info(f"Deleted workflow: {workflow_path}")
            else:
                self.statusMessage.emit("Workflow not found")
        except Exception as e:
            logger.error(f"Failed to delete workflow: {e}")
            self.statusMessage.emit(f"Delete failed: {str(e)}")
    
    # ==================== Portal Login/Logout ====================

    @Slot(str, str, str)
    def portal_login(self, portal_url: str, email: str, password: str):
        """Login to portal. Runs HTTP request in background thread."""
        import threading

        def _do_login():
            try:
                import urllib.request
                import urllib.error

                # Normalize URL
                url = portal_url.rstrip("/")
                endpoint = f"{url}/api/auth/login"

                body = json.dumps({"email": email, "password": password}).encode("utf-8")
                req = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if data.get("status"):
                    token = data.get("data", {}).get("accessToken", "")
                    message = data.get("message", "Login successful")
                    result = json.dumps({
                        "success": True,
                        "message": message,
                        "token": token,
                        "email": email,
                        "portalUrl": url,
                    })
                else:
                    result = json.dumps({
                        "success": False,
                        "message": data.get("message", "Login failed"),
                    })

            except urllib.error.HTTPError as e:
                try:
                    err_body = json.loads(e.read().decode("utf-8"))
                    msg = err_body.get("message", f"HTTP {e.code}")
                except Exception:
                    msg = f"HTTP error {e.code}"
                result = json.dumps({"success": False, "message": msg})
            except urllib.error.URLError as e:
                result = json.dumps({"success": False, "message": f"Connection failed: {e.reason}"})
            except Exception as e:
                result = json.dumps({"success": False, "message": str(e)})

            # Marshal back to main thread
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_handle_portal_login_result",
                Qt.QueuedConnection,
                Q_ARG(str, result),
            )

        thread = threading.Thread(target=_do_login, daemon=True)
        thread.start()
        logger.info(f"Portal login started for {email} at {portal_url}")

    @Slot(str)
    def _handle_portal_login_result(self, result_json: str):
        """Process portal login result on main thread."""
        result = json.loads(result_json)
        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            self.settings_model.portalUrl = result["portalUrl"]
            self.settings_model.portalAccessToken = result["token"]
            self.settings_model.portalUserEmail = result["email"]
            self.settings_model.portalConnected = True
            logger.info(f"Portal login successful: {result['email']}")
        else:
            logger.warning(f"Portal login failed: {message}")

        self.portalLoginResult.emit(success, message)

    @Slot()
    def portal_logout(self):
        """Logout from portal - clear stored credentials."""
        self.settings_model.portalAccessToken = ""
        self.settings_model.portalUserEmail = ""
        self.settings_model.portalConnected = False
        self.statusMessage.emit("Logged out from portal")
        logger.info("Portal logout")

    def _generate_semantic_intent(self, event_type: str, dom_context: dict, payload: dict) -> str:
        """
        Generate human-readable semantic intent for the step.
        This describes WHAT the user is trying to do, not HOW.
        """
        text = dom_context.get("text_content", "")[:50]
        aria = dom_context.get("aria_label", "")
        role = dom_context.get("semantic_role", "")
        tag = dom_context.get("tag_name", "")
        placeholder = dom_context.get("placeholder", "")

        # Determine element description
        element_desc = ""
        if aria:
            element_desc = aria
        elif text:
            element_desc = f'"{text}"'
        elif placeholder:
            element_desc = f'{placeholder} field'
        elif role:
            element_desc = role.replace("-", " ").replace("_", " ")
        elif tag:
            element_desc = tag

        # Generate intent based on event type
        if event_type == "click":
            if "dropdown" in role or "select" in tag:
                return f"Open {element_desc} dropdown"
            elif "button" in role or "submit" in role or tag == "button":
                return f"Click {element_desc} button"
            elif "link" in role or tag == "a":
                return f"Navigate to {element_desc}"
            elif "checkbox" in role or "check" in tag:
                return f"Toggle {element_desc} checkbox"
            else:
                return f"Click on {element_desc}"

        elif event_type in ["input", "type", "change"]:
            input_val = payload.get("input", {}).get("value", "") if payload.get("input") else ""
            if input_val:
                return f"Enter '{input_val[:30]}' into {element_desc}"
            else:
                return f"Fill {element_desc} field"

        elif event_type == "submit":
            return f"Submit {element_desc or 'form'}"

        elif event_type == "select" or event_type == "selectOption":
            return f"Select option from {element_desc}"

        elif event_type == "hover":
            return f"Hover over {element_desc}"

        elif event_type == "dblclick":
            return f"Double-click on {element_desc}"

        else:
            return f"{event_type.capitalize()} on {element_desc}"

    def ingest_event(self, payload: Dict[str, Any]):
        """
        Called from WebSocket server thread.
        Marshals the work to the main GUI thread via QMetaObject.invokeMethod.
        """
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        payload_json = json.dumps(payload)
        QMetaObject.invokeMethod(
            self, "_ingest_event_on_main_thread",
            Qt.QueuedConnection,
            Q_ARG(str, payload_json)
        )

    @Slot(str)
    def _ingest_event_on_main_thread(self, payload_json: str):
        """Process ingested event on the main GUI thread (thread-safe)."""
        payload = json.loads(payload_json)
        try:

            # Capture base URL from first event
            if not self.workflow.steps and payload.get("page", {}).get("url"):
                self.workflow.meta["baseUrl"] = payload["page"]["url"]
                if self.workflow.metadata:
                    self.workflow.metadata["baseUrl"] = payload["page"]["url"]
            
            event_type = payload.get("eventType", payload.get("type", "click"))
            
            
            # Filter out lifecycle events (not user actions)
            LIFECYCLE_EVENTS = {'session_start', 'session_end', 'visibility_change', 'page_load'}
            if event_type in LIFECYCLE_EVENTS:
                logger.debug(f"Skipping lifecycle event: {event_type}")
                return
            
            # Validate event_type is in Step schema
            VALID_TYPES = {
                # Basic interactions
                'click', 'dblclick', 'contextmenu', 'hover', 'dragdrop', 'scroll',
                # Input
                'type', 'input', 'change', 'press',
                # Form controls
                'selectOption', 'check', 'uncheck', 'submit',
                # Frame operations
                'switchFrame', 'switchFrameByName', 'switchFrameByIndex',
                'switchMainFrame', 'switchParentFrame',
                # Window operations
                'switchWindow', 'switchWindowByIndex', 'switchNewWindow', 'closeWindow',
                # Dialog operations
                'handleAlert', 'handleConfirm', 'handlePrompt', 'setDialogHandler',
                # Variable operations
                'storeVariable', 'storeText', 'storeValue', 'storeAttribute', 'storeCount',
                'assertVariable',
                # Wait operations
                'wait', 'waitForElement', 'waitForNavigation', 'waitForUrl',
                # Assertions
                'assert', 'assertText', 'assertVisible', 'assertNotVisible',
                'assertEnabled', 'assertChecked',
                # Other
                'screenshot', 'dragTo', 'dragByOffset', 'custom'
            }

            # Events to skip entirely (redundant low-level events)
            SKIP_EVENTS = {
                'keyup',       # Already captured in keydown/input
                'keypress',    # Deprecated, use keydown
                'mousedown',   # Already captured in click
                'mouseup',     # Already captured in click
                'mouseover',   # Too noisy
                'mouseout',    # Too noisy
                'mousemove',   # Too noisy
                'focus',       # Implicit in other events
                'blur',        # Implicit in other events
            }

            # Skip redundant events
            if event_type in SKIP_EVENTS:
                logger.debug(f"Skipping redundant event: {event_type}")
                return

            # Map keydown to 'press' for special keys, otherwise skip (input event captures typing)
            if event_type == 'keydown':
                key = payload.get("key", "") or payload.get("input", {}).get("key", "")
                # Only record special keys (Enter, Tab, Escape, Arrow keys, etc.)
                special_keys = {'Enter', 'Tab', 'Escape', 'Backspace', 'Delete',
                               'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
                               'Home', 'End', 'PageUp', 'PageDown', 'F1', 'F2', 'F3',
                               'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'}
                if key not in special_keys:
                    logger.debug(f"Skipping regular keydown: {key}")
                    return
                event_type = 'press'
                # Store the key in input
                if not payload.get("input"):
                    payload["input"] = {}
                payload["input"]["key"] = key
                payload["input"]["value"] = key

            # Map common browser events to Step schema types
            # Note: dblclick is NOT mapped to click - it stays as dblclick for proper handling
            EVENT_TYPE_MAPPING = {
                # Add mappings for any browser-specific event names here
            }

            # Apply mapping first
            if event_type in EVENT_TYPE_MAPPING:
                event_type = EVENT_TYPE_MAPPING[event_type]
            elif event_type not in VALID_TYPES:
                logger.warning(f"Unknown event type '{event_type}', skipping")
                return

            # Filter out phantom input events (input/change/type with no value)
            if event_type in ('input', 'change', 'type'):
                input_value = ""
                if payload.get("input"):
                    input_value = payload["input"].get("value", "")
                elif payload.get("value"):
                    input_value = payload.get("value", "")
                if not input_value or input_value.strip() == "":
                    logger.debug(f"Skipping phantom {event_type} event (no value)")
                    return

            target_desc = payload.get("targetText") or payload.get("target") or ""
            
            # Generate multi-dimensional selectors if ML available
            locators = []
            
            # #region agent log
            # Debug: Log raw locators from payload
            try:
                with open(r"f:\auton8\recorder\.cursor\debug.log", "a") as f:
                    import json as _json
                    raw_locs = payload.get("locators", [])
                    f.write(_json.dumps({"location":"app_enhanced.py:ingest_event:raw_locators","message":"Raw locators from payload","data":{"raw_locator_count":len(raw_locs),"first_raw":raw_locs[0] if raw_locs else None,"has_element_key":"element" in payload,"has_cssSelector":payload.get("cssSelector") is not None,"has_xpathAbsolute":payload.get("xpathAbsolute") is not None},"hypothesisId":"H5_LOCATOR_FORMAT","timestamp":int(datetime.now(timezone.utc).timestamp()*1000)}) + "\n")
            except Exception:
                pass  # Debug logging - non-critical
            # #endregion
            
            if self.selector_engine and "element" in payload:
                # Fast path: local ML selector generation
                try:
                    fingerprint = create_fingerprint_from_dom(payload)
                    selector_strategies = self.selector_engine.generate_selectors(fingerprint)

                    locators = [
                        Locator(
                            type=sel.type.value,
                            value=sel.value,
                            score=sel.score
                        )
                        for sel in selector_strategies
                    ]

                    logger.debug(f"Generated {len(locators)} selector strategies (local ML)")
                except Exception as e:
                    logger.error(f"Selector generation failed: {e}")
            elif "element" in payload and self.skill_ctx.skill_mode != SkillMode.LOCAL:
                # Slow path: delegate to server via skills
                try:
                    result = self.skill_registry.execute(
                        "selector_gen", self.skill_ctx,
                        element_data=payload.get("element", payload)
                    )
                    if result.success and result.data:
                        for sel in result.data.get("selectors", []):
                            locators.append(Locator(
                                type=sel.get("type", "css"),
                                value=sel.get("value", ""),
                                score=sel.get("score", 0.5)
                            ))
                        logger.debug(f"Generated {len(locators)} selectors (server)")
                except Exception as e:
                    logger.debug(f"Server selector generation failed: {e}")
            
            # Fallback to basic locators from browser
            if not locators:
                raw_locators = payload.get("locators", [])
                # Also check element.locators if direct locators not found
                if not raw_locators and "element" in payload:
                    raw_locators = payload.get("element", {}).get("locators", [])

                # #region agent log
                try:
                    with open(r"f:\auton8\recorder\.cursor\debug.log", "a") as f:
                        import json as _json
                        f.write(_json.dumps({"location":"app_enhanced.py:fallback_locators","message":"Processing raw_locators","data":{"raw_count":len(raw_locators),"sample":raw_locators[0] if raw_locators else None},"hypothesisId":"H6_PARSING","timestamp":int(datetime.now(timezone.utc).timestamp()*1000)}) + "\n")
                except Exception:
                    pass  # Debug logging - non-critical
                # #endregion

                # Map JavaScript locator types to valid Python schema types
                JS_TO_PYTHON_TYPE_MAP = {
                    "id": "id",               # Now a valid type in schema
                    "aria-label": "aria",
                    "aria-labelledby": "aria",
                    "xpath-relative": "xpath",
                    "xpath-absolute": "xpath",
                    "data-attribute": "data",
                    "name": "name",           # Now a valid type in schema
                    "css": "css",
                    "text": "text",
                    "xpath": "xpath",
                    "data": "data",
                    "aria": "aria",
                    "label": "label",
                    "frame": "frame",
                    "shadow": "shadow",
                }
                VALID_LOCATOR_TYPES = {"data", "aria", "label", "css", "text", "xpath", "frame", "shadow", "id", "name"}

                # Process locators one by one with error handling
                for loc in raw_locators:
                    try:
                        loc_value = loc.get("value") or loc.get("selector", "")
                        if not loc_value:
                            continue

                        # Map the type to a valid Python schema type
                        raw_type = loc.get("type", "css")
                        mapped_type = JS_TO_PYTHON_TYPE_MAP.get(raw_type, raw_type)

                        # Final fallback to css if still invalid
                        if mapped_type not in VALID_LOCATOR_TYPES:
                            logger.debug(f"Unknown locator type '{raw_type}', defaulting to 'css'")
                            mapped_type = "css"

                        locators.append(Locator(
                            type=mapped_type,
                            value=loc_value,
                            score=loc.get("score", 0.5)
                        ))
                    except Exception as loc_error:
                        logger.warning(f"Skipping invalid locator {loc}: {loc_error}")
            
            # Ultimate fallback: use individual selector fields from payload
            if not locators:
                fallback_selectors = []
                # data-testid has highest priority
                if payload.get("attributes", {}).get("data-testid"):
                    fallback_selectors.append(Locator(type="data", value=payload["attributes"]["data-testid"], score=0.95))
                if payload.get("ariaLabel"):
                    fallback_selectors.append(Locator(type="aria", value=payload["ariaLabel"], score=0.9))
                if payload.get("id"):
                    fallback_selectors.append(Locator(type="id", value=f"#{payload['id']}", score=0.85))
                if payload.get("cssSelector"):
                    fallback_selectors.append(Locator(type="css", value=payload["cssSelector"], score=0.7))
                if payload.get("xpathRelative"):
                    fallback_selectors.append(Locator(type="xpath", value=payload["xpathRelative"], score=0.65))
                if payload.get("xpathAbsolute"):
                    fallback_selectors.append(Locator(type="xpath", value=payload["xpathAbsolute"], score=0.4))
                locators = fallback_selectors

                if fallback_selectors:
                    logger.debug(f"Using ultimate fallback: {len(fallback_selectors)} locators from individual fields")
            
            # #region agent log
            # Debug: Log locator extraction details
            try:
                with open(r"f:\auton8\recorder\.cursor\debug.log", "a") as f:
                    import json as _json
                    f.write(_json.dumps({"location":"app_enhanced.py:ingest_event","message":"locator_extraction","data":{"event_type":event_type,"locator_count":len(locators),"locator_sources":"ml" if self.selector_engine else "fallback","first_locator":locators[0].value[:100] if locators else "NONE"},"hypothesisId":"H1_LOCATORS","timestamp":int(datetime.now(timezone.utc).timestamp()*1000)}) + "\n")
            except Exception:
                pass  # Debug logging - non-critical
            # #endregion
            
            # Serialize page.viewport if it's a dict (H2)
            page_data = payload.get("page", {})
            if page_data and "viewport" in page_data:
                viewport = page_data["viewport"]
                if isinstance(viewport, dict):
                    page_data = dict(page_data)
                    page_data["viewport"] = json.dumps(viewport)
            
            step_id = payload.get("id") or str(uuid.uuid4())

            # Build rich domContext from payload for AI/ML/CV use during replay
            dom_context = payload.get("domContext") or {}

            # Extract all semantic and visual data from payload
            dom_context.update({
                # Text content for semantic matching
                "text_content": payload.get("textContent") or payload.get("targetText") or "",

                # ARIA and accessibility attributes
                "aria_label": payload.get("ariaLabel"),
                "aria_role": payload.get("ariaRole") or payload.get("role"),
                "placeholder": payload.get("placeholder"),
                "title": payload.get("title"),

                # Element identity
                "tag_name": payload.get("tagName", "").lower() if payload.get("tagName") else "",
                "id": payload.get("id") if payload.get("id") and not payload.get("hasDynamicId") else None,
                "classes": payload.get("classes", []),
                "name": payload.get("attributes", {}).get("name") if payload.get("attributes") else None,

                # Visual data for CV matching
                "bounding_box": payload.get("boundingBox", [0, 0, 0, 0]),
                "visual_hash": payload.get("visualHash"),  # Computed by vision engine if available
                "screenshot_path": None,  # Will be set if screenshot captured

                # Structural context for ML healing
                "parent_path": "/".join([p.get("tag", "") for p in payload.get("parentChain", [])]),
                "sibling_count": payload.get("siblingCount", 0),
                "depth": payload.get("depth", 0),
                "is_in_iframe": payload.get("isInIframe", False),

                # Stability indicators
                "has_stable_attributes": payload.get("hasStableAttributes", False),
                "has_dynamic_id": payload.get("hasDynamicId", False),

                # Semantic role classification
                "semantic_role": payload.get("semanticRole"),

                # Framework info
                "framework": payload.get("frameworkInfo", {}).get("name") if payload.get("frameworkInfo") else None,

                # Attributes for healing
                "attributes": {
                    k: v for k, v in (payload.get("attributes") or {}).items()
                    if k in ["data-testid", "data-test", "data-cy", "name", "type", "href", "src", "value"]
                },
            })

            # Generate semantic intent (what the user is trying to do)
            semantic_intent = self._generate_semantic_intent(event_type, dom_context, payload)
            dom_context["semantic_intent"] = semantic_intent

            # Capture element screenshot and compute visual hash for CV matching
            bbox = dom_context.get("bounding_box", [0, 0, 0, 0])
            if bbox and bbox != [0, 0, 0, 0] and len(bbox) == 4:
                screenshot_result = self.browser.capture_element_screenshot(
                    bounding_box=tuple(bbox),
                    element_id=step_id
                )
                if screenshot_result:
                    screenshot_path, visual_hash, _ = screenshot_result
                    dom_context["screenshot_path"] = screenshot_path
                    dom_context["visual_hash"] = visual_hash
                    logger.debug(f"Captured visual data: hash={visual_hash[:16]}...")

            # Log rich context capture
            logger.debug(f"Captured rich domContext: text='{dom_context.get('text_content', '')[:30]}', "
                        f"bbox={dom_context.get('bounding_box')}, intent='{semantic_intent}'")

            # Create step with rich context
            step = Step(
                id=step_id,  # Generate UUID if missing or None
                name=payload.get("name") or event_type,
                type=event_type,
                target=Target(locators=locators) if locators else None,
                framePath=payload.get("framePath", []),
                shadowPath=payload.get("shadowPath", []),
                waits=[],
                assertions=[],
                domContext=dom_context,
                page=page_data if page_data else None,
                timing=payload.get("timing"),
                input=payload.get("input"),
                metadata=payload.get("ml_metadata", {}),
                enhancements={}  # Empty for now
            )
            
            
            self.workflow.steps.append(step)
            
            # Add to timeline
            self.timeline_model.append_step({
                "id": step.id,
                "name": step.name,
                "type": step.type,
                "target": target_desc,
                "status": "pending",
                "timestamp": payload.get("timestamp", ""),
            })
            
            self.timelineChanged.emit()
            logger.info(f"Captured step {step.id} ({step.type}) with {len(locators)} selectors")
            
        except Exception as e:
            logger.error(f"Event ingestion error: {e}")


def main():
    """Main application entry point with enhanced UI."""
    # Ensure Playwright browsers are installed
    _ensure_playwright_browsers()

    QQuickStyle.setStyle("Fusion")
    app = QApplication(sys.argv)
    app.setApplicationName("Auton8 Recorder")
    app.setOrganizationName("Auton8")

    engine = QQmlApplicationEngine()

    # Create controller
    controller = EnhancedRecordingController()

    # Register with QML
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("timelineModel", controller.timeline_model)
    engine.rootContext().setContextProperty("workflowListModel", controller.workflow_list_model)
    engine.rootContext().setContextProperty("testLibraryModel", controller.test_library_model)
    engine.rootContext().setContextProperty("replayResultsModel", controller.replay_results_model)
    engine.rootContext().setContextProperty("stepDetailModel", controller.step_detail_model)
    engine.rootContext().setContextProperty("appSettings", controller.settings_model)
    engine.rootContext().setContextProperty("executionHistoryModel", controller.execution_history_model)
    engine.rootContext().setContextProperty("mlStatsModel", controller.ml_stats_model)

    # Expose skill registry status to QML
    engine.rootContext().setContextProperty(
        "skillCount", len(controller.skill_registry.skill_names)
    )
    engine.rootContext().setContextProperty(
        "skillMode", controller.skill_ctx.skill_mode.value
    )

    # Load enhanced UI
    qml_file = os.path.join(os.path.dirname(__file__), "..", "ui", "main_enhanced.qml")

    if not os.path.exists(qml_file):
        logger.error(f"QML file not found: {qml_file}")
        sys.exit(-1)

    engine.load(QUrl.fromLocalFile(os.path.abspath(qml_file)))

    if not engine.rootObjects():
        logger.error("Failed to load QML!")
        sys.exit(-1)

    logger.info(f"Application started | Skills: {len(controller.skill_registry.skill_names)} | Mode: {controller.skill_ctx.skill_mode.value}")

    # Run application
    ret = app.exec()

    # Cleanup
    controller.browser.stop()
    controller.server.stop()
    QCoreApplication.quit()

    sys.exit(ret)


if __name__ == "__main__":
    main()
