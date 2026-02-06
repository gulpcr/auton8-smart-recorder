from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from recorder.schema.workflow import Workflow, Step, Locator
from recorder.services.workflow_store import load_workflow

logger = logging.getLogger(__name__)

# Optional ML imports for healing
try:
    from recorder.ml.healing_engine import SelectorHealingEngine, HealingResult
    from recorder.ml.selector_engine import ElementFingerprint, SelectorStrategy, SelectorType
    HEALING_AVAILABLE = True
except ImportError:
    HEALING_AVAILABLE = False
    logger.debug("Healing engine not available")


@dataclass
class StepResult:
    """Result of a single step execution."""
    index: int
    step_id: str
    name: str
    step_type: str
    status: str  # "passed", "failed", "running", "pending", "skipped"
    duration_ms: int
    error: str
    locator_used: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stepIndex": self.index,
            "id": self.step_id,
            "name": self.name,
            "type": self.step_type,
            "status": self.status,
            "duration": self.duration_ms,
            "error": self.error,
            "locator": self.locator_used,
            "timestamp": self.timestamp,
        }


def locator_to_selector(loc: Locator) -> str:
    if loc.type == "data":
        return loc.value if loc.value.startswith("[") else f'[data-testid="{loc.value}"]'
    if loc.type == "aria":
        # Handle both raw aria labels and already-formatted selectors
        if loc.value.startswith("[aria-"):
            return loc.value
        return f'[aria-label="{loc.value}"]'
    if loc.type == "label":
        return f"label:has-text('{loc.value}')"
    if loc.type == "text":
        return f"text={loc.value}"
    if loc.type == "xpath":
        return f"xpath={loc.value}"
    if loc.type == "id":
        # Handle both raw IDs and CSS selector format (#id)
        if loc.value.startswith("#"):
            return loc.value
        return f"#{loc.value}"
    if loc.type == "name":
        # Handle both raw names and already-formatted selectors
        if loc.value.startswith("[name"):
            return loc.value
        return f'[name="{loc.value}"]'
    return loc.value


class ReplayLauncher:
    """Launches Playwright to replay a recorded workflow with AI healing."""

    def __init__(self, healing_engine=None):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._browser: Optional[Browser] = None
        self._running = False
        self._on_step: Optional[Callable[[int, str], None]] = None
        self._on_step_result: Optional[Callable[[StepResult], None]] = None
        self._on_complete: Optional[Callable[[bool, str, int], None]] = None
        self._on_workflow_loaded: Optional[Callable[[List[Step]], None]] = None
        self._healing_engine = healing_engine
        self._healing_enabled = healing_engine is not None and HEALING_AVAILABLE
        self._llm_engine = None  # Will be set from app_enhanced

    @property
    def is_running(self) -> bool:
        return self._running

    def _urls_match(self, url1: str, url2: str, strict: bool = False) -> bool:
        """Check if two URLs refer to the same page.

        Args:
            strict: If True, require exact path match. If False, only check domain.
        """
        if not url1 or not url2:
            return True  # If no URL info, assume match

        from urllib.parse import urlparse
        p1 = urlparse(url1)
        p2 = urlparse(url2)

        # Always require same domain
        if p1.netloc != p2.netloc:
            return False

        if strict:
            # Strict mode: same host and path
            return p1.path.rstrip('/') == p2.path.rstrip('/')
        else:
            # Lenient mode: same domain is enough
            return True

    def _is_different_page_context(self, step_url: str, current_url: str) -> bool:
        """Check if step is from a completely different page context (e.g., checkout vs homepage)."""
        if not step_url or not current_url:
            return False

        from urllib.parse import urlparse
        p1 = urlparse(step_url)
        p2 = urlparse(current_url)

        # Different domain = definitely different context
        if p1.netloc != p2.netloc:
            return True

        # Check for major path differences (different section of site)
        path1_parts = [p for p in p1.path.split('/') if p]
        path2_parts = [p for p in p2.path.split('/') if p]

        # Checkout vs non-checkout is a different context
        if ('checkout' in p1.path.lower()) != ('checkout' in p2.path.lower()):
            return True

        return False

    def set_healing_engine(self, healing_engine):
        """Set the healing engine for self-healing locators."""
        self._healing_engine = healing_engine
        self._healing_enabled = healing_engine is not None and HEALING_AVAILABLE
        if self._healing_enabled:
            logger.info("Healing engine enabled for replay")

    def set_llm_engine(self, llm_engine):
        """Set the LLM engine for AI-powered element finding."""
        self._llm_engine = llm_engine
        if llm_engine and llm_engine.available:
            logger.info("LLM engine enabled for AI healing")

    def set_callbacks(
        self,
        on_step: Callable[[int, str], None] = None,
        on_step_result: Callable[[StepResult], None] = None,
        on_complete: Callable[[bool, str, int], None] = None,
        on_workflow_loaded: Callable[[List[Step]], None] = None,
    ):
        self._on_step = on_step
        self._on_step_result = on_step_result
        self._on_complete = on_complete
        self._on_workflow_loaded = on_workflow_loaded

    async def _pick_locator(self, page: Page, locators: list[Locator]):
        # Filter out generic tag-only selectors (low specificity)
        specific_locators = [
            loc for loc in locators
            if loc.score > 0.5 or not loc.value.strip().isalpha()
        ]
        # Fallback to all if no specific ones
        candidates = specific_locators if specific_locators else locators

        for loc in sorted(candidates, key=lambda l: l.score, reverse=True):
            selector = locator_to_selector(loc)
            handle = page.locator(selector)
            try:
                count = await handle.count()
                if count > 0:
                    # Prefer visible elements
                    visible = handle.locator("visible=true")
                    if await visible.count() > 0:
                        return visible, loc, None  # No healing used
                    return handle, loc, None  # No healing used
            except Exception:
                continue
        return None, None, None

    async def _ai_find_element(self, page: Page, step: Step, original_locators: list[Locator]) -> tuple:
        """
        Use LLM to intelligently find an element when selectors fail.
        Returns (handle, locator, strategy) or (None, None, None).
        """
        if not self._llm_engine or not self._llm_engine.available:
            logger.debug("LLM not available for AI element finding")
            return None, None, None

        try:
            logger.info(f"Using AI to find element for step: {step.name} ({step.type})")

            # Get all interactive elements from page
            elements = await page.evaluate('''() => {
                const interactive = document.querySelectorAll(
                    'a, button, input, select, textarea, img[onclick], [role="button"], [onclick], [data-testid], .product-item, .menu-item'
                );
                return Array.from(interactive).slice(0, 50).map((el, idx) => {
                    const rect = el.getBoundingClientRect();
                    const text = (el.textContent || '').trim().substring(0, 100);
                    const alt = el.getAttribute('alt') || '';
                    const title = el.getAttribute('title') || '';
                    const href = el.getAttribute('href') || '';
                    const src = el.getAttribute('src') || '';
                    const classes = Array.from(el.classList).join(' ');

                    return {
                        index: idx,
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        classes: classes,
                        text: text,
                        alt: alt,
                        title: title,
                        href: href.substring(0, 100),
                        src: src.split('/').pop() || '',  // Just filename
                        ariaLabel: el.getAttribute('aria-label') || '',
                        visible: rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight,
                        x: Math.round(rect.x + rect.width/2),
                        y: Math.round(rect.y + rect.height/2)
                    };
                }).filter(el => el.visible);
            }''')

            if not elements:
                logger.warning("No interactive elements found on page")
                return None, None, None

            # Build description of what we're looking for
            original_selector = original_locators[0].value if original_locators else ""
            target_description = self._describe_target(step, original_selector)

            # Format elements for LLM
            elements_text = "\n".join([
                f"{e['index']}: <{e['tag']}> id='{e['id']}' class='{e['classes'][:50]}' text='{e['text'][:30]}' alt='{e['alt']}' href='{e['href'][:30]}'"
                for e in elements[:30]
            ])

            # Ask LLM to find the best match
            prompt = f"""Find the element that best matches this target:
Target: {target_description}

Page elements:
{elements_text}

Which element index (0-{len(elements)-1}) best matches the target?
Reply with ONLY a JSON object: {{"index": N, "confidence": 0.X, "reason": "brief reason"}}"""

            system = "You are an expert at finding web elements. Match elements by semantic meaning, not exact text. Reply ONLY with valid JSON."

            response = self._llm_engine.generate(prompt, system_prompt=system, format_json=True, max_tokens=100)

            if response:
                try:
                    import json
                    result = json.loads(response)
                    idx = result.get("index", -1)
                    confidence = result.get("confidence", 0)
                    reason = result.get("reason", "")

                    if 0 <= idx < len(elements) and confidence > 0.5:
                        element = elements[idx]
                        logger.info(f"AI found element {idx}: {element['tag']} '{element['text'][:30]}' (confidence: {confidence}, reason: {reason})")

                        # Build a selector for this element
                        if element['id']:
                            selector = f"#{element['id']}"
                        elif element['alt']:
                            selector = f"img[alt='{element['alt']}']"
                        elif element['ariaLabel']:
                            selector = f"[aria-label='{element['ariaLabel']}']"
                        elif element['text']:
                            selector = f"text={element['text'][:50]}"
                        else:
                            # Use coordinates
                            return (element['x'], element['y']), None, f"ai_coordinates"

                        handle = page.locator(selector)
                        if await handle.count() > 0:
                            loc = Locator(type="css", value=selector, score=confidence)
                            return handle, loc, f"ai_llm:{reason[:20]}"
                        else:
                            # Fall back to coordinates
                            logger.info(f"Selector failed, using coordinates ({element['x']}, {element['y']})")
                            return (element['x'], element['y']), None, "ai_coordinates"

                except json.JSONDecodeError:
                    logger.warning(f"LLM returned invalid JSON: {response[:100]}")

            return None, None, None

        except Exception as e:
            logger.error(f"AI element finding failed: {e}")
            return None, None, None

    def _describe_target(self, step: Step, selector: str) -> str:
        """Create a human-readable description of the target element."""
        parts = []

        # From step info
        if step.type:
            parts.append(f"Action: {step.type}")
        if step.name and step.name != step.type:
            parts.append(f"Name: {step.name}")

        # Parse selector for clues
        if 'menu' in selector.lower():
            parts.append("Type: menu item")
        if 'product' in selector.lower():
            parts.append("Type: product")
        if 'img' in selector.lower():
            parts.append("Type: image")
        if 'button' in selector.lower():
            parts.append("Type: button")
        if 'input' in selector.lower():
            parts.append("Type: input field")

        # Extract meaningful class names
        if 'colorwave' in selector.lower():
            parts.append("Related to: Colorwave")
        if 'thumb' in selector.lower():
            parts.append("Likely: thumbnail image")

        return "; ".join(parts) if parts else f"Element matching: {selector[:100]}"

    def _describe_target_for_menu(self, selector: str, expected_url: str = None) -> str:
        """Create a description for AI menu finding."""
        parts = []

        # Extract clues from selector
        if 'colorwave' in selector.lower():
            parts.append("Colorwave product/category")
        if 'printers' in selector.lower():
            parts.append("Printers section")
        if 'thumb' in selector.lower() or 'img' in selector.lower():
            parts.append("thumbnail/image")

        # Extract clues from URL
        if expected_url:
            url_path = expected_url.split('/')[-1].split('.')[0].replace('-', ' ')
            parts.append(f"links to: {url_path}")

        return "; ".join(parts) if parts else f"target element: {selector[:60]}"

    async def _ai_verify_navigation(self, page: Page, expected_url: str) -> bool:
        """Use AI to verify if we navigated to the expected page."""
        if not self._llm_engine or not self._llm_engine.available or not expected_url:
            return True  # Assume success if no AI available

        try:
            current_url = page.url
            page_title = await page.title()

            # Extract expected identifier from URL
            expected_path = expected_url.split('/')[-1].split('.')[0].replace('-', ' ')

            prompt = f"""Did this navigation succeed?
Expected destination: {expected_path}
Current URL: {current_url}
Page title: {page_title}

Reply ONLY with JSON: {{"success": true/false, "reason": "brief reason"}}"""

            response = self._llm_engine.generate(
                prompt,
                system_prompt="You verify web navigation. Reply ONLY with valid JSON.",
                format_json=True,
                max_tokens=50
            )

            if response:
                import json
                result = json.loads(response)
                success = result.get("success", True)
                reason = result.get("reason", "")
                if success:
                    logger.info(f"AI verified navigation: {reason}")
                else:
                    logger.warning(f"AI says navigation failed: {reason}")
                return success

        except Exception as e:
            logger.debug(f"AI verification failed: {e}")

        return True  # Assume success on error

    async def _attempt_healing(self, page: Page, step: Step, original_locators: list[Locator]) -> tuple:
        """
        Attempt AI-powered healing to find the element using alternative strategies.
        Returns (handle, locator_used, healing_strategy) or (None, None, None) if failed.
        """
        if not self._healing_enabled or not self._healing_engine:
            return None, None, None

        try:
            logger.info(f"Attempting AI healing for step: {step.name}")

            # Extract current page DOM elements for healing analysis
            page_elements = await self._extract_page_elements(page)
            page_state = {"elements": page_elements}

            # Build fingerprint from step's domContext if available
            dom_context = step.domContext or {}
            fingerprint = self._build_fingerprint_from_step(step, dom_context)

            # Convert locators to SelectorStrategy format
            selector_strategies = []
            for loc in original_locators:
                try:
                    strategy = SelectorStrategy(
                        type=SelectorType.CSS if loc.type in ["css", "id", "name"] else
                             SelectorType.XPATH_RELATIVE if "xpath" in loc.type else
                             SelectorType.TEXT if loc.type == "text" else
                             SelectorType.ARIA_LABEL if loc.type == "aria" else SelectorType.CSS,
                        value=loc.value,
                        score=loc.score
                    )
                    selector_strategies.append(strategy)
                except Exception:
                    continue

            # Call healing engine
            healing_result = self._healing_engine.heal_selector(
                original_fingerprint=fingerprint,
                selector_strategies=selector_strategies,
                current_page_state=page_state,
                screenshot=None  # Could add screenshot support later
            )

            if healing_result.success:
                logger.info(f"Healing succeeded using {healing_result.strategy.value} "
                           f"(confidence: {healing_result.confidence:.2f})")

                # Try to use the healed element
                if healing_result.fallback_selector:
                    selector = healing_result.fallback_selector
                    handle = page.locator(selector)
                    if await handle.count() > 0:
                        healed_loc = Locator(type="css", value=selector, score=healing_result.confidence)
                        return handle, healed_loc, healing_result.strategy.value

                # Position-based healing
                if healing_result.element_data and "position" in healing_result.element_data:
                    pos = healing_result.element_data["position"]
                    # Click at position
                    return pos, None, healing_result.strategy.value

                # Text fuzzy match - try text selector
                if healing_result.element_data and healing_result.element_data.get("textContent"):
                    text = healing_result.element_data["textContent"][:50]
                    selector = f"text={text}"
                    handle = page.locator(selector)
                    if await handle.count() > 0:
                        healed_loc = Locator(type="text", value=text, score=healing_result.confidence)
                        return handle, healed_loc, healing_result.strategy.value

            logger.warning(f"Basic healing failed for step: {step.name}, trying LLM AI...")

            # Try LLM-based AI finding as last resort
            ai_result = await self._ai_find_element(page, step, original_locators)
            if ai_result[0] is not None:
                return ai_result

            logger.warning(f"All healing strategies failed for step: {step.name}")
            return None, None, None

        except Exception as e:
            logger.error(f"Healing error: {e}")
            # Still try AI as fallback
            try:
                return await self._ai_find_element(page, step, original_locators)
            except:
                return None, None, None

    async def _extract_page_elements(self, page: Page) -> list:
        """Extract interactive elements from the page for healing analysis."""
        try:
            elements = await page.evaluate('''() => {
                const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [onclick], [data-testid]';
                const elements = document.querySelectorAll(interactiveSelectors);
                return Array.from(elements).slice(0, 200).map(el => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tagName: el.tagName.toLowerCase(),
                        id: el.id || null,
                        classes: Array.from(el.classList),
                        textContent: (el.textContent || '').trim().substring(0, 100),
                        ariaLabel: el.getAttribute('aria-label'),
                        attributes: {
                            'data-testid': el.getAttribute('data-testid'),
                            'name': el.getAttribute('name'),
                            'type': el.getAttribute('type'),
                            'href': el.getAttribute('href'),
                            'role': el.getAttribute('role')
                        },
                        boundingBox: [rect.x, rect.y, rect.width, rect.height],
                        isVisible: rect.width > 0 && rect.height > 0
                    };
                }).filter(el => el.isVisible);
            }''')
            return elements
        except Exception as e:
            logger.error(f"Failed to extract page elements: {e}")
            return []

    def _build_fingerprint_from_step(self, step: Step, dom_context: dict):
        """Build an ElementFingerprint from step data for healing."""
        if HEALING_AVAILABLE:
            return ElementFingerprint(
                tag_name=dom_context.get("tagName", ""),
                id=dom_context.get("id"),
                classes=dom_context.get("classes", []),
                attributes=dom_context.get("attributes", {}),
                text_content=dom_context.get("textContent"),
                aria_label=dom_context.get("ariaLabel"),
                bounding_box=tuple(dom_context.get("boundingBox", [0, 0, 0, 0]))
            )
        return None

    def _is_menu_selector(self, selector: str) -> bool:
        """Check if this selector targets a dropdown menu element."""
        menu_indicators = ['level0', 'menu-item', 'submenu', 'nav-', 'custommenu', 'ui-menu']
        selector_lower = selector.lower()
        return any(ind in selector_lower for ind in menu_indicators)

    async def _ai_find_clickable_element(self, page: Page, selector: str, step=None, search_context: str = None) -> tuple:
        """
        Use AI to find a clickable element when original selector fails.
        Handles: products, autocomplete suggestions, general links.
        """
        if not self._llm_engine or not self._llm_engine.available:
            return None

        try:
            # Determine what kind of element we're looking for
            is_product = 'product' in selector.lower()
            is_autocomplete = any(x in selector.lower() for x in ['autocomplete', 'suggest', 'dropdown', 'search', 'result', 'typeahead'])

            # For autocomplete/search suggestions
            if is_autocomplete or search_context:
                return await self._ai_find_autocomplete(page, search_context or "")

            # For products, scroll down to load more items
            if is_product:
                await page.evaluate("window.scrollTo(0, 500)")
                await asyncio.sleep(0.5)

            # Get clickable elements from page (different query for products vs general)
            query = '.product-item a, .product-photo a, .product-image-photo' if is_product else 'a, button, [onclick]'
            elements = await page.evaluate(f'''() => {{
                const els = document.querySelectorAll('{query}');
                return Array.from(els).slice(0, 30).map((el, idx) => {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 10 || rect.height < 10) return null;
                    const img = el.tagName === 'IMG' ? el : el.querySelector('img');
                    return {{
                        index: idx,
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 50),
                        href: el.href || '',
                        imgAlt: img ? (img.alt || '') : '',
                        imgSrc: img ? img.src.split('/').pop() : '',
                        x: Math.round(rect.x + rect.width/2),
                        y: Math.round(rect.y + rect.height/2),
                        visible: rect.width > 0 && rect.height > 0
                    }};
                }}).filter(el => el);
            }}''')

            if not elements:
                logger.warning("No clickable elements found on page")
                return None

            # Build context for LLM
            element_type = "product" if is_product else "link"
            elements_text = "\n".join([
                f"{e['index']}: text='{e['text'][:30]}' img='{e['imgAlt'] or e['imgSrc'][:20]}' href='{e['href'][-30:]}'"
                for e in elements[:20]
            ])

            prompt = f"""Find the best {element_type} to click.
Looking for: {'a product image/link' if is_product else 'a clickable element'}

Available elements:
{elements_text}

Pick the FIRST valid {element_type} (index 0-{len(elements)-1}).
Reply ONLY with JSON: {{"index": N, "reason": "brief reason"}}"""

            response = self._llm_engine.generate(
                prompt,
                system_prompt=f"You select web elements. For products, pick the first visible product. Reply ONLY with valid JSON.",
                format_json=True,
                max_tokens=60
            )

            if response:
                import json
                result = json.loads(response)
                idx = result.get("index", -1)
                reason = result.get("reason", "")

                if 0 <= idx < len(elements):
                    el = elements[idx]
                    logger.info(f"AI found element [{idx}]: {reason} at ({el['x']}, {el['y']})")
                    return (el['x'], el['y'])

        except Exception as e:
            logger.debug(f"AI element finding failed: {e}")

        return None

    async def _ai_find_autocomplete(self, page: Page, search_query: str) -> tuple:
        """
        Use AI to find autocomplete/search suggestions matching the search query.
        """
        try:
            logger.info(f"AI searching for autocomplete matching: '{search_query}'")

            # Get all visible suggestion-like elements
            elements = await page.evaluate('''() => {
                // Common autocomplete/suggestion selectors
                const selectors = [
                    '[role="option"]', '[role="listbox"] li', '.autocomplete-suggestion',
                    '.search-autocomplete li', '.ui-autocomplete li', '.dropdown-item',
                    '.suggestion', '.search-result', '.typeahead-result',
                    '[class*="suggest"] li', '[class*="autocomplete"] li',
                    '.predictive-search li', '.search-dropdown li', 'a[href*="search"]',
                    'ul li a', '.dropdown a'  // Fallback to general lists
                ];

                let elements = [];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        elements = Array.from(els);
                        break;
                    }
                }

                // If no suggestions found, try any visible clickable near top
                if (elements.length === 0) {
                    elements = Array.from(document.querySelectorAll('a, button, li'));
                }

                return elements.slice(0, 20).map((el, idx) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 10 || rect.height < 10 || rect.top < 0 || rect.top > 600) return null;
                    return {
                        index: idx,
                        text: (el.textContent || '').trim().substring(0, 100),
                        href: el.href || el.querySelector('a')?.href || '',
                        x: Math.round(rect.x + rect.width/2),
                        y: Math.round(rect.y + rect.height/2)
                    };
                }).filter(el => el && el.text);
            }''')

            if not elements:
                logger.warning("No autocomplete suggestions found")
                return None

            # Extract key term from search query
            search_lower = search_query.lower().replace('-', ' ').replace('_', ' ')
            search_terms = search_lower.split()
            key_terms = [t for t in search_terms if t not in ['ink', 'toner', 'it', 'the', 'a', 'an']]
            key_term = key_terms[-1] if key_terms else search_query

            # First: Try direct text match (faster than AI)
            for el in elements:
                el_text = el['text'].lower()
                el_href = el['href'].lower()
                if key_term in el_text or key_term in el_href:
                    logger.info(f"Direct match for '{key_term}' found: '{el['text'][:40]}' at ({el['x']}, {el['y']})")
                    return (el['x'], el['y'])

            # Fallback: Use AI
            elements_text = "\n".join([
                f"{e['index']}: '{e['text'][:60]}' href='{e['href'][-40:]}'"
                for e in elements
            ])

            # Extract key terms from search query (e.g., "ink-toner-brother" -> "brother")
            search_terms = search_query.lower().replace('-', ' ').replace('_', ' ').split()
            # Filter out generic terms
            key_terms = [t for t in search_terms if t not in ['ink', 'toner', 'it', 'the', 'a', 'an']]
            key_term = key_terms[-1] if key_terms else search_query  # Usually last word is most specific (brand/model)

            prompt = f"""Find the autocomplete suggestion containing "{key_term}".

Search: "{search_query}"
Key term to match: "{key_term}"

Suggestions:
{elements_text}

Pick the suggestion that contains "{key_term}" (index 0-{len(elements)-1}).
Reply ONLY with JSON: {{"index": N, "reason": "brief reason"}}"""

            response = self._llm_engine.generate(
                prompt,
                system_prompt=f"Find suggestion containing '{key_term}'. Reply ONLY with valid JSON.",
                format_json=True,
                max_tokens=60
            )

            if response:
                import json
                result = json.loads(response)
                idx = result.get("index", -1)
                reason = result.get("reason", "")

                if 0 <= idx < len(elements):
                    el = elements[idx]
                    logger.info(f"AI found autocomplete [{idx}]: '{el['text'][:40]}' - {reason} at ({el['x']}, {el['y']})")
                    return (el['x'], el['y'])

        except Exception as e:
            logger.debug(f"AI autocomplete finding failed: {e}")

        return None

    async def _click_with_hover_retry(self, page: Page, handle, selector: str, timeout: int = 5000, expected_url: str = None, step=None, search_context: str = None) -> bool:
        """
        Smart click with fallback strategies:
        1. Direct click
        2. For menus: hover reveal + click
        3. For products/search: AI element finding

        Args:
            expected_url: URL the click should navigate to (for verification)
            step: The Step object for AI context
            search_context: Recent search query for autocomplete matching
        """
        try:
            # First attempt: direct click
            await handle.first.wait_for(state="visible", timeout=timeout)
            await handle.first.scroll_into_view_if_needed()
            await handle.first.click(timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            # Element not visible/clickable - determine strategy
            is_menu = self._is_menu_selector(selector)

            if is_menu:
                # Strategy 2: Hover reveal for dropdown menus
                logger.info("Click failed, attempting to reveal element via hover...")
                position = await self._reveal_and_get_position(page, selector, expected_url)
            else:
                # Strategy 3: AI element finding for products/search/regular elements
                if search_context:
                    logger.info(f"Click failed, using AI to find autocomplete for: '{search_context}'")
                else:
                    logger.info("Click failed, using AI to find similar element...")
                position = await self._ai_find_clickable_element(page, selector, step, search_context)

            if position:
                x, y = position
                try:
                    # Try JavaScript click on the link element first (more reliable for dropdowns)
                    # This avoids timing issues where the dropdown closes before coordinate click
                    js_clicked = await page.evaluate(f'''() => {{
                        const el = document.elementFromPoint({x}, {y});
                        if (el) {{
                            const link = el.closest('a') || el;
                            if (link && link.click) {{
                                link.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}''')

                    if js_clicked:
                        logger.info(f"Click succeeded via JS at ({x}, {y}) after hover reveal")
                    else:
                        # Fallback to coordinate click
                        await page.mouse.click(x, y)
                        logger.info(f"Click succeeded via coordinates ({x}, {y}) after hover reveal")

                    await asyncio.sleep(0.5)  # Wait for any navigation
                    return True
                except Exception as e:
                    logger.warning(f"Coordinate click failed: {e}")

            return False

    async def _ai_find_menu_containing_target(self, page: Page, target_description: str, expected_url: str = None) -> int:
        """
        Use LLM to intelligently identify which menu contains the target element.
        Returns the menu index to hover, or -1 if unknown.
        """
        if not self._llm_engine or not self._llm_engine.available:
            return -1

        try:
            # Get all visible menu items with their text content
            menu_data = await page.evaluate('''() => {
                const menus = document.querySelectorAll('li.ui-menu-item.level0, .custommenu > ul > li, nav ul > li.level0');
                return Array.from(menus).slice(0, 15).map((el, idx) => {
                    const text = (el.textContent || '').replace(/\\s+/g, ' ').trim().substring(0, 200);
                    const links = Array.from(el.querySelectorAll('a')).map(a => ({
                        text: (a.textContent || '').trim().substring(0, 50),
                        href: a.href || ''
                    })).slice(0, 10);
                    return { index: idx, menuText: text.substring(0, 100), links: links };
                });
            }''')

            if not menu_data:
                return -1

            # Format for LLM
            menus_text = "\n".join([
                f"Menu {m['index']}: {m['menuText'][:80]}... Links: {[l['text'] for l in m['links'][:5]]}"
                for m in menu_data
            ])

            # Build target hint from expected URL
            url_hint = ""
            if expected_url:
                url_parts = expected_url.split('/')
                url_hint = f"\nTarget URL contains: {url_parts[-1].split('.')[0]}"

            prompt = f"""Which menu item (0-{len(menu_data)-1}) likely contains this target?
Target: {target_description}{url_hint}

Menus:
{menus_text}

Reply ONLY with JSON: {{"menu_index": N, "reason": "brief reason"}}"""

            response = self._llm_engine.generate(
                prompt,
                system_prompt="You analyze website menus. Reply ONLY with valid JSON.",
                format_json=True,
                max_tokens=80
            )

            if response:
                import json
                result = json.loads(response)
                idx = result.get("menu_index", -1)
                reason = result.get("reason", "")
                if 0 <= idx < len(menu_data):
                    logger.info(f"AI suggests menu [{idx}]: {reason}")
                    return idx

        except Exception as e:
            logger.debug(f"AI menu finding failed: {e}")

        return -1

    async def _reveal_and_get_position(self, page: Page, target_selector: str, expected_url: str = None) -> tuple:
        """
        Reveal a hidden element and return its center coordinates.
        Uses AI to intelligently find which menu to hover.
        """
        try:
            logger.info("Attempting to reveal hidden element by hovering parent menus...")

            # Extract the relative part of the selector (after the parent menu item)
            # e.g., "li.ui-menu-item.level0 > div.level0.submenu > ..." -> "div.level0.submenu > ..."
            parent_patterns = [
                'li.ui-menu-item.level0',
                'li.level0',
                'li.menu-item',
                'li.nav-item',
            ]

            extracted_parent = None
            relative_selector = None

            for pattern in parent_patterns:
                if pattern in target_selector:
                    idx = target_selector.find(pattern)
                    end_idx = idx + len(pattern)
                    rest = target_selector[end_idx:]

                    if rest.startswith(' > ') or rest.startswith('>'):
                        extracted_parent = target_selector[:end_idx]
                        # Extract relative path (everything after "li.level0 > ")
                        relative_selector = rest.lstrip(' >').strip()
                        logger.info(f"Extracted parent: {extracted_parent}")
                        logger.info(f"Relative target: {relative_selector[:80]}...")
                        break

            # Menu selectors to try (prefer extracted parent)
            menu_selectors = []
            if extracted_parent:
                menu_selectors.append(extracted_parent)

            menu_selectors.extend([
                'li.ui-menu-item.level0',
                '.custommenu > ul > li',
                'nav ul > li',
                '.navigation ul > li',
                '.menu > li',
            ])

            # AI-FIRST: Ask LLM which menu likely contains our target
            target_desc = self._describe_target_for_menu(target_selector, expected_url)
            ai_suggested_menu = await self._ai_find_menu_containing_target(page, target_desc, expected_url)

            for selector in menu_selectors:
                try:
                    menu_items = page.locator(selector)
                    count = await menu_items.count()
                    logger.debug(f"Trying menu selector '{selector}': {count} items found")

                    # Build iteration order - AI-suggested menu first
                    menu_order = list(range(min(count, 15)))
                    if ai_suggested_menu >= 0 and ai_suggested_menu < count:
                        menu_order.remove(ai_suggested_menu)
                        menu_order.insert(0, ai_suggested_menu)
                        logger.info(f"AI prioritizing menu [{ai_suggested_menu}] for: {target_desc[:50]}")

                    for i in menu_order:
                        try:
                            item = menu_items.nth(i)
                            if await item.is_visible():
                                # Hover and hold
                                await item.hover(timeout=2000)
                                await asyncio.sleep(0.5)  # Wait for submenu animation

                                # KEY FIX: Search for target WITHIN this specific menu item
                                # This ensures we don't find elements from other dropdowns
                                if relative_selector:
                                    # Scoped search within hovered menu item
                                    target = item.locator(relative_selector)
                                else:
                                    # Fallback to page-wide search
                                    target = page.locator(target_selector)

                                target_count = await target.count()
                                if target_count > 0:
                                    # Check all matching elements, not just first
                                    for t_idx in range(min(target_count, 5)):
                                        target_elem = target.nth(t_idx)
                                        try:
                                            await target_elem.wait_for(state="visible", timeout=300)
                                            bbox = await target_elem.bounding_box()
                                            if bbox and bbox['width'] > 0 and bbox['height'] > 0:
                                                x = bbox['x'] + bbox['width'] / 2
                                                y = bbox['y'] + bbox['height'] / 2

                                                # Sanity check: target should be in dropdown area
                                                if y <= 150:
                                                    logger.debug(f"Element at ({x:.0f}, {y:.0f}) too high, skipping")
                                                    continue

                                                # If expected URL provided, verify the link matches
                                                if expected_url:
                                                    href = await target_elem.evaluate('''el => {
                                                        // Check element's href or nearest ancestor link
                                                        if (el.href) return el.href;
                                                        const link = el.closest('a');
                                                        return link ? link.href : null;
                                                    }''')
                                                    if href:
                                                        # Check if href matches expected URL
                                                        expected_path = expected_url.split('/')[-1].split('.')[0]
                                                        if expected_path.lower() in href.lower():
                                                            logger.info(f"Target confirmed: href contains '{expected_path}'")
                                                            logger.info(f"Target at ({x:.0f}, {y:.0f}) after hovering menu [{i}]")
                                                            return (x, y)
                                                        else:
                                                            logger.debug(f"href '{href[:50]}' doesn't match expected '{expected_path}'")
                                                            continue
                                                else:
                                                    # No URL verification needed
                                                    logger.info(f"Target revealed at ({x:.0f}, {y:.0f}) after hovering menu item [{i}]")
                                                    return (x, y)
                                        except Exception:
                                            pass  # Target not visible yet
                        except Exception as e:
                            logger.debug(f"Hover attempt on item {i} failed: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue

            # Strategy 2: Try simpler relative selector (last 3 parts)
            if ' > ' in target_selector:
                parts = target_selector.split(' > ')
                if len(parts) > 3:
                    simple_target = ' > '.join(parts[-3:])
                    logger.info(f"Trying simplified target: {simple_target}")

                    for selector in menu_selectors[:3]:
                        try:
                            menu_items = page.locator(selector)
                            count = await menu_items.count()

                            for i in range(min(count, 10)):
                                try:
                                    item = menu_items.nth(i)
                                    if await item.is_visible():
                                        await item.hover(timeout=2000)
                                        await asyncio.sleep(0.5)

                                        # Scoped search within hovered item
                                        target = item.locator(simple_target)
                                        if await target.count() > 0:
                                            target_elem = target.first
                                            try:
                                                await target_elem.wait_for(state="visible", timeout=500)
                                                bbox = await target_elem.bounding_box()
                                                if bbox and bbox['width'] > 0 and bbox['height'] > 0:
                                                    x = bbox['x'] + bbox['width'] / 2
                                                    y = bbox['y'] + bbox['height'] / 2
                                                    if y > 150:  # Sanity check
                                                        logger.info(f"Target revealed with simple selector at ({x:.0f}, {y:.0f})")
                                                        return (x, y)
                                            except Exception:
                                                pass
                                except Exception:
                                    continue
                        except Exception:
                            continue

            logger.warning("Could not reveal hidden element after all strategies")
            return None

        except Exception as e:
            logger.error(f"Error in reveal_and_get_position: {e}")
            return None

    async def _run_step(self, page: Page, step: Step, index: int, expected_nav_url: str = None, search_context: str = None) -> StepResult:
        """Run a single step. Returns StepResult with timing and status.

        Args:
            expected_nav_url: For click steps, the URL we expect to navigate to.
            search_context: Recent search query for autocomplete matching.
        """
        start_time = time.perf_counter()
        timestamp = time.strftime("%H:%M:%S")
        locator_used = ""

        # Notify step starting
        if self._on_step:
            self._on_step(index, step.type)

        # Emit running status
        if self._on_step_result:
            running_result = StepResult(
                index=index,
                step_id=step.id,
                name=step.name,
                step_type=step.type,
                status="running",
                duration_ms=0,
                error="",
                locator_used="",
                timestamp=timestamp
            )
            self._on_step_result(running_result)

        try:
            # Early skip for input steps with no value (phantom events)
            if step.type in ["input", "change", "type"]:
                value = step.input.get("value", "") if step.input else ""
                if not value:
                    logger.info(f"Step {index + 1}: Skipping input with no value (phantom event)")
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    return StepResult(
                        index=index,
                        step_id=step.id,
                        name=step.name,
                        step_type=step.type,
                        status="skipped",
                        duration_ms=duration_ms,
                        error="Skipped: input step with no value",
                        locator_used="",
                        timestamp=timestamp
                    )

            locators = step.target.locators if step.target else []

            if not locators:
                error = f"No locators defined for this element"
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.warning(f"Step {index + 1} ({step.type}): {error}")
                return StepResult(
                    index=index,
                    step_id=step.id,
                    name=step.name,
                    step_type=step.type,
                    status="failed",
                    duration_ms=duration_ms,
                    error=error,
                    locator_used="",
                    timestamp=timestamp
                )

            handle, used_locator, healing_strategy = await self._pick_locator(page, locators)
            locator_used = used_locator.value[:80] if used_locator else ""

            if not handle:
                # Try AI healing before giving up
                logger.info(f"Step {index + 1}: Primary locators failed, attempting AI healing...")
                handle, healed_locator, healing_strategy = await self._attempt_healing(page, step, locators)

                if handle and healed_locator:
                    used_locator = healed_locator
                    locator_used = f"[HEALED:{healing_strategy}] {healed_locator.value[:60]}"
                    logger.info(f"Step {index + 1}: Healed using {healing_strategy}")
                elif handle and isinstance(handle, tuple):
                    # Position-based click
                    locator_used = f"[HEALED:position] ({handle[0]}, {handle[1]})"
                    logger.info(f"Step {index + 1}: Using position-based healing")
                else:
                    # Build detailed error about tried locators
                    tried = [f"{l.type}={l.value[:40]}..." if len(l.value) > 40 else f"{l.type}={l.value}" for l in locators[:3]]
                    error = f"Element not found (AI healing also failed). Tried: {', '.join(tried)}"
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    logger.warning(f"Step {index + 1} ({step.type}): {error}")
                    return StepResult(
                        index=index,
                        step_id=step.id,
                        name=step.name,
                        step_type=step.type,
                        status="failed",
                        duration_ms=duration_ms,
                        error=error,
                        locator_used=locator_used,
                        timestamp=timestamp
                    )

            # Handle position-based healing (click at coordinates)
            if isinstance(handle, tuple) and len(handle) == 2:
                x, y = handle
                if step.type in ["click", "dblclick"]:
                    await page.mouse.click(x, y)
                elif step.type == "contextmenu":
                    await page.mouse.click(x, y, button="right")
                elif step.type == "hover":
                    await page.mouse.move(x, y)
            elif step.type in ["click", "dblclick"]:
                # Use smart click with AI-powered fallback
                selector = locator_to_selector(used_locator) if used_locator else ""
                click_success = await self._click_with_hover_retry(page, handle, selector, expected_url=expected_nav_url, step=step, search_context=search_context)
                if not click_success:
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    error = "Element not clickable (AI also failed)"
                    return StepResult(
                        index=index,
                        step_id=step.id,
                        name=step.name,
                        step_type=step.type,
                        status="failed",
                        duration_ms=duration_ms,
                        error=error,
                        locator_used=locator_used,
                        timestamp=timestamp
                    )
            elif step.type == "contextmenu":
                await handle.first.click(button="right", timeout=5000)
            elif step.type == "hover":
                await handle.first.hover(timeout=5000)
            elif step.type in ["input", "change", "type"]:
                value = step.input.get("value", "") if step.input else ""
                # Note: Empty value check happens at start of _run_step

                # Check if this is a select element - use select_option instead of fill
                tag_name = await handle.first.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "select":
                    await handle.first.select_option(value=value, timeout=5000)
                else:
                    await handle.first.fill(value, timeout=5000)
            elif step.type == "keydown" or step.type == "press":
                keys = (step.input.get("key", "") or step.input.get("keys", "") or step.input.get("value", "")) if step.input else ""
                if keys:
                    await handle.first.press(keys, timeout=5000)
            elif step.type == "scroll":
                await handle.first.scroll_into_view_if_needed(timeout=5000)

            await asyncio.sleep(0.3)  # Small delay between steps

            # Check if URL changed (navigation occurred) - wait for page to load
            if step.type in ["click", "dblclick"]:
                nav_verified = False
                try:
                    if expected_nav_url:
                        # We expect navigation to a different page - wait for URL change
                        nav_pattern = expected_nav_url.split("/")[-1].split(".")[0]  # e.g., "colorwave"
                        logger.info(f"Step {index + 1}: Waiting for navigation to '{nav_pattern}'...")
                        await page.wait_for_url(f"**{nav_pattern}**", timeout=10000)
                        logger.info(f"Step {index + 1}: Navigated to {page.url[:60]}...")
                        nav_verified = True
                    else:
                        # No expected navigation, just wait for page stability
                        await asyncio.sleep(0.5)
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    logger.info(f"Step {index + 1}: Page load completed after click")
                except Exception as nav_err:
                    logger.warning(f"Step {index + 1}: Navigation wait failed: {nav_err}")

                # AI verification if navigation didn't confirm via URL
                if expected_nav_url and not nav_verified:
                    ai_ok = await self._ai_verify_navigation(page, expected_nav_url)
                    if not ai_ok:
                        logger.warning(f"Step {index + 1}: AI says navigation failed")
                        # Continue anyway - maybe partially successful

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"Step {index + 1} ({step.type}) completed in {duration_ms}ms")

            return StepResult(
                index=index,
                step_id=step.id,
                name=step.name,
                step_type=step.type,
                status="passed",
                duration_ms=duration_ms,
                error="",
                locator_used=locator_used,
                timestamp=timestamp
            )

        except PlaywrightTimeoutError as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            error = f"Timeout - element not responsive within 5s"
            logger.error(f"Step {index + 1} ({step.type}): {error}")
            return StepResult(
                index=index,
                step_id=step.id,
                name=step.name,
                step_type=step.type,
                status="failed",
                duration_ms=duration_ms,
                error=error,
                locator_used=locator_used,
                timestamp=timestamp
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            error = str(exc)
            logger.error(f"Step {index + 1} ({step.type}): {error}")
            return StepResult(
                index=index,
                step_id=step.id,
                name=step.name,
                step_type=step.type,
                status="failed",
                duration_ms=duration_ms,
                error=error,
                locator_used=locator_used,
                timestamp=timestamp
            )

    async def _replay(self, workflow: Workflow):
        self._running = True
        success = True
        error_msg = ""
        total_duration_ms = 0
        replay_start = time.perf_counter()

        # Notify workflow loaded (for pre-populating UI)
        if self._on_workflow_loaded:
            self._on_workflow_loaded(workflow.steps)

        pw = None
        try:
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(headless=False)
            page = await self._browser.new_page()

            # Navigate to base URL or first step's URL
            base_url = workflow.meta.get("baseUrl") if workflow.meta else None
            if not base_url and workflow.metadata:
                base_url = workflow.metadata.get("baseUrl")
            if not base_url and workflow.steps and workflow.steps[0].page:
                base_url = workflow.steps[0].page.get("url")

            if base_url:
                logger.info("Navigating to %s", base_url)
                try:
                    nav_start = time.perf_counter()
                    await page.goto(base_url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(1)  # Wait for page to stabilize
                    nav_duration = int((time.perf_counter() - nav_start) * 1000)
                    logger.info(f"Page loaded in {nav_duration}ms")
                except PlaywrightTimeoutError:
                    error_msg = f"Page load timeout: {base_url} took more than 60 seconds"
                    logger.error(error_msg)
                    total_duration_ms = int((time.perf_counter() - replay_start) * 1000)
                    if self._on_complete:
                        self._on_complete(False, error_msg, total_duration_ms)
                    return
            else:
                logger.error("No base URL found in workflow")
                if self._on_complete:
                    self._on_complete(False, "No base URL found", 0)
                return

            # Run each step with smart URL-aware handling
            last_page_url = page.url
            consecutive_failures = 0
            max_consecutive_failures = 5  # More tolerant - try to complete workflow
            last_search_input = ""  # Track search queries for autocomplete

            for i, step in enumerate(workflow.steps):
                current_url = page.url

                # Check if step's URL is from a completely different context (e.g., checkout)
                step_url = step.page.get("url", "") if step.page else ""
                different_context = self._is_different_page_context(step_url, current_url)

                # Only skip if truly different context (e.g., checkout steps when not in checkout)
                if different_context:
                    logger.info(f"Step {i + 1}: Different page context - step expects {step_url[:50]}..., current is {current_url[:50]}...")
                    logger.info(f"Step {i + 1} skipped - different page context")

                    if self._on_step_result:
                        skip_result = StepResult(
                            index=i,
                            step_id=step.id,
                            name=step.name,
                            step_type=step.type,
                            status="skipped",
                            duration_ms=0,
                            error="Skipped: different page context",
                            locator_used="",
                            timestamp=time.strftime("%H:%M:%S")
                        )
                        self._on_step_result(skip_result)
                    continue  # Skip to next step

                # For click steps, determine expected navigation URL by looking ahead
                expected_nav_url = None
                if step.type in ["click", "dblclick"]:
                    step_url = step.page.get("url", "") if step.page else ""
                    for future_step in workflow.steps[i + 1:]:
                        future_url = future_step.page.get("url", "") if future_step.page else ""
                        if future_url and not self._urls_match(step_url, future_url):
                            expected_nav_url = future_url
                            logger.debug(f"Expected navigation: {expected_nav_url[:60]}...")
                            break

                # Pass search context to click steps (for autocomplete)
                result = await self._run_step(page, step, i, expected_nav_url=expected_nav_url, search_context=last_search_input)

                # Track input values for search context
                if step.type in ["input", "change", "type"] and result.status == "passed":
                    input_val = step.input.get("value", "") if step.input else ""
                    if input_val:
                        last_search_input = input_val
                        logger.debug(f"Search context updated: '{input_val}'")

                # Emit step result
                if self._on_step_result:
                    self._on_step_result(result)

                total_duration_ms += result.duration_ms

                if result.status == "failed":
                    consecutive_failures += 1

                    # Too many consecutive failures - stop
                    if consecutive_failures >= max_consecutive_failures:
                        success = False
                        error_msg = result.error

                        # Mark remaining steps as skipped
                        for j in range(i + 1, len(workflow.steps)):
                            skipped_step = workflow.steps[j]
                            if self._on_step_result:
                                skipped_result = StepResult(
                                    index=j,
                                    step_id=skipped_step.id,
                                    name=skipped_step.name,
                                    step_type=skipped_step.type,
                                    status="skipped",
                                    duration_ms=0,
                                    error="Skipped due to previous failures",
                                    locator_used="",
                                    timestamp=time.strftime("%H:%M:%S")
                                )
                                self._on_step_result(skipped_result)
                        break
                else:
                    consecutive_failures = 0  # Reset on success
                    last_page_url = page.url  # Track URL changes

            # Keep browser open briefly to see result
            await asyncio.sleep(2)

        except Exception as exc:
            logger.exception("Replay failed: %s", exc)
            success = False
            error_msg = str(exc)
        finally:
            self._running = False
            total_duration_ms = int((time.perf_counter() - replay_start) * 1000)
            if self._browser:
                await self._browser.close()
            if pw:
                await pw.stop()
            if self._on_complete:
                self._on_complete(success, error_msg, total_duration_ms)

    def replay(self, workflow_path: str):
        if self._running:
            logger.warning("Replay already running")
            return

        # Load workflow
        import json
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workflow = Workflow(**data)
        except Exception as exc:
            logger.error("Failed to load workflow: %s", exc)
            if self._on_complete:
                self._on_complete(False, f"Failed to load: {exc}", 0)
            return

        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._replay(workflow))

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        logger.info("Replay started for %s", workflow_path)

    def stop(self):
        if self._loop and self._running:
            async def close():
                if self._browser:
                    await self._browser.close()
            asyncio.run_coroutine_threadsafe(close(), self._loop)
