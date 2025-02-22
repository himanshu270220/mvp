#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Running Before Install Script..."

# Stop running Python application safely
if pgrep -f "python main.py"; then
    echo "Stopping existing application..."
    pkill -f "python main.py"
    sleep 3  # Wait a few seconds to ensure the process stops
else
    echo "No existing application found."
fi

# Ensure the target directory exists before deleting
APP_DIR="/var/www/html/RAGHT2.0"
if [ -d "$APP_DIR" ]; then
    echo "Removing old application files..."
    rm -rf "$APP_DIR"/*
else
    echo "Application directory does not exist, creating it..."
    mkdir -p "$APP_DIR"
fi

# Ensure correct permissions after cleanup
echo "Setting correct permissions for $APP_DIR"
chmod -R 755 "$APP_DIR"

echo "Before Install Script Completed."

