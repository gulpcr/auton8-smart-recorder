"""
Screenshot Skill - Element and page screenshot capture.

Always runs locally (requires browser access).
"""

from __future__ import annotations

import logging
from typing import Any

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class ScreenshotSkill(SkillBase):
    name = "screenshot"
    description = "Capture element or full-page screenshots"
    local_capable = True
    server_capable = False

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Capture a screenshot.

        kwargs:
            browser_launcher: BrowserLauncher instance
            mode: "element" | "page" | "full_page"
            bounding_box: tuple (x, y, w, h) for element mode
            element_id: str - identifier for the element
            output_path: str - optional custom output path
        """
        browser = kwargs.get("browser_launcher")
        if not browser:
            return SkillResult(success=False, error="browser_launcher required")

        mode = kwargs.get("mode", "element")

        if mode == "element":
            bbox = kwargs.get("bounding_box")
            element_id = kwargs.get("element_id", "screenshot")
            if not bbox:
                return SkillResult(success=False, error="bounding_box required for element mode")

            result = browser.capture_element_screenshot(
                bounding_box=tuple(bbox),
                element_id=element_id,
            )
            if result:
                path, visual_hash, _ = result
                return SkillResult(
                    success=True,
                    data={
                        "path": path,
                        "visual_hash": visual_hash,
                        "mode": "element",
                    },
                    run_location=SkillRunLocation.LOCAL,
                )
            return SkillResult(success=False, error="Screenshot capture failed")

        elif mode in ("page", "full_page"):
            output_path = kwargs.get("output_path")
            if not output_path:
                from pathlib import Path
                import uuid
                screenshots_dir = ctx.settings.get("screenshotsDirectory", "data/screenshots")
                Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
                output_path = str(Path(screenshots_dir) / f"page-{uuid.uuid4().hex[:8]}.png")

            result = browser.capture_page_screenshot(
                output_path=output_path,
                full_page=(mode == "full_page"),
            )
            if result:
                return SkillResult(
                    success=True,
                    data={"path": output_path, "mode": mode},
                    run_location=SkillRunLocation.LOCAL,
                )
            return SkillResult(success=False, error="Page screenshot failed")

        return SkillResult(success=False, error=f"Unknown mode: {mode}")
