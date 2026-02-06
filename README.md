## Call Intelligence System – Web Recorder (Python Desktop)

Desktop-grade recorder built with PySide6/QML, browser instrumentation, resilient selector capture, and Playwright replay. This repository contains working code (no mock data) for the control center app, instrumentation script, and replay runner.

### Features
- PySide6 + QML premium UI with live timeline, inspector sidebar, and dark/light themes.
- WebSocket ingestion of real browser events (frames + shadow DOM paths).
- JSON workflow storage with multi-locator targets, waits, assertions, and artifacts.
- Playwright-based replay with frame/shadow navigation, waits, and logging.
- AI toggle ready (offline/online modes scaffolded for future LLM integration).

### Structure
- `recorder/app.py` – Qt application entrypoint.
- `recorder/models/timeline_model.py` – QAbstractListModel for steps.
- `recorder/services/ws_server.py` – WebSocket ingestion server for browser events.
- `recorder/services/workflow_store.py` – load/save workflow JSON.
- `recorder/schema/workflow.py` – Pydantic workflow schema.
- `ui/main.qml` – QML UI for the control center.
- `instrumentation/injected.js` – Browser-side capture script (inject or use extension wrapper).
- `replay/replayer.py` – Playwright runner that executes recorded JSON workflows.

### Setup
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m playwright install
```

### Run Desktop App
```bash
python -m recorder.app
```

### Inject Recorder in Browser (manual)
1) Serve `instrumentation/injected.js` or paste into console for dev testing.
2) Ensure the desktop app is running; default WebSocket ingest endpoint: `ws://localhost:8765`.
3) Open target page; events stream into the timeline.

### Replay a Workflow
```bash
python -m replay.replayer data/workflows/session.json
```

### Notes
- Healing/AI hooks are scaffolded; extend `services/ai_bridge.py` (to add) for OpenAI/offline Llama.
- All selectors, frames, and shadow paths are persisted; replay automatically walks them.

