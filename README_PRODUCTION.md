# Call Intelligence System - Production Edition

**Enterprise-grade browser automation and call analysis with advanced ML/AI capabilities**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

### Browser Automation & Recording
- **Multi-dimensional element capture** with 9+ selector strategies (ID, data-testid, ARIA, CSS, XPath, text, visual, position)
- **Intelligent selector healing** using XGBoost and visual matching
- **Computer vision** for element identification (OCR, perceptual hashing, template matching)
- **Framework detection** (React, Vue, Angular component tracking)
- **Advanced event tracking** (mouse, keyboard, touch, network, mutations)
- **Shadow DOM and iframe** navigation support
- **Real-time performance monitoring**

### ML/AI Analysis
- **Local LLM integration** (Llama 2/3, Mistral, Phi-3) for intent classification
- **NLP engine** with BERT embeddings for semantic understanding
- **RAG (Retrieval-Augmented Generation)** with FAISS for statement verification
- **Sentiment analysis** and emotion detection
- **Agent KPI scoring** (knowledge, compliance, empathy, efficiency)

### Audio Transcription
- **WhisperX** with word-level timestamps
- **Speaker diarization** (pyannote.audio)
- **Automatic role classification** (agent/customer)
- **Multi-language support**
- **Noise reduction** and VAD (Voice Activity Detection)

### Professional UI
- **Material Design 3** with dark/light/auto themes
- **Real-time dashboard** with charts and metrics
- **Zoomable timeline** with millisecond precision
- **Workflow management** (grid/list views, bulk operations)
- **Performance monitoring** (CPU, memory, GPU usage)

### API Layer
- **FastAPI** REST API with production endpoints
- **WebSocket** support for real-time updates
- **Job queue** for async processing
- **OpenAPI/Swagger** documentation

## 📋 Requirements

- **Python**: 3.10 or higher
- **OS**: Windows 10/11, macOS 11+, Linux (Ubuntu 20.04+)
- **RAM**: 8GB minimum, 16GB recommended
- **GPU** (optional): NVIDIA GPU with CUDA for faster LLM inference

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourorg/call-intelligence.git
cd call-intelligence
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
python -m playwright install
```

### 5. Download Tesseract OCR

#### Windows
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH: C:\Program Files\Tesseract-OCR
```

#### macOS
```bash
brew install tesseract
```

#### Linux
```bash
sudo apt-get install tesseract-ocr
```

### 6. Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### 7. (Optional) Download LLM Model

For local LLM features, download a quantized model:

```bash
# Create models directory
mkdir -p ~/models

# Download Llama 2 7B Chat (Q4_K_M quantized, ~4GB)
# Option 1: Using huggingface-cli
pip install huggingface-hub
huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF llama-2-7b-chat.Q4_K_M.gguf --local-dir ~/models

# Option 2: Manual download from
# https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
```

Supported models:
- Llama 2/3 7B/13B (Q4_K_M, Q5_K_M)
- Mistral 7B Instruct
- Phi-3 Mini

### 8. (Optional) Setup Knowledge Base for RAG

```bash
# Create knowledge base directory
mkdir -p data/knowledge_base

# Add your documents (TXT, MD, PDF)
# - SOPs (Standard Operating Procedures)
# - FAQs (Frequently Asked Questions)
# - Compliance documents
# - Policy documents

# The system will automatically index them on first run
```

## 🎯 Quick Start

### Run Desktop Application

```bash
# Using the ML-integrated version
python -m recorder.app_ml_integrated

# Or the standard version
python -m recorder.app
```

### Run API Server

```bash
# Start FastAPI server
cd recorder
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Access API docs at: http://localhost:8000/docs
```

### Basic Recording Workflow

1. **Start Application**
   ```bash
   python -m recorder.app_ml_integrated
   ```

2. **Click "Start Recording"**
   - Enter target URL or leave blank for example.com
   - Browser will open with instrumentation

3. **Perform Actions**
   - Click, type, navigate as needed
   - Events are captured in real-time
   - Multi-dimensional selectors generated automatically

4. **Stop & Save**
   - Click "Stop Recording"
   - Click "Save Workflow"
   - Workflow saved to `data/workflows/`

5. **Replay**
   - Select workflow from list
   - Click "Start Replay"
   - Automatic healing if selectors fail

## 📚 Usage Guide

### Browser Recording

#### Manual Injection
Open browser dev console and paste `instrumentation/injected_advanced.js`

#### Extension (Recommended)
Use the Chrome/Firefox extension (see `extension/` directory)

### API Examples

#### Upload Audio for Transcription

```python
import requests

files = {'file': open('call-recording.wav', 'rb')}
response = requests.post('http://localhost:8000/api/upload-audio', files=files)
job_id = response.json()['job_id']

# Check status
status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
print(status.json())
```

#### Analyze Transcript

```python
segments = [
    {
        "speaker": "SPEAKER_00",
        "role": "agent",
        "text": "Thank you for calling. How may I help you?",
        "start": 0.0,
        "end": 2.5,
        "confidence": 0.95
    },
    # ... more segments
]

response = requests.post(
    'http://localhost:8000/api/analyze-transcript',
    json={
        "segments": segments,
        "analysis_types": ["intent", "sentiment", "kpi"]
    }
)

result = response.json()
print(f"Intent: {result['intents']}")
print(f"Sentiment: {result['sentiment']}")
print(f"KPI Scores: {result['agent_kpi']}")
```

#### Verify Statement

```python
response = requests.post(
    'http://localhost:8000/api/verify-statement',
    json={
        "statement": "Our refund policy allows returns within 30 days",
        "context": "Customer service call"
    }
)

result = response.json()
print(f"Verified: {result['is_verified']}")
print(f"Confidence: {result['confidence']}")
print(f"Citations: {result['citations']}")
```

### ML Configuration

#### LLM Settings

```python
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig

config = LLMConfig(
    model_path="~/models/llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=4096,        # Context length
    n_threads=4,       # CPU threads
    n_gpu_layers=32,   # GPU acceleration (0 for CPU only)
    temperature=0.7    # Creativity (0-1)
)

llm = LocalLLMEngine(config)
```

#### RAG Configuration

```python
from recorder.ml.rag_engine import RAGEngine

rag = RAGEngine(
    embedding_model_name="BAAI/bge-large-en-v1.5",
    index_path="data/rag_index"
)

# Ingest documents
rag.ingest_documents_from_directory("data/knowledge_base")
rag.save_index()

# Verify statement
result = rag.verify_statement("Our policy requires ID verification")
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# LLM Configuration
LLM_MODEL_PATH=~/models/llama-2-7b-chat.Q4_K_M.gguf
LLM_N_GPU_LAYERS=0
LLM_CONTEXT_LENGTH=4096

# RAG Configuration
RAG_INDEX_PATH=data/rag_index
RAG_MODEL=BAAI/bge-large-en-v1.5

# Transcription
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cuda

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Recording
WS_PORT=8765
RECORDING_OUTPUT_DIR=data/workflows
SCREENSHOT_DIR=data/screenshots
```

### Performance Tuning

#### GPU Acceleration

For CUDA-enabled GPUs:
```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir --config-settings cmake.args="-DLLAMA_CUBLAS=on"
```

For Apple Silicon (M1/M2/M3):
```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir --config-settings cmake.args="-DLLAMA_METAL=on"
```

#### Memory Optimization

```python
# Use smaller quantization for lower memory
# Q4_K_M: ~4GB RAM
# Q5_K_M: ~5GB RAM
# Q8_0: ~8GB RAM

# Adjust context length
config = LLMConfig(
    model_path="model.gguf",
    n_ctx=2048  # Reduce from 4096 for lower memory
)
```

## 📊 Architecture

```
call-intelligence/
├── recorder/
│   ├── app.py                      # Standard app
│   ├── app_ml_integrated.py        # ML-enhanced app
│   ├── models/                     # Qt models
│   ├── services/                   # Core services
│   ├── schema/                     # Data schemas
│   ├── ml/                         # ML/AI engines
│   │   ├── selector_engine.py      # Multi-dimensional selectors
│   │   ├── healing_engine.py       # Intelligent healing
│   │   ├── vision_engine.py        # Computer vision
│   │   ├── nlp_engine.py           # NLP processing
│   │   ├── llm_engine.py           # Local LLM
│   │   └── rag_engine.py           # RAG with FAISS
│   ├── audio/                      # Audio processing
│   │   └── transcription_engine.py # WhisperX
│   └── api/                        # FastAPI layer
│       └── main.py                 # API endpoints
├── ui/
│   ├── main.qml                    # Standard UI
│   └── main_professional.qml       # Material Design 3 UI
├── instrumentation/
│   ├── injected.js                 # Basic capture
│   └── injected_advanced.js        # Advanced capture
├── replay/
│   └── replayer.py                 # Playwright replay
├── data/
│   ├── workflows/                  # Saved workflows
│   ├── screenshots/                # Element screenshots
│   ├── knowledge_base/             # RAG documents
│   └── rag_index/                  # FAISS index
└── tests/                          # Test suite
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=recorder --cov-report=html

# Run specific tests
pytest tests/test_selector_engine.py
pytest tests/test_healing_engine.py
```

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t call-intelligence:latest .

# Run container
docker run -p 8000:8000 -v $(pwd)/data:/app/data call-intelligence:latest
```

### Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed \
    --add-data "ui:ui" \
    --add-data "instrumentation:instrumentation" \
    --name "CallIntelligence" \
    recorder/app_ml_integrated.py
```

## 📈 Performance Benchmarks

| Component | CPU Time | GPU Time | Memory |
|-----------|----------|----------|--------|
| Selector Generation | <5ms | N/A | ~50MB |
| Selector Healing | <100ms | N/A | ~100MB |
| Visual Matching | ~50ms | ~10ms | ~200MB |
| LLM Inference (7B Q4) | ~2s | ~500ms | ~4GB |
| RAG Query | <200ms | N/A | ~1GB |
| Transcription (Whisper Base) | 1x | 5x | ~1GB |

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Whisper** by OpenAI
- **Llama** by Meta AI
- **FAISS** by Facebook Research
- **Playwright** by Microsoft
- **PySide6** by Qt
- **FastAPI** by Tiangolo

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourorg/call-intelligence/issues)
- **Email**: support@callinteligence.com

## 🗺️ Roadmap

- [ ] Chrome DevTools Protocol (CDP) integration
- [ ] Real-time collaboration features
- [ ] Cloud sync (optional)
- [ ] Mobile app recording
- [ ] Advanced visual regression testing
- [ ] Custom LoRA adapters for domain-specific LLMs
- [ ] Multi-language UI
- [ ] Plugin system

---

**Built with ❤️ for production-grade browser automation and call intelligence**
