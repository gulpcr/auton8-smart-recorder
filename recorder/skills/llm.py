"""
LLM Skill - Intent classification, recovery planning, workflow analysis.

Heavy dependency (Ollama/llama-cpp). Runs locally if Ollama is running,
otherwise delegates to central server.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class LLMSkill(SkillBase):
    name = "llm"
    description = "LLM intent classification, recovery planning, workflow analysis"
    local_capable = True   # If Ollama is running
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None
        self._llm_engine = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.ml.ollama_engine import OllamaLLMEngine, OllamaConfig
            config = OllamaConfig(model_name="ministral-3:latest")
            engine = OllamaLLMEngine(config)
            self._local_available = engine.available
            if self._local_available:
                self._llm_engine = engine
        except ImportError:
            self._local_available = False
        return self._local_available

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run LLM operations locally (requires Ollama running).

        kwargs:
            action: "classify_intent" | "recover" | "analyze_workflow"
            segments: list (for classify_intent)
            step_data: dict (for recover)
            page_context: dict (for recover)
            workflow_steps: list (for analyze_workflow)
            workflow_name: str
            workflow_url: str
        """
        if not self._llm_engine:
            if not self._check_local():
                return SkillResult(success=False, error="Local LLM not available (Ollama not running)")

        action = kwargs.get("action", "classify_intent")

        if action == "classify_intent":
            segments = kwargs.get("segments", [])
            try:
                result = self._llm_engine.classify_intent(segments)
                return SkillResult(
                    success=True,
                    data={
                        "primary_intent": result.primary_intent,
                        "secondary_intents": result.secondary_intents,
                    },
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Intent classification failed: {e}")

        elif action == "recover":
            step_data = kwargs.get("step_data", {})
            page_context = kwargs.get("page_context", {})
            try:
                result = self._llm_engine.generate_recovery_plan(step_data, page_context)
                return SkillResult(
                    success=True,
                    data={"recovery_plan": result},
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Recovery planning failed: {e}")

        elif action == "analyze_workflow":
            steps = kwargs.get("workflow_steps", [])
            name = kwargs.get("workflow_name", "")
            url = kwargs.get("workflow_url", "")
            try:
                result = self._llm_engine.analyze_workflow(steps, name, url)
                return SkillResult(
                    success=True,
                    data={
                        "summary": result.summary,
                        "purpose": result.purpose,
                        "complexity": result.complexity,
                        "suggestions": result.suggestions,
                    },
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Workflow analysis failed: {e}")

        return SkillResult(success=False, error=f"Unknown LLM action: {action}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate LLM operations to central server."""
        action = kwargs.get("action", "classify_intent")

        if action == "classify_intent":
            segments = kwargs.get("segments", [])
            status, data = ctx.portal_client.classify_intent(segments)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._server_error(data)

        elif action == "recover":
            step_data = kwargs.get("step_data", {})
            page_context = kwargs.get("page_context", {})
            status, data = ctx.portal_client.llm_recover(step_data, page_context)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._server_error(data)

        elif action == "analyze_workflow":
            # Server may not have a dedicated endpoint; use generic LLM
            steps = kwargs.get("workflow_steps", [])
            name = kwargs.get("workflow_name", "")
            status, data = ctx.portal_client.post("/api/llm/analyze-workflow", {
                "steps": steps,
                "name": name,
            })
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)
            return self._server_error(data)

        return SkillResult(success=False, error=f"Unknown LLM action: {action}")

    @staticmethod
    def _server_error(data: Any) -> SkillResult:
        error = data.get("detail", "LLM server error") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_ollama_available"] = self._check_local()
        if self._llm_engine:
            status["model"] = getattr(self._llm_engine, "config", {})
        return status
