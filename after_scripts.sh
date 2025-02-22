#!/bin/bash
set -e  # Exit immediately on error

echo "Restarting Apache server..."
sudo systemctl restart apache2.service || { echo "Apache restart failed"; exit 1; }

echo "Deployment successful."

