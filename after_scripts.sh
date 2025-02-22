#!/bin/bash
set -e  # Exit if any command fails

echo "Running After Install Script..."

# Restart Apache2 service to serve the new application
echo "Restarting Apache2 service..."
systemctl restart apache2.service

# Start the Python application
echo "Starting Python application..."
cd /var/www/html/RAGHT2.0
source venv/bin/activate
nohup python main.py > app.log 2>&1 &

echo "After Install Script Completed."

