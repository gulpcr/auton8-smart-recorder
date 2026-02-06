# Auton8 Recorder - Claude Enhancement Context

## CRITICAL: Read Before Making Any Changes

This document provides essential context for enhancing the Auton8 Recorder application. **Do not break or modify existing patterns without explicit approval.**

---

## 1. Architecture Overview

### Application Type
- **Desktop App**: PySide6 (Qt) with QML UI
- **Backend**: Python async with Playwright for browser automation
- **ML/AI**: Custom ML engines for selector ranking, healing, and vision-based element detection

### Directory Structure
```
recorder/
├── app_enhanced.py          # Main application entry point & controller
├── schema/
│   └── workflow.py          # Pydantic models for Step, Workflow, Locator
├── models/                   # Qt models for QML binding
│   ├── timeline_model.py
│   ├── workflow_list_model.py
│   ├── step_detail_model.py
│   └── execution_history_model.py
├── services/
│   ├── workflow_store.py    # Workflow persistence (JSON files)
│   ├── ws_server.py         # WebSocket server for browser extension
│   ├── browser_launcher.py  # Playwright browser management
│   └── execution/           # Execution engine
│       ├── tiered_executor.py    # CORE: Tiered execution strategy
│       ├── page_stability.py     # Page/element stability detection
│       ├── action_verifier.py    # Action outcome verification
│       ├── variable_store.py     # Cross-test variable storage
│       └── frame_handler.py      # Frame, window, dialog handling
├── ml/                       # ML/AI engines (DO NOT MODIFY WITHOUT CARE)
│   ├── selector_engine.py   # Multi-dimensional selector ranking
│   ├── healing_engine.py    # Selector self-healing
│   ├── vision_engine.py     # Computer vision element detection
│   ├── nlp_engine.py        # NLP for semantic understanding
│   └── ollama_engine.py     # LLM integration for recovery
├── api/                      # FastAPI backend for dashboard
│   ├── main.py
│   └── database.py
└── ui/                       # QML UI components
    └── components/
        └── StepDetailPanel.qml
```

---

## 2. TIERED EXECUTION ENGINE (CRITICAL - DO NOT BREAK)

The execution engine uses a **tiered fallback strategy** that is core to the product's value proposition.

### Tier Philosophy
```
Tier 0 (Deterministic) → Tier 1 (Heuristic) → Tier 2 (Vision) → Tier 3 (LLM)
         80%                   15%                  4%              1%
```

**80% of actions MUST complete at Tier 0. AI is a safety net, not a crutch.**

### Tier Details

#### Tier 0: Deterministic (No AI)
- Uses primary selector only
- Playwright's built-in waiting
- Element stability checks
- **File**: `tiered_executor.py` → `_tier_0_deterministic()`

#### Tier 1: Heuristic (Pattern Matching)
- Fallback selectors from ML engine
- Pattern-specific heuristics (dropdowns, forms, modals)
- Semantic discovery by text/aria-label
- **File**: `tiered_executor.py` → `_tier_1_heuristic()`

#### Tier 2: Computer Vision
- Screenshot analysis
- Template matching with OpenCV
- Visual element location when selectors fail
- **File**: `tiered_executor.py` → `_tier_2_vision()`, `vision_engine.py`

#### Tier 3: LLM Recovery (Last Resort)
- Uses Ollama/local LLM for recovery planning
- Analyzes page state and suggests actions
- Only used when all else fails
- **File**: `tiered_executor.py` → `_tier_3_llm()`, `ollama_engine.py`

### Key Classes in tiered_executor.py
```python
class ExecutionTier(Enum):
    TIER_0_DETERMINISTIC = 0
    TIER_1_HEURISTIC = 1
    TIER_2_VISION = 2
    TIER_3_LLM = 3

@dataclass
class ExecutionContext:
    step_index: int
    step_type: str
    step_name: str
    locators: List[LocatorCandidate]
    input_value: Optional[str]
    dom_context: Optional[Dict]
    expected_navigation: bool

@dataclass
class ExecutionResult:
    success: bool
    tier_used: ExecutionTier
    locator_used: Optional[LocatorCandidate]
    verification: Optional[ActionOutcome]
    duration_ms: int
    error: Optional[str]
    healing_change: Optional[HealingChange]
```

---

## 3. ML/AI ENGINES (HANDLE WITH EXTREME CARE)

### 3.1 Selector Engine (`ml/selector_engine.py`)
**Purpose**: Rank and generate multiple selector strategies for each element.

```python
class MultiDimensionalSelectorEngine:
    def generate_selectors(self, fingerprint: ElementFingerprint) -> List[SelectorStrategy]
    def rank_selectors(self, selectors: List[SelectorStrategy], context: dict) -> List[SelectorStrategy]
    def record_selector_result(self, selector, fingerprint, success, execution_time_ms)
```

**Key Concepts**:
- **ElementFingerprint**: Captures element's tag, attributes, text, position, ancestors
- **SelectorStrategy**: type (css/xpath/aria/id/text), value, score, metadata
- **ML Training**: Records success/failure of each selector for ranking improvement

### 3.2 Healing Engine (`ml/healing_engine.py`)
**Purpose**: Self-heal broken selectors using historical data and heuristics.

```python
class SelectorHealingEngine:
    def heal_selector(self, original: str, page_html: str, context: dict) -> Optional[str]
    def record_healing_result(self, original, healed, success)
```

**Healing Strategies**:
1. Attribute relaxation (remove brittle parts)
2. Text-based fallback
3. Structural similarity
4. Historical success patterns

### 3.3 Vision Engine (`ml/vision_engine.py`)
**Purpose**: Find elements visually when selectors fail.

```python
class VisualElementMatcher:
    def find_element_by_screenshot(self, template: bytes, page_screenshot: bytes) -> Optional[Tuple[int, int]]
    def find_by_visual_similarity(self, reference_hash: str, current_screenshot: bytes) -> List[Match]
```

**Techniques**:
- Template matching (OpenCV)
- Perceptual hashing
- Color histogram comparison
- OCR for text detection

### 3.4 NLP Engine (`ml/nlp_engine.py`)
**Purpose**: Semantic understanding of elements and actions.

```python
class NLPEngine:
    def extract_semantic_intent(self, element_context: dict) -> str
    def match_intent_to_element(self, intent: str, candidates: List[dict]) -> Optional[dict]
```

---

## 4. ACTION TYPES & HANDLERS

### Supported Action Types (Step.type in schema)
```python
# Basic Interactions
"click", "dblclick", "contextmenu", "hover", "scroll", "dragTo", "dragByOffset"

# Input
"input", "type", "change", "press", "selectOption", "check", "uncheck", "submit"

# Frame Operations
"switchFrame", "switchFrameByName", "switchFrameByIndex", "switchMainFrame", "switchParentFrame"

# Window Operations
"switchWindow", "switchWindowByIndex", "switchNewWindow", "closeWindow"

# Dialog Operations
"handleAlert", "handleConfirm", "handlePrompt", "setDialogHandler"

# Variable Operations
"storeVariable", "storeText", "storeValue", "storeAttribute", "storeCount", "assertVariable"

# Wait Operations
"wait", "waitForElement", "waitForNavigation", "waitForUrl"

# Assertions
"assertText", "assertVisible", "assertNotVisible", "assertEnabled", "assertChecked"

# Other
"screenshot", "custom"
```

### Action Implementation Location
All actions are implemented in `tiered_executor.py`:
- `_perform_action()` - Main action dispatcher (line ~827)
- `_execute_no_locator_action()` - Actions without element locators (line ~354)

### Handler Classes (`frame_handler.py`)
```python
class FrameHandler:
    async def switch_to_frame(selector: str) -> bool
    async def switch_to_frame_by_name(name: str) -> bool
    async def switch_to_frame_by_index(index: int) -> bool
    def switch_to_parent_frame() -> bool
    def switch_to_main_frame() -> bool

class WindowHandler:
    async def switch_to_window(identifier: str) -> bool
    async def switch_to_new_window(timeout: int) -> bool
    async def close_current_window() -> bool

class DialogHandler:
    async def handle_alert(action: str) -> Optional[str]
    async def handle_confirm(accept: bool) -> Optional[str]
    async def handle_prompt(text: str, accept: bool) -> Optional[str]
    def set_auto_handle(enabled: bool, action: str, text: str)
```

---

## 5. VARIABLE STORE SYSTEM

### File: `variable_store.py`

### Scope Hierarchy (most specific to least)
```
step → test → suite → env
```

### Variable Syntax
```
${varName}           - Simple reference (searches all scopes)
${scope.varName}     - Scoped reference (e.g., ${env.BASE_URL})
${varName:default}   - With default value
```

### Key Methods
```python
class VariableStore:
    def set(name: str, value: Any, scope: str = "test")
    def get(name: str, default: Any = None, scope: Optional[str] = None) -> Any
    def resolve(text: str) -> str  # Resolves ${var} in strings
    def clear_step() / clear_test() / clear_suite()
```

### Element Extraction
```python
class ElementExtractor:
    @staticmethod async def extract_text(page, selector) -> Optional[str]
    @staticmethod async def extract_value(page, selector) -> Optional[str]
    @staticmethod async def extract_attribute(page, selector, attribute) -> Optional[str]
    @staticmethod async def extract_count(page, selector) -> int
```

---

## 6. WORKFLOW SCHEMA

### File: `schema/workflow.py`

```python
class Locator(BaseModel):
    type: Literal["data", "aria", "label", "css", "text", "xpath", "frame", "shadow", "id", "name"]
    value: str
    score: float = 0.5

class Target(BaseModel):
    locators: List[Locator]

class Step(BaseModel):
    id: str
    name: str
    type: Literal[...]  # See action types above
    target: Optional[Target]
    input: Optional[Dict[str, str]]
    domContext: Optional[Dict[str, Any]]  # ML metadata
    waits: List[WaitCondition]
    assertions: List[Assertion]

class Workflow(BaseModel):
    version: str = "1.0"
    steps: List[Step]
    metadata: Optional[Dict[str, Any]]
```

---

## 7. RECORDING FLOW

### Event Flow
```
Browser Extension → WebSocket → app_enhanced.py → Workflow.steps
```

### Event Filtering (`app_enhanced.py`)
```python
# Events that are SKIPPED (not recorded)
SKIP_EVENTS = {'keyup', 'keypress', 'mousedown', 'mouseup', 'mouseover', 'mouseout', 'mousemove', 'focus', 'blur'}

# Special key handling
if event_type == 'keydown':
    if key in SPECIAL_KEYS:  # Enter, Tab, Escape, etc.
        event_type = 'press'  # Convert to press action
    else:
        return  # Skip regular keydown
```

### Selector Generation During Recording
```python
if self.selector_engine and "element" in payload:
    fingerprint = create_fingerprint_from_dom(payload)
    selector_strategies = self.selector_engine.generate_selectors(fingerprint)
    locators = [Locator(type=s.type, value=s.value, score=s.score) for s in selector_strategies]
```

---

## 8. EXECUTION FLOW

### Replay Flow
```
Workflow.steps → TieredExecutor.execute_step() → Tier 0/1/2/3 → Verification → Result
```

### Step Execution
```python
async def execute_step(context: ExecutionContext) -> ExecutionResult:
    # 1. Check for no-locator actions
    if context.step_type in NO_LOCATOR_ACTIONS:
        return await _execute_no_locator_action(context)

    # 2. Wait for page stability
    await _page_stability.wait_for_stability()

    # 3. Try each tier in order
    for tier in ExecutionTier:
        result = await _execute_at_tier(tier, context)
        if result.success:
            return result

    return ExecutionResult(success=False, error="All tiers failed")
```

---

## 9. UI INTEGRATION

### QML Components
- **StepDetailPanel.qml**: Step list with add/edit/delete
- **Add Step Menu**: Categories for all action types

### Qt Models (Python → QML Bridge)
```python
class StepDetailModel(QAbstractListModel):
    # Exposes steps to QML ListView

class ExecutionHistoryModel(QAbstractListModel):
    # Exposes execution results
```

### Controller Slots (`app_enhanced.py`)
```python
@Slot(int, str)
def add_step(after_index: int, step_type: str)

@Slot(int, str)
def add_step_full(after_index: int, step_data_json: str)

@Slot(int)
def delete_step(step_index: int)
```

---

## 10. ENHANCEMENT GUIDELINES

### DO:
1. Add new action types to ALL required locations:
   - `schema/workflow.py` → Step.type Literal
   - `app_enhanced.py` → VALID_TYPES set
   - `tiered_executor.py` → `_perform_action()` or `_execute_no_locator_action()`
   - `ui/components/StepDetailPanel.qml` → Add Step menu

2. Follow the tiered execution pattern for element-based actions
3. Use existing handlers (FrameHandler, WindowHandler, DialogHandler, VariableStore)
4. Record ML training data using `_record_selector_attempt()`
5. Verify actions using ActionVerifier

### DO NOT:
1. Remove or modify the tiered execution flow
2. Change ML engine interfaces without updating all callers
3. Skip element stability checks
4. Add AI/ML calls to Tier 0 (must remain deterministic)
5. Break backward compatibility with existing workflows
6. Remove existing action types
7. Modify selector scoring algorithms without testing

### Testing New Actions
```python
# 1. Unit test the action handler
async def test_new_action():
    executor = TieredExecutor(page)
    context = ExecutionContext(
        step_index=0,
        step_type="newActionType",
        step_name="Test",
        locators=[LocatorCandidate(type="css", value="#test", confidence=1.0, source="test")],
        input_value="test value"
    )
    result = await executor.execute_step(context)
    assert result.success

# 2. Integration test with real browser
# 3. Test ML training data recording
# 4. Test with healing scenarios
```

---

## 11. KEY FILE QUICK REFERENCE

| File | Purpose | Modify With Care |
|------|---------|------------------|
| `tiered_executor.py` | Core execution engine | YES |
| `selector_engine.py` | ML selector ranking | EXTREME |
| `healing_engine.py` | Selector self-healing | EXTREME |
| `vision_engine.py` | CV element detection | EXTREME |
| `variable_store.py` | Cross-test variables | MODERATE |
| `frame_handler.py` | Frame/window/dialog | MODERATE |
| `workflow.py` | Data schema | MODERATE |
| `app_enhanced.py` | Main controller | MODERATE |
| `StepDetailPanel.qml` | UI component | LOW |

---

## 12. COMMON PATTERNS

### Adding a New Action Type
```python
# 1. schema/workflow.py - Add to Step.type Literal
"myNewAction",

# 2. app_enhanced.py - Add to VALID_TYPES
VALID_TYPES = {..., 'myNewAction'}

# 3. tiered_executor.py - Add handler
elif action_type == "myNewAction":
    value = context.input_value
    # Implementation here
    await locator.first.some_playwright_method()

# 4. StepDetailPanel.qml - Add to category
{type: "myNewAction", label: "My Action", color: "#4ecca3"}
```

### Using Variables in Actions
```python
# In executor, resolve variables before use
resolved_value = self._variable_store.resolve(context.input_value)
# ${userName} becomes "John" if userName="John" in store
```

### Handling Actions Without Locators
```python
# Add to NO_LOCATOR_ACTIONS set
NO_LOCATOR_ACTIONS = {..., "myNewAction"}

# Add handler in _execute_no_locator_action()
elif action_type == "myNewAction":
    # Implementation that doesn't need element locator
```

---

This document should be provided to Claude when requesting enhancements to ensure existing functionality is preserved.
