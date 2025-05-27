#!/bin/bash

# Bunny.net DDNS Simple Setup Script
# This script sets up systemd service and runs initial update

set -e  # Exit on any error

echo "🐰 Bunny.net DDNS Setup"
echo "======================"

# Check if we're in the right directory
if [[ ! -f "bunny-ddns.py" ]]; then
    echo "❌ Error: bunny-ddns.py not found in current directory"
    echo "Please run this script from the bunny-ddns repository directory"
    exit 1
fi

# Check if config exists
if [[ ! -f "config.yaml" ]]; then
    echo "❌ Error: config.yaml not found"
    echo "Please copy config.yaml.example to config.yaml and configure it first"
    exit 1
fi

# Variables
SCRIPT_DIR=$(pwd)
CURRENT_USER=$(whoami)
SERVICE_NAME="bunny-ddns"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "📁 Script directory: $SCRIPT_DIR"
echo "👤 User: $CURRENT_USER"
echo ""

# Test configuration first
echo "🔧 Testing configuration..."
if ! python3 -c "import yaml; config=yaml.safe_load(open('config.yaml')); assert config.get('api_key'), 'Missing api_key'"; then
    echo "❌ Configuration test failed"
    exit 1
fi
echo "✅ Configuration looks good"
echo ""

# Run initial update
echo "🚀 Running initial DDNS update..."
echo "================================="
python3 bunny-ddns.py
echo ""
echo "✅ Initial update completed"
echo ""

# Prompt user for timer interval
echo "⏲️  Please specify how often (in minutes) the DDNS update should run (e.g., 5 for every 5 minutes):"
read -p "Enter interval in minutes (minimum 1): " TIMER_INTERVAL

# Validate input
if ! [[ "$TIMER_INTERVAL" =~ ^[0-9]+$ ]] || [ "$TIMER_INTERVAL" -lt 1 ]; then
    echo "❌ Error: Invalid input. Please enter a positive integer for the interval."
    exit 1
fi
echo "✅ Timer will run every $TIMER_INTERVAL minutes"
echo ""

# Create systemd service
echo "⚙️  Creating systemd service..."

sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Bunny.net Dynamic DNS Updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/bunny-ddns.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

# Create timer for periodic execution
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

sudo tee $TIMER_FILE > /dev/null << EOF
[Unit]
Description=Run Bunny.net DDNS Update every $TIMER_INTERVAL minutes
Requires=${SERVICE_NAME}.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=${TIMER_INTERVAL}min
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

echo "✅ Timer file created (runs every $TIMER_INTERVAL minutes)"

# Enable and start
echo "🔄 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.timer
sudo systemctl start ${SERVICE_NAME}.timer

echo ""
echo "📊 Service Status:"
echo "=================="
sudo systemctl status ${SERVICE_NAME}.timer --no-pager

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Your DDNS updater is now running automatically every $TIMER_INTERVAL minutes."
echo ""
echo "Useful commands:"
echo "  Check timer status:    sudo systemctl status bunny-ddns.timer"
echo "  Check last run:        sudo systemctl status bunny-ddns.service"
echo "  View logs:             sudo journalctl -u bunny-ddns.service -n 20"
echo "  Run manually now:      sudo systemctl start bunny-ddns.service"
echo "  Stop automatic runs:   sudo systemctl stop bunny-ddns.timer"
echo "  Disable service:       sudo systemctl disable bunny-ddns.timer"
echo ""
echo "Next automatic update in ~$TIMER_INTERVAL minutes."
