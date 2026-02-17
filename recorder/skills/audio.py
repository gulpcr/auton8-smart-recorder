"""
Audio Skill - Transcription and diarization via WhisperX.

Very heavy dependency (~2GB models). Almost always delegates to server.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class AudioSkill(SkillBase):
    name = "audio"
    description = "Audio transcription and speaker diarization via WhisperX"
    local_capable = True   # If WhisperX installed (rare on tester machines)
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.audio.transcription_engine import TranscriptionEngine
            self._local_available = True
        except ImportError:
            self._local_available = False
        return self._local_available

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Transcribe audio locally.

        kwargs:
            file_path: str - path to audio file
            model_size: str - "base", "small", "medium", "large"
            enable_diarization: bool
        """
        file_path = kwargs.get("file_path")
        if not file_path:
            return SkillResult(success=False, error="file_path required")

        try:
            from recorder.audio.transcription_engine import TranscriptionEngine
            model_size = kwargs.get("model_size", "base")
            engine = TranscriptionEngine(model_size=model_size)

            result = engine.transcribe(
                file_path,
                enable_diarization=kwargs.get("enable_diarization", True),
            )

            return SkillResult(
                success=True,
                data={
                    "segments": [
                        {
                            "speaker": seg.speaker,
                            "role": seg.role,
                            "text": seg.text,
                            "start": seg.start,
                            "end": seg.end,
                            "confidence": seg.confidence,
                        }
                        for seg in result.segments
                    ],
                    "duration": result.duration,
                    "language": result.language,
                    "speakers_count": result.speakers_count,
                },
                run_location=SkillRunLocation.LOCAL,
            )
        except Exception as e:
            return SkillResult(success=False, error=f"Local transcription failed: {e}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Upload audio to server for transcription.

        Returns job_id for async polling.
        """
        file_path = kwargs.get("file_path")
        if not file_path:
            return SkillResult(success=False, error="file_path required")

        # Upload file
        status, data = ctx.portal_client.upload_audio(file_path)
        if status not in (200, 201):
            error = data.get("detail", "Upload failed") if isinstance(data, dict) else str(data)
            return SkillResult(success=False, error=error,
                               run_location=SkillRunLocation.SERVER)

        job_id = data.get("job_id")
        if not job_id:
            return SkillResult(success=False, error="No job_id returned from server")

        # Poll for completion if requested
        if kwargs.get("wait_for_result", False):
            return self._poll_job(ctx, job_id, timeout=kwargs.get("timeout", 300))

        return SkillResult(
            success=True,
            data={"job_id": job_id, "status": "pending"},
            run_location=SkillRunLocation.SERVER,
        )

    def _poll_job(self, ctx: SkillContext, job_id: str, timeout: int = 300) -> SkillResult:
        """Poll server until transcription job completes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status, data = ctx.portal_client.get_job_status(job_id)
            if status == 200:
                job_status = data.get("status", "")
                if job_status == "completed":
                    return SkillResult(
                        success=True,
                        data=data.get("result", {}),
                        run_location=SkillRunLocation.SERVER,
                    )
                elif job_status == "failed":
                    return SkillResult(
                        success=False,
                        error=data.get("error", "Transcription failed"),
                        run_location=SkillRunLocation.SERVER,
                    )
            time.sleep(2)

        return SkillResult(
            success=False,
            error=f"Transcription job {job_id} timed out after {timeout}s",
            run_location=SkillRunLocation.SERVER,
        )

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_whisperx_available"] = self._check_local()
        return status
