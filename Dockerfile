FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV, Tesseract, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (full server stack)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY recorder/ recorder/
COPY data/ data/
COPY instrumentation/ instrumentation/

# Create runtime directories
RUN mkdir -p data/workflows data/screenshots data/executions data/uploads data/rag_index

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "recorder.api.main"]
