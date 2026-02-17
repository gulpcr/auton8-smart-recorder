"""
Auton8 Recorder Skills Package

Skills are capability modules that run locally or delegate to a central server.
Import ``create_default_registry`` to get a pre-populated registry with all skills.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import SkillBase, SkillContext, SkillMode, SkillRegistry, SkillResult
from .portal_client import PortalClient

logger = logging.getLogger(__name__)

__all__ = [
    "SkillBase",
    "SkillContext",
    "SkillMode",
    "SkillRegistry",
    "SkillResult",
    "PortalClient",
    "create_default_registry",
    "create_context",
]


def create_default_registry() -> SkillRegistry:
    """
    Build and return a SkillRegistry pre-loaded with all available skills.

    Each skill import is wrapped in a try/except so a missing optional
    dependency won't break the entire system.
    """
    registry = SkillRegistry()

    # -- Local skills (always available) -----------------------------------
    _safe_register(registry, "recorder.skills.record", "RecordSkill")
    _safe_register(registry, "recorder.skills.replay", "ReplaySkill")
    _safe_register(registry, "recorder.skills.workflow_mgmt", "WorkflowMgmtSkill")
    _safe_register(registry, "recorder.skills.assertions", "AssertionsSkill")
    _safe_register(registry, "recorder.skills.variables", "VariablesSkill")
    _safe_register(registry, "recorder.skills.suite_runner", "SuiteRunnerSkill")
    _safe_register(registry, "recorder.skills.screenshot", "ScreenshotSkill")

    # -- Hybrid skills (local + server) ------------------------------------
    _safe_register(registry, "recorder.skills.healing", "HealingSkill")
    _safe_register(registry, "recorder.skills.selector_gen", "SelectorGenSkill")

    # -- Server-delegated skills -------------------------------------------
    _safe_register(registry, "recorder.skills.vision", "VisionSkill")
    _safe_register(registry, "recorder.skills.llm", "LLMSkill")
    _safe_register(registry, "recorder.skills.nlp", "NLPSkill")
    _safe_register(registry, "recorder.skills.rag", "RAGSkill")
    _safe_register(registry, "recorder.skills.audio", "AudioSkill")
    _safe_register(registry, "recorder.skills.analytics", "AnalyticsSkill")

    logger.info(
        f"Skill registry created with {len(registry.skill_names)} skills: "
        f"{', '.join(registry.skill_names)}"
    )
    return registry


def create_context(
    settings: Optional[dict] = None,
    portal_url: str = "",
    portal_token: str = "",
    skill_mode: str = "hybrid",
) -> SkillContext:
    """
    Convenience factory for building a ``SkillContext``.

    Reads portal connection info from *settings* dict if not passed explicitly.
    """
    settings = settings or {}
    url = portal_url or settings.get("portalUrl", "")
    token = portal_token or settings.get("portalAccessToken", "")
    mode_str = skill_mode or settings.get("skillMode", "hybrid")

    client: Optional[PortalClient] = None
    if url:
        client = PortalClient(base_url=url, access_token=token)

    return SkillContext(
        settings=settings,
        portal_client=client,
        skill_mode=SkillMode(mode_str),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_register(registry: SkillRegistry, module_path: str, class_name: str) -> None:
    """Import and register a skill, swallowing import errors gracefully."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        registry.register(cls())
    except Exception as e:
        logger.debug(f"Could not load skill {module_path}.{class_name}: {e}")
