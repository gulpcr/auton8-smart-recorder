# Auton8 Recorder — Installation, Deployment & Execution Guide

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Requirements](#2-requirements)
3. [Server Deployment (Docker)](#3-server-deployment-docker)
4. [Server Deployment (Manual / No Docker)](#4-server-deployment-manual--no-docker)
5. [Server Deployment — RHEL 9 / CentOS Stream 9](#5-server-deployment--rhel-9--centos-stream-9)
6. [Tester Machine Setup — Windows](#6-tester-machine-setup--windows)
7. [Tester Machine Setup — Linux / macOS](#7-tester-machine-setup--linux--macos)
8. [Tester Machine Setup — RHEL 9](#8-tester-machine-setup--rhel-9)
9. [Connect Tester Machines to the Server](#9-connect-tester-machines-to-the-server)
10. [Running the Recorder](#10-running-the-recorder)
11. [Recording a Workflow](#11-recording-a-workflow)
12. [Replaying a Workflow](#12-replaying-a-workflow)
13. [Verifying Everything Works](#13-verifying-everything-works)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Overview

Auton8 has two distinct components that run on different machines:

```
┌─────────────────────────────────────────────────────────────┐
│                    CENTRAL SERVER                           │
│   FastAPI on port 8010  |  ML Engines  |  SQLite Database  │
│   Handles: healing, vision, NLP, LLM, RAG, audio, analytics│
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP (port 8010)
         ┌─────────────────┼─────────────────┐
         │                 │                 │
┌────────▼───────┐ ┌───────▼────────┐ ┌─────▼──────────┐
│  Tester PC 1   │ │  Tester PC 2   │ │  Tester PC N   │
│  Recorder App  │ │  Recorder App  │ │  Recorder App  │
│  PySide6 + QML │ │  PySide6 + QML │ │  PySide6 + QML │
│  Playwright    │ │  Playwright    │ │  Playwright    │
└────────────────┘ └────────────────┘ └────────────────┘
```

**Server** — runs once, centrally. Hosts all heavy ML models.
**Tester machines** — lightweight install. Record and replay browser workflows. Offload ML work to the server.

---

## 2. Requirements

### Central Server

| Item | Minimum | Recommended |
|------|---------|-------------|
| OS | Ubuntu 22.04 / Debian 12 | Ubuntu 22.04 LTS |
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Disk | 20 GB free | 50 GB |
| Python | 3.10+ | 3.11 |
| Docker | 24+ | latest |
| Docker Compose | v2+ | latest |
| Open port | 8010 | — |

> GPU is optional but speeds up BERT / WhisperX inference significantly.

### Tester Machines (each recorder)

| Item | Requirement |
|------|-------------|
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ |
| Python | 3.10+ |
| RAM | 4 GB |
| Disk | 2 GB free |
| Network | Can reach the central server on port 8010 |

---

## 3. Server Deployment (Docker)

This is the recommended approach. Docker handles all system dependencies automatically.

### Step 1 — Install Docker on the server

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 2 — Copy the project to the server

```bash
# From your local machine
scp -r /path/to/auton8/recorder user@YOUR_SERVER_IP:/opt/auton8

# OR clone from git
git clone https://your-repo-url /opt/auton8
```

### Step 3 — Create the environment file

```bash
cd /opt/auton8
cp .env.example .env
nano .env
```

Edit the values:

```env
# Admin login for the web dashboard and API
ADMIN_EMAIL=admin@yourorg.com
ADMIN_PASSWORD=choose-a-strong-password

# CORS: comma-separated list of allowed origins
# Use * for open access (dev only), or set specific IPs in production
# Example: CORS_ORIGINS=http://192.168.1.10,http://192.168.1.11
CORS_ORIGINS=*

# Log verbosity
LOG_LEVEL=INFO
```

### Step 4 — Build and start the server

```bash
cd /opt/auton8
docker compose up -d --build
```

First build takes 10–20 minutes (downloads ML models and dependencies).

Watch the startup logs:

```bash
docker compose logs -f
```

Wait until you see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8010
```

Press `Ctrl+C` to stop watching logs — the server keeps running in the background.

### Step 5 — Open the firewall port

```bash
# UFW (Ubuntu)
sudo ufw allow 8010/tcp
sudo ufw reload

# Or with iptables
sudo iptables -A INPUT -p tcp --dport 8010 -j ACCEPT
```

If using a cloud provider (AWS, GCP, Azure), add an inbound rule for port 8010 in the security group / firewall settings.

### Step 6 — Verify the server is running

```bash
# From the server itself
curl http://localhost:8010/health

# From any machine on the network
curl http://YOUR_SERVER_IP:8010/health
```

Expected response:

```json
{"status": "healthy", "uptime_seconds": 30, "timestamp": "2026-03-03T10:00:00Z"}
```

Open `http://YOUR_SERVER_IP:8010` in a browser to see the dashboard.

### Step 7 — Get an access token

Every tester machine needs a token to authenticate with the server.

```bash
curl -X POST http://YOUR_SERVER_IP:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourorg.com", "password": "choose-a-strong-password"}'
```

Response:

```json
{
  "status": true,
  "data": {
    "accessToken": "a1b2c3d4e5f6...",
    "user": {"email": "admin@yourorg.com"}
  }
}
```

**Save this token** — you will paste it into each tester machine's settings.

> Note: tokens are stored in memory and reset when the server restarts. If the server restarts, re-run this step and update the token on all tester machines.

### Docker Management Commands

```bash
# Stop the server
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Check container status
docker compose ps
```

---

## 4. Server Deployment (Manual / No Docker)

Use this if you cannot use Docker on the server.

### Step 1 — Install system dependencies

```bash
sudo apt-get update && sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    git
```

### Step 2 — Clone / copy the project

```bash
cd /opt
git clone https://your-repo-url auton8
cd auton8
```

### Step 3 — Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### Step 4 — Install server dependencies

```bash
pip install -r requirements-server.txt
```

This installs FastAPI, all ML libraries, audio processing, and the database layer. No PySide6 or Playwright.

### Step 5 — Download the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### Step 6 — Create required directories

```bash
mkdir -p data/workflows data/screenshots data/executions data/uploads data/rag_index
```

### Step 7 — Set environment variables

```bash
export ADMIN_EMAIL="admin@yourorg.com"
export ADMIN_PASSWORD="choose-a-strong-password"
export CORS_ORIGINS="*"
export LOG_LEVEL="INFO"
```

To make these permanent, add them to `/etc/environment` or a systemd service file.

### Step 8 — Start the server

```bash
source .venv/bin/activate
python -m recorder.api.main
```

### Step 9 — Run as a background service (systemd)

Create `/etc/systemd/system/auton8.service`:

```ini
[Unit]
Description=Auton8 Recorder Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/auton8
ExecStart=/opt/auton8/.venv/bin/python -m recorder.api.main
Restart=on-failure
RestartSec=5
Environment=ADMIN_EMAIL=admin@yourorg.com
Environment=ADMIN_PASSWORD=choose-a-strong-password
Environment=CORS_ORIGINS=*
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable auton8
sudo systemctl start auton8
sudo systemctl status auton8
```

View logs:

```bash
journalctl -u auton8 -f
```

---

## 5. Server Deployment — RHEL 9 / CentOS Stream 9

RHEL 9 uses `dnf` instead of `apt-get`, has different package names, and requires additional repositories for some dependencies. Follow this section instead of Section 3 or 4 if you are on RHEL 9, Rocky Linux 9, or AlmaLinux 9.

### Option A — Docker on RHEL 9 (Recommended)

The Docker container is Debian-based internally, so all system dependencies inside the container install correctly. You only need to install Docker on the host.

#### Step 1 — Install Docker CE

```bash
# Add Docker's official repo for RHEL
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# Install Docker and Compose plugin
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl enable --now docker

# Allow your user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

> If Docker CE is not available for RHEL in your region, use Podman with the `podman-compose` alternative below.

#### Step 2 — Clone and configure

```bash
git clone https://github.com/gulpcr/auton8-smart-recorder.git /opt/auton8
cd /opt/auton8
cp .env.example .env
nano .env   # Set ADMIN_EMAIL and ADMIN_PASSWORD
```

#### Step 3 — Open firewall port

```bash
sudo firewall-cmd --permanent --add-port=8010/tcp
sudo firewall-cmd --reload
```

#### Step 4 — Build and start

```bash
docker compose up -d --build
curl http://localhost:8010/health
```

---

### Option B — Podman + podman-compose on RHEL 9

RHEL 9 ships with Podman as the default container runtime.

```bash
# Install podman-compose
sudo dnf install -y podman podman-compose

# Clone the project
git clone https://github.com/gulpcr/auton8-smart-recorder.git /opt/auton8
cd /opt/auton8
cp .env.example .env
nano .env

# Build and run
podman-compose up -d --build

# Verify
curl http://localhost:8010/health
```

---

### Option C — Manual Install on RHEL 9 (No containers)

#### Step 1 — Enable required repositories

```bash
# EPEL (Extra Packages for Enterprise Linux)
sudo dnf install -y epel-release

# RPM Fusion — needed for ffmpeg
sudo dnf install -y \
  https://download1.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm \
  https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-9.noarch.rpm

# Enable CodeReady Linux Builder (provides some build dependencies)
sudo subscription-manager repos --enable codeready-builder-for-rhel-9-x86_64-rpms
# OR on Rocky/Alma Linux:
sudo dnf config-manager --set-enabled crb
```

#### Step 2 — Install system dependencies

```bash
sudo dnf install -y \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
    tesseract \
    tesseract-langpack-eng \
    mesa-libGL \
    glib2 \
    ffmpeg \
    git \
    gcc \
    gcc-c++ \
    make \
    cmake \
    pkg-config \
    libffi-devel \
    openssl-devel
```

> **Package name differences vs Ubuntu:**
> | Ubuntu | RHEL 9 |
> |--------|--------|
> | `tesseract-ocr` | `tesseract` |
> | `libgl1-mesa-glx` | `mesa-libGL` |
> | `libglib2.0-0` | `glib2` |
> | `python3.11-venv` | included in `python3.11` |
> | `ffmpeg` (main repo) | `ffmpeg` (RPM Fusion required) |

#### Step 3 — Create virtual environment

```bash
cd /opt/auton8
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

#### Step 4 — Install server Python dependencies

```bash
pip install -r requirements-server.txt
```

If `whisperx` fails to install (git dependency), install it separately:

```bash
pip install openai-whisper
pip install git+https://github.com/m-bain/whisperX.git
```

#### Step 5 — Download spaCy model

```bash
python -m spacy download en_core_web_sm
```

#### Step 6 — Handle SELinux (if enforcing)

RHEL 9 runs SELinux in enforcing mode by default. Allow the server to bind to port 8010:

```bash
# Allow Python to bind to port 8010
sudo semanage port -a -t http_port_t -p tcp 8010

# If semanage is not installed:
sudo dnf install -y policycoreutils-python-utils
sudo semanage port -a -t http_port_t -p tcp 8010
```

If you see "Permission denied" errors accessing files in `/opt/auton8/data`:

```bash
sudo chcon -R -t httpd_sys_content_t /opt/auton8/data
# Or temporarily set permissive to diagnose:
sudo setenforce 0
```

#### Step 7 — Open firewall port

```bash
sudo firewall-cmd --permanent --add-port=8010/tcp
sudo firewall-cmd --reload
```

#### Step 8 — Set environment variables and start

```bash
export ADMIN_EMAIL="admin@yourorg.com"
export ADMIN_PASSWORD="strong-password"
export CORS_ORIGINS="*"
export DATA_DIR="/opt/auton8/data"

source .venv/bin/activate
python -m recorder.api.main
```

#### Step 9 — Create a systemd service

```bash
sudo tee /etc/systemd/system/auton8.service > /dev/null <<EOF
[Unit]
Description=Auton8 Recorder Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/auton8
ExecStart=/opt/auton8/.venv/bin/python -m recorder.api.main
Restart=on-failure
RestartSec=5
Environment=ADMIN_EMAIL=admin@yourorg.com
Environment=ADMIN_PASSWORD=strong-password
Environment=CORS_ORIGINS=*
Environment=DATA_DIR=/opt/auton8/data
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now auton8
sudo systemctl status auton8
```

---

## 6. Tester Machine Setup — Windows

Run these steps on every Windows machine that will record or replay workflows.

Run these steps on every Windows machine that will record or replay workflows.

### Step 1 — Install Python 3.11

Download from https://python.org/downloads — choose **Python 3.11**.

During install, check:
- [x] Add Python to PATH
- [x] Install for all users (optional)

Verify:

```cmd
python --version
```

### Step 2 — Open a terminal in the project folder

```cmd
cd C:\path\to\auton8\recorder
```

### Step 3 — Create a virtual environment

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 4 — Install minimal tester dependencies

```cmd
pip install --upgrade pip
pip install -r requirements-minimal.txt
```

This installs only what the recorder app needs: PySide6, Playwright, websockets, pydantic, numpy.

### Step 5 — Install the Playwright browser

```cmd
playwright install chromium
```

### Step 6 — Install Tesseract OCR (optional, for local vision)

Download the installer from:
https://github.com/UB-Mannheim/tesseract/wiki

Install to: `C:\Program Files\Tesseract-OCR`

Add to PATH:
1. Open System Properties → Advanced → Environment Variables
2. Under System Variables, edit `Path`
3. Add: `C:\Program Files\Tesseract-OCR`

Verify: `tesseract --version`

---

## 7. Tester Machine Setup — Linux / macOS

### Step 1 — Install Python 3.11

```bash
# Ubuntu / Debian
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# macOS (via Homebrew)
brew install python@3.11
```

### Step 2 — Open a terminal in the project folder

```bash
cd /path/to/auton8/recorder
```

### Step 3 — Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 4 — Install minimal tester dependencies

```bash
pip install --upgrade pip
pip install -r requirements-minimal.txt
```

### Step 5 — Install the Playwright browser

```bash
playwright install chromium
```

### Step 6 — Install Tesseract OCR (optional)

```bash
# Ubuntu / Debian
sudo apt-get install -y tesseract-ocr

# macOS
brew install tesseract
```

---

## 8. Tester Machine Setup — RHEL 9

Use this section if your tester machines run RHEL 9, Rocky Linux 9, or AlmaLinux 9.

### Step 1 — Install Python 3.11

RHEL 9 ships with Python 3.9 by default. Python 3.11 is available in the AppStream repository:

```bash
sudo dnf install -y python3.11 python3.11-pip
```

Verify:

```bash
python3.11 --version
```

### Step 2 — Install Playwright system dependencies

Playwright on RHEL 9 needs several X11 and graphics libraries:

```bash
sudo dnf install -y \
    nss \
    nspr \
    atk \
    at-spi2-atk \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXrandr \
    libgbm \
    libxcb \
    libxkbcommon \
    mesa-libGL \
    pango \
    cairo \
    cups-libs \
    dbus-libs \
    alsa-lib
```

### Step 3 — Install project dependencies

```bash
cd /path/to/auton8/recorder
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-minimal.txt
```

### Step 4 — Install Playwright browser

```bash
playwright install chromium

# If the above fails due to missing deps, run:
playwright install-deps chromium
playwright install chromium
```

If `playwright install-deps` fails on RHEL (it tries to use apt internally), install the deps manually using Step 2 above and then run `playwright install chromium` again.

### Step 5 — Install Tesseract OCR (optional)

```bash
# Enable EPEL first
sudo dnf install -y epel-release
sudo dnf install -y tesseract tesseract-langpack-eng
```

### Step 6 — Handle SELinux for file access

If the recorder cannot write screenshots or workflow files:

```bash
sudo chcon -R -t user_home_t /path/to/auton8/recorder/data
```

Or add the project directory to the SELinux allow list:

```bash
sudo semanage fcontext -a -t user_home_t "/path/to/auton8/recorder/data(/.*)?"
sudo restorecon -R /path/to/auton8/recorder/data
```

### Step 7 — Run the recorder

```bash
source .venv/bin/activate
python -m recorder.app_enhanced
```

> **Note on display:** If running on a headless RHEL server as a tester (no GUI), you need a virtual display:
> ```bash
> sudo dnf install -y xorg-x11-server-Xvfb
> Xvfb :99 -screen 0 1920x1080x24 &
> export DISPLAY=:99
> python -m recorder.app_enhanced
> ```

---

## 9. Connect Tester Machines to the Server

Do this on every tester machine after completing Section 6, 7, or 8.

### Step 1 — Open `data/settings.json`

It is located at `data/settings.json` inside the project folder.

Edit these fields:

```json
{
  "portalUrl": "http://YOUR_SERVER_IP:8010",
  "portalAccessToken": "a1b2c3d4e5f6...",
  "portalUserEmail": "admin@yourorg.com",
  "portalConnected": false,
  "skillMode": "hybrid",
  "serverFallback": true,
  "serverTimeout": 30
}
```

| Field | Value |
|-------|-------|
| `portalUrl` | Full URL to your server including port |
| `portalAccessToken` | Token from Step 7 of the server setup |
| `portalUserEmail` | Email used to log in |
| `skillMode` | `"hybrid"` — tries local first, falls back to server |
| `serverFallback` | `true` — use server when local fails |
| `serverTimeout` | Seconds to wait for server response |

> Alternatively, configure this from inside the app: open Settings and look for the Portal / Server section.

### Step 2 — Verify network connectivity

From the tester machine, test that the server is reachable:

```bash
# Windows (PowerShell)
Invoke-WebRequest http://YOUR_SERVER_IP:8010/health

# Linux / macOS
curl http://YOUR_SERVER_IP:8010/health
```

If this fails, check:
- Server is running (`docker compose ps` on the server)
- Port 8010 is open in the firewall
- No VPN blocking internal ports

### Step 3 — Start the recorder app and verify connection

```bash
# Windows
.venv\Scripts\activate
python -m recorder.app_enhanced

# Linux / macOS
source .venv/bin/activate
python -m recorder.app_enhanced
```

Once the app launches, check the server's client list:

```bash
curl http://YOUR_SERVER_IP:8010/api/clients
```

You should see this machine listed with `"status": "online"`.

---

## 10. Running the Recorder

### Start the app

```bash
# Windows
.venv\Scripts\activate
python -m recorder.app_enhanced

# Linux / macOS
source .venv/bin/activate
python -m recorder.app_enhanced
```

### App entry points

| Command | Description |
|---------|-------------|
| `python -m recorder.app_enhanced` | Full UI with replay detail panel (recommended) |
| `python -m recorder.app` | Basic UI |
| `python -m recorder.app_ml_integrated` | Full ML mode (requires local ML stack) |
| `python -m recorder.api.main` | API server only (no UI) |

---

## 11. Recording a Workflow

1. Open the recorder app
2. Click **New Recording**
3. Enter a workflow name
4. Click **Start Recording** — a browser window opens
5. Perform your actions in the browser (clicks, typing, navigation)
6. Click **Stop Recording** in the app
7. Click **Save Workflow** — saved to `data/workflows/<name>.json`

The workflow is automatically synced to the server if `portalUrl` is configured.

---

## 12. Replaying a Workflow

### From the UI

1. Open the recorder app
2. Go to the **Workflows** tab
3. Select a workflow from the list
4. Click **Replay**
5. Watch step results in the replay panel — green = passed, orange = healed, red = failed
6. Click any step to expand and see selector details and healing info

### From the command line

```bash
python -m replay.replayer data/workflows/my-workflow.json
```

### From the API (server-side replay)

```bash
curl -X POST http://YOUR_SERVER_IP:8010/api/replay \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"workflow_id": "my-workflow", "headless": true}'
```

This returns a `job_id`. Check progress:

```bash
curl http://YOUR_SERVER_IP:8010/api/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 13. Verifying Everything Works

### Server health

```bash
curl http://YOUR_SERVER_IP:8010/health
# Expected: {"status": "healthy", ...}
```

### ML models loaded

```bash
curl http://YOUR_SERVER_IP:8010/models/status
# Expected: {"selector_engine": true, "healing_engine": true, ...}
```

### Skills available

```bash
curl http://YOUR_SERVER_IP:8010/api/skills/status
```

### Connected recorder clients

```bash
curl http://YOUR_SERVER_IP:8010/api/clients
# Expected: your tester machines listed with "status": "online"
```

### Dashboard

Open `http://YOUR_SERVER_IP:8010` in a browser — shows execution stats, pass rates, connected clients.

---

## 14. Troubleshooting

### Server won't start

```bash
# Check logs for import errors
docker compose logs --tail=50
```

Common cause: a missing ML dependency. Check the first error in the log.

---

### Port 8010 not reachable from tester machine

```bash
# On the server, confirm it's listening
ss -tlnp | grep 8010

# Check UFW
sudo ufw status
```

---

### Tester shows "portalConnected: false"

- Confirm `portalUrl` has no trailing slash: `http://IP:8010` not `http://IP:8010/`
- Confirm the token is correct — re-run the login curl and paste the new token
- Check the server is reachable: `curl http://SERVER_IP:8010/health`

---

### Client disappears from server dashboard

Clients are marked offline if no heartbeat is received for 60 seconds. This means:
- The recorder app was closed
- The machine lost network connectivity
- Restart the recorder app — it resumes the heartbeat automatically

---

### Token stops working after server restart

Auth tokens are stored in memory and reset on every server restart. After a restart:

1. Re-run the login curl (Step 7 of server setup)
2. Update `portalAccessToken` in `data/settings.json` on each tester machine
3. Restart the recorder app

---

### ML healing not working (stuck at Tier 1)

```bash
# Check server models status
curl http://YOUR_SERVER_IP:8010/models/status
```

If `healing_engine` or `selector_engine` is `false`, the server failed to initialize ML on startup. Check logs for the error.

---

### Audio transcription fails

Ensure `ffmpeg` is installed on the server:

```bash
# If using Docker — ffmpeg is included in the Dockerfile
# If manual install:
sudo apt-get install -y ffmpeg
```

---

### Replay step fails with selector error

This is expected behaviour — the healing engine will attempt up to 6 tiers. If all tiers fail, the step is marked as failed. To investigate:

1. Click the failed step in the UI to expand the detail panel
2. View which tiers were attempted and their error messages
3. Update the workflow by re-recording the failing step

---

### Docker image too large / build fails on low disk

```bash
# Check disk space
df -h

# Clean up unused Docker images
docker image prune -a

# Check image size after build
docker images auton8-auton8-server
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start server (Docker) | `docker compose up -d` |
| Stop server | `docker compose down` |
| View server logs | `docker compose logs -f` |
| Rebuild after changes | `docker compose up -d --build` |
| Get auth token | `curl -X POST http://SERVER:8010/api/auth/login -d '{"email":"...","password":"..."}'` |
| Check server health | `curl http://SERVER:8010/health` |
| List connected clients | `curl http://SERVER:8010/api/clients` |
| Start recorder (Windows) | `.venv\Scripts\activate && python -m recorder.app_enhanced` |
| Start recorder (Linux/Mac) | `source .venv/bin/activate && python -m recorder.app_enhanced` |
| Replay from CLI | `python -m replay.replayer data/workflows/name.json` |
| Server dashboard | `http://YOUR_SERVER_IP:8010` |
| API docs (interactive) | `http://YOUR_SERVER_IP:8010/docs` |
