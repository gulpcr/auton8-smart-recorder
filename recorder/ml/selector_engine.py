"""Multi-dimensional ML-powered selector generation engine."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class SelectorType(str, Enum):
    """Types of selectors with priority ranking."""
    ID = "id"
    DATA_TESTID = "data-testid"
    ARIA_LABEL = "aria-label"
    CSS = "css"
    XPATH_RELATIVE = "xpath-relative"
    XPATH_ABSOLUTE = "xpath-absolute"
    TEXT = "text"
    VISUAL = "visual"
    POSITION = "position"


@dataclass
class SelectorStrategy:
    """A selector strategy with confidence score."""
    type: SelectorType
    value: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ElementFingerprint:
    """Complete multi-dimensional fingerprint of an element."""
    # Structural
    tag_name: str
    id: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    xpath_abs: Optional[str] = None
    xpath_rel: Optional[str] = None
    css_selector: Optional[str] = None
    
    # Semantic
    text_content: Optional[str] = None
    aria_label: Optional[str] = None
    aria_role: Optional[str] = None
    placeholder: Optional[str] = None
    title: Optional[str] = None
    
    # Visual
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    color_signature: Optional[str] = None
    visual_hash: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    # Behavioral
    event_listeners: List[str] = field(default_factory=list)
    framework_info: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    parent_chain: List[str] = field(default_factory=list)
    sibling_count: int = 0
    depth: int = 0
    viewport_position: Tuple[int, int] = (0, 0)
    
    # Stability indicators
    has_dynamic_id: bool = False
    has_stable_attributes: bool = True
    is_in_iframe: bool = False
    frame_path: List[str] = field(default_factory=list)
    shadow_path: List[str] = field(default_factory=list)


class MultiDimensionalSelectorEngine:
    """
    Advanced selector generation using ML and multi-dimensional analysis.
    Generates robust selectors with automatic fallback strategies.
    """

    def __init__(self, model_path: Optional[str] = None):
        import threading
        self._lock = threading.Lock()
        self.selector_ranker: Optional[RandomForestClassifier] = None
        self._model_trained = False
        self._model_path = model_path
        self._selector_history: List[Dict[str, Any]] = []
        self._min_samples_for_training = 30
        self._auto_train_threshold = 50
        self._samples_since_last_train = 0
        self._initialize_ranker()

    def _initialize_ranker(self):
        """Initialize ML model for selector ranking."""
        self.selector_ranker = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1  # Use all CPU cores
        )

        # Try to load pre-trained model
        if self._model_path:
            self._load_model(self._model_path)

        logger.info("Selector ranker initialized (trained=%s)", self._model_trained)

    def _load_model(self, path: str) -> bool:
        """Load a pre-trained model from disk."""
        import os
        import pickle

        if os.path.exists(path):
            # Validate path doesn't escape project directory
            resolved = os.path.realpath(path)
            if ".." in os.path.relpath(resolved, os.getcwd()):
                logger.warning(f"Refusing to load model from outside project: {path}")
                return False
            try:
                with open(path, 'rb') as f:
                    self.selector_ranker = pickle.load(f)
                self._model_trained = True
                logger.info(f"Loaded pre-trained selector model from {path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load selector model: {e}")
        return False

    def save_model(self, path: str) -> bool:
        """Save trained model to disk."""
        import pickle
        if not self._model_trained:
            logger.warning("Cannot save untrained model")
            return False
        try:
            with open(path, 'wb') as f:
                pickle.dump(self.selector_ranker, f)
            logger.info(f"Saved selector model to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save selector model: {e}")
            return False

    def record_selector_result(
        self,
        selector: SelectorStrategy,
        fingerprint: ElementFingerprint,
        success: bool,
        execution_time_ms: float = 0.0
    ):
        """
        Record whether a selector worked or failed.
        Used to train the ML model for better ranking.
        """
        features = self._extract_selector_features(selector, fingerprint)
        with self._lock:
            self._selector_history.append({
                "features": features.tolist(),
                "selector_type": selector.type.value,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "base_score": selector.score,
            })

            # Keep only recent history
            if len(self._selector_history) > 2000:
                self._selector_history = self._selector_history[-2000:]

            self._samples_since_last_train += 1

            # Auto-train when enough new samples
            should_train = (self._samples_since_last_train >= self._auto_train_threshold and
                    len(self._selector_history) >= self._min_samples_for_training)

        if should_train:
            self._auto_train()

    def _auto_train(self):
        """Automatically retrain model when enough data is collected."""
        logger.info("Auto-training selector ranker with new data...")
        self.train_ranker()
        self._samples_since_last_train = 0

    def train_ranker(self) -> bool:
        """
        Train the RandomForest model on selector history.

        The model learns to predict which selectors will succeed,
        allowing better ranking of selector strategies.

        Returns:
            True if training succeeded, False otherwise.
        """
        with self._lock:
            if len(self._selector_history) < self._min_samples_for_training:
                logger.warning(
                    f"Not enough selector history to train "
                    f"({len(self._selector_history)}/{self._min_samples_for_training})"
                )
                return False

            # Need both success and failure examples
            successes = sum(1 for r in self._selector_history if r["success"])
            failures = len(self._selector_history) - successes

            if successes < 5 or failures < 5:
                logger.warning(
                    f"Need both success and failure examples "
                    f"(success={successes}, failure={failures})"
                )
                return False

            # Prepare training data
            X = []
            y = []

            for record in self._selector_history:
                X.append(record["features"])
                y.append(1 if record["success"] else 0)

            X = np.array(X)
            y = np.array(y)

            try:
                self.selector_ranker.fit(X, y)
                self._model_trained = True

                # Log training stats
                logger.info(
                    f"Selector ranker trained on {len(X)} samples "
                    f"(success={successes}, failure={failures})"
                )
                return True

            except Exception as e:
                logger.error(f"Selector ranker training failed: {e}")
                return False

    def is_model_ready(self) -> bool:
        """Check if the ML model is trained and ready."""
        return self._model_trained
    
    def generate_selectors(self, fingerprint: ElementFingerprint) -> List[SelectorStrategy]:
        """
        Generate all possible selectors for an element.
        Returns ordered list by predicted robustness.
        """
        selectors: List[SelectorStrategy] = []
        
        # Strategy 1: ID selector (highest priority if stable)
        if fingerprint.id and not fingerprint.has_dynamic_id:
            selectors.append(SelectorStrategy(
                type=SelectorType.ID,
                value=f"#{fingerprint.id}",
                score=0.95,
                metadata={"stable": True}
            ))
        
        # Strategy 2: Data-testid (very stable)
        if "data-testid" in fingerprint.attributes:
            selectors.append(SelectorStrategy(
                type=SelectorType.DATA_TESTID,
                value=f"[data-testid='{fingerprint.attributes['data-testid']}']",
                score=0.93,
                metadata={"stable": True}
            ))
        
        # Strategy 3: ARIA labels (semantic, stable)
        if fingerprint.aria_label:
            selectors.append(SelectorStrategy(
                type=SelectorType.ARIA_LABEL,
                value=f"[aria-label='{fingerprint.aria_label}']",
                score=0.88,
                metadata={"semantic": True}
            ))
        
        # Strategy 4: Smart CSS selector (combination of stable attributes)
        css_sel = self._generate_smart_css(fingerprint)
        if css_sel:
            selectors.append(SelectorStrategy(
                type=SelectorType.CSS,
                value=css_sel,
                score=0.82,
                metadata={"multi_attribute": True}
            ))
        
        # Strategy 5: Relative XPath (resilient to structure changes)
        if fingerprint.xpath_rel:
            selectors.append(SelectorStrategy(
                type=SelectorType.XPATH_RELATIVE,
                value=fingerprint.xpath_rel,
                score=0.75,
                metadata={"relative": True}
            ))
        
        # Strategy 6: Text-based selector (semantic fallback)
        if fingerprint.text_content and len(fingerprint.text_content.strip()) > 0:
            text = fingerprint.text_content.strip()[:50]
            selectors.append(SelectorStrategy(
                type=SelectorType.TEXT,
                value=text,
                score=0.70,
                metadata={"fuzzy": True, "max_distance": 10}
            ))
        
        # Strategy 7: Visual selector (screenshot-based)
        if fingerprint.visual_hash:
            selectors.append(SelectorStrategy(
                type=SelectorType.VISUAL,
                value=fingerprint.visual_hash,
                score=0.65,
                metadata={
                    "bbox": fingerprint.bounding_box,
                    "screenshot": fingerprint.screenshot_path
                }
            ))
        
        # Strategy 8: Position-based (last resort)
        if fingerprint.viewport_position != (0, 0):
            selectors.append(SelectorStrategy(
                type=SelectorType.POSITION,
                value=json.dumps({
                    "x": fingerprint.viewport_position[0],
                    "y": fingerprint.viewport_position[1],
                    "bbox": fingerprint.bounding_box
                }),
                score=0.50,
                metadata={"tolerance": 20}
            ))
        
        # Strategy 9: Absolute XPath (brittle but works)
        if fingerprint.xpath_abs:
            selectors.append(SelectorStrategy(
                type=SelectorType.XPATH_ABSOLUTE,
                value=fingerprint.xpath_abs,
                score=0.40,
                metadata={"brittle": True}
            ))
        
        # Rank selectors using ML model
        selectors = self._rank_selectors(selectors, fingerprint)
        
        return selectors
    
    def _generate_smart_css(self, fp: ElementFingerprint) -> Optional[str]:
        """Generate intelligent CSS selector using stable attributes."""
        parts = [fp.tag_name] if fp.tag_name else []
        
        # Prioritize stable attributes
        stable_attrs = ["name", "type", "role", "data-testid", "data-qa"]
        
        for attr in stable_attrs:
            if attr in fp.attributes:
                parts.append(f"[{attr}='{fp.attributes[attr]}']")
        
        # Add classes if not dynamic
        stable_classes = [c for c in fp.classes if not self._is_dynamic_class(c)]
        if stable_classes:
            parts.append("." + ".".join(stable_classes[:3]))  # Max 3 classes
        
        return "".join(parts) if parts else None
    
    def _is_dynamic_class(self, class_name: str) -> bool:
        """Detect if a class name is likely dynamically generated."""
        # Check for common patterns: hash-like strings, random IDs
        if len(class_name) > 20 and any(c.isdigit() for c in class_name):
            return True
        if any(pattern in class_name for pattern in ["_", "-", "hash", "random", "uuid"]):
            digit_ratio = sum(c.isdigit() for c in class_name) / len(class_name)
            if digit_ratio > 0.3:
                return True
        return False
    
    def _rank_selectors(
        self,
        selectors: List[SelectorStrategy],
        fingerprint: ElementFingerprint
    ) -> List[SelectorStrategy]:
        """Use ML to rank selectors by predicted robustness."""
        if not selectors:
            return selectors

        # If model is trained, use ML predictions to adjust scores
        with self._lock:
            model_trained = self._model_trained
        if model_trained:
            try:
                # Extract features for all selectors
                features_list = [
                    self._extract_selector_features(selector, fingerprint)
                    for selector in selectors
                ]
                X = np.array(features_list)

                # Get probability of success for each selector
                with self._lock:
                    probabilities = self.selector_ranker.predict_proba(X)

                # Adjust scores: combine base score with ML prediction
                # ML prediction weight increases with model confidence
                for i, selector in enumerate(selectors):
                    ml_score = probabilities[i][1]  # Probability of class 1 (success)
                    # Weighted combination: 40% base score, 60% ML prediction
                    selector.score = 0.4 * selector.score + 0.6 * ml_score
                    selector.metadata["ml_score"] = round(ml_score, 3)

                logger.debug(f"ML-ranked {len(selectors)} selectors")

            except Exception as e:
                logger.warning(f"ML ranking failed, using base scores: {e}")

        # Sort by score (descending)
        return sorted(selectors, key=lambda s: s.score, reverse=True)
    
    def _extract_selector_features(
        self,
        selector: SelectorStrategy,
        fp: ElementFingerprint
    ) -> np.ndarray:
        """
        Extract features for ML ranking.

        Features are designed to capture:
        - Selector type (one-hot encoded)
        - Element stability indicators
        - DOM complexity metrics
        - Selector quality indicators
        """
        features = [
            # Selector type one-hot (9 types)
            1.0 if selector.type == SelectorType.ID else 0.0,
            1.0 if selector.type == SelectorType.DATA_TESTID else 0.0,
            1.0 if selector.type == SelectorType.ARIA_LABEL else 0.0,
            1.0 if selector.type == SelectorType.CSS else 0.0,
            1.0 if selector.type == SelectorType.XPATH_RELATIVE else 0.0,
            1.0 if selector.type == SelectorType.XPATH_ABSOLUTE else 0.0,
            1.0 if selector.type == SelectorType.TEXT else 0.0,
            1.0 if selector.type == SelectorType.VISUAL else 0.0,
            1.0 if selector.type == SelectorType.POSITION else 0.0,

            # Element stability
            1.0 if fp.has_stable_attributes else 0.0,
            1.0 if fp.has_dynamic_id else 0.0,
            1.0 if fp.id is not None else 0.0,

            # DOM complexity
            min(float(fp.depth) / 20.0, 1.0),  # Normalized depth
            min(float(fp.sibling_count) / 10.0, 1.0),  # Normalized siblings
            min(float(len(fp.classes)) / 10.0, 1.0),  # Normalized class count
            min(float(len(fp.attributes)) / 15.0, 1.0),  # Normalized attr count

            # Context
            1.0 if fp.is_in_iframe else 0.0,
            1.0 if fp.text_content else 0.0,
            1.0 if fp.aria_label else 0.0,
            1.0 if fp.visual_hash else 0.0,

            # Selector metadata
            1.0 if selector.metadata.get("stable") else 0.0,
            1.0 if selector.metadata.get("semantic") else 0.0,
            1.0 if selector.metadata.get("brittle") else 0.0,

            # Base score (heuristic)
            selector.score,
        ]
        return np.array(features)
    
    def calculate_similarity(
        self, 
        fp1: ElementFingerprint, 
        fp2: ElementFingerprint
    ) -> float:
        """Calculate similarity between two element fingerprints."""
        scores = []
        
        # Structural similarity
        if fp1.tag_name == fp2.tag_name:
            scores.append(1.0)
        
        # Attribute similarity
        common_attrs = set(fp1.attributes.keys()) & set(fp2.attributes.keys())
        if common_attrs:
            attr_score = sum(
                1.0 for attr in common_attrs 
                if fp1.attributes[attr] == fp2.attributes[attr]
            ) / len(common_attrs)
            scores.append(attr_score)
        
        # Text similarity (fuzzy matching)
        if fp1.text_content and fp2.text_content:
            text_score = fuzz.ratio(fp1.text_content, fp2.text_content) / 100.0
            scores.append(text_score)
        
        # Visual similarity (bounding box overlap)
        if fp1.bounding_box != (0, 0, 0, 0) and fp2.bounding_box != (0, 0, 0, 0):
            overlap = self._calculate_bbox_overlap(fp1.bounding_box, fp2.bounding_box)
            scores.append(overlap)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_bbox_overlap(
        self, 
        bbox1: Tuple[int, int, int, int], 
        bbox2: Tuple[int, int, int, int]
    ) -> float:
        """Calculate IoU (Intersection over Union) for bounding boxes."""
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1, w2, h2 = bbox2
        
        x1_2, y1_2 = x1_1 + w1, y1_1 + h1
        x2_2, y2_2 = x2_1 + w2, y2_1 + h2
        
        # Calculate intersection
        x_left = max(x1_1, x2_1)
        y_top = max(y1_1, y2_1)
        x_right = min(x1_2, x2_2)
        y_bottom = min(y1_2, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about selector performance."""
        if not self._selector_history:
            return {
                "total_records": 0,
                "model_trained": self._model_trained,
            }

        successes = sum(1 for r in self._selector_history if r["success"])
        failures = len(self._selector_history) - successes

        # Count by selector type
        type_stats = {}
        for record in self._selector_history:
            stype = record["selector_type"]
            if stype not in type_stats:
                type_stats[stype] = {"success": 0, "failure": 0}
            if record["success"]:
                type_stats[stype]["success"] += 1
            else:
                type_stats[stype]["failure"] += 1

        # Calculate success rate per type
        type_success_rates = {}
        for stype, counts in type_stats.items():
            total = counts["success"] + counts["failure"]
            type_success_rates[stype] = round(counts["success"] / total, 3) if total > 0 else 0

        return {
            "total_records": len(self._selector_history),
            "successes": successes,
            "failures": failures,
            "overall_success_rate": round(successes / len(self._selector_history), 3),
            "type_success_rates": type_success_rates,
            "model_trained": self._model_trained,
            "samples_until_retrain": max(0, self._auto_train_threshold - self._samples_since_last_train),
        }

    def save_history(self, path: str) -> bool:
        """Save selector history to JSON file."""
        try:
            with open(path, 'w') as f:
                json.dump({
                    "history": self._selector_history,
                    "model_trained": self._model_trained,
                }, f, indent=2)
            logger.info(f"Saved {len(self._selector_history)} selector records to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save selector history: {e}")
            return False

    def load_history(self, path: str) -> bool:
        """Load selector history from JSON file."""
        import os
        if not os.path.exists(path):
            logger.warning(f"History file not found: {path}")
            return False
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self._selector_history = data.get("history", [])
            logger.info(f"Loaded {len(self._selector_history)} selector records from {path}")

            # Auto-train if we have enough data
            if (len(self._selector_history) >= self._min_samples_for_training
                    and not self._model_trained):
                logger.info("Training model on loaded history...")
                self.train_ranker()

            return True
        except Exception as e:
            logger.error(f"Failed to load selector history: {e}")
            return False


def create_fingerprint_from_dom(element_data: Dict[str, Any]) -> ElementFingerprint:
    """Create element fingerprint from DOM data."""
    return ElementFingerprint(
        tag_name=element_data.get("tagName", ""),
        id=element_data.get("id"),
        classes=element_data.get("classes", []),
        attributes=element_data.get("attributes", {}),
        xpath_abs=element_data.get("xpathAbsolute"),
        xpath_rel=element_data.get("xpathRelative"),
        css_selector=element_data.get("cssSelector"),
        text_content=element_data.get("textContent"),
        aria_label=element_data.get("ariaLabel"),
        aria_role=element_data.get("ariaRole"),
        placeholder=element_data.get("placeholder"),
        title=element_data.get("title"),
        bounding_box=tuple(element_data.get("boundingBox", [0, 0, 0, 0])),
        color_signature=element_data.get("colorSignature"),
        visual_hash=element_data.get("visualHash"),
        screenshot_path=element_data.get("screenshot"),
        event_listeners=element_data.get("eventListeners", []),
        framework_info=element_data.get("frameworkInfo", {}),
        parent_chain=element_data.get("parentChain", []),
        sibling_count=element_data.get("siblingCount", 0),
        depth=element_data.get("depth", 0),
        viewport_position=tuple(element_data.get("viewportPosition", [0, 0])),
        has_dynamic_id=element_data.get("hasDynamicId", False),
        has_stable_attributes=element_data.get("hasStableAttributes", True),
        is_in_iframe=element_data.get("isInIframe", False),
        frame_path=element_data.get("framePath", []),
        shadow_path=element_data.get("shadowPath", [])
    )
