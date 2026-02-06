"""Local LLM integration using llama.cpp for intent classification and analysis."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("llama-cpp-python not available. LLM features will be disabled.")

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for local LLM."""
    model_path: str
    n_ctx: int = 4096  # Context length
    n_threads: int = 4
    n_gpu_layers: int = 0  # Number of layers to offload to GPU
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""
    primary_intent: str
    confidence: float
    secondary_intents: List[str]
    reasoning: str


@dataclass
class SentimentAnalysisResult:
    """Result of sentiment analysis."""
    sentiment: str  # positive, negative, neutral
    score: float  # -1 to 1
    emotions: List[str]  # frustration, satisfaction, confusion, etc.
    tone: str  # urgent, casual, formal


@dataclass
class AgentKPIScores:
    """KPI scores for call center agent."""
    knowledge_score: float  # 0-1
    compliance_score: float  # 0-1
    empathy_score: float  # 0-1
    efficiency_score: float  # 0-1
    overall_score: float  # 0-1
    feedback: str


class LocalLLMEngine:
    """
    Local LLM engine using llama.cpp for offline inference.
    Supports Llama 2/3, Mistral, Phi-3, and custom LoRA adapters.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model: Optional[Any] = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Load the LLM model."""
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python not installed")
            return
        
        model_path = Path(self.config.model_path)
        if not model_path.exists():
            logger.error(f"Model not found: {model_path}")
            return
        
        try:
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False
            )
            logger.info(f"Loaded LLM model: {model_path.name}")
            logger.info(f"Context length: {self.config.n_ctx}, GPU layers: {self.config.n_gpu_layers}")
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate text from prompt."""
        if not self.model:
            return ""
        
        try:
            response = self.model(
                prompt,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature,
                top_p=self.config.top_p,
                stop=stop or ["</s>", "\n\n"],
                echo=False
            )
            
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""
    
    def classify_intent(
        self,
        action_sequence: List[Dict[str, Any]],
        page_context: Optional[str] = None
    ) -> IntentClassificationResult:
        """
        Classify user intent from action sequence.
        
        Args:
            action_sequence: List of user actions
            page_context: Optional page/URL context
        
        Returns:
            Intent classification result
        """
        # Build prompt
        actions_text = "\n".join([
            f"- {i+1}. {action['type']} on '{action.get('target', 'element')}'"
            for i, action in enumerate(action_sequence)
        ])
        
        context_text = f"Page: {page_context}" if page_context else ""
        
        prompt = f"""<|system|>
You are an AI assistant that analyzes user behavior and classifies their intent.
Possible intents: information_seeking, transaction, navigation, authentication, content_creation, communication, configuration.
</|system|>

<|user|>
Analyze the following user actions and classify the primary intent:

{context_text}

Actions:
{actions_text}

Provide your analysis in JSON format:
{{
  "primary_intent": "intent_name",
  "confidence": 0.0-1.0,
  "secondary_intents": ["intent1", "intent2"],
  "reasoning": "brief explanation"
}}
</|user|>

<|assistant|>
"""
        
        response = self.generate(prompt, max_tokens=200, temperature=0.3)
        
        try:
            # Parse JSON response
            result = json.loads(response)
            return IntentClassificationResult(
                primary_intent=result.get("primary_intent", "unknown"),
                confidence=float(result.get("confidence", 0.0)),
                secondary_intents=result.get("secondary_intents", []),
                reasoning=result.get("reasoning", "")
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return IntentClassificationResult(
                primary_intent="unknown",
                confidence=0.0,
                secondary_intents=[],
                reasoning=""
            )
    
    def analyze_sentiment(self, text: str) -> SentimentAnalysisResult:
        """
        Analyze sentiment and emotions in text.
        """
        prompt = f"""<|system|>
You are a sentiment analysis AI. Analyze the emotional tone and sentiment.
</|system|>

<|user|>
Analyze the sentiment of this text:

"{text}"

Provide analysis in JSON format:
{{
  "sentiment": "positive/negative/neutral",
  "score": -1.0 to 1.0,
  "emotions": ["emotion1", "emotion2"],
  "tone": "urgent/casual/formal"
}}
</|user|>

<|assistant|>
"""
        
        response = self.generate(prompt, max_tokens=150, temperature=0.3)
        
        try:
            result = json.loads(response)
            return SentimentAnalysisResult(
                sentiment=result.get("sentiment", "neutral"),
                score=float(result.get("score", 0.0)),
                emotions=result.get("emotions", []),
                tone=result.get("tone", "neutral")
            )
        except json.JSONDecodeError:
            return SentimentAnalysisResult(
                sentiment="neutral",
                score=0.0,
                emotions=[],
                tone="neutral"
            )
    
    def score_agent_kpi(
        self,
        transcript: List[Dict[str, Any]],
        evaluation_criteria: Optional[Dict[str, Any]] = None
    ) -> AgentKPIScores:
        """
        Score call center agent KPIs from transcript.
        
        Args:
            transcript: List of {role, text, start, end}
            evaluation_criteria: Optional custom evaluation criteria
        
        Returns:
            Agent KPI scores
        """
        # Build conversation text
        conversation = "\n".join([
            f"{seg['role'].upper()}: {seg['text']}"
            for seg in transcript
        ])
        
        prompt = f"""<|system|>
You are an AI that evaluates call center agent performance.
Score the agent on:
- Knowledge: Accuracy and completeness of information (0-1)
- Compliance: Following policies and required disclosures (0-1)
- Empathy: Understanding and addressing customer emotions (0-1)
- Efficiency: Resolving issues quickly without repetition (0-1)
</|system|>

<|user|>
Evaluate this call center conversation:

{conversation}

Provide scores in JSON format:
{{
  "knowledge_score": 0.0-1.0,
  "compliance_score": 0.0-1.0,
  "empathy_score": 0.0-1.0,
  "efficiency_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "feedback": "brief constructive feedback"
}}
</|user|>

<|assistant|>
"""
        
        response = self.generate(prompt, max_tokens=300, temperature=0.3)
        
        try:
            result = json.loads(response)
            return AgentKPIScores(
                knowledge_score=float(result.get("knowledge_score", 0.0)),
                compliance_score=float(result.get("compliance_score", 0.0)),
                empathy_score=float(result.get("empathy_score", 0.0)),
                efficiency_score=float(result.get("efficiency_score", 0.0)),
                overall_score=float(result.get("overall_score", 0.0)),
                feedback=result.get("feedback", "")
            )
        except json.JSONDecodeError:
            return AgentKPIScores(
                knowledge_score=0.0,
                compliance_score=0.0,
                empathy_score=0.0,
                efficiency_score=0.0,
                overall_score=0.0,
                feedback="Failed to evaluate"
            )
    
    def generate_selector_suggestion(
        self,
        element_context: Dict[str, Any],
        failed_selectors: List[str]
    ) -> Optional[str]:
        """Use LLM to suggest alternative selector strategy."""
        context_text = json.dumps(element_context, indent=2)
        failed_text = "\n".join(failed_selectors)
        
        prompt = f"""<|system|>
You are an AI that suggests robust CSS/XPath selectors for web elements.
</|system|>

<|user|>
These selectors failed:
{failed_text}

Element context:
{context_text}

Suggest a better selector strategy.
</|user|>

<|assistant|>
"""
        
        return self.generate(prompt, max_tokens=100, temperature=0.5)
    
    def explain_action_sequence(
        self,
        actions: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable explanation of action sequence."""
        actions_text = "\n".join([
            f"{i+1}. {action['type']} {action.get('target', '')}"
            for i, action in enumerate(actions)
        ])
        
        prompt = f"""<|system|>
Explain this user workflow in simple language.
</|system|>

<|user|>
Actions:
{actions_text}

Explain what the user is trying to do:
</|user|>

<|assistant|>
The user is"""
        
        return "The user is" + self.generate(prompt, max_tokens=100, temperature=0.7)


def get_default_model_path() -> Optional[Path]:
    """
    Get default model path from environment, config, or common locations.

    Search order:
    1. LLM_MODEL_PATH environment variable
    2. AUTON8_MODELS_DIR environment variable + model names
    3. Common locations (~/models, ./models)
    """
    import os

    # Check environment variable for explicit path
    env_path = os.environ.get("LLM_MODEL_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        logger.warning(f"LLM_MODEL_PATH set but file not found: {env_path}")

    # Check for models directory environment variable
    models_dir = os.environ.get("AUTON8_MODELS_DIR")

    # Build list of directories to search
    search_dirs = []
    if models_dir:
        search_dirs.append(Path(models_dir))
    search_dirs.extend([
        Path.home() / "models",
        Path.home() / ".local" / "share" / "models",
        Path("./models"),
        Path("../models"),
    ])

    # Model filenames to search for (in priority order)
    model_names = [
        "llama-2-7b-chat.Q4_K_M.gguf",
        "mistral-7b-instruct.Q4_K_M.gguf",
        "phi-3-mini.Q4_K_M.gguf",
        "llama-2-7b-chat.gguf",
        "mistral-7b-instruct.gguf",
    ]

    # Also search for any .gguf file
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # First try specific model names
        for model_name in model_names:
            path = search_dir / model_name
            if path.exists():
                return path

        # Then try any .gguf file
        gguf_files = list(search_dir.glob("*.gguf"))
        if gguf_files:
            return gguf_files[0]

    return None
