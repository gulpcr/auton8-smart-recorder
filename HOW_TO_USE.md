# How to Use - Call Intelligence System

## 🎬 Getting Started in 3 Steps

### Step 1: Install
```bash
# Windows
install.bat

# macOS/Linux
chmod +x install.sh
./install.sh
```

### Step 2: Run
```bash
# Activate environment
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows

# Launch application
python -m recorder.app_ml_integrated
```

### Step 3: Record
1. Click **"⏺️ Start Recording"**
2. Perform actions in opened browser
3. Click **"⏹️ Stop Recording"**
4. Click **"💾 Save"**

**Done!** Your workflow is saved with intelligent selectors.

---

## 🎯 Use Cases

### 1. Browser Test Automation

**Record Once, Replay Forever**
```bash
# Record workflow
python -m recorder.app_ml_integrated
# → Click "Start Recording"
# → Perform your test steps
# → Click "Save Workflow"

# Replay anytime
python -m recorder.app_ml_integrated
# → Go to "Workflows" tab
# → Select workflow
# → Click "Replay"
```

**Benefits:**
- ✅ Auto-healing when page structure changes
- ✅ Multiple selector strategies
- ✅ Visual fallback if selectors fail
- ✅ Works across frameworks (React, Vue, Angular)

### 2. Call Center Quality Analysis

**Transcribe and Analyze Calls**
```python
from recorder.audio.transcription_engine import TranscriptionEngine
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig

# Transcribe
engine = TranscriptionEngine(model_size="base")
result = engine.transcribe(
    audio_path="call-recording.wav",
    enable_diarization=True
)

# Analyze
llm = LocalLLMEngine(config)
kpi_scores = llm.score_agent_kpi(result.segments)

print(f"Knowledge: {kpi_scores.knowledge_score}")
print(f"Compliance: {kpi_scores.compliance_score}")
print(f"Empathy: {kpi_scores.empathy_score}")
```

**Benefits:**
- ✅ Automatic speaker identification
- ✅ Word-level timestamps
- ✅ 4 KPI metrics per call
- ✅ Sentiment analysis
- ✅ Completely offline

### 3. Compliance Verification

**Verify Agent Statements Against Policies**
```python
from recorder.ml.rag_engine import RAGEngine

# Setup (one-time)
rag = RAGEngine()
rag.ingest_documents_from_directory("data/knowledge_base")
rag.save_index()

# Verify statements
result = rag.verify_statement(
    statement="Refunds are processed within 30 days",
    context="Customer service policy"
)

if result.is_verified:
    print(f"✓ Verified ({result.confidence:.2f})")
    print(f"  Citations: {result.citations}")
else:
    print(f"✗ Not verified ({result.confidence:.2f})")
```

**Benefits:**
- ✅ Instant policy verification
- ✅ Citation tracking
- ✅ Confidence scores
- ✅ No manual lookup needed

### 4. Intent Classification

**Understand User Workflows Automatically**
```python
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig

llm = LocalLLMEngine(config)

actions = [
    {"type": "click", "target": "Shopping Cart"},
    {"type": "click", "target": "Checkout"},
    {"type": "input", "target": "Credit Card Number"},
    {"type": "click", "target": "Place Order"}
]

result = llm.classify_intent(
    actions,
    page_context="https://shop.example.com"
)

print(f"Intent: {result.primary_intent}")  # → "transaction"
print(f"Confidence: {result.confidence}")   # → 0.95
```

**Benefits:**
- ✅ Automatic categorization
- ✅ Secondary intents included
- ✅ Reasoning provided
- ✅ Works with any workflow

---

## 🛠️ Common Tasks

### Record a Multi-Page Workflow

```bash
1. Start recording
2. Navigate through multiple pages
3. Fill forms
4. Click buttons
5. Stop recording

# System automatically:
- Tracks navigation
- Handles iframes
- Captures shadow DOM
- Generates selectors for each step
```

### Replay with Healing

```bash
# If page structure changed:
1. Select workflow
2. Click "Replay"

# System automatically:
- Tries primary selector
- Falls back to alternatives
- Uses visual matching
- Reports healing success

# Check healing stats:
controller.get_healing_stats()
```

### Analyze Multiple Calls

```python
import glob
from recorder.audio.transcription_engine import TranscriptionEngine
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig

engine = TranscriptionEngine()
llm = LocalLLMEngine(config)

results = []
for audio_file in glob.glob("calls/*.wav"):
    # Transcribe
    transcript = engine.transcribe(audio_file)
    
    # Analyze
    kpi = llm.score_agent_kpi(transcript.segments)
    
    results.append({
        "file": audio_file,
        "duration": transcript.duration,
        "speakers": transcript.speakers_count,
        "kpi": kpi.overall_score
    })

# Average KPI
avg_kpi = sum(r["kpi"] for r in results) / len(results)
print(f"Average KPI: {avg_kpi:.2f}")
```

### Build Custom Knowledge Base

```bash
# 1. Create directory
mkdir -p data/knowledge_base

# 2. Add documents
data/knowledge_base/
├── sop_refunds.txt
├── sop_returns.txt
├── faq_shipping.md
├── policy_data_privacy.md
└── compliance_guidelines.txt

# 3. Run app (auto-indexes on startup)
python -m recorder.app_ml_integrated

# Or manually:
from recorder.ml.rag_engine import RAGEngine
rag = RAGEngine()
rag.ingest_documents_from_directory("data/knowledge_base")
rag.save_index()
```

---

## 🔌 API Integration

### Start API Server

```bash
python -m uvicorn recorder.api.main:app --host 0.0.0.0 --port 8000

# Access at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

### Upload & Transcribe Audio

```python
import requests

# Upload
files = {'file': open('recording.wav', 'rb')}
response = requests.post(
    'http://localhost:8000/api/upload-audio',
    files=files
)
job_id = response.json()['job_id']

# Poll for completion
import time
while True:
    status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
    data = status.json()
    
    if data['status'] == 'completed':
        print(data['result'])
        break
    elif data['status'] == 'failed':
        print(f"Error: {data['error']}")
        break
    
    time.sleep(1)
```

### WebSocket Real-Time Updates

```python
import asyncio
import websockets
import json

async def track_job(job_id):
    uri = f"ws://localhost:8000/ws/jobs/{job_id}"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.receive()
            data = json.loads(message)
            
            print(f"Status: {data['status']}")
            print(f"Progress: {data['progress']:.0%}")
            
            if data['status'] in ['completed', 'failed']:
                break

asyncio.run(track_job(job_id))
```

---

## ⚙️ Configuration

### LLM Settings

```python
from recorder.ml.llm_engine import LocalLLMEngine, LLMConfig

# For CPU (4GB RAM)
config = LLMConfig(
    model_path="~/models/llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=4,
    n_gpu_layers=0  # CPU only
)

# For GPU (with CUDA)
config = LLMConfig(
    model_path="~/models/llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=4,
    n_gpu_layers=32  # Offload to GPU
)

llm = LocalLLMEngine(config)
```

### Transcription Settings

```python
from recorder.audio.transcription_engine import TranscriptionEngine

# Fast (CPU)
engine = TranscriptionEngine(
    model_size="tiny",  # or "base"
    device="cpu"
)

# Accurate (GPU)
engine = TranscriptionEngine(
    model_size="medium",  # or "large"
    device="cuda"
)

# Transcribe
result = engine.transcribe(
    audio_path="call.wav",
    enable_diarization=True,
    min_speakers=2,
    max_speakers=4
)
```

### RAG Settings

```python
from recorder.ml.rag_engine import RAGEngine

# High quality embeddings
rag = RAGEngine(
    embedding_model_name="BAAI/bge-large-en-v1.5"
)

# Faster embeddings
rag = RAGEngine(
    embedding_model_name="all-MiniLM-L6-v2"
)

# Hybrid search (best results)
results = rag.retrieve_hybrid(
    query="What is our refund policy?",
    top_k=5,
    dense_weight=0.7  # 70% semantic, 30% keyword
)
```

---

## 📊 Monitoring & Debugging

### Check ML Status

```python
# In QML UI
controller.mlStatusChanged.connect(function(status) {
    console.log("Selector Engine:", status.selector_engine)
    console.log("Healing Engine:", status.healing_engine)
    console.log("LLM Engine:", status.llm_engine)
    console.log("RAG Documents:", status.rag_documents)
})
```

### View Logs

```bash
# Application logs are printed to console
# Set log level:
export LOG_LEVEL=DEBUG

# Or in code:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

```python
import time

# Selector generation
start = time.time()
selectors = selector_engine.generate_selectors(fingerprint)
print(f"Generated {len(selectors)} selectors in {time.time()-start:.3f}s")

# Healing
start = time.time()
result = healing_engine.heal_selector(fingerprint, selectors, page_state)
print(f"Healing took {result.execution_time_ms:.1f}ms")

# LLM inference
start = time.time()
intent = llm.classify_intent(actions)
print(f"LLM inference took {time.time()-start:.2f}s")
```

---

## 🎓 Best Practices

### Recording
1. **Start with clean state** (incognito mode)
2. **Perform actions slowly** for accurate capture
3. **Avoid mouse movement** (only clicks)
4. **Use keyboard shortcuts** when possible
5. **Save frequently** to avoid data loss

### Selectors
1. **Prefer data-testid** over CSS classes
2. **Use ARIA labels** for accessibility
3. **Avoid XPath absolute** (brittle)
4. **Test healing** before production
5. **Review generated selectors** for quality

### LLM Usage
1. **Use Q4_K_M quantization** for balance
2. **Enable GPU** if available
3. **Keep context short** for speed
4. **Batch similar requests** when possible
5. **Cache results** to avoid re-inference

### RAG
1. **Chunk documents** at 512 tokens
2. **Use hybrid search** for best results
3. **Update index** when docs change
4. **Provide context** with queries
5. **Verify citations** for accuracy

---

## 🐛 Troubleshooting

### Selector Fails During Replay
```bash
# Check healing stats
controller.get_healing_stats()

# Try visual matching
# Ensure screenshots are captured

# Add data-testid attributes
# For better stability
```

### LLM Runs Slowly
```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Use smaller model
# Q4_K_M instead of Q5_K_M

# Reduce context length
config.n_ctx = 2048
```

### Transcription Out of Memory
```bash
# Use smaller model
engine = TranscriptionEngine(model_size="tiny")

# Disable diarization
result = engine.transcribe(audio, enable_diarization=False)

# Process in chunks
# Split long audio files
```

### RAG Returns Poor Results
```bash
# Check document quality
print(f"Documents: {len(rag.documents)}")

# Adjust hybrid weights
results = rag.retrieve_hybrid(query, dense_weight=0.8)

# Re-chunk documents
docs_with_smaller_chunks = [
    rag.chunk_document(doc, chunk_size=256)
    for doc in documents
]
```

---

## 📚 Learn More

- **Full Documentation**: `README_PRODUCTION.md`
- **Quick Start**: `QUICKSTART.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **API Reference**: http://localhost:8000/docs

## 💡 Tips

- Use **data-testid** attributes in your apps for stable selectors
- Enable **GPU acceleration** for 4x faster LLM inference
- **Chunk audio files** before transcription for better memory usage
- **Update RAG index** regularly with new documents
- **Monitor healing stats** to improve selector strategies

**Happy Automating! 🚀**
