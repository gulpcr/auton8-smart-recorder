"""Intelligent selector healing using XGBoost and multi-strategy fallback."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
import xgboost as xgb
from rapidfuzz import fuzz, process

from recorder.ml.selector_engine import (
    ElementFingerprint, 
    SelectorStrategy,
    MultiDimensionalSelectorEngine
)
from recorder.ml.vision_engine import VisualElementMatcher

logger = logging.getLogger(__name__)


class HealingStrategy(str, Enum):
    """Different healing strategies with priority."""
    SELECTOR_FALLBACK = "selector_fallback"
    VISUAL_MATCH = "visual_match"
    TEXT_FUZZY = "text_fuzzy"
    POSITION_BASED = "position_based"
    STRUCTURAL_SIMILARITY = "structural_similarity"
    ML_PREDICTION = "ml_prediction"


# Map strategies to numeric labels for ML
STRATEGY_TO_LABEL = {
    HealingStrategy.SELECTOR_FALLBACK: 0,
    HealingStrategy.VISUAL_MATCH: 1,
    HealingStrategy.TEXT_FUZZY: 2,
    HealingStrategy.POSITION_BASED: 3,
    HealingStrategy.STRUCTURAL_SIMILARITY: 4,
}
LABEL_TO_STRATEGY = {v: k for k, v in STRATEGY_TO_LABEL.items()}


@dataclass
class HealingResult:
    """Result of a healing attempt."""
    success: bool
    strategy: HealingStrategy
    confidence: float
    element_data: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0
    fallback_selector: Optional[str] = None


class SelectorHealingEngine:
    """
    Advanced selector healing using ML and multiple fallback strategies.
    Automatically repairs broken selectors during replay.
    """

    def __init__(self, model_path: Optional[str] = None):
        import threading
        self._lock = threading.Lock()
        self.selector_engine = MultiDimensionalSelectorEngine()
        self.vision_matcher = VisualElementMatcher()
        self.healing_model: Optional[xgb.XGBClassifier] = None
        self.healing_history: List[Dict[str, Any]] = []
        self._model_trained = False
        self._model_path = model_path
        self._min_samples_for_training = 50
        self._auto_train_threshold = 100  # Auto-retrain every N new samples
        self._samples_since_last_train = 0
        self._initialize_model()

    def _initialize_model(self):
        """Initialize XGBoost model for healing strategy prediction."""
        # Model predicts WHICH strategy will work best (multi-class)
        self.healing_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='multi:softprob',  # Multi-class probability
            num_class=len(STRATEGY_TO_LABEL),
            random_state=42,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )

        # Try to load pre-trained model
        if self._model_path:
            self._load_model(self._model_path)

        logger.info("Healing model initialized (trained=%s)", self._model_trained)

    def _load_model(self, path: str) -> bool:
        """Load a pre-trained model from disk."""
        import os
        if os.path.exists(path):
            try:
                self.healing_model.load_model(path)
                self._model_trained = True
                logger.info(f"Loaded pre-trained healing model from {path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load healing model: {e}")
        return False

    def save_model(self, path: str) -> bool:
        """Save trained model to disk."""
        if not self._model_trained:
            logger.warning("Cannot save untrained model")
            return False
        try:
            self.healing_model.save_model(path)
            logger.info(f"Saved healing model to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save healing model: {e}")
            return False
    
    def heal_selector(
        self,
        original_fingerprint: ElementFingerprint,
        selector_strategies: List[SelectorStrategy],
        current_page_state: Dict[str, Any],
        screenshot: Optional[np.ndarray] = None
    ) -> HealingResult:
        """
        Attempt to heal a broken selector using multiple strategies.
        
        Args:
            original_fingerprint: Original element fingerprint
            selector_strategies: Ranked selector strategies to try
            current_page_state: Current page DOM state
            screenshot: Current page screenshot (for visual matching)
        
        Returns:
            HealingResult with success status and healed selector
        """
        import time
        start_time = time.time()
        
        # Strategy 1: Try selector fallbacks in order
        for selector in selector_strategies:
            result = self._try_selector_fallback(selector, current_page_state)
            if result.success:
                result.execution_time_ms = (time.time() - start_time) * 1000
                self._record_healing_success(result, original_fingerprint)
                return result
        
        # Strategy 2: Visual matching (if screenshot available)
        if screenshot is not None and original_fingerprint.visual_hash:
            result = self._try_visual_healing(original_fingerprint, screenshot)
            if result.success:
                result.execution_time_ms = (time.time() - start_time) * 1000
                self._record_healing_success(result, original_fingerprint)
                return result
        
        # Strategy 3: Fuzzy text matching
        if original_fingerprint.text_content:
            result = self._try_text_fuzzy_healing(original_fingerprint, current_page_state)
            if result.success:
                result.execution_time_ms = (time.time() - start_time) * 1000
                self._record_healing_success(result, original_fingerprint)
                return result
        
        # Strategy 4: Position-based healing
        if original_fingerprint.bounding_box != (0, 0, 0, 0):
            result = self._try_position_healing(original_fingerprint, current_page_state)
            if result.success:
                result.execution_time_ms = (time.time() - start_time) * 1000
                self._record_healing_success(result, original_fingerprint)
                return result
        
        # Strategy 5: Structural similarity (find similar elements)
        result = self._try_structural_healing(original_fingerprint, current_page_state)
        if result.success:
            result.execution_time_ms = (time.time() - start_time) * 1000
            self._record_healing_success(result, original_fingerprint)
            return result
        
        # Strategy 6: ML prediction (learn from past healings)
        if self._model_trained:
            result = self._try_ml_healing(
                original_fingerprint, current_page_state, screenshot
            )
            if result.success:
                result.execution_time_ms = (time.time() - start_time) * 1000
                self._record_healing_success(result, original_fingerprint)
                return result

        # All strategies failed - record the failure for learning
        execution_time = (time.time() - start_time) * 1000
        self._record_healing_failure(
            original_fingerprint,
            HealingStrategy.SELECTOR_FALLBACK,  # Mark as general failure
            execution_time
        )
        return HealingResult(
            success=False,
            strategy=HealingStrategy.SELECTOR_FALLBACK,
            confidence=0.0,
            execution_time_ms=execution_time
        )
    
    def _try_selector_fallback(
        self,
        selector: SelectorStrategy,
        page_state: Dict[str, Any]
    ) -> HealingResult:
        """Try a selector from the fallback list."""
        # In real implementation, this would execute selector on page
        # For now, simulate selector execution
        elements = page_state.get("elements", [])
        
        for elem in elements:
            if self._selector_matches_element(selector, elem):
                return HealingResult(
                    success=True,
                    strategy=HealingStrategy.SELECTOR_FALLBACK,
                    confidence=selector.score,
                    element_data=elem,
                    fallback_selector=selector.value
                )
        
        return HealingResult(
            success=False,
            strategy=HealingStrategy.SELECTOR_FALLBACK,
            confidence=0.0
        )
    
    def _try_visual_healing(
        self,
        fingerprint: ElementFingerprint,
        screenshot: np.ndarray
    ) -> HealingResult:
        """Use computer vision to find element by visual similarity."""
        if not fingerprint.visual_hash or not fingerprint.bounding_box:
            return HealingResult(
                success=False,
                strategy=HealingStrategy.VISUAL_MATCH,
                confidence=0.0
            )
        
        # Find element by visual similarity
        position = self.vision_matcher.find_element_by_visual_similarity(
            screenshot,
            fingerprint.visual_hash,
            fingerprint.bounding_box,
            tolerance=50
        )
        
        if position:
            x, y = position
            return HealingResult(
                success=True,
                strategy=HealingStrategy.VISUAL_MATCH,
                confidence=0.80,
                element_data={"position": position, "x": x, "y": y}
            )
        
        return HealingResult(
            success=False,
            strategy=HealingStrategy.VISUAL_MATCH,
            confidence=0.0
        )
    
    def _try_text_fuzzy_healing(
        self,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any]
    ) -> HealingResult:
        """Use fuzzy text matching to find element."""
        target_text = fingerprint.text_content
        if not target_text:
            return HealingResult(
                success=False,
                strategy=HealingStrategy.TEXT_FUZZY,
                confidence=0.0
            )
        
        elements = page_state.get("elements", [])
        element_texts = [
            (elem, elem.get("textContent", ""))
            for elem in elements
            if elem.get("textContent")
        ]
        
        if not element_texts:
            return HealingResult(
                success=False,
                strategy=HealingStrategy.TEXT_FUZZY,
                confidence=0.0
            )
        
        # Find best fuzzy match
        texts_only = [text for _, text in element_texts]
        best_match = process.extractOne(
            target_text,
            texts_only,
            scorer=fuzz.ratio
        )
        
        if best_match and best_match[1] >= 80:  # 80% similarity threshold
            matched_text, score, idx = best_match
            matched_element = element_texts[idx][0]
            
            return HealingResult(
                success=True,
                strategy=HealingStrategy.TEXT_FUZZY,
                confidence=score / 100.0,
                element_data=matched_element
            )
        
        return HealingResult(
            success=False,
            strategy=HealingStrategy.TEXT_FUZZY,
            confidence=0.0
        )
    
    def _try_position_healing(
        self,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any]
    ) -> HealingResult:
        """Find element by approximate position."""
        target_bbox = fingerprint.bounding_box
        if target_bbox == (0, 0, 0, 0):
            return HealingResult(
                success=False,
                strategy=HealingStrategy.POSITION_BASED,
                confidence=0.0
            )
        
        target_x, target_y, target_w, target_h = target_bbox
        target_center = (target_x + target_w // 2, target_y + target_h // 2)
        
        elements = page_state.get("elements", [])
        tolerance = 50  # pixels
        
        for elem in elements:
            elem_bbox = elem.get("boundingBox", [0, 0, 0, 0])
            if len(elem_bbox) != 4:
                continue
            
            ex, ey, ew, eh = elem_bbox
            elem_center = (ex + ew // 2, ey + eh // 2)
            
            # Calculate distance
            distance = np.sqrt(
                (target_center[0] - elem_center[0]) ** 2 +
                (target_center[1] - elem_center[1]) ** 2
            )
            
            if distance <= tolerance:
                confidence = 1.0 - (distance / tolerance)
                return HealingResult(
                    success=True,
                    strategy=HealingStrategy.POSITION_BASED,
                    confidence=confidence,
                    element_data=elem
                )
        
        return HealingResult(
            success=False,
            strategy=HealingStrategy.POSITION_BASED,
            confidence=0.0
        )
    
    def _try_structural_healing(
        self,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any]
    ) -> HealingResult:
        """Find element by structural similarity."""
        elements = page_state.get("elements", [])
        
        best_match = None
        best_similarity = 0.0
        
        for elem in elements:
            # Create fingerprint for candidate element
            candidate_fp = self._element_to_fingerprint(elem)
            
            # Calculate similarity
            similarity = self.selector_engine.calculate_similarity(
                fingerprint,
                candidate_fp
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = elem
        
        if best_match and best_similarity >= 0.7:  # 70% similarity threshold
            return HealingResult(
                success=True,
                strategy=HealingStrategy.STRUCTURAL_SIMILARITY,
                confidence=best_similarity,
                element_data=best_match
            )
        
        return HealingResult(
            success=False,
            strategy=HealingStrategy.STRUCTURAL_SIMILARITY,
            confidence=0.0
        )
    
    def _try_ml_healing(
        self,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any],
        screenshot: Optional[np.ndarray] = None
    ) -> HealingResult:
        """Use ML model to predict best healing strategy and execute it."""
        with self._lock:
            model_trained = self._model_trained
        if not model_trained:
            logger.debug("ML healing skipped - model not trained yet")
            return HealingResult(
                success=False,
                strategy=HealingStrategy.ML_PREDICTION,
                confidence=0.0
            )

        # Extract features for prediction
        features = self._extract_healing_features(fingerprint, page_state)

        try:
            # Get probability distribution over strategies
            with self._lock:
                probabilities = self.healing_model.predict_proba([features])[0]

            # Sort strategies by predicted probability (descending)
            strategy_probs = [
                (LABEL_TO_STRATEGY[i], prob)
                for i, prob in enumerate(probabilities)
            ]
            strategy_probs.sort(key=lambda x: x[1], reverse=True)

            logger.debug(f"ML predicted strategy probabilities: {strategy_probs}")

            # Try strategies in order of predicted success
            for strategy, prob in strategy_probs:
                if prob < 0.1:  # Skip very low probability strategies
                    continue

                result = self._execute_strategy(
                    strategy, fingerprint, page_state, screenshot
                )

                if result.success:
                    # Boost confidence based on ML prediction
                    result.confidence = min(1.0, result.confidence * (1 + prob))
                    logger.info(
                        f"ML healing succeeded with {strategy.value} "
                        f"(predicted prob: {prob:.2f})"
                    )
                    return result

        except Exception as e:
            logger.warning(f"ML healing prediction failed: {e}")

        return HealingResult(
            success=False,
            strategy=HealingStrategy.ML_PREDICTION,
            confidence=0.0
        )

    def _execute_strategy(
        self,
        strategy: HealingStrategy,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any],
        screenshot: Optional[np.ndarray] = None
    ) -> HealingResult:
        """Execute a specific healing strategy."""
        if strategy == HealingStrategy.SELECTOR_FALLBACK:
            # Try all selector strategies from the page state
            elements = page_state.get("elements", [])
            if elements:
                return self._try_structural_healing(fingerprint, page_state)
            return HealingResult(
                success=False, strategy=strategy, confidence=0.0
            )

        elif strategy == HealingStrategy.VISUAL_MATCH:
            if screenshot is not None and fingerprint.visual_hash:
                return self._try_visual_healing(fingerprint, screenshot)

        elif strategy == HealingStrategy.TEXT_FUZZY:
            if fingerprint.text_content:
                return self._try_text_fuzzy_healing(fingerprint, page_state)

        elif strategy == HealingStrategy.POSITION_BASED:
            if fingerprint.bounding_box != (0, 0, 0, 0):
                return self._try_position_healing(fingerprint, page_state)

        elif strategy == HealingStrategy.STRUCTURAL_SIMILARITY:
            return self._try_structural_healing(fingerprint, page_state)

        # Strategy not applicable
        return HealingResult(
            success=False,
            strategy=strategy,
            confidence=0.0
        )
    
    def _selector_matches_element(
        self,
        selector: SelectorStrategy,
        element: Dict[str, Any]
    ) -> bool:
        """Check if a selector matches an element."""
        from recorder.ml.selector_engine import SelectorType
        
        if selector.type == SelectorType.ID:
            elem_id = element.get("id", "")
            return f"#{elem_id}" == selector.value
        
        elif selector.type == SelectorType.DATA_TESTID:
            testid = element.get("attributes", {}).get("data-testid", "")
            return f"[data-testid='{testid}']" == selector.value
        
        elif selector.type == SelectorType.ARIA_LABEL:
            aria_label = element.get("ariaLabel", "")
            return f"[aria-label='{aria_label}']" == selector.value
        
        elif selector.type == SelectorType.TEXT:
            text = element.get("textContent", "")
            return fuzz.ratio(text.strip(), selector.value) >= 90
        
        return False
    
    def _element_to_fingerprint(self, element: Dict[str, Any]) -> ElementFingerprint:
        """Convert element dict to fingerprint."""
        from recorder.ml.selector_engine import create_fingerprint_from_dom
        return create_fingerprint_from_dom(element)
    
    def _extract_healing_features(
        self,
        fingerprint: ElementFingerprint,
        page_state: Dict[str, Any]
    ) -> np.ndarray:
        """
        Extract features for ML healing model.

        IMPORTANT: Feature order must match _record_to_features() exactly!
        """
        features = [
            # Must match order in _record_to_features()
            1.0 if fingerprint.id is not None else 0.0,  # has_id
            float(len(fingerprint.classes)),  # class_count
            float(len(fingerprint.attributes)),  # attr_count
            1.0 if fingerprint.text_content else 0.0,  # has_text
            1.0 if fingerprint.visual_hash else 0.0,  # has_visual
            float(fingerprint.depth),  # depth
            1.0 if fingerprint.has_stable_attributes else 0.0,  # is_stable
            float(fingerprint.sibling_count),  # sibling_count
            1.0 if (fingerprint.aria_label or fingerprint.aria_role) else 0.0,  # has_aria
            1.0 if fingerprint.is_in_iframe else 0.0,  # in_iframe
        ]
        return np.array(features)
    
    def _record_healing_attempt(
        self,
        result: HealingResult,
        original_fingerprint: ElementFingerprint,
        attempted_strategy: HealingStrategy
    ):
        """Record healing attempt (success or failure) for model training."""
        with self._lock:
            self.healing_history.append({
                "strategy": attempted_strategy.value,
                "success": result.success,
                "confidence": result.confidence,
                "execution_time_ms": result.execution_time_ms,
                "fingerprint_features": self._fingerprint_to_dict(original_fingerprint)
            })

            # Keep only recent history (last 1000 healings)
            if len(self.healing_history) > 1000:
                self.healing_history = self.healing_history[-1000:]

            self._samples_since_last_train += 1

            # Auto-train when we have enough new samples
            should_train = (self._samples_since_last_train >= self._auto_train_threshold and
                    len(self.healing_history) >= self._min_samples_for_training)

        if should_train:
            self._auto_train()

        if result.success:
            logger.info(
                f"Healing successful using {result.strategy.value} "
                f"(confidence: {result.confidence:.2f}, time: {result.execution_time_ms:.1f}ms)"
            )

    def _record_healing_success(
        self,
        result: HealingResult,
        original_fingerprint: ElementFingerprint
    ):
        """Record successful healing for model training."""
        self._record_healing_attempt(result, original_fingerprint, result.strategy)

    def _record_healing_failure(
        self,
        original_fingerprint: ElementFingerprint,
        attempted_strategy: HealingStrategy,
        execution_time_ms: float
    ):
        """Record failed healing attempt for model training."""
        failed_result = HealingResult(
            success=False,
            strategy=attempted_strategy,
            confidence=0.0,
            execution_time_ms=execution_time_ms
        )
        self._record_healing_attempt(failed_result, original_fingerprint, attempted_strategy)

    def _auto_train(self):
        """Automatically retrain model when enough new data is collected."""
        logger.info("Auto-training healing model with new data...")
        self.train_healing_model()
        self._samples_since_last_train = 0
    
    def _fingerprint_to_dict(self, fp: ElementFingerprint) -> Dict[str, Any]:
        """Convert fingerprint to dict for storage."""
        return {
            "tag_name": fp.tag_name,
            "has_id": fp.id is not None,
            "class_count": len(fp.classes),
            "attr_count": len(fp.attributes),
            "has_text": fp.text_content is not None,
            "has_visual": fp.visual_hash is not None,
            "depth": fp.depth,
            "is_stable": fp.has_stable_attributes,
            "sibling_count": fp.sibling_count,
            "has_aria": fp.aria_label is not None or fp.aria_role is not None,
            "in_iframe": fp.is_in_iframe,
        }
    
    def train_healing_model(self) -> bool:
        """
        Train XGBoost model on healing history.

        The model learns which healing strategy works best for different
        element fingerprints. Only successful healings are used as positive
        examples - the model predicts which strategy will succeed.

        Returns:
            True if training succeeded, False otherwise.
        """
        # Filter to only successful healings for training
        successful_healings = [
            record for record in self.healing_history
            if record.get("success", False)
        ]

        if len(successful_healings) < self._min_samples_for_training:
            logger.warning(
                f"Not enough successful healings to train model "
                f"({len(successful_healings)}/{self._min_samples_for_training})"
            )
            return False

        # Check we have examples of multiple strategies
        strategies_seen = set(r["strategy"] for r in successful_healings)
        if len(strategies_seen) < 2:
            logger.warning(
                f"Need examples of at least 2 strategies, only have: {strategies_seen}"
            )
            return False

        # Prepare training data
        X = []
        y = []

        for record in successful_healings:
            features = self._record_to_features(record)
            strategy_name = record["strategy"]

            # Convert strategy name to label
            try:
                strategy_enum = HealingStrategy(strategy_name)
                if strategy_enum in STRATEGY_TO_LABEL:
                    X.append(features)
                    y.append(STRATEGY_TO_LABEL[strategy_enum])
            except ValueError:
                # Skip unknown strategies
                continue

        if len(X) < self._min_samples_for_training:
            logger.warning(f"Not enough valid samples after filtering: {len(X)}")
            return False

        X = np.array(X)
        y = np.array(y)

        # Train model
        try:
            with self._lock:
                self.healing_model.fit(X, y)
                self._model_trained = True

            # Log training stats
            unique, counts = np.unique(y, return_counts=True)
            strategy_dist = {
                LABEL_TO_STRATEGY[label].value: count
                for label, count in zip(unique, counts)
            }
            logger.info(
                f"Healing model trained on {len(X)} samples. "
                f"Strategy distribution: {strategy_dist}"
            )
            return True

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def _record_to_features(self, record: Dict[str, Any]) -> List[float]:
        """Extract feature vector from a healing record."""
        fp = record["fingerprint_features"]
        return [
            1.0 if fp.get("has_id", False) else 0.0,
            float(fp.get("class_count", 0)),
            float(fp.get("attr_count", 0)),
            1.0 if fp.get("has_text", False) else 0.0,
            1.0 if fp.get("has_visual", False) else 0.0,
            float(fp.get("depth", 0)),
            1.0 if fp.get("is_stable", True) else 0.0,
            # Additional features for better prediction
            float(fp.get("sibling_count", 0)) if "sibling_count" in fp else 0.0,
            1.0 if fp.get("has_aria", False) else 0.0,
            1.0 if fp.get("in_iframe", False) else 0.0,
        ]
    
    def get_healing_stats(self) -> Dict[str, Any]:
        """Get statistics about healing performance."""
        if not self.healing_history:
            return {
                "total_attempts": 0,
                "model_trained": self._model_trained,
            }

        successful = [r for r in self.healing_history if r.get("success", False)]
        failed = [r for r in self.healing_history if not r.get("success", False)]

        strategy_counts = {}
        total_time = 0.0

        for record in successful:
            strategy = record["strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            total_time += record.get("execution_time_ms", 0)

        success_rate = len(successful) / len(self.healing_history) if self.healing_history else 0

        return {
            "total_attempts": len(self.healing_history),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": round(success_rate, 3),
            "strategy_distribution": strategy_counts,
            "avg_execution_time_ms": round(total_time / len(successful), 2) if successful else 0,
            "most_successful_strategy": max(strategy_counts, key=strategy_counts.get) if strategy_counts else None,
            "model_trained": self._model_trained,
            "samples_until_retrain": max(0, self._auto_train_threshold - self._samples_since_last_train),
        }

    def save_history(self, path: str) -> bool:
        """Save healing history to JSON file for persistence."""
        import json
        try:
            with open(path, 'w') as f:
                json.dump({
                    "history": self.healing_history,
                    "model_trained": self._model_trained,
                }, f, indent=2)
            logger.info(f"Saved {len(self.healing_history)} healing records to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save healing history: {e}")
            return False

    def load_history(self, path: str) -> bool:
        """Load healing history from JSON file."""
        import json
        import os
        if not os.path.exists(path):
            logger.warning(f"History file not found: {path}")
            return False
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.healing_history = data.get("history", [])
            logger.info(f"Loaded {len(self.healing_history)} healing records from {path}")

            # Auto-train if we have enough data and model wasn't trained
            if (len(self.healing_history) >= self._min_samples_for_training
                    and not self._model_trained):
                logger.info("Training model on loaded history...")
                self.train_healing_model()

            return True
        except Exception as e:
            logger.error(f"Failed to load healing history: {e}")
            return False

    def is_model_ready(self) -> bool:
        """Check if the ML model is trained and ready for predictions."""
        return self._model_trained
