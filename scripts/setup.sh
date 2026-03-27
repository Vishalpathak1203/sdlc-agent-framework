#!/usr/bin/env bash
# setup.sh — One-command setup for the SDLC Agent Framework
# Usage: bash setup.sh [project-name]
set -e

PROJECT="${1:-default}"
VENV_PATH="${HOME}/.sdlc-agents-venv"
AGENTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== SDLC Agent Framework Setup ==="
echo "Project:     ${PROJECT}"
echo "Agents Root: ${AGENTS_ROOT}"
echo "Venv:        ${VENV_PATH}"
echo ""

# ── Python check ────────────────────────────────────────────────────────────
echo "[1/5] Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "  Python ${PYTHON_VERSION} found"
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        echo "  Version OK (>=3.10)"
    else
        echo "  ERROR: Python 3.10+ required (found ${PYTHON_VERSION})"
        exit 1
    fi
else
    echo "  ERROR: python3 not found. Install Python 3.10+."
    exit 1
fi

# ── Virtual environment ─────────────────────────────────────────────────────
echo ""
echo "[2/5] Creating virtual environment at ${VENV_PATH}..."
if [ -d "${VENV_PATH}" ]; then
    echo "  Venv already exists, updating packages..."
else
    if command -v uv &>/dev/null; then
        echo "  Using uv (fast)"
        uv venv "${VENV_PATH}"
    else
        python3 -m venv "${VENV_PATH}"
    fi
    echo "  Created: ${VENV_PATH}"
fi

if command -v uv &>/dev/null; then
    uv pip install --python "${VENV_PATH}/bin/python" -r "${AGENTS_ROOT}/scripts/requirements.txt"
else
    "${VENV_PATH}/bin/pip" install -r "${AGENTS_ROOT}/scripts/requirements.txt"
fi
echo "  Packages installed"

# ── Verify ──────────────────────────────────────────────────────────────────
echo ""
echo "[3/5] Verifying installation..."
"${VENV_PATH}/bin/python" -c "import weaviate, fastembed; print('  weaviate + fastembed: OK')"

# ── GitHub CLI check ─────────────────────────────────────────────────────────
echo ""
echo "[4/5] Checking GitHub CLI (for PR review KB)..."
if command -v gh &>/dev/null; then
    if gh auth status &>/dev/null; then
        echo "  gh CLI: authenticated"
    else
        echo "  gh CLI installed but not authenticated."
        echo "  Run: gh auth login"
        echo "  (Optional — only needed for PR review KB)"
    fi
else
    echo "  gh CLI not installed. Install with: brew install gh"
    echo "  (Optional — only needed for PR review KB)"
fi

# ── Weaviate ─────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Downloading Weaviate binary..."
"${VENV_PATH}/bin/python" "${AGENTS_ROOT}/scripts/start_weaviate.py" --background --project "${PROJECT}"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "  # Initialize schema"
echo "  AGENTS_WEAVIATE_URL=http://localhost:8090 \\"
echo "  ${VENV_PATH}/bin/python ${AGENTS_ROOT}/scripts/update_kb.py \\"
echo "    --init-schema --project ${PROJECT}"
echo ""
echo "  # Index your codebase"
echo "  AGENTS_WEAVIATE_URL=http://localhost:8090 \\"
echo "  ${VENV_PATH}/bin/python ${AGENTS_ROOT}/scripts/update_kb.py \\"
echo "    --repo-root /path/to/your/project --project ${PROJECT}"
echo ""
echo "  # Test RAG"
echo "  AGENTS_WEAVIATE_URL=http://localhost:8090 \\"
echo "  ${VENV_PATH}/bin/python ${AGENTS_ROOT}/scripts/query_rag.py \\"
echo "    'your query here' --project ${PROJECT}"
echo ""
echo "Add these to your shell profile (~/.zshrc or ~/.bashrc):"
echo "  export AGENTS_ROOT=${AGENTS_ROOT}"
echo "  export AGENTS_VENV=${VENV_PATH}/bin/python"
echo "  export AGENTS_WEAVIATE_URL=http://localhost:8090"
echo "  export AGENTS_PROJECT=${PROJECT}"
