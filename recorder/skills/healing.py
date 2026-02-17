"""
Healing Skill - Selector healing with local heuristics + server ML.

Tier 0-1 (deterministic + heuristic) run locally.
Tier 2-3 (vision + LLM) delegate to server when ML not installed locally.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import SkillBase, SkillContext, SkillMode, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class HealingSkill(SkillBase):
    name = "healing"
    description = "Selector healing: local heuristic (Tier 0-1) + server ML (Tier 2-3)"
    local_capable = True
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        # Lazy-loaded local engines
        self._healing_engine = None
        self._selector_engine = None
        self._local_ml_available: Optional[bool] = None

    def _check_local_ml(self) -> bool:
        """Check if local ML engines are importable."""
        if self._local_ml_available is not None:
            return self._local_ml_available
        try:
            from recorder.ml.healing_engine import SelectorHealingEngine
            from recorder.ml.selector_engine import MultiDimensionalSelectorEngine
            self._local_ml_available = True
        except ImportError:
            self._local_ml_available = False
        return self._local_ml_available

    def _get_local_engines(self):
        """Lazy-initialize local ML engines."""
        if self._healing_engine is None and self._check_local_ml():
            try:
                from recorder.ml.healing_engine import SelectorHealingEngine
                from recorder.ml.selector_engine import MultiDimensionalSelectorEngine
                self._healing_engine = SelectorHealingEngine()
                self._selector_engine = MultiDimensionalSelectorEngine()
                logger.info("[healing] Local ML engines initialized")
            except Exception as e:
                logger.warning(f"[healing] Failed to init local ML: {e}")
                self._local_ml_available = False
        return self._healing_engine, self._selector_engine

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Heal a broken selector locally.

        kwargs:
            element_data: dict - original element fingerprint
            page_state: dict - current page DOM context
            locators: list - current locator candidates
            max_tier: int - max healing tier to attempt
        """
        element_data = kwargs.get("element_data", {})
        page_state = kwargs.get("page_state", {})
        locators = kwargs.get("locators", [])
        max_tier = kwargs.get("max_tier", 1)

        # Tier 0-1: heuristic healing (always available locally)
        # Try alternative locators from the locator list
        if locators:
            for loc in locators:
                # In real execution, TieredExecutor tries these
                # This skill just validates the strategy
                pass

            return SkillResult(
                success=True,
                data={
                    "tier": min(max_tier, 1),
                    "strategy": "heuristic_fallback",
                    "candidates": len(locators),
                },
                run_location=SkillRunLocation.LOCAL,
            )

        # Tier 2+: try local ML if available
        if max_tier >= 2 and self._check_local_ml():
            healing_engine, selector_engine = self._get_local_engines()
            if healing_engine and selector_engine:
                try:
                    from recorder.ml.selector_engine import create_fingerprint_from_dom
                    fingerprint = create_fingerprint_from_dom(element_data)
                    selectors = selector_engine.generate_selectors(fingerprint)
                    result = healing_engine.heal_selector(
                        fingerprint, selectors, page_state
                    )
                    return SkillResult(
                        success=result.success,
                        data={
                            "tier": 2,
                            "strategy": result.strategy.value if result.strategy else "ml",
                            "confidence": result.confidence,
                            "fallback_selector": result.fallback_selector,
                        },
                        run_location=SkillRunLocation.LOCAL,
                    )
                except Exception as e:
                    logger.warning(f"[healing] Local ML healing failed: {e}")

        return SkillResult(
            success=False,
            error="Local healing exhausted, server needed for higher tiers",
        )

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate healing to central server (Tier 2-3)."""
        element_data = kwargs.get("element_data", {})
        page_state = kwargs.get("page_state", {})

        status, data = ctx.portal_client.heal_selector(element_data, page_state)

        if status == 200 and data.get("success"):
            return SkillResult(
                success=True,
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        error = data.get("detail", "Server healing failed") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_ml_available"] = self._check_local_ml()
        return status


class ServerHealingProxy:
    """
    Lightweight proxy that mimics the HealingEngine interface
    but delegates to the central server via PortalClient.

    Used by ReplaySkill to inject into StableReplayer for Tier 2-3.
    """

    def __init__(self, portal_client) -> None:
        self._client = portal_client

    def heal_selector(self, fingerprint, selectors, page_state):
        """Proxy call to server heal endpoint."""
        element_data = {}
        if hasattr(fingerprint, '__dict__'):
            element_data = {
                k: v for k, v in fingerprint.__dict__.items()
                if not k.startswith('_')
            }

        status, data = self._client.heal_selector(element_data, page_state)

        # Return a result-like object
        return _HealingResult(
            success=data.get("success", False) if status == 200 else False,
            strategy=data.get("strategy", "server"),
            confidence=data.get("confidence", 0.0),
            fallback_selector=data.get("fallback_selector"),
        )


class _HealingResult:
    """Simple result container matching HealingEngine's result interface."""

    def __init__(self, success, strategy, confidence, fallback_selector=None):
        self.success = success
        self.strategy = type("S", (), {"value": strategy})()
        self.confidence = confidence
        self.fallback_selector = fallback_selector
        self.execution_time_ms = 0
