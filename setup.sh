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

# Install dependencies
echo ""
echo "[3/5] Installing Python dependencies..."
pip3 install -r requirements.txt
echo "    ✓ Dependencies installed"

# Check Qwen CLI
echo ""
echo "[4/5] Checking Qwen CLI..."
if ! command -v qwen &> /dev/null; then
    echo "    WARNING: qwen CLI not found"
    echo "    Please install Qwen CLI before running the pipeline"
    echo "    See: https://github.com/QwenLM/Qwen"
else
    echo "    ✓ qwen CLI available"
fi

# Make scripts executable
echo ""
echo "[5/5] Making scripts executable..."
chmod +x soa_cli.py scripts/check.py
echo "    ✓ soa_cli.py is executable"
echo "    ✓ scripts/check.py is executable"

# Final instructions
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
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
echo "   python soa_cli.py"
echo ""
echo "4. Find your State of the Art in:"
echo "   artifacts/soa/state_of_the_art_final.tex"
echo ""
echo "For more information, see docs/README.md"
echo ""
