# Auton8 Smart Recorder

Enterprise browser automation system with ML-powered self-healing replay. Record web workflows on lightweight tester machines, replay with AI-driven selector healing, and run all heavy ML inference on a shared central server.

**GitHub:** https://github.com/gulpcr/auton8-smart-recorder

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CENTRAL SERVER                          │
│   FastAPI :8010  │  ML Engines  │  SQLite/PostgreSQL        │
│                                                             │
│  Selector healing · Vision · NLP · LLM · RAG · Audio       │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP REST (port 8010)
         ┌─────────────────┼──────────────────┐
         │                 │                  │
┌────────▼───────┐ ┌───────▼───────┐ ┌────────▼───────┐
│  Tester PC 1   │ │  Tester PC 2  │ │  Tester PC N   │
│  Recorder App  │ │  Recorder App │ │  Recorder App  │
│  PySide6 + QML │ │  PySide6+QML  │ │  PySide6+QML   │
│  Playwright    │ │  Playwright   │ │  Playwright    │
│  WS :8765      │ │  WS :8765     │ │  WS :8765      │
└────────────────┘ └───────────────┘ └────────────────┘
       │ Browser events (localhost only)
  injected.js → ws://127.0.0.1:8765
```

**Tester machines** run only the recorder app (minimal install — no ML dependencies).
**Central server** runs the FastAPI server with all ML engines.
Each tester registers itself via heartbeat and delegates ML-heavy work to the server.

---

## Features

### Recording
- PySide6 + QML desktop UI with live timeline and inspector sidebar
- Playwright-controlled browser with injected event capture
- Captures clicks, inputs, navigation, assertions, screenshots, frames, shadow DOM paths
- Multi-dimensional selector generation (CSS, XPath, ARIA, text, position, structural)
- Auto-saves workflow to JSON with full step metadata

### Replay & Self-Healing
- 6-tier healing strategy — tries each tier before marking a step as failed

| Tier | Strategy | Location |
|------|----------|----------|
| 0 | Primary selector retry | Tester (local) |
| 1 | CSS / XPath fallback | Tester (local) |
| 2 | Visual / OCR matching | Server (OpenCV + Tesseract) |
| 3 | Text fuzzy matching | Server (BERT + spaCy) |
| 4 | Position-based search | Tester (local) |
| 5 | Structural recovery | Server (LLM) |
| 6 | ML-trained model | Server (XGBoost) |

- Expandable step detail panel — see original vs healed selector, per-tier attempt errors
- Execution history with pass/fail/healed stats stored in database

### ML Services (Server)
- **Vision** — OpenCV template matching, Tesseract OCR, SSIM image comparison
- **NLP** — BERT sentence similarity, spaCy entity extraction, sentiment analysis
- **LLM** — llama-cpp-python with any GGUF model (Mistral, Llama, Phi-3); intent classification, recovery planning, KPI scoring
- **RAG** — FAISS + BM25 knowledge base for statement verification against SOPs/FAQs
- **Audio** — WhisperX transcription + pyannote speaker diarization

### Skills Framework
Skills are capability modules with three execution modes:

| Mode | Behaviour |
|------|-----------|
| `local` | Never contacts the server — runs everything on the tester machine |
| `hybrid` | Tries local first, falls back to server if local fails or is unavailable |
| `server` | Always delegates to the central server |

---

## Quick Start

### 1. Deploy the Server

```bash
# Clone the repo
git clone https://github.com/gulpcr/auton8-smart-recorder.git
cd auton8-smart-recorder

# Configure
cp .env.example .env
# Edit .env — set ADMIN_EMAIL and ADMIN_PASSWORD at minimum

# Build and start
docker compose up -d --build

# Verify
curl http://localhost:8010/health
```

### 2. Get an Access Token

```bash
curl -X POST http://YOUR_SERVER_IP:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourorg.com", "password": "your-password"}'
```

Copy the `accessToken` from the response.

### 3. Install the Recorder on Each Tester Machine

```bash
# Minimal install — no ML dependencies needed
pip install -r requirements-minimal.txt
playwright install chromium
```

### 4. Connect the Recorder to the Server

Edit `data/settings.json`:

```json
{
  "portalUrl": "http://YOUR_SERVER_IP:8010",
  "portalAccessToken": "paste-token-here",
  "skillMode": "hybrid",
  "serverFallback": true
}
```

### 5. Run the Recorder

```bash
python -m recorder.app_enhanced
```

The app connects to the server, sends a heartbeat every 30 seconds, and appears on the server dashboard at `http://YOUR_SERVER_IP:8010`.

---

## Installation

See **[INSTALLATION.md](INSTALLATION.md)** for the complete step-by-step guide covering:
- Docker and manual server deployment
- Windows and Linux/macOS tester machine setup
- Firewall configuration
- Verification steps
- Troubleshooting

---

## Configuration

### Tester Machine — `data/settings.json`

| Key | Default | Description |
|-----|---------|-------------|
| `portalUrl` | `""` | Central server URL, e.g. `http://192.168.1.100:8010` |
| `portalAccessToken` | `""` | Bearer token from `/api/auth/login` |
| `skillMode` | `"hybrid"` | `local` / `hybrid` / `server` |
| `serverFallback` | `true` | Use server when local ML fails |
| `serverTimeout` | `30` | Server request timeout (seconds) |
| `maxTier` | `3` | Maximum healing tier to attempt (0–6) |
| `browserType` | `"chromium"` | `chromium` / `firefox` / `webkit` |
| `headlessMode` | `false` | Run browser without a visible window |
| `websocketPort` | `8765` | Local WebSocket port for browser events |

### Server — Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_EMAIL` | `admin@localhost` | Login email |
| `ADMIN_PASSWORD` | *(empty — any password accepted)* | Login password — **always set in production** |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins, e.g. `http://192.168.1.10,http://192.168.1.11` |
| `DATA_DIR` | `<project_root>/data` | Absolute path to data directory |
| `LLM_MODEL_PATH` | *(auto-detected)* | Absolute path to a `.gguf` model file |
| `AUTON8_MODELS_DIR` | *(auto-detected)* | Directory containing `.gguf` files |
| `LLM_N_CTX` | `4096` | LLM context window size |
| `LLM_N_THREADS` | `4` | CPU threads for LLM inference |
| `LLM_N_GPU_LAYERS` | `0` | GPU layers for LLM inference (0 = CPU only) |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## Usage

### Recording a Workflow

1. Open the recorder app — `python -m recorder.app_enhanced`
2. Click **New Recording**, enter a name
3. Click **Start Recording** — Playwright opens a browser
4. Perform your actions in the browser
5. Click **Stop Recording**, then **Save Workflow**
6. Workflow is saved to `data/workflows/<name>.json` and synced to the server

### Replaying a Workflow

**From the UI** — select a workflow → click **Replay** → watch step results in the detail panel.

**From the CLI:**
```bash
python -m replay.replayer data/workflows/my-workflow.json
```

**From the API:**
```bash
curl -X POST http://YOUR_SERVER_IP:8010/api/replay \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "my-workflow.json", "headless": true}'
```

### Uploading Audio for Transcription

```bash
curl -X POST http://YOUR_SERVER_IP:8010/api/upload-audio \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@recording.wav"
```

Returns a `job_id`. Poll for results:

```bash
curl http://YOUR_SERVER_IP:8010/api/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Project Structure

```
auton8-smart-recorder/
│
├── recorder/                    # Main Python package
│   ├── api/
│   │   ├── main.py              # FastAPI server — all endpoints
│   │   ├── database.py          # SQLAlchemy models + repositories
│   │   └── templates/           # Web dashboard HTML
│   │
│   ├── skills/                  # Skills framework
│   │   ├── base.py              # SkillBase, SkillRegistry, SkillMode
│   │   ├── portal_client.py     # stdlib HTTP client (no requests/httpx)
│   │   ├── record.py            # Browser recording
│   │   ├── replay.py            # Workflow execution
│   │   ├── healing.py           # Selector healing (hybrid)
│   │   ├── selector_gen.py      # ML selector generation (hybrid)
│   │   ├── assertions.py        # Text, visible, URL, storage, regex
│   │   ├── variables.py         # Store / get / evaluate variables
│   │   ├── workflow_mgmt.py     # CRUD + server sync
│   │   ├── suite_runner.py      # Multi-workflow execution
│   │   ├── screenshot.py        # Element and page capture
│   │   ├── vision.py            # Server-delegated CV
│   │   ├── nlp.py               # Server-delegated NLP
│   │   ├── llm.py               # Server-delegated LLM
│   │   ├── rag.py               # Server-delegated RAG
│   │   ├── audio.py             # Server-delegated audio
│   │   └── analytics.py         # Server-delegated analytics
│   │
│   ├── ml/                      # ML engines (server-side)
│   │   ├── selector_engine.py   # Multi-dimensional selector generation
│   │   ├── healing_engine.py    # 6-tier self-healing
│   │   ├── vision_engine.py     # OpenCV + Tesseract + SSIM
│   │   ├── nlp_engine.py        # BERT + spaCy
│   │   ├── llm_engine.py        # llama-cpp-python inference
│   │   ├── rag_engine.py        # FAISS + BM25 knowledge base
│   │   └── ollama_engine.py     # Ollama integration
│   │
│   ├── audio/
│   │   └── transcription_engine.py  # WhisperX + pyannote diarization
│   │
│   ├── services/
│   │   ├── ws_server.py         # WebSocket ingest (port 8765)
│   │   ├── stable_replay.py     # Tiered replay executor
│   │   ├── workflow_store.py    # Workflow CRUD
│   │   ├── expression_engine.py # Variable evaluation
│   │   └── global_variable_registry.py
│   │
│   ├── models/                  # PySide6 QML data models
│   ├── schema/                  # Pydantic schemas
│   ├── app_enhanced.py          # Main desktop app (recommended)
│   ├── app.py                   # Basic desktop app
│   └── app_ml_integrated.py     # Full local ML app
│
├── ui/                          # QML UI components
│   ├── main_enhanced.qml        # Main UI with replay detail panel
│   └── components/              # Reusable QML components
│
├── instrumentation/
│   ├── injected.js              # Browser event capture script
│   └── injected_advanced.js     # Advanced capture with shadow DOM
│
├── replay/
│   └── replayer.py              # CLI workflow runner
│
├── data/                        # Runtime data (git-ignored)
│   ├── workflows/               # Saved workflow JSON files
│   ├── screenshots/             # Step screenshots
│   ├── executions/              # Execution records
│   ├── uploads/                 # Audio file uploads
│   ├── rag_index/               # FAISS knowledge base index
│   └── settings.json            # App configuration
│
├── Dockerfile                   # Server container image
├── docker-compose.yml           # Single-service compose
├── .env.example                 # Environment variable template
├── requirements-minimal.txt     # Tester machine install
├── requirements-server.txt      # Server install (no UI/browser deps)
├── requirements-core.txt        # Core ML deps
├── requirements-ml-advanced.txt # BERT / FAISS / transformers
├── requirements-audio.txt       # WhisperX / pyannote
├── requirements.txt             # Full development install
├── pyproject.toml               # Package build config
├── INSTALLATION.md              # Full deployment guide
└── README.md
```

---

## API Reference

The server exposes a full REST API. Interactive docs are available at `http://YOUR_SERVER_IP:8010/docs`.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + uptime |
| `GET` | `/models/status` | ML engine status |
| `GET` | `/api/skills/status` | Available skills on server |
| `POST` | `/api/auth/login` | Get bearer token |
| `POST` | `/api/clients/heartbeat` | Recorder registration |
| `GET` | `/api/clients` | List connected recorders |
| `GET` | `/api/workflows` | List workflows |
| `POST` | `/api/replay` | Trigger replay (async job) |
| `GET` | `/api/jobs/{id}` | Job status + result |
| `POST` | `/api/selectors/generate` | ML selector generation |
| `POST` | `/api/selectors/heal` | Selector healing |
| `POST` | `/api/vision/match` | OpenCV template matching |
| `POST` | `/api/nlp/similarity` | BERT text similarity |
| `POST` | `/api/llm/classify-intent` | LLM intent classification |
| `POST` | `/api/llm/recover` | LLM recovery planning |
| `POST` | `/api/verify-statement` | RAG fact verification |
| `POST` | `/api/rag/ingest` | Load documents into knowledge base |
| `POST` | `/api/upload-audio` | Audio transcription (async) |
| `POST` | `/api/analyze-transcript` | Intent + sentiment + KPI scoring |
| `GET` | `/api/executions` | Execution history |
| `GET` | `/api/dashboard/stats` | Pass rate, healing rate, ML stats |

---

## Development

### Full local install

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
playwright install chromium
python -m spacy download en_core_web_sm
```

### Run the server locally

```bash
python -m recorder.api.main
```

### Run the desktop app

```bash
python -m recorder.app_enhanced
```

### Entry points (after `pip install -e .`)

```bash
auton8-recorder   # Desktop app
auton8-server     # API server
```

---

## Requirements Summary

| Install | Command | Use case |
|---------|---------|----------|
| Tester machine | `pip install -r requirements-minimal.txt` | Record + replay only |
| Server (Docker) | `docker compose up --build` | Full ML stack |
| Server (manual) | `pip install -r requirements-server.txt` | Full ML, no UI/browser |
| Full dev | `pip install -r requirements.txt` | Local development |
| Package extras | `pip install ".[full]"` | All features via pyproject.toml |

---

## License

MIT
