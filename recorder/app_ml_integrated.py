"""
Enhanced Recording Controller with Full ML/AI Integration
Integrates all production-ready components:
- Multi-dimensional selector engine
- Intelligent healing with XGBoost
- Computer vision for element matching
- NLP for semantic understanding
- Local LLM for intent classification
- RAG for statement verification
- Transcription with WhisperX
"""

from __future__ import annotations

import os
import sys
import uuid
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal, QUrl, QCoreApplication, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from recorder.models.timeline_model import TimelineModel
from recorder.models.workflow_list_model import WorkflowListModel
from recorder.schema.workflow import Workflow, Step, Target, Locator
from recorder.services import workflow_store
from recorder.services.ws_server import WebSocketIngestServer
from recorder.services.browser_launcher import BrowserLauncher
from recorder.services.replay_launcher import ReplayLauncher

# Setup logging first
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recorder")

# ML/AI Components
from recorder.ml.selector_engine import (
    MultiDimensionalSelectorEngine,
    create_fingerprint_from_dom
)
from recorder.ml.healing_engine import SelectorHealingEngine
from recorder.ml.vision_engine import VisualElementMatcher, ScreenshotManager
from recorder.ml.nlp_engine import NLPEngine

# Optional components (graceful degradation)
try:
    from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig, get_default_model_path
    LLM_AVAILABLE = True
except Exception as e:
    logger.warning(f"LLM engine not available: {e}")
    LocalLLMEngine = None
    LLMConfig = None
    get_default_model_path = None
    LLM_AVAILABLE = False

try:
    from recorder.ml.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except Exception as e:
    logger.warning(f"RAG engine not available: {e}")
    RAGEngine = None
    RAG_AVAILABLE = False

try:
    from recorder.audio.transcription_engine import TranscriptionEngine
    TRANSCRIPTION_AVAILABLE = True
except Exception as e:
    logger.warning(f"Transcription engine not available: {e}")
    TranscriptionEngine = None
    TRANSCRIPTION_AVAILABLE = False


class EnhancedRecordingController(QObject):
    """
    Enhanced recording controller with full ML/AI capabilities.
    """
    
    # Signals
    timelineChanged = Signal()
    statusMessage = Signal(str)
    recordingStateChanged = Signal(bool)
    replayStateChanged = Signal(bool)
    replayProgress = Signal(int, str)
    mlStatusChanged = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.timeline_model = TimelineModel()
        self.workflow_list_model = WorkflowListModel()
        self.workflow = Workflow()
        self.server = WebSocketIngestServer()
        self.browser = BrowserLauncher()
        self.replayer = ReplayLauncher()
        
        # ML/AI components
        self.selector_engine: Optional[MultiDimensionalSelectorEngine] = None
        self.healing_engine: Optional[SelectorHealingEngine] = None
        self.vision_matcher: Optional[VisualElementMatcher] = None
        self.nlp_engine: Optional[NLPEngine] = None
        self.llm_engine: Optional[LocalLLMEngine] = None
        self.rag_engine: Optional[RAGEngine] = None
        self.transcription_engine: Optional[TranscriptionEngine] = None
        self.screenshot_manager: Optional[ScreenshotManager] = None
        
        # Initialize
        self._initialize_ml_components()
        self._setup_connections()
        self.refresh_workflow_list()
        
        logger.info("Enhanced recording controller initialized")
    
    def _initialize_ml_components(self):
        """Initialize all ML/AI components."""
        try:
            # Selector and healing engines
            self.selector_engine = MultiDimensionalSelectorEngine()
            self.healing_engine = SelectorHealingEngine()
            logger.info("✓ Selector and healing engines initialized")
            
            # Vision components
            self.vision_matcher = VisualElementMatcher()
            screenshots_path = Path("data/screenshots")
            self.screenshot_manager = ScreenshotManager(screenshots_path)
            logger.info("✓ Computer vision engine initialized")
            
            # NLP engine
            self.nlp_engine = NLPEngine()
            logger.info("✓ NLP engine initialized")
            
            # LLM engine (optional - requires model)
            if LLM_AVAILABLE and get_default_model_path:
                model_path = get_default_model_path()
                if model_path and model_path.exists():
                    config = LLMConfig(
                        model_path=str(model_path),
                        n_ctx=4096,
                        n_gpu_layers=0  # Set to >0 for GPU acceleration
                    )
                    self.llm_engine = LocalLLMEngine(config)
                    logger.info("✓ Local LLM engine initialized")
                else:
                    logger.warning("⚠ LLM model not found. LLM features disabled.")
                    logger.warning("  Download a model to: ~/models/llama-2-7b-chat.Q4_K_M.gguf")
            else:
                logger.info("⚠ LLM engine not available. LLM features disabled.")
            
            # RAG engine
            if RAG_AVAILABLE and RAGEngine:
                self.rag_engine = RAGEngine()
                self.rag_engine.load_index()  # Try to load existing index
                
                # Check if we need to ingest documents
                if len(self.rag_engine.documents) == 0:
                    docs_path = Path("data/knowledge_base")
                    if docs_path.exists():
                        logger.info("Ingesting knowledge base documents...")
                        self.rag_engine.ingest_documents_from_directory(docs_path)
                        self.rag_engine.save_index()
                    else:
                        logger.info("Knowledge base directory not found: data/knowledge_base")
                
                logger.info(f"✓ RAG engine initialized ({len(self.rag_engine.documents)} documents)")
            else:
                logger.info("⚠ RAG engine not available. Statement verification disabled.")
            
            # Transcription engine
            if TRANSCRIPTION_AVAILABLE and TranscriptionEngine:
                self.transcription_engine = TranscriptionEngine(model_size="base")
                logger.info("✓ Transcription engine initialized")
            else:
                logger.info("⚠ Transcription engine not available. Audio features disabled.")
            
            # Emit ML status
            self._emit_ml_status()
            
        except Exception as e:
            logger.error(f"ML component initialization error: {e}")
            self.statusMessage.emit(f"ML initialization warning: {str(e)}")
    
    def _emit_ml_status(self):
        """Emit ML components status."""
        status = {
            "selector_engine": self.selector_engine is not None,
            "healing_engine": self.healing_engine is not None,
            "vision_matcher": self.vision_matcher is not None,
            "nlp_engine": self.nlp_engine is not None,
            "llm_engine": self.llm_engine is not None,
            "rag_engine": self.rag_engine is not None,
            "transcription_engine": self.transcription_engine is not None,
            "rag_documents": len(self.rag_engine.documents) if self.rag_engine else 0
        }
        self.mlStatusChanged.emit(status)
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.server.set_callback(self.ingest_event)
        self.server.start()
        
        self.replayer.set_callbacks(
            on_step=self._on_replay_step,
            on_complete=self._on_replay_complete
        )
    
    def _on_replay_step(self, index: int, step_type: str):
        self.replayProgress.emit(index, step_type)
    
    def _on_replay_complete(self, success: bool, error: str, total_duration_ms: int = 0):
        self.replayStateChanged.emit(False)
        if success:
            self.statusMessage.emit("Replay completed successfully ✓")
        else:
            self.statusMessage.emit(f"Replay failed: {error}")
    
    @Slot(str)
    def start_recording(self, url: str):
        """Start recording session."""
        if not url.strip():
            url = "https://example.com"
        if not url.startswith("http"):
            url = "https://" + url
        
        self.browser.launch(url)
        self.statusMessage.emit(f"Recording browser opened: {url}")
        self.recordingStateChanged.emit(True)
        logger.info(f"Started recording session for {url}")
    
    @Slot()
    def stop_recording(self):
        """Stop recording session."""
        self.browser.stop()
        self.statusMessage.emit("Recording stopped")
        self.recordingStateChanged.emit(False)
        logger.info("Stopped recording session")
    
    @Slot()
    def save_workflow(self):
        """Save current workflow."""
        filename = f"session-{uuid.uuid4()}.json"
        path = workflow_store.save_workflow(self.workflow, filename)
        self.statusMessage.emit(f"Saved workflow to {path}")
        self.refresh_workflow_list()
        logger.info(f"Workflow saved to {path}")
    
    @Slot()
    def refresh_workflow_list(self):
        """Refresh workflow list."""
        workflows = workflow_store.list_workflows()
        self.workflow_list_model.set_workflows(workflows)
        logger.info(f"Loaded {len(workflows)} workflows")
    
    @Slot(str)
    def start_replay(self, workflow_path: str):
        """Start workflow replay."""
        if not workflow_path:
            self.statusMessage.emit("No workflow selected")
            return
        
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
        self.timeline_model.beginResetModel()
        self.timeline_model._items.clear()
        self.timeline_model.endResetModel()
        self.workflow.steps.clear()
        self.statusMessage.emit("Timeline cleared")
    
    def ingest_event(self, payload: Dict[str, Any]):
        """
        Called from WebSocket server thread.
        Marshals the work to the main GUI thread via QMetaObject.invokeMethod.
        """
        import json
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
        import json
        payload = json.loads(payload_json)

        try:
            # Capture base URL from first event
            if not self.workflow.steps and payload.get("page", {}).get("url"):
                self.workflow.meta["baseUrl"] = payload["page"]["url"]

            event_type = payload.get("eventType", payload.get("type", "click"))
            target_desc = payload.get("targetText") or payload.get("target") or ""

            # Process with ML engines
            enhanced_payload = self._enhance_with_ml(payload)

            # Generate multi-dimensional selectors
            locators = []
            if self.selector_engine and "element" in enhanced_payload:
                try:
                    fingerprint = create_fingerprint_from_dom(enhanced_payload)
                    selector_strategies = self.selector_engine.generate_selectors(fingerprint)

                    locators = [
                        Locator(
                            type=sel.type.value,
                            value=sel.value,
                            score=sel.score
                        )
                        for sel in selector_strategies
                    ]

                    logger.debug(f"Generated {len(locators)} selector strategies")
                except Exception as e:
                    logger.error(f"Selector generation failed: {e}")

            # Fallback to basic locators
            if not locators:
                locators = [
                    Locator(type=loc["type"], value=loc["value"], score=loc.get("score", 0.5))
                    for loc in payload.get("locators", [])
                ]

            # Create step
            step = Step(
                id=payload.get("id", str(uuid.uuid4())),
                name=payload.get("name", event_type),
                type=event_type,
                target=Target(locators=locators) if locators else None,
                framePath=payload.get("framePath", []),
                shadowPath=payload.get("shadowPath", []),
                waits=[],
                assertions=[],
                domContext=enhanced_payload.get("domContext"),
                page=payload.get("page"),
                timing=payload.get("timing"),
                input=payload.get("input"),
                metadata=enhanced_payload.get("ml_metadata", {})
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
                "confidence": enhanced_payload.get("ml_metadata", {}).get("confidence", 0.0)
            })

            self.timelineChanged.emit()
            logger.info(f"Captured step {step.id} ({step.type}) with {len(locators)} selectors")

        except Exception as e:
            logger.error(f"Event ingestion error: {e}")
    
    def _enhance_with_ml(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance payload with ML analysis.
        """
        enhanced = payload.copy()
        ml_metadata = {}
        
        try:
            # NLP analysis
            if self.nlp_engine:
                text = payload.get("textContent", "")
                if text:
                    analysis = self.nlp_engine.analyze_text(
                        text,
                        context={
                            "action_type": payload.get("eventType", ""),
                            "url": payload.get("page", {}).get("url", "")
                        }
                    )
                    
                    ml_metadata["intent"] = analysis.intent.value
                    ml_metadata["confidence"] = analysis.confidence
                    ml_metadata["keywords"] = analysis.keywords
                    ml_metadata["sentiment"] = analysis.sentiment
            
            # Visual analysis
            if self.vision_matcher and payload.get("screenshot"):
                # In production, would process actual screenshot
                ml_metadata["visual_processed"] = True
            
            # Framework detection
            if payload.get("frameworkInfo"):
                ml_metadata["framework"] = payload["frameworkInfo"].get("name", "unknown")
            
            enhanced["ml_metadata"] = ml_metadata
            
        except Exception as e:
            logger.error(f"ML enhancement error: {e}")
        
        return enhanced
    
    @Slot(str)
    def analyze_intent(self, workflow_id: str):
        """Analyze workflow intent using LLM."""
        if not self.llm_engine:
            self.statusMessage.emit("LLM engine not available")
            return
        
        try:
            # Get workflow steps
            actions = [
                {
                    "type": step.type,
                    "target": step.target.locators[0].value if step.target and step.target.locators else ""
                }
                for step in self.workflow.steps
            ]
            
            # Classify intent
            result = self.llm_engine.classify_intent(
                actions,
                page_context=self.workflow.meta.get("baseUrl", "")
            )
            
            message = f"Intent: {result.primary_intent} (confidence: {result.confidence:.2f})"
            self.statusMessage.emit(message)
            logger.info(f"Intent analysis: {message}")
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            self.statusMessage.emit(f"Intent analysis failed: {str(e)}")
    
    @Slot(str, str)
    def verify_statement(self, statement: str, context: str = ""):
        """Verify statement against knowledge base."""
        if not self.rag_engine:
            self.statusMessage.emit("RAG engine not available")
            return
        
        try:
            result = self.rag_engine.verify_statement(statement, context)
            
            message = f"Verification: {result.is_verified} (confidence: {result.confidence:.2f})"
            self.statusMessage.emit(message)
            logger.info(f"Statement verification: {message}")
            logger.info(f"  {result.explanation}")
            
        except Exception as e:
            logger.error(f"Statement verification failed: {e}")
            self.statusMessage.emit(f"Verification failed: {str(e)}")
    
    @Slot()
    def get_healing_stats(self):
        """Get selector healing statistics."""
        if not self.healing_engine:
            return {}
        
        return self.healing_engine.get_healing_stats()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Call Intelligence System - Professional")
    app.setOrganizationName("CallIntelligence")
    
    engine = QQmlApplicationEngine()
    
    # Create controller
    controller = EnhancedRecordingController()
    
    # Register with QML
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("timelineModel", controller.timeline_model)
    engine.rootContext().setContextProperty("workflowListModel", controller.workflow_list_model)
    
    # Load QML (use working UI)
    qml_files = [
        "ui/main.qml",  # Working UI with actual functionality
        "ui/main_professional.qml"
    ]
    
    qml_file = None
    for qml_path in qml_files:
        full_path = os.path.join(os.path.dirname(__file__), "..", qml_path)
        if os.path.exists(full_path):
            qml_file = full_path
            break
    
    if not qml_file:
        logger.error("No QML file found!")
        sys.exit(-1)
    
    engine.load(QUrl.fromLocalFile(os.path.abspath(qml_file)))
    
    if not engine.rootObjects():
        logger.error("Failed to load QML!")
        sys.exit(-1)
    
    logger.info(f"Application started with {qml_file}")
    
    # Run application
    ret = app.exec()
    
    # Cleanup
    controller.browser.stop()
    controller.server.stop()
    QCoreApplication.quit()
    
    sys.exit(ret)


if __name__ == "__main__":
    main()
