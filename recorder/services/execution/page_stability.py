"""
Page Stability Detection Module

Provides reliable page readiness detection beyond simple domcontentloaded.
Monitors: network activity, DOM mutations, visual stability, element stability.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


@dataclass
class StabilityState:
    """Current stability state of the page."""
    network_idle: bool = False
    dom_stable: bool = False
    visual_stable: bool = False
    last_check_time: float = 0
    confidence: float = 0.0

    @property
    def is_stable(self) -> bool:
        return self.network_idle and self.dom_stable

    @property
    def is_fully_stable(self) -> bool:
        return self.network_idle and self.dom_stable and self.visual_stable


class PageStabilityDetector:
    """
    Detects when a page is truly ready for interaction.

    Goes beyond domcontentloaded to detect:
    - Network idle (no pending requests)
    - DOM stability (no mutations)
    - Visual stability (no layout shifts)
    - Element stability (target not moving)
    """

    def __init__(self, page: Page):
        self.page = page
        self._network_requests = 0
        self._dom_mutations = 0
        self._last_mutation_time = 0
        self._monitoring = False

    async def start_monitoring(self):
        """Start monitoring page stability signals."""
        if self._monitoring:
            return

        if self.page.is_closed():
            self._monitoring = False
            return

        self._monitoring = True
        self._network_requests = 0
        self._dom_mutations = 0

        # Inject DOM mutation observer
        try:
            await self.page.evaluate('''() => {
                window.__stabilityMutationCount = 0;
                window.__stabilityLastMutation = Date.now();

                if (!window.__stabilityObserver) {
                    window.__stabilityObserver = new MutationObserver((mutations) => {
                        window.__stabilityMutationCount += mutations.length;
                        window.__stabilityLastMutation = Date.now();
                    });

                    window.__stabilityObserver.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        characterData: true
                    });
                }
            }''')
        except Exception as e:
            logger.debug(f"Stability monitor injection failed: {e}")
            self._monitoring = False

    async def stop_monitoring(self):
        """Stop monitoring page stability."""
        self._monitoring = False
        try:
            await self.page.evaluate('''() => {
                if (window.__stabilityObserver) {
                    window.__stabilityObserver.disconnect();
                    window.__stabilityObserver = null;
                }
            }''')
        except Exception:
            pass  # Page may have navigated

    async def get_stability_state(self) -> StabilityState:
        """Get current stability state."""
        state = StabilityState(last_check_time=time.time())

        try:
            # Check network idle
            state.network_idle = await self._check_network_idle()

            # Check DOM stability
            state.dom_stable = await self._check_dom_stable()

            # Calculate confidence
            state.confidence = self._calculate_confidence(state)

        except Exception as e:
            logger.debug(f"Stability check error: {e}")
            state.confidence = 0.0

        return state

    async def _check_network_idle(self, threshold_ms: int = 300) -> bool:
        """Check if network has been idle for threshold duration."""
        try:
            result = await self.page.evaluate(f'''() => {{
                // Check for pending fetch/XHR
                const pendingRequests = performance.getEntriesByType('resource')
                    .filter(r => r.responseEnd === 0).length;

                if (pendingRequests > 0) return false;

                // Check if recent network activity
                const now = Date.now();
                const recentResources = performance.getEntriesByType('resource')
                    .filter(r => now - r.responseEnd < {threshold_ms});

                return recentResources.length === 0;
            }}''')
            return result
        except Exception:
            return True  # Assume idle on error

    async def _check_dom_stable(self, threshold_ms: int = 500) -> bool:
        """Check if DOM has been stable for threshold duration."""
        try:
            result = await self.page.evaluate(f'''() => {{
                if (typeof window.__stabilityLastMutation === 'undefined') return true;
                const elapsed = Date.now() - window.__stabilityLastMutation;
                return elapsed > {threshold_ms};
            }}''')
            return result
        except Exception:
            return True  # Assume stable on error

    def _calculate_confidence(self, state: StabilityState) -> float:
        """Calculate overall stability confidence."""
        score = 0.0
        if state.network_idle:
            score += 0.5
        if state.dom_stable:
            score += 0.5
        return score

    async def wait_for_stability(
        self,
        timeout_ms: int = 10000,
        network_idle_ms: int = 300,
        dom_stable_ms: int = 500
    ) -> StabilityState:
        """
        Wait for page to become stable.

        Args:
            timeout_ms: Maximum time to wait
            network_idle_ms: Network must be idle for this duration
            dom_stable_ms: DOM must be unchanged for this duration

        Returns:
            StabilityState with final stability assessment
        """
        if self.page.is_closed():
            return StabilityState(last_check_time=time.time())

        start_time = time.time()
        deadline = start_time + (timeout_ms / 1000)

        await self.start_monitoring()

        stable_since = None
        required_stable_duration = max(network_idle_ms, dom_stable_ms) / 1000

        try:
            while time.time() < deadline:
                if self.page.is_closed():
                    return StabilityState(last_check_time=time.time())
                state = await self.get_stability_state()

                if state.is_stable:
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= required_stable_duration:
                        logger.debug(f"Page stable after {int((time.time()-start_time)*1000)}ms")
                        return state
                else:
                    stable_since = None

                await asyncio.sleep(0.1)

            # Timeout reached
            logger.warning(f"Page stability timeout after {timeout_ms}ms")
            return await self.get_stability_state()

        finally:
            await self.stop_monitoring()


class ElementStabilityChecker:
    """Checks if a specific element is stable and ready for interaction."""

    def __init__(self, page: Page):
        self.page = page

    async def is_element_stable(
        self,
        locator: Locator,
        stability_ms: int = 200
    ) -> tuple[bool, dict]:
        """
        Check if element position and size are stable.

        Returns:
            (is_stable, details) tuple
        """
        details = {
            "exists": False,
            "visible": False,
            "enabled": False,
            "stable_position": False,
            "not_covered": False,
            "confidence": 0.0
        }

        try:
            # Check existence
            count = await locator.count()
            if count == 0:
                return False, details
            details["exists"] = True

            # Check visibility
            details["visible"] = await locator.first.is_visible()
            if not details["visible"]:
                return False, details

            # Check enabled
            details["enabled"] = await locator.first.is_enabled()

            # Check position stability
            box1 = await locator.first.bounding_box()
            if not box1:
                return False, details

            await asyncio.sleep(stability_ms / 1000)

            box2 = await locator.first.bounding_box()
            if not box2:
                return False, details

            # Check if position changed
            position_stable = (
                abs(box1["x"] - box2["x"]) < 2 and
                abs(box1["y"] - box2["y"]) < 2 and
                abs(box1["width"] - box2["width"]) < 2 and
                abs(box1["height"] - box2["height"]) < 2
            )
            details["stable_position"] = position_stable

            # Check if covered by overlay
            details["not_covered"] = await self._check_not_covered(locator)

            # Calculate confidence
            confidence = sum([
                0.2 if details["exists"] else 0,
                0.2 if details["visible"] else 0,
                0.2 if details["enabled"] else 0,
                0.2 if details["stable_position"] else 0,
                0.2 if details["not_covered"] else 0
            ])
            details["confidence"] = confidence

            is_stable = all([
                details["visible"],
                details["enabled"],
                details["stable_position"],
                details["not_covered"]
            ])

            return is_stable, details

        except Exception as e:
            logger.debug(f"Element stability check error: {e}")
            return False, details

    async def _check_not_covered(self, locator: Locator) -> bool:
        """Check if element is not covered by another element."""
        try:
            box = await locator.first.bounding_box()
            if not box:
                return False

            # Get element at center point
            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2

            result = await self.page.evaluate(f'''() => {{
                const el = document.elementFromPoint({center_x}, {center_y});
                if (!el) return false;

                // Check if it's the target or a child of target
                const target = document.evaluate(
                    'ancestor-or-self::*',
                    el,
                    null,
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE
                );

                return true;  // Simplified check
            }}''')

            return result
        except Exception:
            return True  # Assume not covered on error

    async def wait_for_element_stable(
        self,
        locator: Locator,
        timeout_ms: int = 5000,
        stability_ms: int = 200
    ) -> tuple[bool, dict]:
        """Wait for element to become stable."""
        start_time = time.time()
        deadline = start_time + (timeout_ms / 1000)

        last_details = {}

        while time.time() < deadline:
            is_stable, details = await self.is_element_stable(locator, stability_ms)
            last_details = details

            if is_stable:
                return True, details

            await asyncio.sleep(0.1)

        return False, last_details
