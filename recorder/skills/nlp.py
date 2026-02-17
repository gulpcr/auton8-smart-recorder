"""
NLP Skill - Text similarity, entity extraction, semantic analysis.

Heavy dependency (BERT, spaCy). Delegates to server when not installed locally.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class NLPSkill(SkillBase):
    name = "nlp"
    description = "Text similarity, entity extraction, semantic analysis via BERT/spaCy"
    local_capable = True   # If NLP libs installed
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None
        self._nlp_engine = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.ml.nlp_engine import NLPEngine
            self._local_available = True
        except ImportError:
            self._local_available = False
        return self._local_available

    def _get_engine(self):
        if self._nlp_engine is None and self._check_local():
            try:
                from recorder.ml.nlp_engine import NLPEngine
                self._nlp_engine = NLPEngine()
            except Exception as e:
                logger.warning(f"[nlp] Failed to init local NLP: {e}")
                self._local_available = False
        return self._nlp_engine

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run NLP operations locally.

        kwargs:
            action: "similarity" | "entities" | "sentiment" | "classify"
            text_a: str
            text_b: str (for similarity)
            text: str (for entities/sentiment/classify)
        """
        engine = self._get_engine()
        if not engine:
            return SkillResult(success=False, error="NLP engine not available locally")

        action = kwargs.get("action", "similarity")

        if action == "similarity":
            text_a = kwargs.get("text_a", "")
            text_b = kwargs.get("text_b", "")
            try:
                score = engine.compute_similarity(text_a, text_b)
                return SkillResult(
                    success=True,
                    data={"similarity": score, "text_a": text_a, "text_b": text_b},
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Similarity failed: {e}")

        elif action == "entities":
            text = kwargs.get("text", "")
            try:
                entities = engine.extract_entities(text)
                return SkillResult(
                    success=True,
                    data={"entities": entities},
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Entity extraction failed: {e}")

        elif action == "sentiment":
            text = kwargs.get("text", "")
            try:
                result = engine.analyze_sentiment(text)
                return SkillResult(
                    success=True,
                    data=result,
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Sentiment analysis failed: {e}")

        return SkillResult(success=False, error=f"Unknown NLP action: {action}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate NLP operations to central server."""
        action = kwargs.get("action", "similarity")

        if action == "similarity":
            text_a = kwargs.get("text_a", "")
            text_b = kwargs.get("text_b", "")
            status, data = ctx.portal_client.nlp_similarity(text_a, text_b)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
        else:
            text = kwargs.get("text", "")
            status, data = ctx.portal_client.post(f"/api/nlp/{action}", {"text": text})
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)

        error = data.get("detail", "NLP server error") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_nlp_available"] = self._check_local()
        return status
