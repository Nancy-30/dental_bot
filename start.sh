#!/usr/bin/env bash
# =============================================================================
#  start.sh — ABC Dental Clinic AI Receptionist — single launcher
#
#  Steps:
#    1. Copy .env.example → .env  (if .env is missing)
#    2. pip install -r requirements.txt
#    3. npm install  (frontend)
#    4. npm run build  (frontend → frontend/dist/)
#    5. python agent.py download-files  (Silero VAD + turn-detector models)
#    6. uvicorn backend.main:app   (FastAPI on :7000 — serves API + SPA)
#    7. python agent.py dev        (LiveKit agent worker)
#
#  All logs stream live to this terminal.
#  Ctrl+C stops all processes cleanly.
# =============================================================================

set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
MAGENTA="\033[35m"
RST="\033[0m"

step()   { echo -e "\n${BOLD}${CYAN}[$1] $2${RST}"; }
ok()     { echo -e "${GREEN}    ✓ $1${RST}"; }
warn()   { echo -e "${YELLOW}    ! $1${RST}"; }
err()    { echo -e "${RED}    ✗ $1${RST}" >&2; }
banner() { echo -e "${BOLD}$1${RST}"; }

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"
ENV_FILE="$ROOT/.env"
ENV_EX="$ROOT/.env.example"
MODELS_MARKER="$ROOT/.models_downloaded"

# Force UTF-8 I/O for Python on Windows (prevents charmap encoding errors)
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

BACKEND_PID=""
AGENT_PID=""

# ── Cleanup: kill both services on Ctrl+C or crash ────────────────────────────
cleanup() {
    echo ""
    banner "Shutting down…"
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        ok "Backend stopped"
    fi
    if [ -n "$AGENT_PID" ] && kill -0 "$AGENT_PID" 2>/dev/null; then
        kill "$AGENT_PID" 2>/dev/null
        ok "Agent stopped"
    fi
    wait 2>/dev/null
    echo "Goodbye."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ═══════════════════════════════════════════════════════════════════════════════
banner "$(printf '═%.0s' {1..56})"
banner "  ABC Dental Clinic — AI Receptionist Startup"
banner "$(printf '═%.0s' {1..56})"

# ── Step 1: .env ───────────────────────────────────────────────────────────────
step 1 "Environment file"
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EX" ]; then
        cp "$ENV_EX" "$ENV_FILE"
        warn "Copied .env.example → .env — edit it with your API keys and re-run."
        exit 1
    else
        err ".env not found. Create one from .env.example."
        exit 1
    fi
else
    ok ".env found"
fi

# ── Step 2: Python dependencies ────────────────────────────────────────────────
step 2 "Python dependencies"
pip install -r "$ROOT/requirements.txt" --quiet
ok "Python packages ready"

# ── Step 3: Frontend — npm install ────────────────────────────────────────────
step 3 "Frontend — npm install"
cd "$FRONTEND"
npm install --silent
ok "node_modules ready"
cd "$ROOT"

# ── Step 4: Frontend — npm run build ──────────────────────────────────────────
step 4 "Frontend — npm run build"
cd "$FRONTEND"
npm run build
ok "Built → $FRONTEND/dist"
cd "$ROOT"

# ── Step 5: Agent model files ─────────────────────────────────────────────────
step 5 "Agent model files (Silero VAD + turn-detector)"
if [ -f "$MODELS_MARKER" ]; then
    ok "Already downloaded — skipping"
else
    python agent.py download-files
    touch "$MODELS_MARKER"
    ok "Models downloaded"
fi

# ── Step 6: FastAPI backend — logs stream to terminal with [BACKEND] prefix ───
step 6 "Starting FastAPI backend  →  http://localhost:7000"

python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-7000} \
    --log-level info 2>&1 | \
    while IFS= read -r line; do
        echo -e "${CYAN}[BACKEND]${RST} $line"
    done &
BACKEND_PID=$!

# Wait until the backend is actually accepting connections (max 15 s)
for i in $(seq 1 30); do
    if bash -c 'echo > /dev/tcp/127.0.0.1/7000' 2>/dev/null; then break; fi
    sleep 0.5
done
ok "Backend is up  (PID $BACKEND_PID)"

# ── Step 7: LiveKit agent worker — logs stream to terminal with [AGENT] prefix
step 7 "Starting LiveKit agent worker"

python agent.py dev 2>&1 | \
    while IFS= read -r line; do
        echo -e "${GREEN}[AGENT]${RST}   $line"
    done &
AGENT_PID=$!
ok "Agent started  (PID $AGENT_PID)"

# ── Ready banner ───────────────────────────────────────────────────────────────
echo ""
banner "$(printf '═%.0s' {1..56})"
banner "  All services running — logs streaming below"
echo ""
echo -e "  ${GREEN}Web UI + API${RST}   →  http://localhost:7000"
echo -e "  ${GREEN}API docs      ${RST}  →  http://localhost:7000/docs"
echo -e "  ${GREEN}Health check  ${RST}  →  http://localhost:7000/health"
echo ""
echo -e "  ${CYAN}[BACKEND]${RST}  FastAPI / uvicorn logs"
echo -e "  ${GREEN}[AGENT]${RST}    LiveKit agent worker logs"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${RST} to stop everything."
banner "$(printf '═%.0s' {1..56})"
echo ""

# ── Monitor: shut everything down if either process dies unexpectedly ─────────
while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        err "Backend exited unexpectedly — shutting down."
        cleanup
    fi
    if ! kill -0 "$AGENT_PID" 2>/dev/null; then
        err "Agent exited unexpectedly — shutting down."
        cleanup
    fi
    sleep 3
done
