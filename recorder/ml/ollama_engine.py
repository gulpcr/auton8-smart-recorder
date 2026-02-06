"""Ollama LLM integration for local model inference."""

from __future__ import annotations

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama LLM."""
    model_name: str = "ministral-3:latest"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 512
    timeout: int = 30


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""
    primary_intent: str
    confidence: float
    secondary_intents: List[str]
    reasoning: str


@dataclass
class WorkflowAnalysisResult:
    """Result of workflow analysis."""
    summary: str
    purpose: str
    steps_count: int
    complexity: str  # simple, moderate, complex
    suggestions: List[str]


class OllamaLLMEngine:
    """
    Ollama-based LLM engine for local inference.
    Supports any model available in Ollama (Mistral, Llama, Phi, etc.)
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.available = self._check_availability()
        
        if self.available:
            logger.info(f"✓ Ollama LLM engine initialized with model: {self.config.model_name}")
        else:
            logger.warning(f"⚠ Ollama not available at {self.config.base_url}")
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            # Check Ollama server
            with urllib.request.urlopen(
                f"{self.config.base_url}/api/tags",
                timeout=2
            ) as response:
                if response.status != 200:
                    return False
                payload = json.load(response)

            # Check if our model is available
            models = payload.get("models", [])
            model_names = [m.get("name") for m in models]
            model_names = [m for m in model_names if m]
            
            # Check for exact match or partial match (e.g., "ministral-3:latest" or "ministral-3")
            model_base = self.config.model_name.split(":")[0]
            available = any(
                self.config.model_name in name or model_base in name
                for name in model_names
            )
            
            if not available and model_names:
                fallback = model_names[0]
                logger.warning(
                    f"Model '{self.config.model_name}' not found in Ollama. "
                    f"Falling back to '{fallback}'. Available models: {', '.join(model_names)}"
                )
                self.config.model_name = fallback
                return True
            elif not available:
                logger.warning(
                    f"Model '{self.config.model_name}' not found in Ollama. "
                    f"Available models: {', '.join(model_names)}"
                )
            
            return available
            
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        format_json: bool = False
    ) -> str:
        """Generate text from prompt using Ollama."""
        if not self.available:
            return ""
        
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "num_predict": max_tokens or self.config.max_tokens,
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            if format_json:
                payload["format"] = "json"

            request = urllib.request.Request(
                f"{self.config.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                if response.status == 200:
                    result = json.load(response)
                    return result.get("response", "").strip()
                logger.error(f"Ollama API error: {response.status}")
                return ""

        except urllib.error.URLError as e:
            logger.error(f"Ollama request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
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
        # Build action description
        actions_text = "\n".join([
            f"- {i+1}. {action['type']} on '{action.get('target', 'element')}'"
            for i, action in enumerate(action_sequence[:10])  # Limit to first 10 actions
        ])
        
        context_text = f"Page: {page_context}\n\n" if page_context else ""
        
        system_prompt = """You are an AI assistant that analyzes user behavior and classifies their intent.
Possible intents: information_seeking, transaction, navigation, authentication, content_creation, communication, configuration, data_entry, form_filling, search.
Respond ONLY with valid JSON."""
        
        prompt = f"""Analyze these user actions and classify the primary intent:

{context_text}Actions:
{actions_text}

Provide your analysis in this exact JSON format:
{{
  "primary_intent": "intent_name",
  "confidence": 0.95,
  "secondary_intents": ["intent1", "intent2"],
  "reasoning": "brief explanation"
}}"""
        
        response = self.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.3,
            format_json=True
        )
        
        try:
            # Parse JSON response
            result = json.loads(response)
            return IntentClassificationResult(
                primary_intent=result.get("primary_intent", "unknown"),
                confidence=float(result.get("confidence", 0.0)),
                secondary_intents=result.get("secondary_intents", []),
                reasoning=result.get("reasoning", "")
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {response[:200]}")
            return IntentClassificationResult(
                primary_intent="unknown",
                confidence=0.0,
                secondary_intents=[],
                reasoning=""
            )
    
    def analyze_workflow(
        self,
        workflow_steps: List[Dict[str, Any]],
        workflow_name: str = "",
        base_url: str = ""
    ) -> WorkflowAnalysisResult:
        """
        Analyze a recorded workflow and provide insights.
        
        Args:
            workflow_steps: List of workflow steps
            workflow_name: Name of the workflow
            base_url: Base URL of the workflow
        
        Returns:
            Workflow analysis result
        """
        # Build step description
        steps_text = "\n".join([
            f"{i+1}. {step.get('type', 'action')} - {step.get('action', '')} "
            f"({step.get('selector', 'no selector')[:50]})"
            for i, step in enumerate(workflow_steps[:20])  # Limit to first 20 steps
        ])
        
        context = f"Workflow: {workflow_name}\nURL: {base_url}\n\n" if workflow_name or base_url else ""
        
        system_prompt = """You are an AI that analyzes test automation workflows.
Assess complexity as: simple (1-5 steps), moderate (6-15 steps), complex (16+ steps).
Provide actionable suggestions. Respond ONLY with valid JSON."""
        
        prompt = f"""Analyze this test workflow and provide insights:

{context}Steps ({len(workflow_steps)} total):
{steps_text}

Provide analysis in this exact JSON format:
{{
  "summary": "one sentence summary",
  "purpose": "what the workflow does",
  "steps_count": {len(workflow_steps)},
  "complexity": "simple/moderate/complex",
  "suggestions": ["suggestion1", "suggestion2", "suggestion3"]
}}"""
        
        response = self.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.5,
            format_json=True
        )
        
        try:
            result = json.loads(response)
            return WorkflowAnalysisResult(
                summary=result.get("summary", "Unknown workflow"),
                purpose=result.get("purpose", ""),
                steps_count=result.get("steps_count", len(workflow_steps)),
                complexity=result.get("complexity", "unknown"),
                suggestions=result.get("suggestions", [])
            )
        except (json.JSONDecodeError, ValueError):
            return WorkflowAnalysisResult(
                summary=f"Workflow with {len(workflow_steps)} steps",
                purpose="",
                steps_count=len(workflow_steps),
                complexity="moderate" if len(workflow_steps) <= 15 else "complex",
                suggestions=[]
            )
    
    def generate_test_description(
        self,
        workflow_steps: List[Dict[str, Any]],
        page_title: str = ""
    ) -> str:
        """Generate a human-readable description of the test workflow."""
        if not self.available:
            return f"Test workflow with {len(workflow_steps)} steps"
        
        steps_text = "\n".join([
            f"{i+1}. {step.get('type', 'action')}"
            for i, step in enumerate(workflow_steps[:10])
        ])
        
        context = f"Page: {page_title}\n\n" if page_title else ""
        
        system_prompt = "You are a technical writer creating clear test descriptions."
        
        prompt = f"""{context}Describe this test in one clear sentence:

Steps:
{steps_text}

Description:"""
        
        description = self.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=60,
            temperature=0.7
        )
        
        return description or f"Test workflow with {len(workflow_steps)} steps"
    
    def suggest_selector_improvement(
        self,
        element_context: Dict[str, Any],
        failed_selectors: List[str]
    ) -> str:
        """Suggest improved selector based on element context and failures."""
        if not self.available:
            return ""
        
        context_str = json.dumps(element_context, indent=2)[:500]  # Limit context size
        failed_str = "\n".join(failed_selectors[:5])
        
        system_prompt = "You are an expert in web automation and CSS/XPath selectors."
        
        prompt = f"""These selectors failed:
{failed_str}

Element context:
{context_str}

Suggest ONE better, more robust selector (CSS or XPath). Explain briefly why it's better.
Response format: "selector | reason"
"""
        
        return self.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=100,
            temperature=0.5
        )
