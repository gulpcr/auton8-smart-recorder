"""
Selector Generation Skill - ML-powered multi-dimensional selector generation.

Heavy dependency (Random Forest, scikit-learn). Delegates to server
when ML not installed locally.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class SelectorGenSkill(SkillBase):
    name = "selector_gen"
    description = "ML-powered multi-dimensional selector generation"
    local_capable = True   # If ML libs installed
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None
        self._selector_engine = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.ml.selector_engine import MultiDimensionalSelectorEngine
            self._local_available = True
        except ImportError:
            self._local_available = False
        return self._local_available

    def _get_engine(self):
        if self._selector_engine is None and self._check_local():
            try:
                from recorder.ml.selector_engine import MultiDimensionalSelectorEngine
                self._selector_engine = MultiDimensionalSelectorEngine()
            except Exception as e:
                logger.warning(f"[selector_gen] Failed to init local engine: {e}")
                self._local_available = False
        return self._selector_engine

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Generate selectors locally.

        kwargs:
            element_data: dict - DOM element fingerprint
            page_url: str
        """
        engine = self._get_engine()
        if not engine:
            return SkillResult(success=False, error="Selector engine not available locally")

        element_data = kwargs.get("element_data", {})
        if not element_data:
            return SkillResult(success=False, error="element_data required")

        try:
            from recorder.ml.selector_engine import create_fingerprint_from_dom
            fingerprint = create_fingerprint_from_dom(element_data)
            selectors = engine.generate_selectors(fingerprint)

            selector_list = [
                {
                    "type": sel.type.value,
                    "value": sel.value,
                    "score": sel.score,
                    "metadata": sel.metadata if hasattr(sel, "metadata") else {},
                }
                for sel in selectors
            ]

            return SkillResult(
                success=True,
                data={"selectors": selector_list, "count": len(selector_list)},
                run_location=SkillRunLocation.LOCAL,
            )
        except Exception as e:
            return SkillResult(success=False, error=f"Selector generation failed: {e}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate selector generation to central server."""
        element_data = kwargs.get("element_data", {})
        if not element_data:
            return SkillResult(success=False, error="element_data required")

        status, data = ctx.portal_client.generate_selectors(element_data)

        if status == 200:
            return SkillResult(
                success=True,
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        error = data.get("detail", "Selector generation failed") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_ml_available"] = self._check_local()
        return status
