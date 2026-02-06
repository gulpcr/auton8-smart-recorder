"""Computer vision components for visual element recognition and matching."""

from __future__ import annotations

import io
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Tuple, List
import hashlib

import cv2
import numpy as np
from PIL import Image
import imagehash
import pytesseract
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)


class VisualElementMatcher:
    """
    Advanced computer vision for element identification and matching.
    Uses OCR, template matching, perceptual hashing, and SSIM.
    """
    
    _CACHE_MAX_SIZE = 200

    def __init__(self):
        self.template_cache = OrderedDict()
        self.hash_cache = OrderedDict()
    
    def extract_text_ocr(self, image: np.ndarray) -> str:
        """
        Extract text from element screenshot using OCR.
        """
        try:
            # Preprocess for better OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Increase contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # OCR with Tesseract
            text = pytesseract.image_to_string(
                enhanced,
                config='--psm 6'  # Assume single uniform block of text
            )
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return ""
    
    def compute_visual_hash(self, image: np.ndarray, hash_type: str = "phash") -> str:
        """
        Compute perceptual hash for visual similarity matching.
        Supports: phash (perceptual), dhash (difference), ahash (average).
        """
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            if hash_type == "phash":
                img_hash = imagehash.phash(pil_image, hash_size=16)
            elif hash_type == "dhash":
                img_hash = imagehash.dhash(pil_image, hash_size=16)
            elif hash_type == "ahash":
                img_hash = imagehash.average_hash(pil_image, hash_size=16)
            else:
                img_hash = imagehash.phash(pil_image, hash_size=16)
            
            hash_str = str(img_hash)
            # Evict oldest entries if cache exceeds limit
            while len(self.hash_cache) >= self._CACHE_MAX_SIZE:
                self.hash_cache.popitem(last=False)
            self.hash_cache[hash_str] = image
            return hash_str
        except Exception as e:
            logger.warning(f"Visual hash computation failed: {e}")
            return ""
    
    def compute_color_histogram(self, image: np.ndarray, bins: int = 32) -> np.ndarray:
        """
        Compute color histogram signature for color-based matching.
        """
        hist_b = cv2.calcHist([image], [0], None, [bins], [0, 256])
        hist_g = cv2.calcHist([image], [1], None, [bins], [0, 256])
        hist_r = cv2.calcHist([image], [2], None, [bins], [0, 256])
        
        hist = np.concatenate([hist_b, hist_g, hist_r])
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist
    
    def compare_histograms(
        self, 
        hist1: np.ndarray, 
        hist2: np.ndarray, 
        method: str = "correlation"
    ) -> float:
        """
        Compare two color histograms.
        Methods: correlation, chi-square, intersection, bhattacharyya
        Returns similarity score [0-1].
        """
        if method == "correlation":
            score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0.0, score)  # Normalize to [0, 1]
        elif method == "intersection":
            return cv2.compareHist(hist1, hist2, cv2.HISTCMP_INTERSECT)
        else:
            return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    
    def template_match(
        self, 
        screenshot: np.ndarray, 
        template: np.ndarray,
        threshold: float = 0.8
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find template in screenshot using multiple methods.
        Returns (x, y, confidence) if found, None otherwise.
        """
        methods = [
            cv2.TM_CCOEFF_NORMED,
            cv2.TM_CCORR_NORMED,
            cv2.TM_SQDIFF_NORMED
        ]
        
        best_match = None
        best_confidence = 0.0
        
        for method in methods:
            result = cv2.matchTemplate(screenshot, template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if method == cv2.TM_SQDIFF_NORMED:
                confidence = 1.0 - min_val
                location = min_loc
            else:
                confidence = max_val
                location = max_loc
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = (*location, confidence)
        
        return best_match if best_confidence >= threshold else None
    
    def compute_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Structural Similarity Index (SSIM) between two images.
        Returns similarity score [0-1].
        """
        try:
            # Convert to grayscale if needed
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = img1
            
            if len(img2.shape) == 3:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = img2
            
            # Resize to same dimensions if needed
            if gray1.shape != gray2.shape:
                gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
            
            score, _ = ssim(gray1, gray2, full=True)
            return max(0.0, score)
        except Exception as e:
            logger.warning(f"SSIM computation failed: {e}")
            return 0.0
    
    def detect_shapes(self, image: np.ndarray) -> List[dict]:
        """
        Detect shapes (rectangles, circles, etc.) in image.
        Useful for icon/button recognition.
        """
        shapes = []
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(
                edges, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 100:  # Skip tiny contours
                    continue
                
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
                x, y, w, h = cv2.boundingRect(approx)
                
                shape_info = {
                    "vertices": len(approx),
                    "area": area,
                    "bbox": (x, y, w, h),
                    "perimeter": perimeter
                }
                
                # Classify shape
                if len(approx) == 3:
                    shape_info["type"] = "triangle"
                elif len(approx) == 4:
                    aspect_ratio = w / float(h)
                    shape_info["type"] = "square" if 0.95 <= aspect_ratio <= 1.05 else "rectangle"
                elif len(approx) > 8:
                    shape_info["type"] = "circle"
                else:
                    shape_info["type"] = "polygon"
                
                shapes.append(shape_info)
        
        except Exception as e:
            logger.warning(f"Shape detection failed: {e}")
        
        return shapes
    
    def extract_dominant_colors(
        self, 
        image: np.ndarray, 
        n_colors: int = 5
    ) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors using K-means clustering.
        Returns list of RGB tuples.
        """
        try:
            # Reshape image to list of pixels
            pixels = image.reshape((-1, 3))
            pixels = np.float32(pixels)
            
            # K-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            _, labels, centers = cv2.kmeans(
                pixels, 
                n_colors, 
                None, 
                criteria, 
                10, 
                cv2.KMEANS_PP_CENTERS
            )
            
            # Convert to integer RGB
            centers = np.uint8(centers)
            dominant_colors = [tuple(color[::-1]) for color in centers]  # BGR to RGB
            
            return dominant_colors
        except Exception as e:
            logger.warning(f"Dominant color extraction failed: {e}")
            return []
    
    def find_element_by_visual_similarity(
        self,
        current_screenshot: np.ndarray,
        target_hash: str,
        target_bbox: Tuple[int, int, int, int],
        tolerance: int = 50,
        target_image: Optional[np.ndarray] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find element in current screenshot by visual similarity.

        Uses multiple strategies:
        1. Template matching with cached/provided image
        2. Perceptual hash scanning of candidate regions
        3. Color histogram matching as fallback

        Args:
            current_screenshot: Current page screenshot
            target_hash: Perceptual hash of target element
            target_bbox: Original bounding box (x, y, w, h)
            tolerance: Search area expansion in pixels
            target_image: Optional target element image (if not cached)

        Returns:
            (x, y) center coordinates if found, None otherwise
        """
        x, y, w, h = target_bbox

        # Validate bbox
        if w <= 0 or h <= 0:
            logger.warning("Invalid target bbox")
            return None

        # Get target image from cache or parameter
        target_img = None
        if target_hash in self.hash_cache:
            target_img = self.hash_cache[target_hash]
        elif target_image is not None:
            target_img = target_image

        # Strategy 1: Template matching (if we have target image)
        if target_img is not None:
            result = self._search_with_template(
                current_screenshot, target_img, x, y, w, h, tolerance
            )
            if result:
                return result

        # Strategy 2: Perceptual hash scanning
        if target_hash:
            result = self._search_with_hash(
                current_screenshot, target_hash, x, y, w, h, tolerance
            )
            if result:
                return result

        # Strategy 3: Search at original position with expanded tolerance
        if target_img is not None:
            result = self._search_with_template(
                current_screenshot, target_img, x, y, w, h, tolerance * 2
            )
            if result:
                return result

        return None

    def _search_with_template(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        orig_x: int,
        orig_y: int,
        width: int,
        height: int,
        tolerance: int
    ) -> Optional[Tuple[int, int]]:
        """Search for template in screenshot around original position."""
        # Define search region
        search_x1 = max(0, orig_x - tolerance)
        search_y1 = max(0, orig_y - tolerance)
        search_x2 = min(screenshot.shape[1], orig_x + width + tolerance)
        search_y2 = min(screenshot.shape[0], orig_y + height + tolerance)

        # Ensure search region is larger than template
        if (search_x2 - search_x1) < template.shape[1] or \
           (search_y2 - search_y1) < template.shape[0]:
            # Search full screenshot
            search_region = screenshot
            search_x1, search_y1 = 0, 0
        else:
            search_region = screenshot[search_y1:search_y2, search_x1:search_x2]

        # Try template matching
        match = self.template_match(search_region, template, threshold=0.70)

        if match:
            match_x, match_y, confidence = match
            center_x = search_x1 + match_x + width // 2
            center_y = search_y1 + match_y + height // 2
            logger.debug(f"Template match found at ({center_x}, {center_y}) conf={confidence:.2f}")
            return (center_x, center_y)

        return None

    def _search_with_hash(
        self,
        screenshot: np.ndarray,
        target_hash: str,
        orig_x: int,
        orig_y: int,
        width: int,
        height: int,
        tolerance: int
    ) -> Optional[Tuple[int, int]]:
        """
        Search for element by scanning regions and comparing perceptual hashes.
        """
        # Define search area
        search_x1 = max(0, orig_x - tolerance)
        search_y1 = max(0, orig_y - tolerance)
        search_x2 = min(screenshot.shape[1], orig_x + width + tolerance)
        search_y2 = min(screenshot.shape[0], orig_y + height + tolerance)

        best_match = None
        best_similarity = 0.0
        similarity_threshold = 0.75

        # Scan with sliding window
        step = max(width // 4, 10)  # Step size

        for scan_y in range(search_y1, search_y2 - height, step):
            for scan_x in range(search_x1, search_x2 - width, step):
                # Extract candidate region
                candidate = screenshot[scan_y:scan_y + height, scan_x:scan_x + width]

                if candidate.shape[0] < 10 or candidate.shape[1] < 10:
                    continue

                # Compute hash and compare
                try:
                    candidate_hash = self.compute_visual_hash(candidate, "phash")
                    if not candidate_hash:
                        continue

                    similarity = self.compare_visual_hash_similarity(target_hash, candidate_hash)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = (scan_x + width // 2, scan_y + height // 2)

                except Exception:
                    continue

        if best_match and best_similarity >= similarity_threshold:
            logger.debug(f"Hash match found at {best_match} similarity={best_similarity:.2f}")
            return best_match

        return None

    def find_all_similar_elements(
        self,
        screenshot: np.ndarray,
        target_hash: str,
        target_size: Tuple[int, int],
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Tuple[int, int, int, int, float]]:
        """
        Find all elements visually similar to target in the screenshot.

        Returns list of (x, y, w, h, similarity) tuples.
        """
        results = []
        width, height = target_size
        step = max(min(width, height) // 3, 15)

        for scan_y in range(0, screenshot.shape[0] - height, step):
            for scan_x in range(0, screenshot.shape[1] - width, step):
                candidate = screenshot[scan_y:scan_y + height, scan_x:scan_x + width]

                if candidate.shape[0] < 10 or candidate.shape[1] < 10:
                    continue

                try:
                    candidate_hash = self.compute_visual_hash(candidate, "phash")
                    if not candidate_hash:
                        continue

                    similarity = self.compare_visual_hash_similarity(target_hash, candidate_hash)

                    if similarity >= similarity_threshold:
                        # Check for overlapping results
                        is_overlapping = False
                        for rx, ry, rw, rh, _ in results:
                            if abs(scan_x - rx) < width // 2 and abs(scan_y - ry) < height // 2:
                                is_overlapping = True
                                break

                        if not is_overlapping:
                            results.append((scan_x, scan_y, width, height, similarity))

                            if len(results) >= max_results:
                                return sorted(results, key=lambda x: x[4], reverse=True)

                except Exception:
                    continue

        return sorted(results, key=lambda x: x[4], reverse=True)
    
    def compare_visual_hash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compare two perceptual hashes.
        Returns similarity score [0-1].
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)

            # Hamming distance
            distance = h1 - h2

            # Convert to similarity (max distance is hash_size^2)
            max_distance = len(hash1) * 4  # Each hex char = 4 bits
            similarity = 1.0 - (distance / max_distance)

            return max(0.0, similarity)
        except Exception as e:
            logger.warning(f"Hash comparison failed: {e}")
            return 0.0

    def find_element_by_text(
        self,
        screenshot: np.ndarray,
        target_text: str,
        similarity_threshold: float = 0.8
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find element containing specific text using OCR.

        Args:
            screenshot: Page screenshot
            target_text: Text to search for
            similarity_threshold: Minimum text similarity (0-1)

        Returns:
            (x, y, w, h) bounding box if found, None otherwise
        """
        try:
            from rapidfuzz import fuzz

            # Get OCR data with bounding boxes
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                enhanced,
                config='--psm 6',
                output_type=pytesseract.Output.DICT
            )

            target_lower = target_text.lower().strip()
            best_match = None
            best_score = 0.0

            n_boxes = len(ocr_data['text'])
            for i in range(n_boxes):
                text = ocr_data['text'][i]
                if not text or not text.strip():
                    continue

                # Compare text similarity
                text_lower = text.lower().strip()
                score = fuzz.ratio(target_lower, text_lower) / 100.0

                if score > best_score and score >= similarity_threshold:
                    best_score = score
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    best_match = (x, y, w, h)

            if best_match:
                logger.debug(f"Text '{target_text}' found at {best_match} score={best_score:.2f}")

            return best_match

        except ImportError:
            logger.warning("rapidfuzz not available for text matching")
            return None
        except Exception as e:
            logger.warning(f"Text search failed: {e}")
            return None

    def find_clickable_elements(
        self,
        screenshot: np.ndarray,
        min_area: int = 100
    ) -> List[Tuple[int, int, int, int, str]]:
        """
        Find potential clickable elements (buttons, links) in screenshot.

        Uses shape detection and color analysis to identify UI elements.

        Returns:
            List of (x, y, w, h, element_type) tuples
        """
        elements = []

        # Detect shapes that could be buttons
        shapes = self.detect_shapes(screenshot)

        for shape in shapes:
            if shape['area'] < min_area:
                continue

            x, y, w, h = shape['bbox']

            # Classify element type based on shape and aspect ratio
            aspect_ratio = w / h if h > 0 else 0

            if shape['type'] in ('rectangle', 'square'):
                if 1.5 < aspect_ratio < 8:
                    element_type = 'button'
                elif aspect_ratio >= 8:
                    element_type = 'input'
                else:
                    element_type = 'icon'
            elif shape['type'] == 'circle':
                element_type = 'icon'
            else:
                element_type = 'unknown'

            elements.append((x, y, w, h, element_type))

        return elements


class ScreenshotManager:
    """Manage element screenshots and full-page captures."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_screenshot(
        self, 
        image: np.ndarray, 
        element_id: str,
        session_id: str
    ) -> Path:
        """Save element screenshot to disk."""
        filename = f"{session_id}_{element_id}.png"
        filepath = self.storage_path / filename
        
        cv2.imwrite(str(filepath), image)
        return filepath
    
    def load_screenshot(self, filepath: Path) -> Optional[np.ndarray]:
        """Load screenshot from disk."""
        if not filepath.exists():
            return None
        
        return cv2.imread(str(filepath))
    
    def capture_element_with_bbox(
        self,
        full_screenshot: np.ndarray,
        bbox: Tuple[int, int, int, int],
        padding: int = 10
    ) -> np.ndarray:
        """
        Extract element region from full screenshot with padding.
        """
        x, y, w, h = bbox
        
        # Add padding
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(full_screenshot.shape[1], x + w + padding)
        y2 = min(full_screenshot.shape[0], y + h + padding)
        
        element_img = full_screenshot[y1:y2, x1:x2]
        return element_img
    
    def draw_bbox_overlay(
        self,
        screenshot: np.ndarray,
        bbox: Tuple[int, int, int, int],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """Draw bounding box on screenshot for visualization."""
        result = screenshot.copy()
        x, y, w, h = bbox
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
        return result
