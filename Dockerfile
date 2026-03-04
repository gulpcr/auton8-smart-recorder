FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV, Tesseract, audio (ffmpeg), and whisperx (git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install server-only Python deps (no PySide6, no Playwright, no test tools)
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy only the server package — data/ is mounted as a volume at runtime
COPY recorder/ recorder/

# Create runtime directories (populated via the mounted volume)
RUN mkdir -p data/workflows data/screenshots data/executions data/uploads data/rag_index

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

CMD ["python", "-m", "recorder.api.main"]
