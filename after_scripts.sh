#!/bin/bash
set -e  # Exit if any command fails

echo "Running After Install Script..."

# Restart Apache (if using Apache as a reverse proxy)
echo "Restarting Apache..."
systemctl restart apache2

echo "After Install Script Completed."
