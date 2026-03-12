#!/bin/bash

# SOA-CLI Setup Script
# Initializes the multi-agent system

set -e

echo "=========================================="
echo "SOA-CLI Setup"
echo "=========================================="
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "    Found Python $python_version"

# Check if pip is available
echo ""
echo "[2/5] Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "    ERROR: pip3 not found. Please install pip."
    exit 1
fi
echo "    ✓ pip3 available"

# Create virtual environment
echo ""
echo "[3/5] Creating Python virtual environment (.venv)..."
if [ -d ".venv" ]; then
    echo "    ℹ Virtual environment already exists"
else
    python3 -m venv .venv
    echo "    ✓ Virtual environment created"
fi

# Activate virtual environment and install dependencies
echo ""
echo "[4/5] Installing Python dependencies in virtual environment..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "    ✓ Dependencies installed in .venv"

# Check Qwen CLI
echo ""
echo "[5/6] Checking Qwen CLI..."
if ! command -v qwen &> /dev/null; then
    echo "    WARNING: qwen CLI not found"
    echo "    Please install Qwen CLI before running the pipeline"
    echo "    See: https://github.com/QwenLM/Qwen"
else
    echo "    ✓ qwen CLI available"
fi

# Make scripts executable
echo ""
echo "[6/6] Making scripts executable..."
chmod +x soa_cli.py
echo "    ✓ soa_cli.py is executable"


# Final instructions
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "⚠️  IMPORTANT: Activate the virtual environment before running:"
echo "   source .venv/bin/activate"
echo ""
echo "Next steps:"
echo ""
echo "1. Define your research scope (IMPORTANT):"
echo "   python -m src.theme_builder template"
echo "   nano theme_input.json"
echo "   python -m src.theme_builder build"
echo ""
echo "2. Add your PDF papers to the papers/ directory:"
echo "   cp /path/to/papers/*.pdf papers/"
echo ""
echo "3. Run the complete pipeline:"
echo "   python3 soa_cli.py"
echo ""
echo "4. Find your State of the Art in:"
echo "   STATE_OF_THE_ART.tex"
echo ""
echo "Optional: Test the installation:"
echo "   python3 test_langgraph.py"
echo ""
echo "To deactivate the virtual environment later:"
echo "   deactivate"
echo ""
echo "For more information, see docs/README.md"
echo ""
