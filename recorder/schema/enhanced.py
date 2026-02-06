"""
Enhanced schema models for premium features.
All new models are optional and backward compatible.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowMetadata(BaseModel):
    """Enhanced metadata for workflows with test management features."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    status: Literal["draft", "ready", "flaky", "broken"] = "draft"
    tags: List[str] = Field(default_factory=list)
    createdAt: Optional[str] = None  # ISO 8601
    updatedAt: Optional[str] = None  # ISO 8601
    lastRunAt: Optional[str] = None  # ISO 8601
    version: int = 1
    baseUrl: Optional[str] = None  # Keep backward compatibility
    author: Optional[str] = None
    
    # Test statistics
    totalRuns: int = 0
    successfulRuns: int = 0
    failedRuns: int = 0
    avgDuration: float = 0.0  # seconds
    
    # Portal integration
    portalId: Optional[str] = None
    portalUrl: Optional[str] = None
    lastPublishedAt: Optional[str] = None


class LoopConfig(BaseModel):
    """Configuration for loop block."""
    
    kind: Literal["count", "dataset", "while"]
    count: Optional[int] = None
    dataset: Optional[str] = None  # Path to CSV file
    condition: Optional[str] = None  # Expression for while loops
    maxIterations: int = 100  # Safety limit


class ConditionConfig(BaseModel):
    """Configuration for conditional block."""
    
    kind: Literal["element_visible", "element_hidden", "text_contains", 
                  "url_contains", "variable_equals", "custom"]
    target: Optional[str] = None  # Selector or URL
    value: Optional[str] = None  # Expected value
    expression: Optional[str] = None  # Custom condition expression
    elseSteps: List[str] = Field(default_factory=list)  # Step IDs for else branch


class VariableConfig(BaseModel):
    """Variable capture and storage configuration."""
    
    name: str
    source: Literal["element_text", "element_attribute", "page_url", 
                   "page_title", "custom", "dataset"]
    selector: Optional[str] = None  # For element-based capture
    attribute: Optional[str] = None  # For attribute capture
    expression: Optional[str] = None  # For custom extraction
    mask: bool = False  # For sensitive data (passwords, tokens)
    persistent: bool = False  # Keep across workflow runs


class AssertionConfig(BaseModel):
    """Enhanced assertion configuration."""
    
    kind: Literal["text_equals", "text_contains", "text_matches",
                  "element_visible", "element_hidden", "element_count",
                  "attribute_equals", "url_contains", "url_equals",
                  "variable_equals", "custom"]
    target: Optional[str] = None  # Selector
    value: Optional[str] = None  # Expected value
    expression: Optional[str] = None  # Custom assertion
    screenshotOnFailure: bool = True
    continueOnFailure: bool = False
    timeout: int = 5000  # ms


class StepEnhancements(BaseModel):
    """Optional enhancements for steps."""
    
    # Control flow
    loop: Optional[LoopConfig] = None
    condition: Optional[ConditionConfig] = None
    
    # Variables
    variableCapture: Optional[VariableConfig] = None
    variableBindings: Dict[str, str] = Field(default_factory=dict)  # {{var}} -> value
    
    # Execution control
    timeout: int = 30000  # ms
    retries: int = 0
    retryDelay: int = 1000  # ms
    continueOnError: bool = False
    
    # Enhanced assertions
    assertions: List[AssertionConfig] = Field(default_factory=list)
    
    # Nested steps (for loops/conditions)
    nestedSteps: List[str] = Field(default_factory=list)  # Step IDs
    
    # User notes
    comment: Optional[str] = None
    disabled: bool = False  # Skip during replay


class ReplayResult(BaseModel):
    """Result of workflow replay."""
    
    workflowId: str
    status: Literal["pass", "fail", "partial"]
    startedAt: str  # ISO 8601
    completedAt: Optional[str] = None
    duration: float = 0.0  # seconds
    
    # Step results
    stepResults: List[StepResult] = Field(default_factory=list)
    
    # Artifacts
    screenshotDir: Optional[str] = None
    tracePath: Optional[str] = None
    videoPath: Optional[str] = None
    logPath: Optional[str] = None
    
    # Errors
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class StepResult(BaseModel):
    """Result of individual step execution."""
    
    stepId: str
    status: Literal["pass", "fail", "warn", "skip"]
    startedAt: str  # ISO 8601
    duration: float = 0.0  # seconds
    
    # Locator used (for healing tracking)
    usedLocator: Optional[Dict[str, Any]] = None
    locatorIndex: int = 0  # Which locator succeeded
    
    # Artifacts
    screenshotPath: Optional[str] = None
    
    # Errors
    error: Optional[str] = None
    errorType: Optional[str] = None
    errorStack: Optional[str] = None
    
    # Assertions
    assertionResults: List[AssertionResult] = Field(default_factory=list)


class AssertionResult(BaseModel):
    """Result of assertion execution."""
    
    assertion: AssertionConfig
    passed: bool
    actual: Optional[str] = None
    expected: Optional[str] = None
    error: Optional[str] = None
    screenshotPath: Optional[str] = None


class PackageMetadata(BaseModel):
    """Metadata for exported test package."""
    
    packageId: str
    workflowId: str
    name: str
    version: int
    createdAt: str  # ISO 8601
    createdBy: Optional[str] = None
    
    # Contents
    includedAssets: List[str] = Field(default_factory=list)
    totalSize: int = 0  # bytes
    
    # Portal info
    portalUrl: Optional[str] = None
    uploadedAt: Optional[str] = None


class PortalConfig(BaseModel):
    """Configuration for test portal integration."""
    
    url: str
    authToken: str  # Masked in UI
    projectId: Optional[str] = None
    enabled: bool = True
    
    # Upload settings
    autoUpload: bool = False
    uploadOnSuccess: bool = True
    uploadOnFailure: bool = False
    
    # Offline queue
    queuePath: str = "data/upload_queue"
    maxRetries: int = 3
    retryDelay: int = 5000  # ms
