from __future__ import annotations

import os
import sys
import uuid
import logging
from typing import Any, Dict

from PySide6.QtCore import QObject, Slot, Signal, QUrl, QCoreApplication
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


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recorder")


class RecordingController(QObject):
    """
    Glue between the WebSocket ingest server, the workflow model, and the QML UI.
    """

    timelineChanged = Signal()
    statusMessage = Signal(str)
    recordingStateChanged = Signal(bool)
    replayStateChanged = Signal(bool)
    replayProgress = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.timeline_model = TimelineModel()
        self.workflow_list_model = WorkflowListModel()
        self.workflow = Workflow()
        self.server = WebSocketIngestServer()
        self.server.set_callback(self.ingest_event)
        self.server.start()
        self.browser = BrowserLauncher()
        self.replayer = ReplayLauncher()
        self.replayer.set_callbacks(
            on_step=self._on_replay_step,
            on_complete=self._on_replay_complete,
        )
        self.refresh_workflow_list()
        logger.info("Recording controller initialized and server started.")

    def _on_replay_step(self, index: int, step_type: str):
        self.replayProgress.emit(index, step_type)

    def _on_replay_complete(self, success: bool, error: str, total_duration_ms: int = 0):
        self.replayStateChanged.emit(False)
        if success:
            self.statusMessage.emit("Replay completed successfully")
        else:
            self.statusMessage.emit(f"Replay failed: {error}")

    @Slot(str)
    def start_recording(self, url: str):
        if not url.strip():
            url = "https://example.com"
        if not url.startswith("http"):
            url = "https://" + url
        self.browser.launch(url)
        self.statusMessage.emit(f"Recording browser opened: {url}")
        self.recordingStateChanged.emit(True)
        logger.info("Started recording session for %s", url)

    @Slot()
    def stop_recording(self):
        self.browser.stop()
        self.statusMessage.emit("Recording stopped")
        self.recordingStateChanged.emit(False)
        logger.info("Stopped recording session")

    @Slot()
    def save_workflow(self):
        filename = f"session-{uuid.uuid4()}.json"
        path = workflow_store.save_workflow(self.workflow, filename)
        self.statusMessage.emit(f"Saved workflow to {path}")
        self.refresh_workflow_list()
        logger.info("Workflow saved to %s", path)

    @Slot()
    def refresh_workflow_list(self):
        workflows = workflow_store.list_workflows()
        self.workflow_list_model.set_workflows(workflows)
        logger.info("Loaded %d workflows", len(workflows))

    @Slot(str)
    def start_replay(self, workflow_path: str):
        if not workflow_path:
            self.statusMessage.emit("No workflow selected")
            return
        self.replayer.replay(workflow_path)
        self.replayStateChanged.emit(True)
        self.statusMessage.emit("Replay started...")
        logger.info("Started replay for %s", workflow_path)

    @Slot()
    def stop_replay(self):
        self.replayer.stop()
        self.replayStateChanged.emit(False)
        self.statusMessage.emit("Replay stopped")
        logger.info("Stopped replay")

    @Slot()
    def clear_timeline(self):
        self.timeline_model.beginResetModel()
        self.timeline_model._items.clear()
        self.timeline_model.endResetModel()
        self.workflow.steps.clear()
        self.statusMessage.emit("Timeline cleared")

    def ingest_event(self, payload: Dict[str, Any]):
        """
        Called from the WebSocket server thread.
        Marshals the work to the main GUI thread via QMetaObject.invokeMethod.
        """
        import json
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        # Serialize payload to pass across thread boundary
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

        # Capture base URL from first event
        if not self.workflow.steps and payload.get("page", {}).get("url"):
            self.workflow.meta["baseUrl"] = payload["page"]["url"]

        event_type = payload.get("type", "click")
        target_desc = payload.get("targetText") or payload.get("target") or ""
        locators = [Locator(type=loc["type"], value=loc["value"], score=loc.get("score", 0.5)) for loc in payload.get("locators", [])]
        step = Step(
            id=payload.get("id", str(uuid.uuid4())),
            name=payload.get("name", event_type),
            type=event_type,
            target=Target(locators=locators) if locators else None,
            framePath=payload.get("framePath", []),
            shadowPath=payload.get("shadowPath", []),
            waits=[],
            assertions=[],
            domContext=payload.get("domContext"),
            page=payload.get("page"),
            timing=payload.get("timing"),
            input=payload.get("input"),
        )
        self.workflow.steps.append(step)
        self.timeline_model.append_step(
            {
                "id": step.id,
                "name": step.name,
                "type": step.type,
                "target": target_desc,
                "status": "pending",
                "timestamp": payload.get("timestamp", ""),
            }
        )
        self.timelineChanged.emit()
        logger.info("Captured step %s (%s)", step.id, step.type)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Call Intelligence Recorder")
    engine = QQmlApplicationEngine()

    controller = RecordingController()
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("timelineModel", controller.timeline_model)
    engine.rootContext().setContextProperty("workflowListModel", controller.workflow_list_model)

    qml_file = os.path.join(os.path.dirname(__file__), "..", "ui", "main.qml")
    engine.load(QUrl.fromLocalFile(os.path.abspath(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    ret = app.exec()
    controller.browser.stop()
    controller.server.stop()
    QCoreApplication.quit()
    sys.exit(ret)


if __name__ == "__main__":
    main()

