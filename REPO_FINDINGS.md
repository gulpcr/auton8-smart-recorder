# Repository Findings Summary

## 📋 Overview
This is a **desktop Playwright recorder application** built with **PySide6/QML** that captures browser interactions, generates multi-dimensional ML-powered selectors, and replays workflows using Playwright. The app integrates advanced ML/AI features including computer vision, NLP, and intelligent selector healing.

---

## 🗂️ Repository Structure

```
recorder/
├── app.py                          # Basic entry point (original)
├── app_ml_integrated.py            # Enhanced ML/AI entry point (current)
├── models/
│   ├── timeline_model.py           # QAbstractListModel for steps display
│   └── workflow_list_model.py      # QAbstractListModel for saved workflows
├── schema/
│   └── workflow.py                 # Pydantic models (Workflow, Step, Target, Locator)
├── services/
│   ├── ws_server.py                # WebSocket server for event ingestion
│   ├── workflow_store.py           # JSON file persistence layer
│   ├── browser_launcher.py         # Browser automation with injected script
│   └── replay_launcher.py          # Replay execution wrapper
├── ml/                             # ML/AI components (DO NOT MODIFY INTERNALS)
│   ├── selector_engine.py          # Multi-dimensional selector generation
│   ├── healing_engine.py           # XGBoost-powered selector healing
│   ├── vision_engine.py            # OCR, template matching, SSIM
│   ├── nlp_engine.py               # BERT embeddings, spaCy NLP
│   ├── llm_engine.py               # Local LLM integration (Llama.cpp)
│   └── rag_engine.py               # FAISS vector search
├── audio/
│   └── transcription_engine.py     # WhisperX transcription (optional)
└── api/
    └── main.py                     # FastAPI server (optional)

replay/
└── replayer.py                      # Playwright-based workflow executor

ui/
├── main.qml                         # Current functional UI (2-tab layout)
└── main_professional.qml            # Professional mockup (needs enhancement)

instrumentation/
├── injected.js                      # Basic browser instrumentation
└── injected_advanced.js             # ML-enhanced instrumentation

data/
└── workflows/                       # Saved workflow JSON files
```

---

## 🔑 Key Components

### 1. **Entry Points**
- **`recorder/app.py`**: Original basic recorder
- **`recorder/app_ml_integrated.py`**: Current ML-powered version with `EnhancedRecordingController`

### 2. **Core Models** (QAbstractListModel for QML binding)

**`TimelineModel`** (`recorder/models/timeline_model.py`)
- Roles: `IdRole`, `NameRole`, `TypeRole`, `StatusRole`, `TargetRole`, `TimestampRole`
- Methods: `append_step()`, `update_status()`, `to_list()`

**`WorkflowListModel`** (`recorder/models/workflow_list_model.py`)
- Roles: `NameRole`, `FilenameRole`, `PathRole`, `StepCountRole`, `BaseUrlRole`
- Methods: `set_workflows()`, `getPath(index)`

### 3. **Schema** (Pydantic, backward compatible)

**`Workflow`** (`recorder/schema/workflow.py`)
```python
class Workflow(BaseModel):
    version: str = "1.0"
    project: Dict[str, object]      # Can extend for test metadata
    meta: Dict[str, object]          # Can add: name, status, tags, createdAt
    steps: List[Step]
    assets: Dict[str, object]        # Screenshots, traces
    replay: Dict[str, object]        # Replay results
```

**`Step`**
```python
class Step(BaseModel):
    id: str
    name: str
    type: Literal["click", "type", "input", "wait", ...]
    target: Optional[Target]         # Contains locators
    framePath: List[FrameHint]
    shadowPath: List[ShadowHost]
    waits: List[WaitCondition]
    assertions: List[Assertion]
    input: Optional[Dict]
    artifacts: Optional[Dict]
    domContext: Optional[Dict]
    page: Optional[Dict]
    healing: Optional[Dict]
    timing: Optional[Dict]
    semantic: Optional[Dict]         # ✅ Available for ML metadata
```

**`Locator`**
```python
class Locator(BaseModel):
    type: Literal["data", "aria", "label", "css", "text", "xpath", "frame", "shadow"]
    value: str
    score: float = 0.5              # ML confidence score
```

### 4. **Workflow Storage** (`recorder/services/workflow_store.py`)
- **Storage**: JSON files in `data/workflows/`
- **Functions**:
  - `save_workflow(workflow, filename)` → path
  - `load_workflow(filename)` → Workflow
  - `list_workflows()` → List[dict] with metadata
- **Format**: Standard JSON with UTF-8 encoding

### 5. **Event Ingestion** (`recorder/services/ws_server.py`)
- **Protocol**: WebSocket on `ws://127.0.0.1:8765`
- **Flow**: Browser → WS → `controller.ingest_event(payload)` → Model update
- **Payload Structure**:
```javascript
{
  type: "click",
  targetText: "...",
  locators: [{type, value, score}],
  page: {url, title},
  framePath: [...],
  shadowPath: [...],
  domContext: {...},
  timing: {...}
}
```

### 6. **ML/AI Integration Points** (BLACK BOX - DO NOT MODIFY)

**Selector Engine** (`recorder/ml/selector_engine.py`)
- **Public Interface**:
  - `MultiDimensionalSelectorEngine.generate_selectors(fingerprint)` → List[SelectorStrategy]
  - `create_fingerprint_from_dom(payload)` → ElementFingerprint
- **Output**: 7+ selector types (ID, CSS, XPath, ARIA, text, visual, position)

**Healing Engine** (`recorder/ml/healing_engine.py`)
- **Public Interface**: `SelectorHealingEngine.heal(selector, context)` → healed selector
- **Technology**: XGBoost classifier

**Vision Engine** (`recorder/ml/vision_engine.py`)
- **Public Interface**: `VisualElementMatcher.match(screenshot, template)` → similarity score
- **Features**: OCR, perceptual hashing, template matching, SSIM

**NLP Engine** (`recorder/ml/nlp_engine.py`)
- **Public Interface**: `NLPEngine.analyze_text(text, context)` → TextAnalysis
- **Features**: BERT embeddings, intent classification, keyword extraction

**LLM Engine** (`recorder/ml/llm_engine.py`) [Optional]
- **Public Interface**: `LocalLLMEngine.classify_intent(actions, context)` → IntentResult

**RAG Engine** (`recorder/ml/rag_engine.py`) [Optional]
- **Public Interface**: `RAGEngine.verify_statement(statement, context)` → VerificationResult

### 7. **Replay System** (`replay/replayer.py`)

**Core Functions**:
- `run_workflow(workflow)` → async execution
- `run_step(page, step)` → executes single step
- `resolve_target(page, step)` → handles frames/shadows, tries locators by score

**Locator Strategy**:
```python
async def pick_locator_handle(context, current, locs: List[Locator]):
    for loc in sorted(locs, key=lambda l: l.score, reverse=True):
        selector = locator_to_selector(loc)
        handle = current.locator(selector)
        if await handle.count() > 0:
            return handle, loc
    raise RuntimeError("No locator matched target")
```

### 8. **UI Framework** (QML 6.4)

**Current UI** (`ui/main.qml`)
- **Layout**: 2 tabs (Record, Replay)
- **Styling**: Dark theme (`#1a1a2e` background, `#e94560` accent)
- **Bindings**: Direct to `controller`, `timelineModel`, `workflowListModel`
- **Features**: URL input, record/stop, live step list, workflow selection

**Professional UI** (`ui/main_professional.qml`)
- Mockup design (needs functional integration)

---

## 🎯 Important Integration Points

### Recording Flow
```
Browser Event
  → injected_advanced.js captures interaction
  → WebSocket payload → ws_server.py
  → controller.ingest_event(payload)
  → ML enhancement (_enhance_with_ml)
  → selector_engine.generate_selectors(fingerprint)
  → Create Step with multi-dimensional locators
  → Append to workflow.steps
  → Update timelineModel
  → Emit timelineChanged signal → UI updates
```

### Replay Flow
```
User selects workflow
  → controller.start_replay(path)
  → ReplayLauncher.replay(path)
  → replayer.run_workflow(workflow)
  → For each step:
    → resolve_target (tries locators by score)
    → execute action (click, type, etc.)
    → run assertions
  → Emit progress signals → UI updates
```

### ML Integration Points (DO NOT TOUCH)
- **`app_ml_integrated.py:305-320`**: `generate_selectors()` call
- **`app_ml_integrated.py:364-403`**: `_enhance_with_ml()` method
- **Healing**: Currently only in demo, not in live replay (future enhancement)

---

## 🔒 Backward Compatibility Requirements

1. **Schema**:
   - All new fields must be Optional or have defaults
   - Keep existing field names unchanged
   - Add new fields to `meta`, `project`, `assets` dicts

2. **Locator Types**:
   - Keep existing types: `data`, `aria`, `label`, `css`, `text`, `xpath`
   - Can add new types via union extension

3. **File Format**:
   - JSON with UTF-8 encoding
   - Version field for migration tracking
   - Old workflows must load without errors

4. **UI**:
   - Keep `controller` QML property name
   - Keep existing signals/slots for backward compat
   - Add new features via new properties/methods

---

## 🎨 Design System (Current)

**Colors**:
- Background: `#1a1a2e` (dark navy)
- Panel: `#16213e` (lighter navy)
- Input: `#0f3460` (blue)
- Accent: `#e94560` (coral red)
- Text: `#e0e0e0` (light gray)
- Muted: `#888` (gray)

**Typography**:
- Headers: 16-22px, bold
- Body: 13-15px
- Small: 11-12px

**Spacing**:
- Margins: 16-24px
- Item spacing: 6-12px
- Border radius: 6-12px

---

## 📝 Notes

1. **ML Features**: Fully operational but optional (graceful degradation if models missing)
2. **State Management**: Qt signals/slots + QML bindings
3. **Async**: Replay uses asyncio, recording uses threads (WebSocket server)
4. **Error Handling**: Try-except with logger.error() throughout
5. **No Database**: Pure file-based (JSON workflows, screenshots in data/)

---

## ⚠️ Critical Constraints

1. **DO NOT** refactor ML/AI internal logic
2. **DO NOT** break existing JSON format
3. **DO NOT** rename existing schema fields without aliases
4. **DO** add new features additively
5. **DO** maintain backward compatibility with existing workflows
6. **DO** use feature flags for major changes
7. **DO** keep UI responsive (no blocking operations on main thread)

---

## 🚀 Next Steps

See `IMPLEMENTATION_PLAN.md` for detailed enhancement roadmap.
