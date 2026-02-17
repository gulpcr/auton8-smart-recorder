"""
Skills Framework - Base classes for the Auton8 Recorder skill system.

Skills are capability modules that can run locally on a tester machine
or delegate to a central server for heavy ML/AI operations.

Modes:
  - local:  Never call server. Use only what's installed on this machine.
  - hybrid: Try local first; fall back to server when local can't handle it.
  - server: Always delegate to server (thin client mode).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .portal_client import PortalClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillMode(str, Enum):
    LOCAL = "local"
    HYBRID = "hybrid"
    SERVER = "server"


class SkillRunLocation(str, Enum):
    LOCAL = "local"
    SERVER = "server"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillResult:
    """Uniform result returned by every skill execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    run_location: SkillRunLocation = SkillRunLocation.LOCAL
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillContext:
    """
    Runtime context passed to every skill call.

    Carries references to shared resources so skills don't need to
    import them individually.
    """
    settings: Dict[str, Any] = field(default_factory=dict)
    portal_client: Optional["PortalClient"] = None
    skill_mode: SkillMode = SkillMode.HYBRID
    # Populated by the registry after all skills register
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base Skill
# ---------------------------------------------------------------------------

class SkillBase:
    """
    Abstract base for every skill.

    Subclasses must set *name*, and implement at least one of
    ``execute_local`` or ``execute_server``.
    """

    name: str = ""
    description: str = ""
    local_capable: bool = False    # Can run without a server
    server_capable: bool = False   # Can delegate to server
    version: str = "1.0.0"

    def __init__(self) -> None:
        if not self.name:
            raise ValueError("Skill must define a 'name'")

    # -- public entry point ------------------------------------------------

    def execute(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Route execution based on skill mode and capabilities.

        Order for hybrid mode:
          1. Try local if capable
          2. If local fails or isn't capable, try server
        """
        start = time.perf_counter_ns()

        mode = ctx.skill_mode

        if mode == SkillMode.LOCAL:
            result = self._run_local(ctx, **kwargs)
        elif mode == SkillMode.SERVER:
            result = self._run_server(ctx, **kwargs)
        else:
            # hybrid
            if self.local_capable:
                result = self._run_local(ctx, **kwargs)
                if not result.success and self.server_capable:
                    logger.info(
                        f"[{self.name}] Local failed, falling back to server: "
                        f"{result.error}"
                    )
                    result = self._run_server(ctx, **kwargs)
            elif self.server_capable:
                result = self._run_server(ctx, **kwargs)
            else:
                result = SkillResult(
                    success=False,
                    error=f"Skill '{self.name}' has no execution target",
                )

        elapsed_ms = int((time.perf_counter_ns() - start) / 1_000_000)
        result.duration_ms = elapsed_ms
        return result

    # -- internal helpers --------------------------------------------------

    def _run_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        if not self.local_capable:
            return SkillResult(
                success=False,
                error=f"Skill '{self.name}' cannot run locally",
            )
        try:
            return self.execute_local(ctx, **kwargs)
        except Exception as exc:
            logger.error(f"[{self.name}] Local execution error: {exc}")
            return SkillResult(success=False, error=str(exc))

    def _run_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        if not self.server_capable:
            return SkillResult(
                success=False,
                error=f"Skill '{self.name}' has no server implementation",
            )
        if not ctx.portal_client or not ctx.portal_client.is_connected:
            return SkillResult(
                success=False,
                error="Portal server not connected",
            )
        try:
            return self.execute_server(ctx, **kwargs)
        except Exception as exc:
            logger.error(f"[{self.name}] Server execution error: {exc}")
            return SkillResult(success=False, error=str(exc))

    # -- overridable -------------------------------------------------------

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        raise NotImplementedError

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        raise NotImplementedError

    def get_status(self) -> Dict[str, Any]:
        """Return current skill status for health checks."""
        return {
            "name": self.name,
            "version": self.version,
            "local_capable": self.local_capable,
            "server_capable": self.server_capable,
        }


# ---------------------------------------------------------------------------
# Skill Registry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """
    Central registry that holds all available skills.

    Usage:
        registry = SkillRegistry()
        registry.register(RecordSkill())
        result = registry.execute("record", ctx, url="https://example.com")
    """

    def __init__(self) -> None:
        self._skills: Dict[str, SkillBase] = {}

    def register(self, skill: SkillBase) -> None:
        if skill.name in self._skills:
            logger.warning(f"Skill '{skill.name}' already registered, overwriting")
        self._skills[skill.name] = skill
        logger.debug(f"Registered skill: {skill.name}")

    def get(self, name: str) -> Optional[SkillBase]:
        return self._skills.get(name)

    def execute(self, name: str, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        skill = self._skills.get(name)
        if not skill:
            return SkillResult(success=False, error=f"Unknown skill: {name}")
        return skill.execute(ctx, **kwargs)

    @property
    def skill_names(self) -> List[str]:
        return list(self._skills.keys())

    def get_all_status(self) -> List[Dict[str, Any]]:
        return [s.get_status() for s in self._skills.values()]
