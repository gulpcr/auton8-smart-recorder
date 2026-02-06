"""WhisperX transcription engine with diarization and speaker identification."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

import numpy as np
import torch

try:
    import whisper
    import whisperx
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("WhisperX not available. Transcription features disabled.")

try:
    import librosa
    import soundfile as sf
    import noisereduce as nr
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Audio processing libraries not available.")

logger = logging.getLogger(__name__)


@dataclass
class Word:
    """Word-level transcription with timestamp."""
    word: str
    start: float
    end: float
    confidence: float


@dataclass
class TranscriptionSegment:
    """Transcription segment with speaker identification."""
    speaker: str  # SPEAKER_00, SPEAKER_01, etc.
    role: Optional[str]  # agent, customer
    text: str
    start: float
    end: float
    words: List[Word]
    confidence: float
    language: str = "en"


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    segments: List[TranscriptionSegment]
    duration: float
    language: str
    speakers_count: int
    metadata: Dict[str, Any]


class TranscriptionEngine:
    """
    Advanced transcription engine using WhisperX.
    Features:
    - Word-level timestamps
    - Speaker diarization
    - Noise reduction
    - VAD (Voice Activity Detection)
    - Multi-language support
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "float16"
    ):
        self.model_size = model_size
        self.device = self._get_device(device)
        self.compute_type = compute_type
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None
        self._align_language = None

        self._initialize_models()
    
    def _get_device(self, device: str) -> str:
        """Determine compute device."""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    def _initialize_models(self):
        """Load Whisper and diarization models."""
        if not WHISPERX_AVAILABLE:
            logger.error("WhisperX not installed")
            return
        
        try:
            # Load WhisperX model
            self.model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type
            )
            logger.info(f"Loaded WhisperX model: {self.model_size} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load WhisperX model: {e}")

    def cleanup(self):
        """Release models and free GPU memory."""
        for attr in ("model", "align_model", "diarize_model", "align_metadata"):
            if getattr(self, attr, None) is not None:
                delattr(self, attr)
                setattr(self, attr, None)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Transcription engine cleaned up")

    def __del__(self):
        self.cleanup()

    def preprocess_audio(
        self,
        audio_path: Path,
        sample_rate: int = 16000,
        reduce_noise: bool = True
    ) -> np.ndarray:
        """
        Preprocess audio file.
        - Load and resample
        - Normalize
        - Reduce noise
        """
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.error("Audio processing libraries not available")
            return np.array([])
        
        try:
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=sample_rate)
            
            # Normalize
            audio = librosa.util.normalize(audio)
            
            # Noise reduction
            if reduce_noise:
                audio = nr.reduce_noise(y=audio, sr=sr)
            
            logger.info(f"Preprocessed audio: {len(audio)/sr:.2f}s at {sr}Hz")
            return audio
        
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            return np.array([])
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        enable_diarization: bool = True,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file with speaker diarization.
        
        Args:
            audio_path: Path to audio file
            language: Language code (None for auto-detect)
            enable_diarization: Enable speaker diarization
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
        
        Returns:
            TranscriptionResult with segments and metadata
        """
        if not self.model:
            logger.error("Model not initialized")
            return TranscriptionResult(
                segments=[],
                duration=0.0,
                language="en",
                speakers_count=0,
                metadata={"error": "Model not initialized"}
            )
        
        try:
            # Preprocess audio
            audio = self.preprocess_audio(audio_path)
            if len(audio) == 0:
                raise ValueError("Audio preprocessing failed")
            
            # Transcribe with Whisper
            logger.info("Starting transcription...")
            result = self.model.transcribe(
                audio,
                language=language,
                batch_size=16
            )
            
            detected_language = result.get("language", "en")
            logger.info(f"Detected language: {detected_language}")
            
            # Align whisper output for word-level timestamps
            logger.info("Aligning timestamps...")
            # Reuse alignment model if language matches, otherwise reload
            if self.align_model is None or self._align_language != detected_language:
                # Free previous alignment model before loading new one
                if self.align_model is not None:
                    del self.align_model
                    self.align_model = None
                self.align_model, self.align_metadata = whisperx.load_align_model(
                    language_code=detected_language,
                    device=self.device
                )
                self._align_language = detected_language
            result = whisperx.align(
                result["segments"],
                self.align_model,
                self.align_metadata,
                audio,
                self.device,
                return_char_alignments=False
            )
            
            segments = result["segments"]
            
            # Speaker diarization
            if enable_diarization:
                logger.info("Performing speaker diarization...")
                segments = self._diarize_segments(
                    audio_path,
                    segments,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers
                )
            
            # Convert to TranscriptionSegment objects
            transcription_segments = []
            for seg in segments:
                words = [
                    Word(
                        word=w["word"],
                        start=w["start"],
                        end=w["end"],
                        confidence=w.get("score", 0.0)
                    )
                    for w in seg.get("words", [])
                ]
                
                transcription_segments.append(TranscriptionSegment(
                    speaker=seg.get("speaker", "SPEAKER_00"),
                    role=self._classify_speaker_role(seg.get("speaker")),
                    text=seg["text"],
                    start=seg["start"],
                    end=seg["end"],
                    words=words,
                    confidence=np.mean([w.confidence for w in words]) if words else 0.0,
                    language=detected_language
                ))
            
            # Get audio duration
            duration = librosa.get_duration(y=audio, sr=16000)
            
            # Count unique speakers
            speakers = set(seg.speaker for seg in transcription_segments)
            
            return TranscriptionResult(
                segments=transcription_segments,
                duration=duration,
                language=detected_language,
                speakers_count=len(speakers),
                metadata={
                    "model": self.model_size,
                    "device": self.device,
                    "diarization": enable_diarization
                }
            )
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return TranscriptionResult(
                segments=[],
                duration=0.0,
                language="en",
                speakers_count=0,
                metadata={"error": str(e)}
            )
    
    def _diarize_segments(
        self,
        audio_path: Path,
        segments: List[Dict[str, Any]],
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform speaker diarization on segments.
        """
        try:
            # Reuse diarization pipeline across calls
            if self.diarize_model is None:
                self.diarize_model = whisperx.DiarizationPipeline(
                    use_auth_token=None,  # In production, use HuggingFace token
                    device=self.device
                )

            # Perform diarization
            diarize_segments = self.diarize_model(
                str(audio_path),
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            
            # Assign speakers to segments
            # whisperx.assign_word_speakers returns a dict with "segments" key
            result = whisperx.assign_word_speakers(
                diarize_segments,
                {"segments": segments}
            )

            return result.get("segments", segments)
        
        except Exception as e:
            logger.warning(f"Diarization failed: {e}")
            # Return segments without speaker labels
            for seg in segments:
                seg["speaker"] = "SPEAKER_00"
            return segments
    
    def _classify_speaker_role(self, speaker_id: Optional[str]) -> Optional[str]:
        """
        Classify speaker as agent or customer.
        In production, use LLM or pattern analysis.
        """
        if not speaker_id:
            return None
        
        # Simple heuristic: SPEAKER_00 is typically agent
        if speaker_id == "SPEAKER_00":
            return "agent"
        else:
            return "customer"
    
    def export_transcript(
        self,
        result: TranscriptionResult,
        output_path: Path,
        format: str = "json"
    ):
        """
        Export transcript to file.
        Supports: json, txt, srt, vtt
        """
        output_path = Path(output_path)
        
        if format == "json":
            self._export_json(result, output_path)
        elif format == "txt":
            self._export_txt(result, output_path)
        elif format == "srt":
            self._export_srt(result, output_path)
        elif format == "vtt":
            self._export_vtt(result, output_path)
        else:
            logger.error(f"Unsupported format: {format}")
    
    def _export_json(self, result: TranscriptionResult, output_path: Path):
        """Export as JSON."""
        data = {
            "segments": [
                {
                    "speaker": seg.speaker,
                    "role": seg.role,
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "confidence": seg.confidence,
                    "words": [
                        {
                            "word": w.word,
                            "start": w.start,
                            "end": w.end,
                            "confidence": w.confidence
                        }
                        for w in seg.words
                    ]
                }
                for seg in result.segments
            ],
            "metadata": {
                "duration": result.duration,
                "language": result.language,
                "speakers_count": result.speakers_count,
                **result.metadata
            }
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported transcript to {output_path}")
    
    def _export_txt(self, result: TranscriptionResult, output_path: Path):
        """Export as plain text."""
        with open(output_path, "w", encoding="utf-8") as f:
            for seg in result.segments:
                speaker_label = seg.role.upper() if seg.role else seg.speaker
                f.write(f"{speaker_label}: {seg.text}\n")
        
        logger.info(f"Exported transcript to {output_path}")
    
    def _export_srt(self, result: TranscriptionResult, output_path: Path):
        """Export as SRT subtitle format."""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result.segments, 1):
                start_time = self._format_timestamp_srt(seg.start)
                end_time = self._format_timestamp_srt(seg.end)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg.text}\n\n")
        
        logger.info(f"Exported SRT to {output_path}")
    
    def _export_vtt(self, result: TranscriptionResult, output_path: Path):
        """Export as WebVTT format."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for seg in result.segments:
                start_time = self._format_timestamp_vtt(seg.start)
                end_time = self._format_timestamp_vtt(seg.end)
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg.text}\n\n")
        
        logger.info(f"Exported WebVTT to {output_path}")
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format timestamp for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format timestamp for WebVTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def detect_silences(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = -40.0,
    min_silence_len: float = 0.5
) -> List[Tuple[float, float]]:
    """
    Detect silence regions in audio for VAD.
    Returns list of (start, end) timestamps in seconds.
    """
    if not AUDIO_PROCESSING_AVAILABLE:
        return []
    
    # Convert to dB
    audio_db = librosa.amplitude_to_db(np.abs(audio), ref=np.max)
    
    # Find frames below threshold
    silence_frames = audio_db < threshold_db
    
    # Convert to time segments
    frame_length = len(audio) / sr
    silence_segments = []
    
    in_silence = False
    silence_start = 0.0
    
    for i, is_silent in enumerate(silence_frames):
        time = i * frame_length / len(silence_frames)
        
        if is_silent and not in_silence:
            silence_start = time
            in_silence = True
        elif not is_silent and in_silence:
            if time - silence_start >= min_silence_len:
                silence_segments.append((silence_start, time))
            in_silence = False
    
    return silence_segments
