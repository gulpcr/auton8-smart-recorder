"""
RAG Skill - Knowledge base verification via FAISS + sentence-transformers.

Heavy dependency. Delegates to server when not installed locally.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import SkillBase, SkillContext, SkillResult, SkillRunLocation

logger = logging.getLogger(__name__)


class RAGSkill(SkillBase):
    name = "rag"
    description = "Knowledge base verification and document retrieval via RAG"
    local_capable = True   # If FAISS installed
    server_capable = True

    def __init__(self) -> None:
        super().__init__()
        self._local_available: Optional[bool] = None
        self._rag_engine = None

    def _check_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from recorder.ml.rag_engine import RAGEngine
            self._local_available = True
        except ImportError:
            self._local_available = False
        return self._local_available

    def _get_engine(self):
        if self._rag_engine is None and self._check_local():
            try:
                from recorder.ml.rag_engine import RAGEngine
                self._rag_engine = RAGEngine()
                self._rag_engine.load_index()
            except Exception as e:
                logger.warning(f"[rag] Failed to init local RAG: {e}")
                self._local_available = False
        return self._rag_engine

    @property
    def local_capable(self) -> bool:
        return self._check_local()

    @local_capable.setter
    def local_capable(self, value):
        pass

    def execute_local(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """
        Run RAG operations locally.

        kwargs:
            action: "verify" | "search" | "ingest"
            statement: str (for verify)
            query: str (for search)
            context: str
            directory: str (for ingest)
        """
        engine = self._get_engine()
        if not engine:
            return SkillResult(success=False, error="RAG engine not available locally")

        action = kwargs.get("action", "verify")

        if action == "verify":
            statement = kwargs.get("statement", "")
            context = kwargs.get("context", "")
            try:
                result = engine.verify_statement(statement, context=context)
                return SkillResult(
                    success=True,
                    data={
                        "is_verified": result.is_verified,
                        "confidence": result.confidence,
                        "citations": result.citations,
                        "explanation": result.explanation,
                    },
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Verification failed: {e}")

        elif action == "search":
            query = kwargs.get("query", "")
            try:
                results = engine.search(query, top_k=kwargs.get("top_k", 5))
                return SkillResult(
                    success=True,
                    data={"results": results},
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Search failed: {e}")

        elif action == "ingest":
            directory = kwargs.get("directory", "")
            try:
                from pathlib import Path
                engine.ingest_documents_from_directory(Path(directory))
                engine.save_index()
                return SkillResult(
                    success=True,
                    data={"documents": len(engine.documents)},
                    run_location=SkillRunLocation.LOCAL,
                )
            except Exception as e:
                return SkillResult(success=False, error=f"Ingestion failed: {e}")

        return SkillResult(success=False, error=f"Unknown RAG action: {action}")

    def execute_server(self, ctx: SkillContext, **kwargs: Any) -> SkillResult:
        """Delegate RAG operations to central server."""
        action = kwargs.get("action", "verify")

        if action == "verify":
            statement = kwargs.get("statement", "")
            context = kwargs.get("context", "")
            status, data = ctx.portal_client.verify_statement(statement, context)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)

        elif action == "ingest":
            directory = kwargs.get("directory", "")
            status, data = ctx.portal_client.post("/api/rag/ingest", directory)
            if status == 200:
                return SkillResult(success=True, data=data,
                                   run_location=SkillRunLocation.SERVER)

        error = data.get("detail", "RAG server error") if isinstance(data, dict) else str(data)
        return SkillResult(success=False, error=error, run_location=SkillRunLocation.SERVER)

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["local_rag_available"] = self._check_local()
        if self._rag_engine:
            status["documents"] = len(self._rag_engine.documents)
        return status
