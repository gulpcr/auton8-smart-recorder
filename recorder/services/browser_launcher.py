from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Optional, Tuple
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Screenshot storage directory
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "screenshots"


class BrowserLauncher:
    """
    Launches a Playwright browser with the recorder instrumentation script injected.
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _get_injected_script(self) -> str:
        # Use advanced instrumentation for ML-powered selector generation
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "instrumentation", "injected_advanced.js"
        )
        with open(script_path, "r", encoding="utf-8") as f:
            return f.read()

    async def _launch(self, url: str):
        self._running = True
        pw = None
        try:
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(headless=False)
            self._context = await self._browser.new_context()

            # Inject the recorder script into every page
            script = self._get_injected_script()
            await self._context.add_init_script(script)

            self._page = await self._context.new_page()
            # Increased timeout for slow websites (60 seconds instead of 30)
            await self._page.goto(url, timeout=60000, wait_until="domcontentloaded")
            logger.info("Browser launched and navigated to %s", url)

            # Wait for browser to close
            await self._page.wait_for_event("close", timeout=0)
        except Exception as exc:
            logger.exception("Browser session ended: %s", exc)
        finally:
            self._running = False
            if self._browser:
                await self._browser.close()
            if pw:
                await pw.stop()

    def launch(self, url: str = "https://example.com"):
        if self._running:
            logger.warning("Browser already running")
            return

        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._launch(url))

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        logger.info("Browser launcher thread started")

    def stop(self):
        if self._loop and self._running:
            async def close():
                if self._browser:
                    await self._browser.close()
            asyncio.run_coroutine_threadsafe(close(), self._loop)

    def capture_element_screenshot(
        self,
        bounding_box: Tuple[int, int, int, int],
        element_id: str
    ) -> Optional[Tuple[str, str, np.ndarray]]:
        """
        Capture screenshot of element and compute visual hash.

        Args:
            bounding_box: (x, y, width, height) of element
            element_id: Unique ID for the element

        Returns:
            Tuple of (screenshot_path, visual_hash, image_array) or None if failed
        """
        if not self._loop or not self._running or not self._page:
            return None

        async def capture():
            try:
                # Ensure screenshot directory exists
                SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

                # Capture full page screenshot
                screenshot_bytes = await self._page.screenshot(type="png")

                # Convert to numpy array
                nparr = np.frombuffer(screenshot_bytes, np.uint8)
                full_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if full_image is None:
                    return None

                # Crop to element bounding box
                x, y, w, h = bounding_box
                # Ensure bounds are valid
                x = max(0, int(x))
                y = max(0, int(y))
                w = max(1, int(w))
                h = max(1, int(h))

                # Clamp to image dimensions
                img_h, img_w = full_image.shape[:2]
                x2 = min(x + w, img_w)
                y2 = min(y + h, img_h)

                if x >= img_w or y >= img_h or x2 <= x or y2 <= y:
                    return None

                element_image = full_image[y:y2, x:x2]

                if element_image.size == 0:
                    return None

                # Save element screenshot
                screenshot_path = SCREENSHOT_DIR / f"{element_id}.png"
                cv2.imwrite(str(screenshot_path), element_image)

                # Compute visual hash using perceptual hashing
                visual_hash = self._compute_visual_hash(element_image)

                logger.debug(f"Captured screenshot for {element_id}: {screenshot_path}")
                return (str(screenshot_path), visual_hash, element_image)

            except Exception as e:
                logger.warning(f"Screenshot capture failed: {e}")
                return None

        try:
            future = asyncio.run_coroutine_threadsafe(capture(), self._loop)
            return future.result(timeout=5.0)  # 5 second timeout
        except Exception as e:
            logger.warning(f"Screenshot capture error: {e}")
            return None

    def _compute_visual_hash(self, image: np.ndarray) -> str:
        """Compute perceptual hash for visual similarity matching."""
        try:
            from PIL import Image
            import imagehash

            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # Compute perceptual hash
            phash = imagehash.phash(pil_image, hash_size=16)
            return str(phash)
        except Exception as e:
            logger.warning(f"Visual hash computation failed: {e}")
            return ""
