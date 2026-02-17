"""
Vision Skill - Computer vision element matching (OpenCV, Tesseract, SSIM).

Heavy dependencies. Runs locally only if CV libs are installed,
otherwise delegates to central server.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class VisionSkill(SkillBase):
    name = "vision"
    description = "CV template matching, OCR, visual hash comparison"
    local_capable = True   # If OpenCV installed
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None
        self._vision_engine = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.ml.vision_engine import VisualElementMatcher
            self._local_available = True
        except ImportError:
            self._local_available = False
        return self._local_available

    def _get_engine(self):
        if self._vision_engine is None and self._check_local():
            try:
                from recorder.ml.vision_engine import VisualElementMatcher
                self._vision_engine = VisualElementMatcher()
            except Exception as e:
                logger.warning(f"[vision] Failed to init local CV: {e}")
                self._local_available = False
        return self._vision_engine

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass  # Dynamically determined

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run CV matching locally.

        kwargs:
            action: "template_match" | "ocr" | "visual_hash" | "ssim"
            screenshot_path: str
            template_path: str
            threshold: float
            text_query: str (for OCR)
        """
        engine = self._get_engine()
        if not engine:
            return SkillResult(success=False, error="Vision engine not available locally")

        action = kwargs.get("action", "template_match")

        if action == "template_match":
            screenshot = kwargs.get("screenshot_path", "")
            template = kwargs.get("template_path", "")
            threshold = kwargs.get("threshold", 0.75)

            match = engine.find_element_by_template(screenshot, template, threshold)
            if match:
                return SkillResult(
                    success=True,
                    data={"match": match, "action": action},
                    run_location=SkillRunLocation.LOCAL,
                )
            return SkillResult(success=False, error="No template match found")

        elif action == "ocr":
            screenshot = kwargs.get("screenshot_path", "")
            text_query = kwargs.get("text_query", "")
            results = engine.find_text_in_screenshot(screenshot, text_query)
            return SkillResult(
                success=bool(results),
                data={"results": results, "action": action},
                run_location=SkillRunLocation.LOCAL,
            )

        elif action == "visual_hash":
            image_a = kwargs.get("image_a", "")
            image_b = kwargs.get("image_b", "")
            similarity = engine.compare_visual_hashes(image_a, image_b)
            return SkillResult(
                success=True,
                data={"similarity": similarity, "action": action},
                run_location=SkillRunLocation.LOCAL,
            )

        return SkillResult(success=False, error=f"Unknown vision action: {action}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate CV operation to server."""
        action = kwargs.get("action", "template_match")
        screenshot = kwargs.get("screenshot_path", "")
        template = kwargs.get("template_path", "")
        threshold = kwargs.get("threshold", 0.75)

        status, data = ctx.portal_client.vision_match(screenshot, template, threshold)

        if status == 200:
            return SkillResult(
                success=data.get("found", False),
                data=data,
                run_location=SkillRunLocation.SERVER,
            )

        error = data.get("detail", "Vision match failed") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_cv_available"] = self._check_local()
        return status
