from __future__ import annotations

import asyncio
import json
import logging
import socket
import threading
from typing import Callable, Awaitable

import websockets

logger = logging.getLogger(__name__)


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(host, port):
            return port
    return start_port  # Fallback to original


class WebSocketIngestServer:
    """
    Lightweight WebSocket server to receive recorder events from the browser
    and push them into the desktop app via a callback.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._callback: Callable[[dict], None] | None = None
        self._server = None
        self._started = False

    def set_callback(self, callback: Callable[[dict], None]):
        self._callback = callback

    async def _handler(self, websocket):
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if self._callback:
                        self._callback(data)
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON message: %s", e)
                except Exception as exc:
                    logger.exception("Failed to process message: %s", exc)
        except websockets.exceptions.ConnectionClosed:
            pass  # Normal close, ignore
        except Exception as e:
            logger.debug("Connection handler ended: %s", e)

    async def _start(self):
        try:
            # Check if port is available, find alternative if not
            if not is_port_available(self.host, self.port):
                old_port = self.port
                self.port = find_available_port(self.host, self.port)
                if self.port != old_port:
                    logger.warning("Port %d in use, using port %d instead", old_port, self.port)
            
            self._server = await websockets.serve(self._handler, self.host, self.port)
            self._started = True
            logger.info("server listening on %s:%s", self.host, self.port)
            logger.info("WebSocket ingest listening on ws://%s:%s", self.host, self.port)
            
            # #region agent log
            try:
                with open(r"f:\auton8\recorder\.cursor\debug.log", "a") as f:
                    import json, time
                    f.write(json.dumps({"location":"ws_server.py:_start","message":"websocket_started","data":{"host":self.host,"port":self.port},"hypothesisId":"H3_PORT","timestamp":int(time.time()*1000)}) + "\n")
            except Exception:
                pass  # Debug logging - non-critical
            # #endregion
            await self._server.wait_closed()
        except OSError as e:
            logger.error("Failed to start WebSocket server: %s", e)
            self._started = False
        except Exception as e:
            logger.error("WebSocket server error: %s", e)
            self._started = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        def runner():
            try:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop.run_until_complete(self._start())
            except Exception as e:
                logger.error("WebSocket server runner error: %s", e)

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def stop(self):
        try:
            if self._server:
                self._server.close()
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=1)
        except Exception as e:
            logger.debug("Error during server stop: %s", e)

