#!/bin/bash

# Installation script for Call Intelligence System
# Supports: Linux, macOS

set -e

echo "🚀 Call Intelligence System - Installation Script"
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_warning "$1 is not installed"
        return 1
    fi
}

# Check Python version
echo ""
echo "Checking Python installation..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        print_success "Python $PYTHON_VERSION (>= 3.10 required)"
    else
        print_error "Python 3.10+ required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
print_success "pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
python -m playwright install
print_success "Playwright browsers installed"

# Install Tesseract (OS-specific)
echo ""
echo "Checking Tesseract OCR..."
if check_command tesseract; then
    print_success "Tesseract is installed"
else
    print_warning "Tesseract not found"
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing Tesseract on macOS..."
        if check_command brew; then
            brew install tesseract
            print_success "Tesseract installed via Homebrew"
        else
            print_error "Homebrew not found. Please install Tesseract manually:"
            echo "  brew install tesseract"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Tesseract on Linux..."
        if check_command apt-get; then
            sudo apt-get update
            sudo apt-get install -y tesseract-ocr
            print_success "Tesseract installed via apt"
        elif check_command yum; then
            sudo yum install -y tesseract
            print_success "Tesseract installed via yum"
        else
            print_error "Package manager not found. Please install Tesseract manually"
        fi
    fi
fi

# Download spaCy model
echo ""
echo "Downloading spaCy language model..."
python -m spacy download en_core_web_sm
print_success "spaCy model downloaded"

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p data/workflows
mkdir -p data/screenshots
mkdir -p data/knowledge_base
mkdir -p data/rag_index
mkdir -p data/uploads
mkdir -p models
print_success "Data directories created"

# Optional: Download LLM model
echo ""
echo "Would you like to download a local LLM model? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "Downloading Llama 2 7B Chat (Q4_K_M, ~4GB)..."
    echo "This may take several minutes..."
    
    pip install huggingface-hub
    
    mkdir -p ~/models
    
    python3 << EOF
from huggingface_hub import hf_hub_download
import os

model_path = hf_hub_download(
    repo_id="TheBloke/Llama-2-7B-Chat-GGUF",
    filename="llama-2-7b-chat.Q4_K_M.gguf",
    local_dir=os.path.expanduser("~/models")
)
print(f"Model downloaded to: {model_path}")
EOF
    
    print_success "LLM model downloaded"
else
    print_warning "Skipped LLM model download"
    echo "  You can download manually later from:"
    echo "  https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF"
fi

# Installation complete
echo ""
echo "=================================================="
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo "=================================================="
echo ""
echo "To get started:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Run desktop app: python -m recorder.app_ml_integrated"
echo "  3. Or run API server: python -m uvicorn recorder.api.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Documentation: README_PRODUCTION.md"
echo "API Docs: http://localhost:8000/docs (after starting API)"
echo ""
