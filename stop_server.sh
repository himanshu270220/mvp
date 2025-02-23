#!/bin/bash
set -e  # Exit if any command fails

echo "Stopping Python Application..."

# Kill running Python process
pkill -f "python main.py" || true

echo "Application stopped successfully."
