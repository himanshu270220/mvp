#!/bin/bash
set -e  # Exit if any command fails

echo "Starting Python Application..."

cd /var/www/html/RAGHT2.0 || { echo "Application directory not found"; exit 1; }

# Activate virtual environment
source venv/bin/activate

# Start application in the background
nohup python main.py > app.log 2>&1 &

echo "Application started successfully."
