#!/bin/bash

# Quick activation script for SOA-CLI virtual environment
# Run with: source activate.sh

if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
    echo "Python: $(which python)"
    echo "To deactivate: deactivate"
else
    echo "✗ Virtual environment not found"
    echo "Run ./setup.sh first"
    exit 1
fi
