"""NLP components for semantic understanding and text analysis."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sentence_transformers import SentenceTransformer
from rapidfuzz import fuzz
import spacy
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """User intent categories."""
    INFORMATION_SEEKING = "information_seeking"
    TRANSACTION = "transaction"
    NAVIGATION = "navigation"
    AUTHENTICATION = "authentication"
    CONTENT_CREATION = "content_creation"
    COMMUNICATION = "communication"
    CONFIGURATION = "configuration"
    SEARCH = "search"
    DOWNLOAD = "download"
    UNKNOWN = "unknown"


class ElementRole(str, Enum):
    """Semantic role of UI elements."""
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    FORM = "form"
    MENU = "menu"
    NAVIGATION = "navigation"
    CONTENT = "content"
    MEDIA = "media"
    DIALOG = "dialog"
    UNKNOWN = "unknown"


@dataclass
class SemanticAnalysis:
    """Result of semantic analysis."""
    intent: IntentType
    confidence: float
    keywords: List[str]
    entities: List[Tuple[str, str]]  # (text, label)
    sentiment: float  # -1 to 1
    language: str


class NLPEngine:
    """
    Natural Language Processing engine for semantic understanding.
    Uses BERT embeddings, spaCy, and custom classifiers.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.embedding_model: Optional[SentenceTransformer] = None
        self.spacy_model: Optional[Any] = None
        self.model_name = model_name
        self._intent_embeddings: Dict[IntentType, np.ndarray] = {}
        self._initialize_models()
        self._initialize_intent_embeddings()

    def _initialize_models(self):
        """Load NLP models."""
        try:
            # Load sentence transformer for embeddings
            self.embedding_model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")

        try:
            # Load spaCy model for NER and linguistic features
            self.spacy_model = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model: en_core_web_sm")
        except Exception as e:
            logger.warning(f"spaCy model not available: {e}")
            logger.warning("Run: python -m spacy download en_core_web_sm")

    def _initialize_intent_embeddings(self):
        """Pre-compute embeddings for intent classification."""
        if not self.embedding_model:
            return

        # Representative phrases for each intent
        intent_phrases = {
            IntentType.AUTHENTICATION: [
                "login to my account",
                "sign in with password",
                "create new account registration",
                "logout sign out",
                "forgot password reset"
            ],
            IntentType.TRANSACTION: [
                "buy product checkout",
                "add to shopping cart",
                "make payment purchase",
                "place order complete transaction",
                "proceed to checkout"
            ],
            IntentType.SEARCH: [
                "search for items",
                "find products query",
                "look for information",
                "search results filter"
            ],
            IntentType.NAVIGATION: [
                "go to homepage",
                "navigate to page menu",
                "back to previous next page",
                "open link click menu"
            ],
            IntentType.CONTENT_CREATION: [
                "create new document",
                "write compose message",
                "edit update content",
                "upload file publish post",
                "save draft submit form"
            ],
            IntentType.COMMUNICATION: [
                "send message email",
                "share content social",
                "comment reply post",
                "contact support chat"
            ],
            IntentType.CONFIGURATION: [
                "settings preferences options",
                "configure customize profile",
                "change account settings",
                "update preferences"
            ],
            IntentType.DOWNLOAD: [
                "download file save",
                "export data document",
                "get file attachment"
            ],
            IntentType.INFORMATION_SEEKING: [
                "read information details",
                "view content page",
                "learn more about",
                "check status information"
            ]
        }

        try:
            for intent, phrases in intent_phrases.items():
                # Compute average embedding for all phrases
                embeddings = self.embedding_model.encode(phrases, convert_to_numpy=True)
                self._intent_embeddings[intent] = np.mean(embeddings, axis=0)
            logger.info(f"Initialized embeddings for {len(self._intent_embeddings)} intents")
        except Exception as e:
            logger.warning(f"Failed to initialize intent embeddings: {e}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate BERT embedding for text."""
        if not self.embedding_model:
            return np.zeros(384)  # Default embedding size
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return np.zeros(384)
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        if not self.embedding_model:
            # Fallback to fuzzy string matching
            return fuzz.ratio(text1, text2) / 100.0
        
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return fuzz.ratio(text1, text2) / 100.0
    
    def classify_intent(
        self,
        action_type: str,
        element_text: Optional[str] = None,
        url: Optional[str] = None,
        use_embeddings: bool = True
    ) -> Tuple[IntentType, float]:
        """
        Classify user intent based on action and context.

        Uses hybrid approach:
        1. Semantic similarity with pre-computed intent embeddings (if available)
        2. Keyword matching as fallback/boost

        Args:
            action_type: Type of action (click, type, etc.)
            element_text: Text content of the element
            url: Current page URL
            use_embeddings: Whether to use semantic embeddings

        Returns:
            (intent, confidence) tuple
        """
        text_to_analyze = " ".join(filter(None, [
            action_type,
            element_text or "",
            url or ""
        ])).lower().strip()

        if not text_to_analyze:
            return IntentType.UNKNOWN, 0.0

        # Strategy 1: Semantic similarity using embeddings
        semantic_intent = IntentType.UNKNOWN
        semantic_score = 0.0

        if use_embeddings and self.embedding_model and self._intent_embeddings:
            semantic_intent, semantic_score = self._classify_intent_semantic(text_to_analyze)

        # Strategy 2: Keyword matching
        keyword_intent, keyword_score = self._classify_intent_keywords(text_to_analyze)

        # Combine strategies
        if semantic_score > 0.5 and keyword_score > 0:
            # Both agree or semantic is strong
            if semantic_intent == keyword_intent:
                return semantic_intent, min((semantic_score + keyword_score) / 2 + 0.1, 1.0)
            elif semantic_score > keyword_score:
                return semantic_intent, semantic_score
            else:
                return keyword_intent, keyword_score
        elif semantic_score > 0.6:
            return semantic_intent, semantic_score
        elif keyword_score > 0.3:
            return keyword_intent, keyword_score
        elif semantic_score > 0:
            return semantic_intent, semantic_score

        return IntentType.UNKNOWN, 0.0

    def _classify_intent_semantic(self, text: str) -> Tuple[IntentType, float]:
        """Classify intent using semantic similarity with embeddings."""
        try:
            text_embedding = self.embedding_model.encode(text, convert_to_numpy=True)

            best_intent = IntentType.UNKNOWN
            best_similarity = 0.0

            for intent, intent_embedding in self._intent_embeddings.items():
                # Cosine similarity
                similarity = np.dot(text_embedding, intent_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(intent_embedding)
                )
                similarity = float(similarity)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_intent = intent

            # Normalize similarity to confidence (typical range 0.3-0.8)
            confidence = max(0.0, min(1.0, (best_similarity - 0.2) / 0.6))

            return best_intent, confidence

        except Exception as e:
            logger.debug(f"Semantic classification failed: {e}")
            return IntentType.UNKNOWN, 0.0

    def _classify_intent_keywords(self, text: str) -> Tuple[IntentType, float]:
        """Classify intent using keyword matching."""
        intent_keywords = {
            IntentType.AUTHENTICATION: [
                "login", "sign in", "log in", "register", "sign up",
                "password", "logout", "sign out"
            ],
            IntentType.TRANSACTION: [
                "buy", "purchase", "checkout", "cart", "payment",
                "pay", "order", "add to cart", "proceed"
            ],
            IntentType.SEARCH: [
                "search", "find", "query", "look for", "explore"
            ],
            IntentType.NAVIGATION: [
                "menu", "home", "back", "next", "previous", "navigate"
            ],
            IntentType.CONTENT_CREATION: [
                "create", "compose", "write", "edit", "upload",
                "post", "publish", "save", "submit"
            ],
            IntentType.COMMUNICATION: [
                "send", "message", "email", "share", "comment",
                "reply", "contact"
            ],
            IntentType.CONFIGURATION: [
                "settings", "preferences", "configure", "options",
                "customize", "profile"
            ],
            IntentType.DOWNLOAD: [
                "download", "export", "save as", "get"
            ]
        }

        best_intent = IntentType.UNKNOWN
        best_score = 0.0

        for intent, keywords in intent_keywords.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text:
                    score += 1.0
                else:
                    # Fuzzy matching
                    fuzzy_score = fuzz.partial_ratio(keyword, text) / 100.0
                    if fuzzy_score > 0.8:
                        score += fuzzy_score * 0.5

            if score > best_score:
                best_score = score
                best_intent = intent

        # Normalize confidence
        confidence = min(best_score / 3.0, 1.0)

        return best_intent, confidence
    
    def classify_element_role(
        self,
        tag_name: str,
        element_text: Optional[str] = None,
        aria_role: Optional[str] = None,
        element_type: Optional[str] = None
    ) -> Tuple[ElementRole, float]:
        """
        Classify the semantic role of a UI element.
        Returns (role, confidence).
        """
        # Priority to explicit ARIA roles
        aria_role_map = {
            "button": ElementRole.BUTTON,
            "link": ElementRole.LINK,
            "textbox": ElementRole.INPUT,
            "searchbox": ElementRole.INPUT,
            "form": ElementRole.FORM,
            "navigation": ElementRole.NAVIGATION,
            "menu": ElementRole.MENU,
            "menuitem": ElementRole.MENU,
            "dialog": ElementRole.DIALOG,
            "img": ElementRole.MEDIA,
            "video": ElementRole.MEDIA
        }
        
        if aria_role and aria_role.lower() in aria_role_map:
            return aria_role_map[aria_role.lower()], 0.95
        
        # Tag-based classification
        tag_role_map = {
            "button": ElementRole.BUTTON,
            "a": ElementRole.LINK,
            "input": ElementRole.INPUT,
            "textarea": ElementRole.INPUT,
            "select": ElementRole.INPUT,
            "form": ElementRole.FORM,
            "nav": ElementRole.NAVIGATION,
            "img": ElementRole.MEDIA,
            "video": ElementRole.MEDIA,
            "audio": ElementRole.MEDIA
        }
        
        if tag_name.lower() in tag_role_map:
            return tag_role_map[tag_name.lower()], 0.85
        
        # Text-based classification for generic elements
        if element_text:
            text_lower = element_text.lower()
            
            button_keywords = ["click", "submit", "send", "buy", "add", "get", "start"]
            if any(kw in text_lower for kw in button_keywords):
                return ElementRole.BUTTON, 0.70
            
            link_keywords = ["learn more", "read more", "details", "view"]
            if any(kw in text_lower for kw in link_keywords):
                return ElementRole.LINK, 0.65
        
        # Type attribute for inputs
        if element_type:
            type_lower = element_type.lower()
            if type_lower in ["text", "email", "password", "search", "tel", "url"]:
                return ElementRole.INPUT, 0.80
            elif type_lower in ["button", "submit"]:
                return ElementRole.BUTTON, 0.80
        
        return ElementRole.UNKNOWN, 0.0
    
    def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract named entities from text using spaCy."""
        if not self.spacy_model:
            return []
        
        try:
            doc = self.spacy_model(text)
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            return entities
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract important keywords from text."""
        if not self.spacy_model:
            # Simple fallback: split and filter
            words = text.lower().split()
            return [w for w in words if len(w) > 3][:top_n]
        
        try:
            doc = self.spacy_model(text)
            
            # Extract nouns, verbs, and adjectives
            keywords = []
            for token in doc:
                if (token.pos_ in ["NOUN", "VERB", "ADJ"] and 
                    not token.is_stop and 
                    len(token.text) > 2):
                    keywords.append(token.lemma_.lower())
            
            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)
            
            return unique_keywords[:top_n]
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        try:
            return detect(text)
        except LangDetectException:
            return "en"  # Default to English
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text.
        Returns score from -1 (negative) to 1 (positive).
        """
        # Simple rule-based sentiment (in production, use fine-tuned model)
        positive_words = [
            "good", "great", "excellent", "happy", "love", "wonderful",
            "amazing", "perfect", "best", "fantastic", "awesome"
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "worst", "horrible",
            "poor", "disappointing", "useless", "broken"
        ]
        
        text_lower = text.lower()
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        sentiment = (pos_count - neg_count) / total
        return sentiment
    
    def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> SemanticAnalysis:
        """
        Comprehensive text analysis.
        
        Args:
            text: Text to analyze
            context: Optional context (action_type, url, etc.)
        
        Returns:
            SemanticAnalysis with all extracted information
        """
        context = context or {}
        
        # Classify intent
        intent, confidence = self.classify_intent(
            action_type=context.get("action_type", ""),
            element_text=text,
            url=context.get("url")
        )
        
        # Extract keywords
        keywords = self.extract_keywords(text)
        
        # Extract entities
        entities = self.extract_entities(text)
        
        # Analyze sentiment
        sentiment = self.analyze_sentiment(text)
        
        # Detect language
        language = self.detect_language(text)
        
        return SemanticAnalysis(
            intent=intent,
            confidence=confidence,
            keywords=keywords,
            entities=entities,
            sentiment=sentiment,
            language=language
        )
    
    def fuzzy_match_elements(
        self,
        target_text: str,
        candidate_texts: List[str],
        threshold: int = 80
    ) -> List[Tuple[str, int, int]]:
        """
        Find fuzzy matches for target text in candidates.
        Returns list of (text, score, index) tuples.
        """
        from rapidfuzz import process
        
        matches = process.extract(
            target_text,
            candidate_texts,
            scorer=fuzz.ratio,
            limit=5
        )
        
        return [(match[0], match[1], match[2]) for match in matches if match[1] >= threshold]
