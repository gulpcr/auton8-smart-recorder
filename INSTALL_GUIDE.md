# Installation Guide - Staged Approach

## ✅ You Already Have: Basic App Working!

Your basic recorder app is already running with:
- Core UI with PySide6
- Browser automation with Playwright
- WebSocket event capture
- Workflow recording & replay

## 🎯 Choose Your Installation Level

### Level 1: Basic (CURRENT - Already Installed ✓)
```bash
pip install -r requirements-minimal.txt
python -m recorder.app  # ✓ Working!
```

**What you have:**
- Desktop UI
- Browser recording
- Workflow replay
- Basic selectors

---

### Level 2: ML Core (Recommended Next)
```bash
pip install -r requirements-core.txt
```

**Adds (~5-10 minutes, ~2GB):**
- ✅ Multi-dimensional selector generation
- ✅ Intelligent healing with XGBoost
- ✅ Computer vision (OCR, visual matching)
- ✅ Basic NLP features
- ✅ Traditional ML models

**Then run:**
```bash
python -m recorder.app_ml_integrated
```

---

### Level 3: Advanced ML (Full Power)
```bash
pip install -r requirements-ml-advanced.txt
```

**Adds (~10-15 minutes, ~5GB):**
- ✅ Local LLM (Llama, Mistral, Phi-3)
- ✅ BERT embeddings
- ✅ RAG with FAISS
- ✅ Semantic search
- ✅ Intent classification
- ✅ FastAPI server

**Download LLM model:**
```bash
pip install huggingface-hub
huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF llama-2-7b-chat.Q4_K_M.gguf --local-dir ~/models
```

---

### Level 4: Audio Processing (Optional)
```bash
pip install -r requirements-audio.txt
```

**Adds (~10 minutes, ~3GB):**
- ✅ Audio transcription (Whisper)
- ✅ Noise reduction
- ✅ Audio analysis

---

## 🚀 Quick Install Commands

### Option A: Install Everything at Once (if you're brave)
```bash
pip install -r requirements-core.txt
pip install -r requirements-ml-advanced.txt
pip install -r requirements-audio.txt
```

### Option B: Staged Installation (Recommended)
```bash
# Stage 1: Core ML (do this next!)
pip install -r requirements-core.txt
python -m spacy download en_core_web_sm

# Test it
python -m recorder.app_ml_integrated

# Stage 2: Advanced ML (if you want LLM features)
pip install -r requirements-ml-advanced.txt

# Stage 3: Audio (if you need transcription)
pip install -r requirements-audio.txt
```

---

## ⚡ What's Working Right Now

You can use the basic app **immediately**:

```bash
# In terminal (or it's already running!)
python -m recorder.app
```

**Current Features:**
- ✅ Record browser workflows
- ✅ Save/load workflows  
- ✅ Replay workflows
- ✅ Multi-selector strategies
- ✅ Timeline visualization

---

## 🎯 Recommended Next Step

Install **Level 2** for the best experience:

```bash
pip install -r requirements-core.txt
python -m spacy download en_core_web_sm
python -m recorder.app_ml_integrated
```

This gives you ML-powered selectors and healing without the heavy LLM dependencies!

---

## 🐛 Troubleshooting

### Issue: PyTorch installation fails
```bash
# Install PyTorch separately first
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: llama-cpp-python fails to build
```bash
# Skip it for now, you don't need LLM for most features
# Or install pre-built wheel
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

### Issue: Any package fails
```bash
# Just skip it and try the next level
# The app will work without it
```

---

## 📊 Installation Times & Sizes

| Level | Time | Disk Space | Key Features |
|-------|------|------------|--------------|
| Basic | 2 min | 500MB | Recording, Replay |
| Core | 10 min | 2GB | ML Selectors, Healing |
| Advanced | 20 min | 7GB | LLM, RAG, Full AI |
| Audio | 10 min | 10GB | Transcription |

---

## ✨ Remember

**Your basic app is already working!** You can:
- Use it right now without any more installs
- Add features incrementally
- Skip what you don't need

**Start recording workflows immediately while you decide which features to add!** 🚀
