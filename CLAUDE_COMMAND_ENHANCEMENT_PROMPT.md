# Auton8 Recorder - Command Configuration Enhancement

## ⚠️ CRITICAL RULES - READ BEFORE ANY IMPLEMENTATION

### Compatibility Requirements (NON-NEGOTIABLE)

1. **ALL new fields MUST be `Optional[T] = None`** with safe defaults
2. **Old workflows MUST execute unchanged** - no migration required for basic operation
3. **Existing action types remain** - `assertText`, `assertVisible`, etc. are NOT replaced
4. **New selector config MAPS to existing `Locator` model** - do NOT create parallel system
5. **Per-step config is HINTS** - executor still controls tier progression (0→1→2→3)
6. **Implicit executor behaviors REMAIN** unless explicitly overridden by step config
7. **Tier-0 must stay deterministic** - no AI/ML in Tier-0, ever

### Architecture Preservation

```
EXISTING FLOW (PRESERVE):
Browser Extension → WebSocket → app_enhanced.py → Workflow.steps → TieredExecutor

TIERED EXECUTION (DO NOT CHANGE):
Tier 0 (80%) → Tier 1 (15%) → Tier 2 (4%) → Tier 3 (1%)
Deterministic    Heuristic      Vision       LLM
```

### File Modification Rules

| File | What You Can Do | What You Cannot Do |
|------|-----------------|-------------------|
| `schema/workflow.py` | Add Optional fields to Step | Remove/rename existing fields |
| `tiered_executor.py` | Read new config, apply as overrides | Change tier progression logic |
| `variable_store.py` | Use existing API | Change scope hierarchy |
| `frame_handler.py` | Use existing handlers | Change handler interfaces |
| `StepDetailPanel.qml` | Add config UI sections | Remove existing UI elements |
| `ml/*.py` | DO NOT TOUCH | DO NOT TOUCH |

---

## 1️⃣ SCHEMA EXTENSION

### Extend Step Model (schema/workflow.py)

Add a new `StepConfig` model and optional `config` field to `Step`:

```python
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class SelectorConfig(BaseModel):
    """Extended selector configuration - maps to existing Locator system"""
    strategy: Literal["css", "xpath", "id", "name", "text", "aria", "data", "role", "label", "placeholder"] = "css"
    value: str = ""
    # These map to existing Locator model internally


class ExecutionConfig(BaseModel):
    """Step execution control settings"""
    timeoutMs: int = 30000
    retryCount: int = 0
    retryDelayMs: int = 1000
    continueOnFail: bool = False  # Soft fail - log but continue


class ConditionConfig(BaseModel):
    """Conditional execution settings"""
    runIf: Optional[str] = None  # Expression: ${var} == "value"
    skipIf: Optional[str] = None  # Expression: ${var} != ""
    onTargetNotFound: Literal["fail", "skip", "warn"] = "fail"


class StabilityConfig(BaseModel):
    """Pre-action stability checks - OVERRIDE defaults, not replace"""
    ensureVisible: Optional[bool] = None  # None = use executor default
    ensureEnabled: Optional[bool] = None
    ensureStable: Optional[bool] = None
    autoScrollIntoView: Optional[bool] = None
    stabilityTimeoutMs: Optional[int] = None


class HealingHints(BaseModel):
    """Hints for healing system - executor still controls tier progression"""
    disableHealing: bool = False  # Skip tiers 1-3, fail at tier 0
    preferVisualHealing: bool = False  # Hint to try tier 2 before tier 1
    # Note: These are HINTS, not commands. Executor decides final behavior.


class EvidenceConfig(BaseModel):
    """Debug and evidence collection"""
    screenshotOnFail: bool = False
    screenshotOnSuccess: bool = False
    highlightElement: bool = False
    logSelectorResolution: bool = False


class PostStepConfig(BaseModel):
    """Post-step wait and validation"""
    waitAfter: Literal["none", "networkIdle", "domContentLoaded", "load", "custom"] = "none"
    waitAfterMs: int = 0  # For custom wait
    waitForSelector: Optional[str] = None  # Wait for element after action


class ClickConfig(BaseModel):
    """Click-specific configuration"""
    clickCount: int = 1  # 1=single, 2=double
    button: Literal["left", "right", "middle"] = "left"
    modifiers: List[Literal["Alt", "Control", "Meta", "Shift"]] = Field(default_factory=list)
    position: Optional[Dict[str, int]] = None  # {"x": 10, "y": 10} relative to element
    force: bool = False  # Playwright force click
    noWaitAfter: bool = False


class InputConfig(BaseModel):
    """Input/type configuration"""
    clearFirst: bool = True
    typeMode: Literal["fill", "type"] = "fill"  # fill=instant, type=keystroke
    typeDelayMs: int = 0  # Delay between keystrokes (type mode only)
    pressEnterAfter: bool = False
    maskInLogs: bool = False  # Hide value in logs (passwords)


class SelectConfig(BaseModel):
    """Select dropdown configuration"""
    selectBy: Literal["value", "label", "index"] = "value"
    multiple: bool = False  # Multi-select


class WaitConfig(BaseModel):
    """Wait command configuration"""
    waitType: Literal["time", "selector", "function", "navigation", "networkIdle"] = "time"
    waitMs: int = 1000
    waitSelector: Optional[str] = None
    waitState: Literal["attached", "detached", "visible", "hidden"] = "visible"


class AssertConfig(BaseModel):
    """Unified assert configuration - supplements existing assert types"""
    assertType: Literal["text", "visible", "hidden", "enabled", "disabled", "value", "attribute", "url", "count", "checked"] = "text"
    # Text assertions
    matchMode: Literal["equals", "contains", "startsWith", "endsWith", "regex"] = "contains"
    expectedValue: str = ""
    caseSensitive: bool = False
    normalizeWhitespace: bool = True
    # Attribute assertions
    attributeName: Optional[str] = None
    # Count assertions
    expectedCount: Optional[int] = None
    countComparison: Literal["equals", "greaterThan", "lessThan", "atLeast", "atMost"] = "equals"
    # Behavior
    softAssert: bool = False  # Log failure but continue
    waitForCondition: bool = True  # Auto-wait for condition
    assertTimeoutMs: int = 5000


class DialogConfig(BaseModel):
    """Dialog handling configuration"""
    expectedType: Literal["alert", "confirm", "prompt", "beforeunload", "any"] = "any"
    action: Literal["accept", "dismiss"] = "accept"
    promptText: Optional[str] = None  # Text to enter for prompt
    validateMessage: Optional[str] = None  # Assert dialog message contains


class FrameConfig(BaseModel):
    """Frame switching configuration"""
    frameBy: Literal["selector", "name", "index", "url"] = "selector"
    frameValue: str = ""  # Selector, name, index as string, or URL pattern
    waitForLoad: bool = True


class WindowConfig(BaseModel):
    """Window switching configuration"""
    windowBy: Literal["index", "title", "url", "newest"] = "newest"
    windowValue: str = ""  # Index as string, title pattern, or URL pattern
    bringToFront: bool = True


class VariableConfig(BaseModel):
    """Variable store/extract configuration"""
    variableName: str = ""
    scope: Literal["step", "test", "suite", "env"] = "test"
    # For extraction
    extractFrom: Literal["text", "value", "attribute", "count", "url", "title"] = "text"
    attributeName: Optional[str] = None
    regexPattern: Optional[str] = None  # Extract with regex group
    regexGroup: int = 0
    # For assertion
    comparison: Literal["equals", "notEquals", "contains", "greaterThan", "lessThan", "matches"] = "equals"
    expectedValue: Optional[str] = None


class StepConfig(BaseModel):
    """
    Complete step configuration - ALL FIELDS OPTIONAL

    This extends Step without breaking existing workflows.
    When fields are None, executor uses its default behavior.
    """
    # Execution control
    execution: Optional[ExecutionConfig] = None
    conditions: Optional[ConditionConfig] = None
    stability: Optional[StabilityConfig] = None
    healingHints: Optional[HealingHints] = None
    evidence: Optional[EvidenceConfig] = None
    postStep: Optional[PostStepConfig] = None

    # Command-specific (only one applies based on step.type)
    click: Optional[ClickConfig] = None
    input: Optional[InputConfig] = None
    select: Optional[SelectConfig] = None
    wait: Optional[WaitConfig] = None
    assertConfig: Optional[AssertConfig] = None  # Named to avoid Python keyword
    dialog: Optional[DialogConfig] = None
    frame: Optional[FrameConfig] = None
    window: Optional[WindowConfig] = None
    variable: Optional[VariableConfig] = None


# EXTEND existing Step model - ADD this field, don't modify others
class Step(BaseModel):
    # ... existing fields remain unchanged ...

    # NEW: Optional configuration (None = use defaults)
    config: Optional[StepConfig] = None
```

---

## 2️⃣ EXECUTOR INTEGRATION

### Modify tiered_executor.py

The executor should READ config as OVERRIDES, not replacements:

```python
async def _perform_action(self, locator: Locator, context: ExecutionContext):
    """Perform action with config overrides"""
    action_type = context.step_type
    config = context.step_config  # New: StepConfig or None

    # Get command-specific config (or empty default)
    click_cfg = (config.click if config and config.click else ClickConfig()) if action_type in ["click", "dblclick"] else None

    if action_type == "click":
        # Apply config overrides
        click_count = click_cfg.clickCount if click_cfg else 1
        button = click_cfg.button if click_cfg else "left"
        modifiers = click_cfg.modifiers if click_cfg else []
        force = click_cfg.force if click_cfg else False
        position = click_cfg.position if click_cfg else None

        await locator.first.click(
            click_count=click_count,
            button=button,
            modifiers=modifiers,
            force=force,
            position=position
        )

    # ... similar pattern for other actions
```

### Apply Stability Overrides

```python
async def _check_stability(self, locator: Locator, context: ExecutionContext) -> bool:
    """Check stability with config overrides"""
    config = context.step_config
    stability = config.stability if config else None

    # Use config value if set, otherwise use executor default
    ensure_visible = stability.ensureVisible if (stability and stability.ensureVisible is not None) else True
    ensure_stable = stability.ensureStable if (stability and stability.ensureStable is not None) else True

    if ensure_visible:
        await locator.first.wait_for(state="visible")

    if ensure_stable:
        is_stable, _ = await self._element_stability.is_element_stable(locator)
        if not is_stable:
            return False

    return True
```

### Apply Condition Evaluation

```python
def _evaluate_condition(self, expression: str) -> bool:
    """
    Evaluate simple condition expression.

    Supported syntax:
    - ${var}           -> truthy check
    - !${var}          -> falsy check
    - ${var} == "val"  -> equals
    - ${var} != "val"  -> not equals
    - ${var} > 5       -> numeric comparison (>, <, >=, <=)
    """
    if not expression:
        return True

    # Resolve variables first
    resolved = self._variable_store.resolve(expression)

    # Simple truthy check
    if resolved and '==' not in resolved and '!=' not in resolved and '>' not in resolved and '<' not in resolved:
        return bool(resolved.strip())

    # Parse comparison
    import re
    match = re.match(r'(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)', resolved)
    if match:
        left, op, right = match.groups()
        left = left.strip().strip('"\'')
        right = right.strip().strip('"\'')

        # Try numeric comparison
        try:
            left_num = float(left)
            right_num = float(right)
            if op == '==': return left_num == right_num
            if op == '!=': return left_num != right_num
            if op == '>': return left_num > right_num
            if op == '<': return left_num < right_num
            if op == '>=': return left_num >= right_num
            if op == '<=': return left_num <= right_num
        except ValueError:
            pass

        # String comparison
        if op == '==': return left == right
        if op == '!=': return left != right

    return True  # Default to true if can't parse


async def execute_step(self, context: ExecutionContext) -> ExecutionResult:
    """Execute with condition checks"""
    config = context.step_config

    # Check runIf condition
    if config and config.conditions and config.conditions.runIf:
        if not self._evaluate_condition(config.conditions.runIf):
            return ExecutionResult(
                success=True,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=0,
                skipped=True,
                skip_reason="runIf condition not met"
            )

    # Check skipIf condition
    if config and config.conditions and config.conditions.skipIf:
        if self._evaluate_condition(config.conditions.skipIf):
            return ExecutionResult(
                success=True,
                tier_used=ExecutionTier.TIER_0_DETERMINISTIC,
                locator_used=None,
                verification=None,
                duration_ms=0,
                skipped=True,
                skip_reason="skipIf condition met"
            )

    # Continue with normal execution...
```

---

## 3️⃣ UI IMPLEMENTATION (StepDetailPanel.qml)

### Structure: Collapsible Sections

```qml
// Step Configuration Panel - shown when step is expanded
ColumnLayout {
    id: stepConfigPanel
    visible: stepRow.isExpanded
    spacing: 8

    // Section: Basic (always visible)
    ConfigSection {
        title: "Basic"
        expanded: true

        ColumnLayout {
            // Timeout
            ConfigRow {
                label: "Timeout (ms)"
                SpinBox {
                    from: 1000; to: 120000; stepSize: 1000
                    value: stepConfig?.execution?.timeoutMs ?? 30000
                    onValueChanged: updateConfig("execution.timeoutMs", value)
                }
            }

            // Continue on fail
            ConfigRow {
                label: "Continue on fail"
                Switch {
                    checked: stepConfig?.execution?.continueOnFail ?? false
                    onCheckedChanged: updateConfig("execution.continueOnFail", checked)
                }
            }
        }
    }

    // Section: Conditions (collapsed by default)
    ConfigSection {
        title: "Conditions"
        expanded: false

        ColumnLayout {
            ConfigRow {
                label: "Run if"
                TextField {
                    placeholderText: '${loggedIn} == "true"'
                    text: stepConfig?.conditions?.runIf ?? ""
                    onTextChanged: updateConfig("conditions.runIf", text)
                }
            }

            ConfigRow {
                label: "Skip if"
                TextField {
                    placeholderText: '${skipTest}'
                    text: stepConfig?.conditions?.skipIf ?? ""
                    onTextChanged: updateConfig("conditions.skipIf", text)
                }
            }

            ConfigRow {
                label: "If target not found"
                ComboBox {
                    model: ["fail", "skip", "warn"]
                    currentIndex: model.indexOf(stepConfig?.conditions?.onTargetNotFound ?? "fail")
                    onCurrentTextChanged: updateConfig("conditions.onTargetNotFound", currentText)
                }
            }
        }
    }

    // Section: Command-Specific (based on step.type)
    ConfigSection {
        title: getCommandTitle(step.type)
        expanded: true
        visible: hasCommandConfig(step.type)

        Loader {
            source: getCommandConfigComponent(step.type)
            // Loads: ClickConfig.qml, InputConfig.qml, etc.
        }
    }

    // Section: Stability (collapsed)
    ConfigSection {
        title: "Stability Checks"
        expanded: false
        visible: requiresElement(step.type)

        ColumnLayout {
            ConfigRow {
                label: "Ensure visible"
                TriStateCheckbox {  // null = use default
                    state: stepConfig?.stability?.ensureVisible
                    onStateChanged: updateConfig("stability.ensureVisible", state)
                }
            }
            // ... more stability options
        }
    }

    // Section: Evidence (collapsed)
    ConfigSection {
        title: "Evidence & Debug"
        expanded: false

        ColumnLayout {
            ConfigRow {
                label: "Screenshot on fail"
                Switch {
                    checked: stepConfig?.evidence?.screenshotOnFail ?? false
                }
            }
            ConfigRow {
                label: "Highlight element"
                Switch {
                    checked: stepConfig?.evidence?.highlightElement ?? false
                }
            }
        }
    }

    // Section: Post-Step (collapsed)
    ConfigSection {
        title: "After Step"
        expanded: false

        ColumnLayout {
            ConfigRow {
                label: "Wait after"
                ComboBox {
                    model: ["none", "networkIdle", "domContentLoaded", "load", "custom"]
                }
            }
        }
    }
}
```

### Command-Specific Config Components

Create separate QML files for each command type:

**ClickConfig.qml:**
```qml
ColumnLayout {
    ConfigRow {
        label: "Click type"
        ComboBox {
            model: ["Single", "Double", "Right-click"]
            currentIndex: {
                var cfg = stepConfig?.click
                if (!cfg) return 0
                if (cfg.button === "right") return 2
                if (cfg.clickCount === 2) return 1
                return 0
            }
        }
    }

    ConfigRow {
        label: "Force click"
        Switch {
            checked: stepConfig?.click?.force ?? false
        }
        helpText: "Click even if element is covered"
    }

    ConfigRow {
        label: "Modifier keys"
        Flow {
            CheckBox { text: "Shift"; property string key: "Shift" }
            CheckBox { text: "Ctrl"; property string key: "Control" }
            CheckBox { text: "Alt"; property string key: "Alt" }
        }
    }
}
```

**InputConfig.qml:**
```qml
ColumnLayout {
    ConfigRow {
        label: "Clear first"
        Switch { checked: stepConfig?.input?.clearFirst ?? true }
    }

    ConfigRow {
        label: "Type mode"
        ComboBox {
            model: ["fill (instant)", "type (keystrokes)"]
        }
    }

    ConfigRow {
        label: "Press Enter after"
        Switch { checked: stepConfig?.input?.pressEnterAfter ?? false }
    }

    ConfigRow {
        label: "Mask in logs"
        Switch {
            checked: stepConfig?.input?.maskInLogs ?? false
        }
        helpText: "Hide value in logs (for passwords)"
    }
}
```

---

## 4️⃣ RECORDING INTEGRATION

### Update app_enhanced.py

When recording, create default config based on event:

```python
def _create_step_from_event(self, payload: dict) -> Step:
    """Create step with default config from recorded event"""
    event_type = payload.get("eventType", "click")

    # Create basic step (existing logic)
    step = Step(
        id=str(uuid.uuid4()),
        name=event_type,
        type=event_type,
        target=target,
        input=input_data,
        domContext=dom_context
    )

    # Add config with sensible defaults based on event type
    if event_type in ["click", "dblclick"]:
        step.config = StepConfig(
            click=ClickConfig(
                clickCount=2 if event_type == "dblclick" else 1
            )
        )
    elif event_type in ["input", "type", "change"]:
        step.config = StepConfig(
            input=InputConfig(
                clearFirst=True,
                typeMode="fill"
            )
        )

    return step
```

---

## 5️⃣ BACKWARD COMPATIBILITY

### Workflow Loading (workflow_store.py)

```python
def load_workflow(filename: str) -> Optional[Workflow]:
    """Load workflow with backward compatibility"""
    path = WORKFLOWS_DIR / filename
    if not path.exists():
        return None

    with open(path, "r") as f:
        data = json.load(f)

    # Handle old workflows without config field
    for step_data in data.get("steps", []):
        if "config" not in step_data:
            step_data["config"] = None  # Will use executor defaults

    return Workflow.model_validate(data)
```

---

## 6️⃣ WHAT NOT TO CHANGE

### DO NOT MODIFY:

1. **ml/selector_engine.py** - Selector ranking algorithm
2. **ml/healing_engine.py** - Healing strategies
3. **ml/vision_engine.py** - CV matching
4. **ml/ollama_engine.py** - LLM integration
5. **Tier progression logic** in tiered_executor.py
6. **Existing Locator model** - only add new fields if needed
7. **Variable store scope hierarchy** (step→test→suite→env)
8. **WebSocket protocol** with browser extension

### DO NOT REMOVE:

1. Any existing action types
2. Any existing Step fields
3. Pattern heuristics in executor
4. Stability detection code
5. Action verification code

---

## 7️⃣ TESTING REQUIREMENTS

Before considering implementation complete:

```python
# Test 1: Old workflow still works
def test_old_workflow_compatibility():
    old_workflow = {"version": "1.0", "steps": [
        {"id": "1", "name": "click", "type": "click", "target": {"locators": [{"type": "css", "value": "#btn", "score": 0.9}]}}
    ]}
    workflow = Workflow.model_validate(old_workflow)
    assert workflow.steps[0].config is None  # No config, uses defaults

# Test 2: New config doesn't break execution
def test_config_with_defaults():
    step = Step(id="1", name="click", type="click", config=StepConfig())
    # Should use all default values, not fail

# Test 3: Tier 0 still works without ML
def test_tier_0_deterministic():
    executor = TieredExecutor(page, healing_engine=None)
    executor.set_max_tier(ExecutionTier.TIER_0_DETERMINISTIC)
    # Should still execute successfully

# Test 4: Conditions evaluate correctly
def test_condition_evaluation():
    executor._variable_store.set("loggedIn", "true", "test")
    assert executor._evaluate_condition('${loggedIn} == "true"') == True
    assert executor._evaluate_condition('${loggedIn} != "true"') == False
```

---

## 8️⃣ IMPLEMENTATION ORDER

1. **Phase 1: Schema** - Add StepConfig to schema/workflow.py
2. **Phase 2: Executor** - Read config as overrides in tiered_executor.py
3. **Phase 3: UI Components** - Create ConfigSection, ConfigRow QML components
4. **Phase 4: Command Configs** - Add ClickConfig.qml, InputConfig.qml, etc.
5. **Phase 5: Integration** - Wire UI to model, test backward compatibility
6. **Phase 6: Recording** - Add default configs during recording

---

## ✅ SUCCESS CRITERIA

- [ ] All existing workflows execute unchanged
- [ ] Tier-0 success rate remains ≥80%
- [ ] UI shows config sections (collapsed by default)
- [ ] Config changes persist to workflow JSON
- [ ] Conditions (runIf/skipIf) work with variables
- [ ] ML engines untouched
- [ ] No new required fields in Step schema

---

## 9️⃣ QUICK REFERENCE: EXISTING CODE LOCATIONS

### Key Files to Understand Before Modifying

```
schema/workflow.py          # Lines 58-97: Step model definition
tiered_executor.py          # Lines 827-1050: _perform_action method
tiered_executor.py          # Lines 263-332: execute_step method
tiered_executor.py          # Lines 354-500: _execute_no_locator_action
variable_store.py           # Lines 132-166: resolve() method for ${var} syntax
frame_handler.py            # Lines 45-249: FrameHandler class
frame_handler.py            # Lines 251-444: WindowHandler class
frame_handler.py            # Lines 447-593: DialogHandler class
app_enhanced.py             # Lines 1050-1250: Event recording logic
StepDetailPanel.qml         # Lines 520-870: Add Step dialog
```

### Existing Data Classes (DO NOT DUPLICATE)

```python
# Already exists in tiered_executor.py
@dataclass
class ExecutionContext:
    step_index: int
    step_type: str
    step_name: str
    locators: List[LocatorCandidate]
    input_value: Optional[str] = None
    dom_context: Optional[Dict] = None
    expected_navigation: bool = False
    # ADD HERE: step_config: Optional[StepConfig] = None

@dataclass
class ExecutionResult:
    success: bool
    tier_used: ExecutionTier
    locator_used: Optional[LocatorCandidate]
    verification: Optional[ActionOutcome]
    duration_ms: int
    error: Optional[str] = None
    healing_change: Optional[HealingChange] = None
    # ADD HERE: skipped: bool = False
    # ADD HERE: skip_reason: Optional[str] = None
```

### Existing Action Handler Pattern

```python
# This is the EXISTING pattern in _perform_action - EXTEND, don't replace
async def _perform_action(self, locator: Locator, context: ExecutionContext):
    action_type = context.step_type

    if action_type in ["click", "dblclick"]:
        if action_type == "dblclick":
            await locator.first.dblclick()
        else:
            await locator.first.click()

    # EXTEND like this:
    if action_type in ["click", "dblclick"]:
        cfg = self._get_click_config(context)  # New helper
        await locator.first.click(
            click_count=cfg.clickCount,
            button=cfg.button,
            modifiers=cfg.modifiers,
            force=cfg.force,
            position=cfg.position
        )
```

---

## 🔟 HELPER METHODS TO ADD

### Config Extraction Helpers (tiered_executor.py)

```python
def _get_click_config(self, context: ExecutionContext) -> ClickConfig:
    """Get click config with defaults"""
    if context.step_config and context.step_config.click:
        return context.step_config.click
    return ClickConfig()  # Returns defaults

def _get_input_config(self, context: ExecutionContext) -> InputConfig:
    """Get input config with defaults"""
    if context.step_config and context.step_config.input:
        return context.step_config.input
    return InputConfig()

def _get_execution_config(self, context: ExecutionContext) -> ExecutionConfig:
    """Get execution config with defaults"""
    if context.step_config and context.step_config.execution:
        return context.step_config.execution
    return ExecutionConfig()

def _should_skip_step(self, context: ExecutionContext) -> Tuple[bool, Optional[str]]:
    """Check if step should be skipped based on conditions"""
    if not context.step_config or not context.step_config.conditions:
        return False, None

    cond = context.step_config.conditions

    if cond.runIf and not self._evaluate_condition(cond.runIf):
        return True, f"runIf condition not met: {cond.runIf}"

    if cond.skipIf and self._evaluate_condition(cond.skipIf):
        return True, f"skipIf condition met: {cond.skipIf}"

    return False, None
```

---

## 📋 FINAL CHECKLIST BEFORE IMPLEMENTATION

Before writing any code, confirm:

- [ ] Read and understand tiered_executor.py execute_step() flow
- [ ] Read and understand _perform_action() method
- [ ] Read and understand existing Step model in workflow.py
- [ ] Understand how variable_store.resolve() works
- [ ] Have NOT modified any ml/*.py files
- [ ] All new Pydantic fields are Optional with defaults
- [ ] Plan to test with existing workflow JSON files
