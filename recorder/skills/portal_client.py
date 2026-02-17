"""
Portal Client - HTTP client for communicating with the central Auton8 server.

All server-delegated skills route through this single client.
Handles authentication, retries, timeouts, and graceful fallback.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30  # seconds
_HEALTH_CACHE_TTL = 60  # seconds


class PortalClient:
    """
    Lightweight HTTP client for the central Auton8 Portal server.

    Uses only stdlib (urllib) so tester machines don't need ``requests``
    or ``httpx`` installed.
    """

    def __init__(
        self,
        base_url: str = "",
        access_token: str = "",
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.access_token = access_token
        self.timeout = timeout

        # Health cache
        self._healthy: Optional[bool] = None
        self._healthy_checked_at: float = 0.0
        self._lock = threading.Lock()

        # Server capability cache
        self._server_skills: Optional[List[str]] = None

    # -- connection status -------------------------------------------------

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    @property
    def is_connected(self) -> bool:
        """Check if server is reachable (cached for performance)."""
        if not self.is_configured:
            return False

        now = time.monotonic()
        with self._lock:
            if (
                self._healthy is not None
                and (now - self._healthy_checked_at) < _HEALTH_CACHE_TTL
            ):
                return self._healthy

        # Cache expired or first check
        healthy = self._check_health()
        with self._lock:
            self._healthy = healthy
            self._healthy_checked_at = time.monotonic()
        return healthy

    def configure(self, base_url: str, access_token: str = "") -> None:
        """Update connection settings."""
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.access_token = access_token
        # Reset caches
        with self._lock:
            self._healthy = None
            self._server_skills = None

    # -- HTTP primitives ---------------------------------------------------

    def _build_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if extra:
            headers.update(extra)
        return headers

    def get(self, path: str, params: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
        """HTTP GET. Returns (status_code, parsed_json)."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"

        req = Request(url, headers=self._build_headers(), method="GET")
        return self._send(req)

    def post(self, path: str, body: Any = None) -> Tuple[int, Any]:
        """HTTP POST with JSON body. Returns (status_code, parsed_json)."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, headers=self._build_headers(), method="POST")
        return self._send(req)

    def post_file(
        self,
        path: str,
        file_path: str,
        field_name: str = "file",
    ) -> Tuple[int, Any]:
        """HTTP POST multipart file upload. Returns (status_code, parsed_json)."""
        import mimetypes
        import uuid

        url = urljoin(self.base_url + "/", path.lstrip("/"))
        boundary = uuid.uuid4().hex
        filepath = Path(file_path)

        content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"

        body_parts = []
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{filepath.name}"\r\n'.encode()
        )
        body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        body_parts.append(filepath.read_bytes())
        body_parts.append(f"\r\n--{boundary}--\r\n".encode())

        data = b"".join(body_parts)

        headers = self._build_headers()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        req = Request(url, data=data, headers=headers, method="POST")
        return self._send(req)

    def _send(self, req: Request) -> Tuple[int, Any]:
        """Execute request with error handling."""
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = body
                return resp.status, parsed
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
                parsed = json.loads(body)
            except Exception:
                parsed = body
            logger.warning(f"HTTP {e.code} from {req.full_url}: {parsed}")
            return e.code, parsed
        except URLError as e:
            logger.warning(f"Connection error to {req.full_url}: {e.reason}")
            raise ConnectionError(f"Cannot reach server: {e.reason}") from e
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    # -- health check ------------------------------------------------------

    def _check_health(self) -> bool:
        try:
            status, data = self.get("/health")
            return status == 200 and data.get("status") == "healthy"
        except Exception:
            return False

    def check_health(self) -> Dict[str, Any]:
        """Public health check, returns full status."""
        try:
            status, data = self.get("/health")
            healthy = status == 200 and data.get("status") == "healthy"
            with self._lock:
                self._healthy = healthy
                self._healthy_checked_at = time.monotonic()
            return {"connected": healthy, "status": status, "data": data}
        except Exception as e:
            with self._lock:
                self._healthy = False
                self._healthy_checked_at = time.monotonic()
            return {"connected": False, "error": str(e)}

    # -- skill availability ------------------------------------------------

    def get_server_skills(self) -> List[str]:
        """Get list of skills available on the server."""
        if self._server_skills is not None:
            return self._server_skills
        try:
            status, data = self.get("/api/skills/status")
            if status == 200:
                self._server_skills = [
                    s["name"] for s in data.get("skills", [])
                    if s.get("available", False)
                ]
                return self._server_skills
        except Exception:
            pass
        return []

    def get_models_status(self) -> Dict[str, bool]:
        """Get ML model availability on server."""
        try:
            status, data = self.get("/models/status")
            if status == 200:
                return data
        except Exception:
            pass
        return {}

    # -- convenience methods for common API calls --------------------------

    def heal_selector(self, element_data: Dict, page_state: Dict) -> Tuple[int, Any]:
        return self.post("/api/selectors/heal", {
            "original_element": element_data,
            "current_page_state": page_state,
        })

    def generate_selectors(self, element_data: Dict) -> Tuple[int, Any]:
        return self.post("/api/selectors/generate", {"element": element_data})

    def classify_intent(self, segments: List[Dict]) -> Tuple[int, Any]:
        return self.post("/api/llm/classify-intent", {"segments": segments})

    def llm_recover(self, step_data: Dict, page_context: Dict) -> Tuple[int, Any]:
        return self.post("/api/llm/recover", {
            "step": step_data,
            "page_context": page_context,
        })

    def vision_match(
        self,
        screenshot_path: str,
        template_path: str,
        threshold: float = 0.75,
    ) -> Tuple[int, Any]:
        return self.post("/api/vision/match", {
            "screenshot_path": screenshot_path,
            "template_path": template_path,
            "threshold": threshold,
        })

    def nlp_similarity(self, text_a: str, text_b: str) -> Tuple[int, Any]:
        return self.post("/api/nlp/similarity", {
            "text_a": text_a,
            "text_b": text_b,
        })

    def verify_statement(self, statement: str, context: str = "") -> Tuple[int, Any]:
        return self.post("/api/verify-statement", {
            "statement": statement,
            "context": context,
        })

    def upload_audio(self, file_path: str) -> Tuple[int, Any]:
        return self.post_file("/api/upload-audio", file_path)

    def get_job_status(self, job_id: str) -> Tuple[int, Any]:
        return self.get(f"/api/jobs/{job_id}")

    def sync_workflow(self, workflow_data: Dict) -> Tuple[int, Any]:
        return self.post("/api/workflows/sync", workflow_data)

    def get_dashboard_stats(self) -> Tuple[int, Any]:
        return self.get("/api/dashboard/stats")

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, Any]:
        params: Dict[str, str] = {"page": str(page), "page_size": str(page_size)}
        if workflow_id:
            params["workflow_id"] = workflow_id
        return self.get("/api/executions", params)

    def upload_training_data(self, data: List[Dict]) -> Tuple[int, Any]:
        return self.post("/api/ml/training-data", data)
