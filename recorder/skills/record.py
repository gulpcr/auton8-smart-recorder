"""
Record Skill - Browser recording via Playwright + injected.js

Always runs locally. No server delegation needed.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class RecordSkill(SkillBase):
    name = "record"
    description = "Record browser interactions via Playwright and WebSocket event capture"
    local_capable = True
    server_capable = False

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Start or stop a browser recording session.

        kwargs:
            action: "start" | "stop"
            url: str  (for start)
            browser_launcher: BrowserLauncher instance
            ws_server: WebSocketIngestServer instance
        """
        action = kwargs.get("action", "start")
        browser = kwargs.get("browser_launcher")
        ws_server = kwargs.get("ws_server")

        if not browser:
            return SkillResult(success=False, error="browser_launcher not provided")

        if action == "start":
            url = kwargs.get("url", "https://example.com")
            if not url.startswith("http"):
                url = "https://" + url

            # Start WebSocket ingest server if provided and not running
            if ws_server and not ws_server.is_running:
                ws_server.start()

            browser.launch(url)
            logger.info(f"[record] Started recording session: {url}")
            return SkillResult(
                success=True,
                data={"url": url, "recording": True},
                run_location=SkillRunLocation.LOCAL,
            )

        elif action == "stop":
            browser.stop()
            logger.info("[record] Stopped recording session")
            return SkillResult(
                success=True,
                data={"recording": False},
                run_location=SkillRunLocation.LOCAL,
            )

        return SkillResult(success=False, error=f"Unknown action: {action}")
