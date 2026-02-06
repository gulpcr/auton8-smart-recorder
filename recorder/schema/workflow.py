from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class Locator(BaseModel):
    # Extended type list to support common locator strategies from browser instrumentation
    type: Literal["data", "aria", "label", "css", "text", "xpath", "frame", "shadow", "id", "name"] = "css"
    value: str
    score: float = 0.5


class FrameHint(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    src: Optional[str] = None
    title: Optional[str] = None
    index: Optional[int] = None
    locators: List[Locator] = Field(default_factory=list)


class ShadowHost(BaseModel):
    locators: List[Locator] = Field(default_factory=list)


class WaitCondition(BaseModel):
    kind: Literal[
        "attached",
        "visible",
        "enabled",
        "stable",
        "text",
        "gone",
        "navigation",
        "networkIdle",
    ]
    value: Optional[str] = None
    timeoutMs: int = 5000


class Assertion(BaseModel):
    kind: Literal["textContains", "exists", "count", "urlContains", "toastEquals"]
    target: Optional["Target"] = None
    value: Optional[str] = None


class HealingEntry(BaseModel):
    locator: Optional[str] = None
    result: Literal["pass", "fail"]
    timestamp: Optional[str] = None


class Target(BaseModel):
    locators: List[Locator] = Field(default_factory=list)


# =============================================================================
# STEP CONFIGURATION MODELS
# All fields are Optional with safe defaults for backward compatibility
# =============================================================================

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


class WaitStepConfig(BaseModel):
    """Wait command configuration"""
    waitType: Literal["time", "selector", "function", "navigation", "networkIdle"] = "time"
    waitMs: int = 1000
    waitSelector: Optional[str] = None
    waitState: Literal["attached", "detached", "visible", "hidden"] = "visible"


class AssertConfig(BaseModel):
    """
    Unified assert configuration - comprehensive assertion system.

    Supports multiple assertion types, match modes, retry logic,
    collection handling, and browser storage/console assertions.
    """
    # Core assertion type
    assertType: Literal[
        # Element assertions
        "text", "visible", "hidden", "enabled", "disabled",
        "value", "attribute", "count", "checked",
        # Page assertions
        "url", "title",
        # Storage assertions
        "localStorage", "sessionStorage", "cookie",
        # Console assertions
        "consoleError", "consoleWarning", "consoleLog"
    ] = "text"

    # Text/value matching configuration
    matchMode: Literal["equals", "contains", "startsWith", "endsWith", "regex"] = "contains"
    expectedValue: str = ""
    caseSensitive: bool = False
    normalizeWhitespace: bool = True

    # Negation - inverts the assertion result
    negate: bool = False  # If True, assertion passes when condition is NOT met

    # Custom error message for better debugging
    customMessage: Optional[str] = None  # User-defined failure message

    # Attribute assertions
    attributeName: Optional[str] = None

    # Count assertions
    expectedCount: Optional[int] = None
    countComparison: Literal["equals", "greaterThan", "lessThan", "atLeast", "atMost"] = "equals"

    # Numeric tolerance for value comparisons
    numericTolerance: Optional[float] = None  # Tolerance value (e.g., 0.1 for 10% or 5 for absolute)
    numericToleranceType: Literal["percent", "absolute"] = "absolute"

    # Collection mode - how to handle multiple matching elements
    collectionMode: Literal["first", "last", "all", "any", "none"] = "first"
    # first = assert on first element only (default)
    # last = assert on last element only
    # all = ALL elements must pass the assertion
    # any = at least ONE element must pass
    # none = NO elements should pass (all must fail)

    # Storage/cookie key (for localStorage, sessionStorage, cookie assertions)
    storageKey: Optional[str] = None

    # Retry/polling configuration for dynamic content
    retryUntilPass: bool = False  # Keep retrying until assertion passes
    retryIntervalMs: int = 500  # Interval between retries
    maxRetries: int = 10  # Maximum number of retry attempts

    # Behavior
    softAssert: bool = False  # Log failure but continue (don't fail the test)
    waitForCondition: bool = True  # Auto-wait for element before asserting
    assertTimeoutMs: int = 5000  # Timeout for waiting

    # Evidence collection
    screenshotOnFail: bool = False  # Capture screenshot when assertion fails


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
    scope: Literal["step", "test", "suite", "global"] = "test"

    # Source of the variable value
    source: Literal[
        "manual",           # Direct value assignment
        "element_text",     # Extract text from element
        "element_value",    # Extract input value
        "element_attribute",# Extract attribute value
        "element_count",    # Count matching elements
        "page_url",         # Current page URL
        "page_title",       # Current page title
        "expression",       # Evaluate expression
        "json_path",        # Extract from JSON response
        "regex"             # Extract with regex
    ] = "element_text"

    # For manual source
    manualValue: Optional[str] = None
    valueType: Literal["string", "number", "boolean", "auto"] = "auto"

    # For element-based sources (uses step's target selector)
    attributeName: Optional[str] = None  # For element_attribute

    # For expression source
    expression: Optional[str] = None  # ${price} * ${quantity}

    # For regex extraction
    regexPattern: Optional[str] = None
    regexGroup: int = 0

    # For JSON path extraction
    jsonPath: Optional[str] = None  # $.data.items[0].price

    # Options
    persistent: bool = False  # Keep across workflow runs (global scope)
    masked: bool = False  # Hide in logs (passwords, tokens)

    # Legacy fields for backward compatibility
    extractFrom: Literal["text", "value", "attribute", "count", "url", "title"] = "text"
    comparison: Literal["equals", "notEquals", "contains", "greaterThan", "lessThan", "matches"] = "equals"
    expectedValue: Optional[str] = None


class CalculateConfig(BaseModel):
    """
    Calculated expression configuration for dynamic assertions.

    Supports math operations, comparisons, and variable substitution.
    Example: ${price} * ${quantity} + ${shipping} - ${discount}
    """
    # Expression to evaluate (supports ${varName} substitution)
    expression: str = ""

    # How to compare calculated value with actual
    comparisonMode: Literal[
        "equals", "notEquals",
        "greaterThan", "greaterOrEqual",
        "lessThan", "lessOrEqual",
        "contains", "notContains",
        "startsWith", "endsWith",
        "matchesRegex", "between"
    ] = "equals"

    # Tolerance for numeric comparisons (for floating point)
    tolerance: float = 0.0

    # For 'between' mode: upper bound (expression is lower bound)
    upperBound: Optional[str] = None

    # Where to get actual value to compare
    actualValueFrom: Literal["element", "variable", "expression"] = "element"
    actualVariableName: Optional[str] = None  # If actualValueFrom is "variable"
    actualExpression: Optional[str] = None  # If actualValueFrom is "expression"

    # Result variable - store calculated result in this variable
    storeResultAs: Optional[str] = None

    # Display formatting
    formatResult: Optional[str] = None  # Format string: "{:.2f}" for 2 decimal places

    # Soft assertion - log but don't fail
    softAssert: bool = False

    # Custom message on failure
    customMessage: Optional[str] = None


class HoverConfig(BaseModel):
    """Hover-specific configuration"""
    hoverDurationMs: int = 0  # How long to hover (0 = just move)
    position: Optional[Dict[str, int]] = None  # {"x": 10, "y": 10} relative to element
    force: bool = False


class ScrollConfig(BaseModel):
    """Scroll configuration"""
    scrollTarget: Literal["page", "element"] = "element"
    direction: Literal["up", "down", "left", "right"] = "down"
    amount: Optional[int] = None  # Pixels, None = scroll into view
    behavior: Literal["auto", "smooth"] = "auto"


class DragConfig(BaseModel):
    """Drag and drop configuration"""
    targetSelector: Optional[str] = None  # For dragTo
    offsetX: int = 0  # For dragByOffset
    offsetY: int = 0
    steps: int = 1  # Number of intermediate steps


class ScreenshotConfig(BaseModel):
    """Screenshot configuration"""
    filename: Optional[str] = None  # Auto-generated if None
    fullPage: bool = False
    captureElement: bool = True  # Screenshot element vs page


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
    hover: Optional[HoverConfig] = None
    scroll: Optional[ScrollConfig] = None
    drag: Optional[DragConfig] = None
    inputConfig: Optional[InputConfig] = None  # Named to avoid shadowing
    select: Optional[SelectConfig] = None
    waitConfig: Optional[WaitStepConfig] = None  # Named to avoid shadowing
    assertConfig: Optional[AssertConfig] = None  # Named to avoid Python keyword
    dialog: Optional[DialogConfig] = None
    frame: Optional[FrameConfig] = None
    window: Optional[WindowConfig] = None
    variable: Optional[VariableConfig] = None
    screenshot: Optional[ScreenshotConfig] = None
    calculate: Optional[CalculateConfig] = None  # For calculateAssert/evaluate steps


# =============================================================================
# STEP MODEL
# =============================================================================

class Step(BaseModel):
    id: str
    name: str
    description: Optional[str] = None  # User-provided step description
    type: Literal[
        # Basic interactions
        "click",
        "dblclick",
        "contextmenu",
        "hover",
        "dragdrop",
        "scroll",
        # Input
        "type",
        "input",
        "change",
        "keydown",
        "keyup",
        "keypress",
        "selectOption",
        "check",
        "uncheck",
        "press",
        "submit",
        # Frame operations
        "switchFrame",
        "switchFrameByName",
        "switchFrameByIndex",
        "switchMainFrame",
        "switchParentFrame",
        # Window operations
        "switchWindow",
        "switchWindowByIndex",
        "switchNewWindow",
        "closeWindow",
        # Dialog operations
        "handleAlert",
        "handleConfirm",
        "handlePrompt",
        "setDialogHandler",
        # Variable operations
        "storeVariable",
        "storeText",
        "storeValue",
        "storeAttribute",
        "storeCount",
        "assertVariable",
        "setVariable",
        "extractVariable",
        # Calculated assertions
        "calculateAssert",
        "evaluate",
        # Wait operations
        "wait",
        "waitForElement",
        "waitForNavigation",
        "waitForUrl",
        # Assertions
        "assert",
        "assertText",
        "assertVisible",
        "assertNotVisible",
        "assertEnabled",
        "assertDisabled",
        "assertChecked",
        "assertValue",
        "assertAttribute",
        "assertUrl",
        "assertCount",
        # Drag and drop
        "dragTo",
        "dragByOffset",
        # Screenshot
        "screenshot",
        # Custom
        "custom",
    ]
    semantic: Optional[Dict[str, str]] = None
    framePath: List[FrameHint] = Field(default_factory=list)
    shadowPath: List[ShadowHost] = Field(default_factory=list)
    target: Optional[Target] = None
    input: Optional[Dict[str, str]] = None
    waits: List[WaitCondition] = Field(default_factory=list)
    assertions: List[Assertion] = Field(default_factory=list)
    artifacts: Optional[Dict[str, str]] = None
    domContext: Optional[Dict[str, Any]] = None
    page: Optional[Dict[str, str]] = None
    healing: Optional[Dict[str, object]] = None
    timing: Optional[Dict[str, object]] = None
    metadata: Optional[Dict[str, Any]] = None  # ML metadata, preserved
    enhancements: Optional[Dict[str, Any]] = None  # New: advanced features (loops, conditions, etc.)
    config: Optional[StepConfig] = None  # NEW: Step configuration (all optional, uses defaults when None)


class VariableImportConfig(BaseModel):
    """Import a variable from global registry into workflow."""
    globalName: str  # Name in global registry
    localName: Optional[str] = None  # Local variable name (defaults to globalName)
    required: bool = True  # Fail workflow if not found
    defaultValue: Optional[Any] = None  # Use if not found and not required


class VariableExportConfig(BaseModel):
    """Export a variable from workflow to global registry."""
    variableName: str  # Local variable name in workflow
    globalName: Optional[str] = None  # Name in registry (defaults to variableName)
    group: str = "default"  # Variable group for organization
    overwrite: bool = True  # Overwrite if already exists
    persistent: bool = True  # Persist to disk
    masked: bool = False  # Hide sensitive values in logs


class WorkflowVariables(BaseModel):
    """
    Variable import/export configuration for cross-workflow sharing.

    Imports are resolved before workflow execution starts.
    Exports are saved after workflow execution completes (success or failure).
    """
    imports: List[VariableImportConfig] = Field(default_factory=list)
    exports: List[VariableExportConfig] = Field(default_factory=list)


class Workflow(BaseModel):
    version: str = "1.0"
    project: Dict[str, object] = Field(default_factory=dict)
    meta: Dict[str, object] = Field(default_factory=dict)  # Deprecated, use metadata
    steps: List[Step] = Field(default_factory=list)
    assets: Dict[str, object] = Field(default_factory=dict)
    replay: Dict[str, object] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None  # New: enhanced metadata (name, status, tags, etc.)
    variables: Optional[WorkflowVariables] = None  # NEW: Cross-workflow variable sharing


Assertion.model_rebuild()

