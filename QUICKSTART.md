# Quick Start Guide

Get up and running with Call Intelligence System in 5 minutes!

## Prerequisites

- Python 3.10+
- 8GB RAM minimum
- Internet connection (for model downloads)

## Installation (Automated)

### Windows

```bash
# Run the installer
install.bat

# Follow the prompts
```

### macOS / Linux

```bash
# Make script executable
chmod +x install.sh

# Run the installer
./install.sh

# Follow the prompts
```

## Manual Installation

If the automated installer doesn't work:

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate (Windows)
.\.venv\Scripts\activate

# 2. Activate (macOS/Linux)
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright
python -m playwright install

# 5. Download spaCy model
python -m spacy download en_core_web_sm

# 6. Create directories
mkdir -p data/{workflows,screenshots,knowledge_base,rag_index,uploads}
```

## First Run

### Desktop Application

```bash
# Activate virtual environment
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Run application
python -m recorder.app_ml_integrated
```

### API Server

```bash
# Start FastAPI server
python -m uvicorn recorder.api.main:app --host 0.0.0.0 --port 8000

# Open browser
# http://localhost:8000/docs
```

## Basic Workflow

### 1. Record a Workflow

1. Launch application
2. Click **"⏺️ Start Recording"**
3. Browser opens automatically
4. Perform your actions (click, type, navigate)
5. Click **"⏹️ Stop Recording"**
6. Click **"💾 Save Workflow"**

### 2. Replay a Workflow

1. Go to **"Workflows"** tab
2. Select a workflow from the list
3. Click **"▶️ Replay"**
4. Watch automatic execution

### 3. View Dashboard

1. Go to **"Dashboard"** tab
2. See real-time metrics:
   - Total workflows
   - Success rate
   - Healing statistics
   - Performance metrics

## Using API

### Transcribe Audio

```python
import requests

# Upload audio file
with open('recording.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload-audio',
        files={'file': f}
    )

job_id = response.json()['job_id']

# Check status
status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
print(status.json())
```

### Generate Selectors

```python
element_data = {
    "tagName": "button",
    "id": "submit-btn",
    "classes": ["btn", "btn-primary"],
    "textContent": "Submit Form",
    "ariaLabel": "Submit",
    "boundingBox": [100, 200, 80, 40]
}

response = requests.post(
    'http://localhost:8000/api/selectors/generate',
    json={"element": element_data}
)

selectors = response.json()['selectors']
for sel in selectors:
    print(f"{sel['type']}: {sel['value']} (score: {sel['score']})")
```

## Configuration

### Enable LLM Features

1. Download a model:
   ```bash
   pip install huggingface-hub
   huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF llama-2-7b-chat.Q4_K_M.gguf --local-dir ~/models
   ```

2. Model will be auto-detected on startup

### Setup Knowledge Base (RAG)

1. Create directory:
   ```bash
   mkdir -p data/knowledge_base
   ```

2. Add documents:
   - `.txt` files with policies
   - `.md` files with FAQs
   - Any text documents

3. Documents are auto-indexed on first run

### Enable GPU Acceleration

For CUDA GPUs:
```bash
pip uninstall llama-cpp-python -y
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --no-cache-dir
```

For Apple Silicon:
```bash
pip uninstall llama-cpp-python -y
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --no-cache-dir
```

## Troubleshooting

### "Module not found" errors

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Tesseract not found

**Windows:**
1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR`
3. Add to PATH

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### Playwright browser not found

```bash
python -m playwright install
```

### Out of memory (LLM)

Use smaller quantization:
- Q4_K_M (~4GB): Best balance
- Q5_K_M (~5GB): Better quality
- Q8_0 (~8GB): Highest quality

Or reduce context length:
```python
config = LLMConfig(
    model_path="model.gguf",
    n_ctx=2048  # Reduced from 4096
)
```

### WebSocket connection failed

1. Check port 8765 is free
2. Firewall may be blocking
3. Try different port in settings

## Next Steps

- 📖 Read full documentation: [README_PRODUCTION.md](README_PRODUCTION.md)
- 🎯 Try examples in [examples/](examples/)
- 🧪 Run tests: `pytest`
- ⚙️ Configure settings in UI
- 📊 Explore API docs: http://localhost:8000/docs

## Getting Help

- **Documentation**: Full docs in `README_PRODUCTION.md`
- **Issues**: Report bugs on GitHub
- **Examples**: Check `examples/` directory
- **API Reference**: http://localhost:8000/docs

## Key Features to Try

✅ Multi-dimensional selector generation  
✅ Intelligent healing when selectors break  
✅ Visual element matching with screenshots  
✅ Intent classification with local LLM  
✅ Statement verification with RAG  
✅ Audio transcription with speaker diarization  
✅ Real-time dashboard with metrics  
✅ Professional Material Design 3 UI  

**Happy Recording! 🎉**
