"""
Stable Execution System

A tiered approach to test execution:
- Tier 0: Deterministic (Playwright native)
- Tier 1: Heuristic (fallback selectors, patterns)
- Tier 2: Computer Vision (visual location)
- Tier 3: LLM (recovery planning, last resort)

80% of actions should complete at Tier 0.
AI is a safety net, not a crutch.
"""

from .page_stability import PageStabilityDetector, ElementStabilityChecker, StabilityState
from .action_verifier import ActionVerifier, ActionOutcome, VerificationResult
from .tiered_executor import TieredExecutor, ExecutionTier, ExecutionContext, ExecutionResult, LocatorCandidate
from .variable_store import VariableStore, ElementExtractor, get_variable_store

__all__ = [
    'PageStabilityDetector',
    'ElementStabilityChecker',
    'StabilityState',
    'ActionVerifier',
    'ActionOutcome',
    'VerificationResult',
    'TieredExecutor',
    'ExecutionTier',
    'ExecutionContext',
    'ExecutionResult',
    'LocatorCandidate',
    'VariableStore',
    'ElementExtractor',
    'get_variable_store',
]
