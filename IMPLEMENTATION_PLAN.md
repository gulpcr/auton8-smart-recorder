# Implementation Plan - Desktop Recorder Enhancement

## 🎯 Objective
Transform the existing desktop Playwright recorder into a **premium, production-grade test automation tool** with modern UX, advanced features, and zero breaking changes.

---

## 📋 Implementation Phases

### ✅ **Phase 0: Foundation** (Current Status)
- [x] Analyze existing codebase
- [x] Document architecture and integration points
- [x] Identify ML/AI black-box boundaries
- [x] Create implementation checklist

---

### 🚀 **Phase 1: Enhanced Schema & Models** (MVP Foundation)
**Goal**: Extend data model to support new features without breaking existing workflows.

#### 1.1 Schema Extensions
**File**: `recorder/schema/workflow.py`

**Changes** (additive only):
```python
class WorkflowMetadata(BaseModel):
    """New metadata model for enhanced workflow info."""
    name: Optional[str] = None                    # User-friendly name
    description: Optional[str] = None              # Test case description
    status: Literal["draft", "ready", "flaky", "broken"] = "draft"
    tags: List[str] = Field(default_factory=list)  # Search/filter tags
    createdAt: Optional[str] = None                # ISO timestamp
    updatedAt: Optional[str] = None                # ISO timestamp
    lastRunAt: Optional[str] = None                # Last replay time
    version: int = 1                               # Version tracking
    baseUrl: Optional[str] = None                  # Existing field (keep)
    author: Optional[str] = None                   # Creator
    
class StepEnhancements(BaseModel):
    """New optional fields for steps."""
    variables: Dict[str, str] = Field(default_factory=dict)  # Variable capture
    loop: Optional[LoopConfig] = None              # Loop wrapper
    condition: Optional[ConditionConfig] = None     # If/else wrapper
    timeout: int = 30000                           # Step timeout
    retries: int = 0                               # Retry count
    
class LoopConfig(BaseModel):
    kind: Literal["count", "dataset", "while"]
    count: Optional[int] = None
    dataset: Optional[str] = None  # CSV path
    condition: Optional[str] = None  # while condition
    
class ConditionConfig(BaseModel):
    kind: Literal["element_visible", "text_contains", "url_contains", "variable_equals"]
    target: Optional[str] = None
    value: Optional[str] = None
    else_steps: List[str] = Field(default_factory=list)  # Step IDs
```

**Backward Compatibility**:
- Add `metadata: Optional[WorkflowMetadata]` to `Workflow` (defaults to empty)
- Add `enhancements: Optional[StepEnhancements]` to `Step` (defaults to empty)
- Migration function: `migrate_old_workflow(data)` converts old `meta` dict

**Files to Create**:
- `recorder/schema/enhanced.py` (new models)
- `recorder/services/migration.py` (version migration)

**PR Size**: Small (~200 lines)

---

#### 1.2 Enhanced Models
**Files**: `recorder/models/`

**New Models**:
1. **`TestLibraryModel`** (QAbstractListModel)
   - Roles: name, status, tags, lastUpdated, stepCount, version
   - Methods: `filter(status, tags)`, `sort(key, order)`, `search(query)`

2. **`StepEditorModel`** (QAbstractListModel + drag-drop)
   - Enable `DragEnabled | DropEnabled` flags
   - Override `supportedDropActions()`, `moveRows()`
   - Add `update_step(index, field, value)`

3. **`ReplayResultsModel`** (QAbstractListModel)
   - Roles: stepId, status (pass/warn/fail), error, screenshot, duration
   - Real-time updates during replay

**Files to Create**:
- `recorder/models/test_library_model.py`
- `recorder/models/step_editor_model.py`
- `recorder/models/replay_results_model.py`

**PR Size**: Medium (~400 lines)

---

### 🎨 **Phase 2: Test Library UI** (MVP Critical)
**Goal**: Professional home screen with search, filter, and test management.

#### 2.1 Test Library QML Component
**File**: `ui/components/TestLibrary.qml` (new)

**Features**:
- Card/list view toggle
- Search bar with live filtering
- Status filter chips (Draft/Ready/Flaky/Broken)
- Tag filter dropdown
- Sort options (Name, Date, Status)
- Quick actions per test:
  - Edit (open in recorder)
  - Replay (run test)
  - Duplicate
  - Delete (with confirmation)
  - Export
  - Upload to portal

**Layout**:
```
┌─────────────────────────────────────────┐
│ 🔍 Search...    [Draft][Ready] 📅Sort   │
├─────────────────────────────────────────┤
│ ╔═══════════════════════════════════╗   │
│ ║ Test: Login Flow                  ║   │
│ ║ ● Ready  🏷️ auth, critical       ║   │
│ ║ 12 steps • Updated 2h ago         ║   │
│ ║ [▶️ Run] [✏️ Edit] [⋮ More]      ║   │
│ ╚═══════════════════════════════════╝   │
│ ...more cards...                        │
└─────────────────────────────────────────┘
```

**Empty State**:
- Hero message: "No tests yet"
- Large CTA button: "Record Your First Test"
- Quick tips

**Files to Create**:
- `ui/components/TestLibrary.qml`
- `ui/components/TestCard.qml`
- `ui/components/SearchBar.qml`
- `ui/components/FilterChips.qml`

**PR Size**: Large (~800 lines QML)

---

#### 2.2 New Test Wizard
**File**: `ui/components/NewTestWizard.qml` (new)

**3-Step Wizard**:

**Step 1: Test Name**
- Input field with validation
- Suggested naming patterns
- Check for duplicate names

**Step 2: Starting URL**
- URL input with validation
- Recent URLs dropdown
- URL templates (e.g., staging vs prod)

**Step 3: Confirmation**
- Summary of test details
- "Start Recording" CTA button

**Layout**:
```
┌─────────────────────────────────────┐
│  (1)──●──(2)────○──(3)              │
│   Name    URL      Start            │
├─────────────────────────────────────┤
│                                     │
│  📝 Test Case Name                  │
│  ┌───────────────────────────────┐ │
│  │ Login with Google OAuth       │ │
│  └───────────────────────────────┘ │
│                                     │
│  [Next →]                           │
└─────────────────────────────────────┘
```

**Backend Support**:
- Add `controller.create_new_test(name, url, tags)` → initializes workflow
- Validates uniqueness, creates metadata

**Files to Create**:
- `ui/components/NewTestWizard.qml`
- `ui/components/WizardStep.qml`
- Controller method: `RecordingController.create_new_test()`

**PR Size**: Medium (~400 lines)

---

### 🎬 **Phase 3: Recording UX Upgrade** (MVP Critical)
**Goal**: 3-panel layout with live inspector and enhanced step list.

#### 3.1 Three-Panel Layout
**File**: `ui/RecordingView.qml` (new, replaces current Record tab)

**Layout**:
```
┌──────────┬─────────────────┬──────────┐
│  Steps   │   Browser View  │ Inspector│
│  Panel   │   (External)    │  Panel   │
│          │                 │          │
│ 1. Click │   [Shown in     │ Element: │
│ 2. Type  │    separate     │ ───────  │
│ 3. Click │    browser]     │ ID: btn  │
│          │                 │ Class:.. │
│ [+ Add]  │                 │ Selector │
│          │                 │ [📋Copy] │
└──────────┴─────────────────┴──────────┘
    30%           40%             30%
```

**Left Panel: Steps**
- Live list of captured steps
- Animated entrance on capture
- Step status indicators
- Hover → highlight element in browser
- Click → show in inspector

**Center**: Browser (external window)
- Managed by existing `BrowserLauncher`
- Injection of `injected_advanced.js`

**Right Panel: Inspector**
- Selected element details
- 7 selector strategies with scores
- Copy button per selector
- "Set as primary" button
- Element properties (tag, text, attributes)
- Screenshot thumbnail

**Files to Create**:
- `ui/RecordingView.qml`
- `ui/components/StepsList.qml`
- `ui/components/InspectorPanel.qml`
- `ui/components/SelectorDisplay.qml`

**PR Size**: Large (~1000 lines QML)

---

#### 3.2 Recording State Management
**File**: `recorder/app_ml_integrated.py`

**New Features**:
- `@Slot(str, result=dict) def get_step_details(step_id)` → returns full step + selectors
- `@Slot(str, int) def set_primary_selector(step_id, locator_index)` → reorders locators
- `@Slot(str, result=str) def get_selector_preview(step_id)` → formatted selector text
- Signal: `selectedStepChanged(dict)` → emits step details for inspector

**Recording UI Enhancements**:
- Add "Recording" pill indicator with timer
- Pause/Resume buttons
- Real-time step count

**PR Size**: Small (~300 lines)

---

### ✏️ **Phase 4: Step Editor** (MVP Important)
**Goal**: Inline editing, drag-drop reorder, re-pick element.

#### 4.1 Editable Step List
**File**: `ui/components/EditableStepsList.qml` (new)

**Features**:
- Drag handle for reordering
- Inline dropdown for command type
- Inline edit for selector/value
- Collapsible "Advanced" section per step:
  - Wait strategies
  - Timeout
  - Retries
  - Assertions

**Layout per Step**:
```
┌──────────────────────────────────────┐
│ ⣿ [1] Click      ▼                  │
│    Target: #login-btn               │
│    [📍 Re-pick] [🔽 Advanced]       │
│    ┌─ Advanced Options (collapsed) ─┐
│    │ Wait: visible ⏱️ 5000ms       │
│    │ Retry: 2 times                 │
│    └────────────────────────────────┘
└──────────────────────────────────────┘
```

**Backend Support**:
- `@Slot(int, int) def move_step(from_index, to_index)` → reorders workflow.steps
- `@Slot(str, str, str) def update_step_field(step_id, field, value)` → inline edit
- `@Slot(str) def start_repick_element(step_id)` → initiates element picker mode

**PR Size**: Large (~600 lines QML + 200 lines Python)

---

#### 4.2 Re-Pick Element Feature
**Flow**:
1. User clicks "Re-pick" on a step
2. Browser enters "picker mode" (visual overlay)
3. User clicks target element
4. ML selector engine regenerates selectors
5. Step updated with new locators
6. Inspector refreshes

**Implementation**:
- Inject picker mode JS into browser: `instrumentation/picker.js`
- New signal: `elementRepicked(step_id, new_selectors)`
- Uses existing `selector_engine.generate_selectors()` (no ML code modification)

**Files to Create**:
- `instrumentation/picker.js`
- Controller method: `start_repick_element()`, `handle_repicked_element()`

**PR Size**: Medium (~400 lines)

---

### 🔁 **Phase 5: Replay Runner UI** (MVP Important)
**Goal**: Visual replay progress with timeline, screenshots, and trace viewer.

#### 5.1 Enhanced Replay View
**File**: `ui/ReplayView.qml` (replaces current Replay tab)

**Layout**:
```
┌────────────────────────────────────────┐
│ Timeline: ●━━━━━━○━━━━━━○━━━━━━━━━━━  │
│           Step 1  Step 2  Step 3...    │
├────────────────────────────────────────┤
│ ╔══════════════════════════════════╗   │
│ ║ Step 2: Type "test@example.com"  ║   │
│ ║ ✅ Passed • 1.2s                 ║   │
│ ║ [🖼️ Screenshot] [📊 Trace]      ║   │
│ ╚══════════════════════════════════╝   │
│ ... more steps...                      │
└────────────────────────────────────────┘
```

**Features**:
- Interactive timeline (click step → jump to details)
- Real-time status updates (pass ✅ / warn ⚠️ / fail ❌)
- Screenshot thumbnails per step
- "Open Playwright Trace" button
- Logs panel (collapsible)
- "Run from Step X" option

**Backend Support**:
- Modify `replay/replayer.py` to capture:
  - Screenshots after each step
  - Playwright traces (enable in launch)
  - Step execution time
  - Errors with stack traces
- New model: `ReplayResultsModel` (from Phase 1.2)
- Signal: `stepExecuted(step_id, status, duration, screenshot_path)`

**Files to Modify**:
- `replay/replayer.py` (add screenshot/trace capture)
- `recorder/services/replay_launcher.py` (emit detailed signals)

**Files to Create**:
- `ui/ReplayView.qml`
- `ui/components/ReplayTimeline.qml`
- `ui/components/StepResult.qml`

**PR Size**: Large (~800 lines QML + 300 lines Python)

---

#### 5.2 Playwright Trace Integration
**Goal**: Generate and open `.trace.zip` files.

**Implementation**:
- In `replay/replayer.py`, add tracing:
```python
context = await browser.new_context()
await context.tracing.start(screenshots=True, snapshots=True)
# ... run steps ...
await context.tracing.stop(path="data/traces/workflow_{timestamp}.zip")
```
- Add button: "Open Trace in Viewer"
- Launches: `playwright show-trace <path>`

**PR Size**: Small (~150 lines)

---

### 📦 **Phase 6: Package & Portal Upload** (MVP Nice-to-Have)
**Goal**: Export test packages and upload to remote test management portal.

#### 6.1 Package Builder
**File**: `recorder/services/packager.py` (new)

**Package Structure** (ZIP):
```
test-package-{id}.zip
├── test.json             # Workflow JSON
├── meta.json             # Metadata (name, status, tags, etc.)
├── assets/
│   ├── screenshots/
│   │   ├── step-1.png
│   │   └── step-2.png
│   └── trace.zip         # Playwright trace
└── README.md             # Human-readable test description
```

**Functions**:
- `create_package(workflow_id)` → ZIP path
- `extract_package(zip_path)` → imports workflow

**PR Size**: Small (~250 lines)

---

#### 6.2 Portal Upload Client
**File**: `recorder/services/portal_client.py` (new)

**Features**:
- HTTP client for portal API
- Auth token management (stored securely)
- Chunked upload for large files
- Offline queue (stores failed uploads)
- Progress tracking

**API Endpoints** (example):
```python
POST /api/v1/auth/login        # Get auth token
POST /api/v1/tests             # Create new test
PUT  /api/v1/tests/{id}        # Update test
POST /api/v1/tests/{id}/upload # Upload package
GET  /api/v1/tests/{id}        # Get test details
```

**UI**:
- "Publish to Portal" button in Test Library
- Modal dialog:
  - Portal URL input
  - Auth token input (masked)
  - Progress bar
  - Success: "View in Portal" link

**Files to Create**:
- `recorder/services/portal_client.py`
- `ui/components/PublishDialog.qml`

**PR Size**: Medium (~500 lines)

---

### 🔧 **Phase 7: Advanced Features** (Post-MVP)
**Goal**: Loops, conditions, variables, and assertions.

#### 7.1 Loop Blocks
**UI**:
- "Add Loop" button in step editor
- Modal: Select loop type (count, dataset, while)
- Steps nested under loop visually (indentation)

**Schema**: Already defined in Phase 1.1 (`LoopConfig`)

**Replay**:
- Modify `replay/replayer.py` to handle loop execution:
```python
async def run_loop_step(page, step):
    loop_config = step.enhancements.loop
    if loop_config.kind == "count":
        for i in range(loop_config.count):
            for nested_step_id in step.nested_steps:
                await run_step(page, nested_step_id)
    # ...similar for dataset, while
```

**PR Size**: Medium (~400 lines)

---

#### 7.2 Conditional Blocks (If/Else)
**UI**:
- "Add Condition" button
- Modal: Select condition type
- Visual branching in step list

**Replay**:
```python
async def run_condition_step(page, step):
    cond = step.enhancements.condition
    if await evaluate_condition(page, cond):
        # Run "then" steps
    else:
        # Run "else" steps
```

**PR Size**: Medium (~400 lines)

---

#### 7.3 Variables & Data Binding
**Features**:
- Capture element text → store as variable
- Use `{{variable_name}}` in input values
- Variables panel in Inspector

**UI**:
- "Capture Value" button on element
- Variables list with inline edit
- "Insert Variable" dropdown in input fields

**Replay**:
- Variable substitution during replay
- Context tracking: `replay_context = {"vars": {}}`

**PR Size**: Medium (~500 lines)

---

#### 7.4 Assertions Builder
**UI**:
- "Add Assertion" button per step
- Templates:
  - Text contains
  - Element visible/hidden
  - Attribute equals
  - URL contains
  - Count

**Schema**: Already defined (`Assertion` model)

**Replay**: Already implemented in `replay/replayer.py` (lines 113-121)

**Enhancement**: Visual assertion builder instead of manual JSON editing

**PR Size**: Small (~300 lines QML)

---

## 📊 Implementation Roadmap

### Sprint 1: Foundation (Week 1)
- [x] Phase 0: Analysis & Planning
- [ ] Phase 1.1: Schema Extensions
- [ ] Phase 1.2: Enhanced Models
- [ ] Testing: Load old workflows successfully

### Sprint 2: MVP Core (Week 2-3)
- [ ] Phase 2.1: Test Library UI
- [ ] Phase 2.2: New Test Wizard
- [ ] Phase 3.1: Three-Panel Recording Layout
- [ ] Testing: Record → Save → Load in library

### Sprint 3: Editor & Replay (Week 4-5)
- [ ] Phase 3.2: Recording State Management
- [ ] Phase 4.1: Editable Step List
- [ ] Phase 4.2: Re-Pick Element
- [ ] Phase 5.1: Enhanced Replay View
- [ ] Testing: Edit workflow → Replay → View results

### Sprint 4: Polish & Advanced (Week 6-7)
- [ ] Phase 5.2: Playwright Trace Integration
- [ ] Phase 6.1: Package Builder
- [ ] Phase 6.2: Portal Upload
- [ ] Testing: Full end-to-end workflow

### Sprint 5: Advanced Features (Week 8+)
- [ ] Phase 7.1: Loop Blocks
- [ ] Phase 7.2: Conditional Blocks
- [ ] Phase 7.3: Variables & Data Binding
- [ ] Phase 7.4: Assertions Builder
- [ ] Testing: Complex workflows with advanced features

---

## 🔒 Safety Checklist (Every PR)

- [ ] No modifications to `recorder/ml/*.py` internals (only call public methods)
- [ ] Old workflows load without errors
- [ ] New schema fields are Optional or have defaults
- [ ] No renamed fields (use aliases if needed)
- [ ] Unit tests for new functions
- [ ] QML components are self-contained
- [ ] No blocking operations on main thread
- [ ] Error handling with logger.error()
- [ ] Feature flag for breaking changes
- [ ] Documentation updated

---

## 🎨 Design Principles

1. **Additive Changes**: Extend, don't replace
2. **Graceful Degradation**: New features optional
3. **Consistent Styling**: Follow existing color scheme
4. **Responsive UI**: Smooth animations, no lag
5. **Clear Feedback**: Status messages, progress indicators
6. **Power User Friendly**: Keyboard shortcuts, drag-drop
7. **Minimal Modals**: Inline editing preferred
8. **Empty States**: Helpful CTAs when no data

---

## 🚀 Next: Start Phase 1.1
Begin with schema extensions to enable all future features while maintaining 100% backward compatibility.
