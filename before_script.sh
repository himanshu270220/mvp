#!/bin/bash
set -e  # Exit if any command fails

echo "Running Before Install Script..."

# Stop the existing application if running
echo "Stopping existing application..."
pkill -f "python main.py" || true

# Clean up old application files
echo "Removing old application files..."
rm -rf /var/www/html/RAGHT2.0/*

echo "Before Install Script Completed."
