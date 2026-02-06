"""FastAPI main application with all production endpoints."""

from __future__ import annotations

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from recorder.ml.selector_engine import MultiDimensionalSelectorEngine, create_fingerprint_from_dom
from recorder.ml.healing_engine import SelectorHealingEngine
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig
from recorder.ml.rag_engine import RAGEngine
from recorder.audio.transcription_engine import TranscriptionEngine
from recorder.services import workflow_store

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Call Intelligence API",
    description="Production API for browser automation and call analysis",
    version="1.0.0"
)

# Add CORS middleware
# Note: allow_credentials=True is incompatible with allow_origins=["*"]
# per the CORS spec. Browsers will refuse to send credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML components (lazy loading)
selector_engine: Optional[MultiDimensionalSelectorEngine] = None
healing_engine: Optional[SelectorHealingEngine] = None
llm_engine: Optional[LocalLLMEngine] = None
rag_engine: Optional[RAGEngine] = None
transcription_engine: Optional[TranscriptionEngine] = None

# Job storage (in production, use Redis or database)
jobs: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Request/Response Models
# ============================================================================

class ElementData(BaseModel):
    """Element data for selector generation."""
    tagName: str
    id: Optional[str] = None
    classes: List[str] = []
    attributes: Dict[str, str] = {}
    textContent: Optional[str] = None
    ariaLabel: Optional[str] = None
    ariaRole: Optional[str] = None
    boundingBox: List[int] = [0, 0, 0, 0]
    framePath: List[str] = []
    shadowPath: List[str] = []


class SelectorGenerationRequest(BaseModel):
    """Request for generating selectors."""
    element: ElementData
    page_url: Optional[str] = None


class SelectorGenerationResponse(BaseModel):
    """Response with generated selectors."""
    selectors: List[Dict[str, Any]]
    fingerprint_id: str


class TranscriptionSegment(BaseModel):
    """Transcription segment."""
    speaker: str
    role: Optional[str]
    text: str
    start: float
    end: float
    confidence: float


class TranscriptAnalysisRequest(BaseModel):
    """Request for transcript analysis."""
    segments: List[TranscriptionSegment]
    analysis_types: List[str] = ["intent", "sentiment", "kpi"]


class TranscriptAnalysisResponse(BaseModel):
    """Response with transcript analysis."""
    intents: List[str]
    sentiment: Dict[str, Any]
    agent_kpi: Optional[Dict[str, float]] = None


class StatementVerificationRequest(BaseModel):
    """Request for statement verification."""
    statement: str
    context: Optional[str] = None


class StatementVerificationResponse(BaseModel):
    """Response with verification result."""
    is_verified: bool
    confidence: float
    citations: List[str]
    explanation: str


class WorkflowReplayRequest(BaseModel):
    """Request to replay a workflow."""
    workflow_id: str
    headless: bool = True
    record_video: bool = False


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global selector_engine, healing_engine, rag_engine, transcription_engine
    
    logger.info("Initializing API components...")
    
    # Initialize selector and healing engines
    selector_engine = MultiDimensionalSelectorEngine()
    healing_engine = SelectorHealingEngine()
    
    # Initialize RAG engine
    rag_engine = RAGEngine()
    # Try to load existing index
    rag_engine.load_index()
    
    # Initialize transcription engine
    transcription_engine = TranscriptionEngine(model_size="base")
    
    logger.info("API components initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down API...")


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Call Intelligence API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/models/status")
async def models_status():
    """Get status of loaded models."""
    return {
        "selector_engine": selector_engine is not None,
        "healing_engine": healing_engine is not None,
        "llm_engine": llm_engine is not None,
        "rag_engine": rag_engine is not None,
        "transcription_engine": transcription_engine is not None,
        "rag_documents": len(rag_engine.documents) if rag_engine else 0
    }


# ============================================================================
# Selector Generation & Healing
# ============================================================================

@app.post("/api/selectors/generate", response_model=SelectorGenerationResponse)
async def generate_selectors(request: SelectorGenerationRequest):
    """Generate multi-dimensional selectors for an element."""
    if not selector_engine:
        raise HTTPException(status_code=503, detail="Selector engine not initialized")
    
    try:
        # Create fingerprint from element data
        element_dict = request.element.dict()
        fingerprint = create_fingerprint_from_dom(element_dict)
        
        # Generate selectors
        selectors = selector_engine.generate_selectors(fingerprint)
        
        # Convert to response format
        selectors_data = [
            {
                "type": sel.type.value,
                "value": sel.value,
                "score": sel.score,
                "metadata": sel.metadata
            }
            for sel in selectors
        ]
        
        fingerprint_id = str(uuid.uuid4())
        
        return SelectorGenerationResponse(
            selectors=selectors_data,
            fingerprint_id=fingerprint_id
        )
    
    except Exception as e:
        logger.error(f"Selector generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/selectors/heal")
async def heal_selector(
    original_element: ElementData,
    current_page_state: Dict[str, Any]
):
    """Attempt to heal a broken selector."""
    if not healing_engine or not selector_engine:
        raise HTTPException(status_code=503, detail="Healing engine not initialized")
    
    try:
        # Create fingerprint
        fingerprint = create_fingerprint_from_dom(original_element.dict())
        
        # Generate selector strategies
        selectors = selector_engine.generate_selectors(fingerprint)
        
        # Attempt healing
        result = healing_engine.heal_selector(
            fingerprint,
            selectors,
            current_page_state
        )
        
        return {
            "success": result.success,
            "strategy": result.strategy.value,
            "confidence": result.confidence,
            "execution_time_ms": result.execution_time_ms,
            "fallback_selector": result.fallback_selector
        }
    
    except Exception as e:
        logger.error(f"Selector healing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Audio Upload & Transcription
# ============================================================================

@app.post("/api/upload-audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload audio file for transcription.
    Returns job_id for tracking progress.
    """
    if not transcription_engine:
        raise HTTPException(status_code=503, detail="Transcription engine not initialized")
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.mp3', '.m4a', '.flac', '.ogg')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename to prevent path traversal
        safe_filename = Path(file.filename).name if file.filename else "audio"
        file_path = upload_dir / f"{job_id}_{safe_filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create job entry
        jobs[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "file_path": str(file_path),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Start transcription in background
        background_tasks.add_task(
            process_transcription,
            job_id,
            file_path
        )
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Transcription job started"
        }
    
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_transcription(job_id: str, audio_path: Path):
    """Background task for processing transcription."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0.1
        
        # Transcribe
        result = transcription_engine.transcribe(
            audio_path,
            enable_diarization=True
        )
        
        jobs[job_id]["progress"] = 0.9
        
        # Convert result to dict
        result_dict = {
            "segments": [
                {
                    "speaker": seg.speaker,
                    "role": seg.role,
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "confidence": seg.confidence
                }
                for seg in result.segments
            ],
            "duration": result.duration,
            "language": result.language,
            "speakers_count": result.speakers_count
        }
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = result_dict
        
    except Exception as e:
        logger.error(f"Transcription processing failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# ============================================================================
# Transcript Analysis
# ============================================================================

@app.post("/api/analyze-transcript", response_model=TranscriptAnalysisResponse)
async def analyze_transcript(request: TranscriptAnalysisRequest):
    """Analyze transcript for intent, sentiment, and KPIs."""
    
    try:
        result = {
            "intents": [],
            "sentiment": {},
            "agent_kpi": None
        }
        
        # Convert segments to format expected by LLM
        segments = [
            {
                "role": seg.role or "unknown",
                "text": seg.text,
                "start": seg.start,
                "end": seg.end
            }
            for seg in request.segments
        ]
        
        # Intent classification
        if "intent" in request.analysis_types and llm_engine:
            intent_result = llm_engine.classify_intent(segments)
            result["intents"] = [intent_result.primary_intent] + intent_result.secondary_intents
        
        # Sentiment analysis
        if "sentiment" in request.analysis_types:
            # Combine all text
            full_text = " ".join(seg.text for seg in request.segments)
            
            if llm_engine:
                sentiment_result = llm_engine.analyze_sentiment(full_text)
                result["sentiment"] = {
                    "sentiment": sentiment_result.sentiment,
                    "score": sentiment_result.score,
                    "emotions": sentiment_result.emotions,
                    "tone": sentiment_result.tone
                }
            else:
                result["sentiment"] = {"sentiment": "neutral", "score": 0.0}
        
        # Agent KPI scoring
        if "kpi" in request.analysis_types and llm_engine:
            kpi_result = llm_engine.score_agent_kpi(segments)
            result["agent_kpi"] = {
                "knowledge_score": kpi_result.knowledge_score,
                "compliance_score": kpi_result.compliance_score,
                "empathy_score": kpi_result.empathy_score,
                "efficiency_score": kpi_result.efficiency_score,
                "overall_score": kpi_result.overall_score
            }
        
        return TranscriptAnalysisResponse(**result)
    
    except Exception as e:
        logger.error(f"Transcript analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG & Statement Verification
# ============================================================================

@app.post("/api/verify-statement", response_model=StatementVerificationResponse)
async def verify_statement(request: StatementVerificationRequest):
    """Verify statement against knowledge base."""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")
    
    try:
        result = rag_engine.verify_statement(
            request.statement,
            context=request.context
        )
        
        return StatementVerificationResponse(
            is_verified=result.is_verified,
            confidence=result.confidence,
            citations=result.citations,
            explanation=result.explanation
        )
    
    except Exception as e:
        logger.error(f"Statement verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/ingest")
async def ingest_documents(directory_path: str):
    """Ingest documents from directory into RAG knowledge base."""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")
    
    try:
        directory = Path(directory_path).resolve()
        # Restrict to data directory to prevent arbitrary filesystem access
        allowed_root = Path("data").resolve()
        if not str(directory).startswith(str(allowed_root)):
            raise HTTPException(status_code=403, detail="Access denied: path outside data directory")
        if not directory.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        rag_engine.ingest_documents_from_directory(directory)
        rag_engine.save_index()
        
        return {
            "status": "success",
            "documents_count": len(rag_engine.documents),
            "message": f"Ingested documents from {directory_path}"
        }
    
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Management
# ============================================================================

@app.get("/api/workflows")
async def list_workflows():
    """List all workflows."""
    workflows = workflow_store.list_workflows()
    return {"workflows": workflows}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow by ID."""
    # Sanitize workflow_id to prevent path traversal
    safe_id = Path(workflow_id).name
    if safe_id != workflow_id or ".." in workflow_id:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    workflow_path = Path(f"data/workflows/{safe_id}")

    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflow_store.load_workflow(workflow_path)
    return workflow.dict() if workflow else {}


@app.post("/api/replay")
async def replay_workflow(
    background_tasks: BackgroundTasks,
    request: WorkflowReplayRequest
):
    """Execute workflow replay."""
    # Sanitize workflow_id to prevent path traversal
    safe_id = Path(request.workflow_id).name
    if safe_id != request.workflow_id or ".." in request.workflow_id:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    workflow_path = Path(f"data/workflows/{safe_id}")

    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "workflow_id": request.workflow_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Start replay in background
    background_tasks.add_task(
        process_replay,
        job_id,
        workflow_path,
        request.headless,
        request.record_video
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Replay job started"
    }


async def process_replay(
    job_id: str,
    workflow_path: Path,
    headless: bool,
    record_video: bool
):
    """Background task for replay execution with real Playwright."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0.1

        # Import replay components
        from recorder.services.stable_replay import StableReplayer
        from recorder.services import workflow_store

        # Load workflow
        workflow_name = workflow_path.name
        workflow = workflow_store.load_workflow(workflow_name)
        if not workflow:
            raise Exception(f"Workflow not found: {workflow_path}")

        jobs[job_id]["progress"] = 0.2
        jobs[job_id]["total_steps"] = len(workflow.steps)

        # Create replayer with ML engines if available
        replayer = StableReplayer()

        if selector_engine:
            replayer.set_selector_engine(selector_engine)
        if healing_engine:
            replayer.set_healing_engine(healing_engine)

        # Track step results
        step_results = []
        total_steps = len(workflow.steps)
        passed = 0
        failed = 0
        healed = 0

        def on_step_result(result):
            nonlocal passed, failed, healed
            step_results.append(result.to_dict() if hasattr(result, 'to_dict') else {
                "index": result.index,
                "status": result.status,
                "duration_ms": result.duration_ms,
                "error": result.error,
                "tier_used": result.tier_used,
            })
            if result.status == "passed":
                passed += 1
            elif result.status == "failed":
                failed += 1
            if hasattr(result, 'healed') and result.healed:
                healed += 1

            # Update progress
            progress = 0.2 + (0.7 * len(step_results) / total_steps)
            jobs[job_id]["progress"] = min(progress, 0.9)
            jobs[job_id]["current_step"] = len(step_results)

        replayer.on_step_result(on_step_result)

        # Execute replay
        success = False
        error_msg = ""

        def on_complete(success_flag: bool, error: str, duration_ms: int):
            nonlocal success, error_msg
            success = success_flag
            error_msg = error

        replayer.on_complete(on_complete)

        # Run replay (this is blocking in the current implementation)
        # We wrap it in asyncio.to_thread to not block the event loop
        await asyncio.to_thread(replayer.replay, str(workflow_path))

        # Wait for completion with timeout
        timeout = 300  # 5 minutes max
        start_time = asyncio.get_event_loop().time()
        while replayer._running:
            await asyncio.sleep(0.5)
            if asyncio.get_event_loop().time() - start_time > timeout:
                replayer.stop()
                raise Exception("Replay timeout")

        jobs[job_id]["progress"] = 1.0

        if success or failed == 0:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = {
                "success": True,
                "total_steps": total_steps,
                "passed": passed,
                "failed": failed,
                "healed": healed,
                "steps": step_results,
            }
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = error_msg or f"{failed} step(s) failed"
            jobs[job_id]["result"] = {
                "success": False,
                "total_steps": total_steps,
                "passed": passed,
                "failed": failed,
                "healed": healed,
                "steps": step_results,
            }

        # Store execution in database if available
        if DB_AVAILABLE:
            try:
                session = get_session()
                exec_repo = ExecutionRepository(session)

                # Create execution record
                execution = exec_repo.create({
                    "workflow_id": workflow_path.stem,
                    "status": jobs[job_id]["status"],
                    "headless": headless,
                    "total_steps": total_steps,
                    "passed_steps": passed,
                    "failed_steps": failed,
                    "healed_steps": healed,
                    "error_message": error_msg if failed > 0 else None,
                    "executed_by": "api",
                })

                # Add step results
                for step_data in step_results:
                    exec_repo.add_step_result(execution.id, {
                        "step_index": step_data.get("index", 0),
                        "step_type": step_data.get("step_type", "unknown"),
                        "status": step_data.get("status", "unknown"),
                        "duration_ms": step_data.get("duration_ms", 0),
                        "tier_used": step_data.get("tier_used"),
                        "was_healed": step_data.get("healed", False),
                        "error_message": step_data.get("error"),
                    })

                # Update workflow stats
                workflow_repo = WorkflowRepository(session)
                workflow_repo.update_stats(workflow_path.stem, execution)

                session.close()
            except Exception as db_err:
                logger.warning(f"Failed to store execution in database: {db_err}")

    except Exception as e:
        logger.error(f"Replay processing failed: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# ============================================================================
# Job Status
# ============================================================================

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status by ID."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0.0),
        result=job.get("result"),
        error=job.get("error")
    )


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()
    
    try:
        while True:
            if job_id in jobs:
                await websocket.send_json(jobs[job_id])
                
                # Close connection if job is completed or failed
                if jobs[job_id]["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")


# ============================================================================
# Dashboard & Statistics Endpoints
# ============================================================================

# Import database components
try:
    from recorder.api.database import (
        get_session, DatabaseManager,
        WorkflowRepository, ExecutionRepository, MLTrainingDataRepository,
        Workflow as DBWorkflow, Execution as DBExecution, StepResult as DBStepResult,
        ExecutionStatus, StepStatus
    )
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database module not available: {e}")
    DB_AVAILABLE = False


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""
    total_workflows: int = 0
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    pass_rate: float = 0.0
    total_steps_executed: int = 0
    healed_steps: int = 0
    healing_rate: float = 0.0
    ml_selector_samples: int = 0
    ml_healing_samples: int = 0
    ml_selector_trained: bool = False
    ml_healing_trained: bool = False


class ExecutionListResponse(BaseModel):
    """Execution list response."""
    executions: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class WorkflowCreateRequest(BaseModel):
    """Request to create/sync a workflow."""
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    tags: List[str] = []
    local_file_path: Optional[str] = None


@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    stats = DashboardStatsResponse()

    # Get workflow count
    workflows = workflow_store.list_workflows()
    stats.total_workflows = len(workflows)

    if DB_AVAILABLE:
        try:
            session = get_session()
            exec_repo = ExecutionRepository(session)
            ml_repo = MLTrainingDataRepository(session)

            # Execution stats
            exec_stats = exec_repo.get_stats()
            stats.total_runs = exec_stats.get("total_runs", 0)
            stats.passed_runs = exec_stats.get("completed_runs", 0)
            stats.failed_runs = exec_stats.get("failed_runs", 0)
            stats.pass_rate = exec_stats.get("pass_rate", 0.0)
            stats.total_steps_executed = exec_stats.get("total_steps_executed", 0)
            stats.healed_steps = exec_stats.get("healed_steps", 0)
            stats.healing_rate = exec_stats.get("healing_rate", 0.0)

            # ML stats
            ml_stats = ml_repo.get_stats()
            stats.ml_selector_samples = ml_stats.get("selector_samples", 0)
            stats.ml_healing_samples = ml_stats.get("healing_samples", 0)

            session.close()
        except Exception as e:
            logger.error(f"Failed to get dashboard stats from DB: {e}")

    # Check if models are trained
    if selector_engine:
        stats.ml_selector_trained = getattr(selector_engine, '_model_trained', False)
    if healing_engine:
        stats.ml_healing_trained = healing_engine.healing_model is not None

    return stats


@app.get("/api/executions", response_model=ExecutionListResponse)
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
):
    """List executions with optional filtering."""
    executions = []
    total = 0

    if DB_AVAILABLE:
        try:
            session = get_session()
            exec_repo = ExecutionRepository(session)

            if workflow_id:
                all_executions = exec_repo.list_for_workflow(workflow_id, limit=1000)
            else:
                all_executions = exec_repo.list_recent(limit=1000, status=status)

            # Filter by status if provided and not already filtered
            if status and not workflow_id:
                all_executions = [e for e in all_executions if e.status == status]

            total = len(all_executions)

            # Paginate
            start = (page - 1) * page_size
            end = start + page_size
            paginated = all_executions[start:end]

            executions = [e.to_dict() for e in paginated]
            session.close()
        except Exception as e:
            logger.error(f"Failed to list executions: {e}")

    return ExecutionListResponse(
        executions=executions,
        total=total,
        page=page,
        page_size=page_size
    )


@app.get("/api/executions/{execution_id}")
async def get_execution_details(execution_id: str):
    """Get detailed execution results including step results."""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = get_session()
        exec_repo = ExecutionRepository(session)

        execution = exec_repo.get_by_id(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        result = execution.to_dict(include_steps=True)
        session.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/status")
async def get_ml_status():
    """Get ML model status."""
    status = {
        "selector_engine": {
            "available": selector_engine is not None,
            "trained": False,
            "samples": 0
        },
        "healing_engine": {
            "available": healing_engine is not None,
            "trained": False,
            "samples": 0
        },
        "rag_engine": {
            "available": rag_engine is not None,
            "documents": 0,
            "ready": False
        },
        "llm_engine": {
            "available": llm_engine is not None,
            "model": None
        },
        "transcription_engine": {
            "available": transcription_engine is not None
        }
    }

    if selector_engine:
        status["selector_engine"]["trained"] = getattr(selector_engine, '_model_trained', False)
        status["selector_engine"]["samples"] = len(getattr(selector_engine, '_training_data', []))

    if healing_engine:
        status["healing_engine"]["trained"] = healing_engine.healing_model is not None
        status["healing_engine"]["samples"] = len(getattr(healing_engine, 'training_data', []))

    if rag_engine:
        status["rag_engine"]["documents"] = len(rag_engine.documents)
        status["rag_engine"]["ready"] = rag_engine.is_ready()

    if llm_engine:
        status["llm_engine"]["model"] = getattr(llm_engine, 'model_name', 'Unknown')

    return status


@app.post("/api/workflows/sync")
async def sync_workflow(request: WorkflowCreateRequest):
    """Create or update a workflow in the database."""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = get_session()
        workflow_repo = WorkflowRepository(session)

        # Check if workflow exists by name
        existing = workflow_repo.get_by_name(request.name)

        workflow_data = {
            "name": request.name,
            "description": request.description,
            "url": request.url,
            "steps": request.steps,
            "tags": request.tags,
            "step_count": len(request.steps),
            "local_file_path": request.local_file_path
        }

        if existing:
            workflow = workflow_repo.update(existing.id, workflow_data)
            action = "updated"
        else:
            workflow = workflow_repo.create(workflow_data)
            action = "created"

        session.close()

        return {
            "status": "success",
            "action": action,
            "workflow_id": workflow.id,
            "name": workflow.name
        }
    except Exception as e:
        logger.error(f"Failed to sync workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/training-data/stats")
async def get_ml_training_stats():
    """Get ML training data statistics."""
    if not DB_AVAILABLE:
        return {"selector_samples": 0, "healing_samples": 0}

    try:
        session = get_session()
        ml_repo = MLTrainingDataRepository(session)
        stats = ml_repo.get_stats()
        session.close()
        return stats
    except Exception as e:
        logger.error(f"Failed to get ML training stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/training-data")
async def upload_training_data(data: List[Dict[str, Any]]):
    """Upload ML training data from desktop clients."""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = get_session()
        ml_repo = MLTrainingDataRepository(session)

        added = 0
        for item in data:
            ml_repo.add(item)
            added += 1

        session.close()

        return {"status": "success", "added": added}
    except Exception as e:
        logger.error(f"Failed to upload training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
