"""
Frame, IFrame, and Window Handler

Handles:
- Switching between frames and iframes
- New window/tab handling
- Popup detection and handling
- Alert/confirm/prompt dialogs
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, List, Callable, Any, Dict
from dataclasses import dataclass
from urllib.parse import urlparse

from playwright.async_api import Page, Frame, BrowserContext, Dialog

logger = logging.getLogger(__name__)


@dataclass
class FrameInfo:
    """Information about a frame."""
    name: str
    url: str
    frame: Frame
    parent_frame: Optional[Frame]
    depth: int
    selector: Optional[str]  # Selector used to find the iframe element


@dataclass
class WindowInfo:
    """Information about a browser window/tab."""
    page: Page
    url: str
    title: str
    is_popup: bool
    opener_url: Optional[str]


class FrameHandler:
    """
    Handles frame/iframe navigation and switching.
    """

    def __init__(self, page: Page):
        self._page = page
        self._current_frame: Frame = page.main_frame
        self._frame_stack: List[Frame] = []

    def set_page(self, page: Page):
        """Update the page reference."""
        self._page = page
        self._current_frame = page.main_frame
        self._frame_stack.clear()

    @property
    def current_frame(self) -> Frame:
        """Get the current active frame."""
        return self._current_frame

    async def switch_to_frame(self, selector: str) -> bool:
        """
        Switch to a frame by selector.

        Args:
            selector: CSS selector for the iframe element

        Returns:
            True if switch successful
        """
        try:
            # Find the iframe element
            iframe_element = self._current_frame.locator(selector).first

            # Get the frame from the element
            frame = await iframe_element.content_frame()
            if frame:
                self._frame_stack.append(self._current_frame)
                self._current_frame = frame
                logger.info(f"Switched to frame: {selector}")
                return True
            else:
                logger.warning(f"Could not get content frame for: {selector}")
                return False

        except Exception as e:
            logger.error(f"Failed to switch to frame {selector}: {e}")
            return False

    async def switch_to_frame_by_name(self, name: str) -> bool:
        """
        Switch to a frame by name or id.

        Args:
            name: Frame name or id attribute

        Returns:
            True if switch successful
        """
        try:
            frame = self._page.frame(name=name)
            if frame:
                self._frame_stack.append(self._current_frame)
                self._current_frame = frame
                logger.info(f"Switched to frame by name: {name}")
                return True

            # Try by id
            return await self.switch_to_frame(f"iframe#{name}, frame#{name}, iframe[name='{name}'], frame[name='{name}']")

        except Exception as e:
            logger.error(f"Failed to switch to frame {name}: {e}")
            return False

    async def switch_to_frame_by_index(self, index: int) -> bool:
        """
        Switch to a frame by index.

        Args:
            index: Zero-based frame index

        Returns:
            True if switch successful
        """
        try:
            frames = self._current_frame.child_frames
            if 0 <= index < len(frames):
                self._frame_stack.append(self._current_frame)
                self._current_frame = frames[index]
                logger.info(f"Switched to frame by index: {index}")
                return True
            else:
                logger.warning(f"Frame index {index} out of range (0-{len(frames)-1})")
                return False

        except Exception as e:
            logger.error(f"Failed to switch to frame index {index}: {e}")
            return False

    async def switch_to_frame_by_url(self, url_pattern: str) -> bool:
        """
        Switch to a frame by URL pattern.

        Args:
            url_pattern: URL substring or pattern to match

        Returns:
            True if switch successful
        """
        try:
            for frame in self._page.frames:
                if url_pattern in frame.url:
                    self._frame_stack.append(self._current_frame)
                    self._current_frame = frame
                    logger.info(f"Switched to frame by URL: {frame.url}")
                    return True

            logger.warning(f"No frame found matching URL: {url_pattern}")
            return False

        except Exception as e:
            logger.error(f"Failed to switch to frame by URL {url_pattern}: {e}")
            return False

    def switch_to_parent_frame(self) -> bool:
        """
        Switch to the parent frame.

        Returns:
            True if switch successful
        """
        try:
            if self._frame_stack:
                self._current_frame = self._frame_stack.pop()
                logger.info("Switched to parent frame")
                return True
            elif self._current_frame.parent_frame:
                self._current_frame = self._current_frame.parent_frame
                logger.info("Switched to parent frame (no stack)")
                return True
            else:
                logger.debug("Already at main frame")
                return True

        except Exception as e:
            logger.error(f"Failed to switch to parent frame: {e}")
            return False

    def switch_to_main_frame(self) -> bool:
        """
        Switch to the main/top frame.

        Returns:
            True if switch successful
        """
        try:
            self._current_frame = self._page.main_frame
            self._frame_stack.clear()
            logger.info("Switched to main frame")
            return True

        except Exception as e:
            logger.error(f"Failed to switch to main frame: {e}")
            return False

    async def get_all_frames(self) -> List[FrameInfo]:
        """Get information about all frames in the page."""
        frames = []

        def collect_frames(frame: Frame, depth: int = 0):
            info = FrameInfo(
                name=frame.name or f"frame_{len(frames)}",
                url=frame.url,
                frame=frame,
                parent_frame=frame.parent_frame,
                depth=depth,
                selector=None
            )
            frames.append(info)

            for child in frame.child_frames:
                collect_frames(child, depth + 1)

        collect_frames(self._page.main_frame)
        return frames

    async def wait_for_frame(self, selector: str, timeout: int = 30000) -> bool:
        """
        Wait for a frame to appear and switch to it.

        Args:
            selector: CSS selector for the iframe
            timeout: Timeout in milliseconds

        Returns:
            True if frame found and switched
        """
        try:
            await self._current_frame.wait_for_selector(selector, timeout=timeout)
            return await self.switch_to_frame(selector)
        except Exception as e:
            logger.error(f"Timeout waiting for frame {selector}: {e}")
            return False


class WindowHandler:
    """
    Handles multiple windows/tabs and popups.
    """

    def __init__(self, context: BrowserContext, page: Page):
        self._context = context
        self._page = page
        self._windows: Dict[str, WindowInfo] = {}
        self._popup_callback: Optional[Callable] = None
        self._setup_listeners()

    def _setup_listeners(self):
        """Setup event listeners for new windows/popups."""
        self._context.on("page", self._on_new_page)

    async def _on_new_page(self, page: Page):
        """Handle new page/popup event."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)

            info = WindowInfo(
                page=page,
                url=page.url,
                title=await page.title(),
                is_popup=True,
                opener_url=self._page.url if self._page else None
            )

            window_id = f"window_{len(self._windows)}"
            self._windows[window_id] = info

            logger.info(f"New window detected: {info.url}")

            if self._popup_callback:
                await self._popup_callback(page, info)

        except Exception as e:
            logger.warning(f"Error handling new page: {e}")

    def set_popup_callback(self, callback: Callable):
        """Set callback for popup handling."""
        self._popup_callback = callback

    @property
    def current_page(self) -> Page:
        """Get the current active page."""
        return self._page

    def set_page(self, page: Page):
        """Set the current page."""
        self._page = page

    async def switch_to_window(self, identifier: str) -> bool:
        """
        Switch to a window by identifier.

        Args:
            identifier: Window handle, URL pattern, or title pattern

        Returns:
            True if switch successful
        """
        try:
            # Try by stored window ID
            if identifier in self._windows:
                self._page = self._windows[identifier].page
                await self._page.bring_to_front()
                logger.info(f"Switched to window: {identifier}")
                return True

            # Try by URL pattern
            for page in self._context.pages:
                if identifier in page.url:
                    self._page = page
                    await self._page.bring_to_front()
                    logger.info(f"Switched to window by URL: {page.url}")
                    return True

            # Try by title pattern
            for page in self._context.pages:
                title = await page.title()
                if identifier in title:
                    self._page = page
                    await self._page.bring_to_front()
                    logger.info(f"Switched to window by title: {title}")
                    return True

            logger.warning(f"No window found matching: {identifier}")
            return False

        except Exception as e:
            logger.error(f"Failed to switch to window {identifier}: {e}")
            return False

    async def switch_to_window_by_index(self, index: int) -> bool:
        """
        Switch to a window by index.

        Args:
            index: Zero-based window index

        Returns:
            True if switch successful
        """
        try:
            pages = self._context.pages
            if 0 <= index < len(pages):
                self._page = pages[index]
                await self._page.bring_to_front()
                logger.info(f"Switched to window index {index}: {self._page.url}")
                return True
            else:
                logger.warning(f"Window index {index} out of range")
                return False

        except Exception as e:
            logger.error(f"Failed to switch to window index {index}: {e}")
            return False

    async def switch_to_new_window(self, timeout: int = 30000) -> bool:
        """
        Wait for and switch to a new window/popup.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            True if new window found and switched
        """
        try:
            current_count = len(self._context.pages)

            # Wait for new page
            async with self._context.expect_page(timeout=timeout) as page_info:
                pass

            new_page = await page_info.value
            await new_page.wait_for_load_state("domcontentloaded")

            self._page = new_page
            await self._page.bring_to_front()
            logger.info(f"Switched to new window: {self._page.url}")
            return True

        except Exception as e:
            logger.error(f"Failed to switch to new window: {e}")
            return False

    async def close_current_window(self) -> bool:
        """
        Close the current window and switch to another.

        Returns:
            True if closed and switched successfully
        """
        try:
            pages = self._context.pages
            if len(pages) <= 1:
                logger.warning("Cannot close the only window")
                return False

            await self._page.close()

            # Switch to the last remaining page
            self._page = self._context.pages[-1]
            await self._page.bring_to_front()
            logger.info(f"Closed window, switched to: {self._page.url}")
            return True

        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return False

    async def get_all_windows(self) -> List[WindowInfo]:
        """Get information about all open windows."""
        windows = []
        for i, page in enumerate(self._context.pages):
            try:
                info = WindowInfo(
                    page=page,
                    url=page.url,
                    title=await page.title(),
                    is_popup=i > 0,
                    opener_url=None
                )
                windows.append(info)
            except Exception:
                pass
        return windows

    def get_window_count(self) -> int:
        """Get the number of open windows."""
        return len(self._context.pages)


class DialogHandler:
    """
    Handles JavaScript dialogs (alert, confirm, prompt).
    """

    def __init__(self, page: Page):
        self._page = page
        self._dialog_queue: List[Dialog] = []
        self._auto_handle = True
        self._default_action = "accept"
        self._default_text = ""
        self._setup_listener()

    def _setup_listener(self):
        """Setup dialog event listener."""
        self._page.on("dialog", self._on_dialog)

    async def _on_dialog(self, dialog: Dialog):
        """Handle dialog event."""
        logger.info(f"Dialog detected: {dialog.type} - {dialog.message}")

        if self._auto_handle:
            if self._default_action == "accept":
                await dialog.accept(self._default_text)
            else:
                await dialog.dismiss()
        else:
            self._dialog_queue.append(dialog)

    def set_page(self, page: Page):
        """Update the page reference."""
        self._page = page
        self._setup_listener()

    def set_auto_handle(self, enabled: bool, action: str = "accept", text: str = ""):
        """
        Configure automatic dialog handling.

        Args:
            enabled: Whether to auto-handle dialogs
            action: "accept" or "dismiss"
            text: Text to enter for prompt dialogs
        """
        self._auto_handle = enabled
        self._default_action = action
        self._default_text = text

    async def handle_alert(self, action: str = "accept") -> Optional[str]:
        """
        Handle an alert dialog.

        Args:
            action: "accept" or "dismiss"

        Returns:
            Alert message if handled
        """
        if self._dialog_queue:
            dialog = self._dialog_queue.pop(0)
            message = dialog.message

            if action == "accept":
                await dialog.accept()
            else:
                await dialog.dismiss()

            return message

        return None

    async def handle_confirm(self, accept: bool = True) -> Optional[str]:
        """
        Handle a confirm dialog.

        Args:
            accept: Whether to accept or dismiss

        Returns:
            Confirm message if handled
        """
        if self._dialog_queue:
            dialog = self._dialog_queue.pop(0)
            message = dialog.message

            if accept:
                await dialog.accept()
            else:
                await dialog.dismiss()

            return message

        return None

    async def handle_prompt(self, text: str = "", accept: bool = True) -> Optional[str]:
        """
        Handle a prompt dialog.

        Args:
            text: Text to enter
            accept: Whether to accept or dismiss

        Returns:
            Prompt message if handled
        """
        if self._dialog_queue:
            dialog = self._dialog_queue.pop(0)
            message = dialog.message

            if accept:
                await dialog.accept(text)
            else:
                await dialog.dismiss()

            return message

        return None

    async def wait_for_dialog(self, timeout: int = 5000) -> Optional[Dialog]:
        """
        Wait for a dialog to appear.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            Dialog if one appears
        """
        # If already queued, return immediately
        if self._dialog_queue:
            return self._dialog_queue.pop(0)

        # Temporarily disable auto-handle
        old_auto = self._auto_handle
        self._auto_handle = False

        try:
            # Wait for dialog
            start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start) * 1000 < timeout:
                if self._dialog_queue:
                    return self._dialog_queue.pop(0)
                await asyncio.sleep(0.1)

            return None

        finally:
            self._auto_handle = old_auto
