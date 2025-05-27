# 🐰 Bunny.net Dynamic DNS Updater

A lightweight, efficient Dynamic DNS updater for Bunny.net DNS service, optimized for low-resource devices like Raspberry Pi Zero 2W.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bunny.net](https://img.shields.io/badge/DNS-Bunny.net-orange.svg)](https://bunny.net)

## ✨ Features

- **🌐 Multi-Zone Support**: Manage multiple domains and zones from a single configuration
- **📡 IPv4 & IPv6 Support**: Automatic detection and updating of both A and AAAA records
- **⚡ Lightweight**: Minimal resource usage, perfect for Raspberry Pi and other SBCs
- **⚙️ Flexible Configuration**: YAML-based configuration with customization options

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Bunny.net account with DNS service enabled
- Your domain's DNS managed by Bunny.net

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/drshounak/bunny-ddns.git
   cd bunny-ddns
   ```

2. **Install dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Copy and configure the config file**:
   ```bash
   cp config.yaml.example config.yaml
   nano config.yaml
   ```

4. **Get your Bunny.net credentials**:
   - Log into your [Bunny.net dashboard](https://panel.bunny.net)
   - Go to **DNS Zone** → Select your domain
   - Copy the **Zone ID** from the URL or zone details
   - Go to **Account** → **Settings** → **API Keys**
   - Create or copy your **API Key**

### Basic Configuration

Edit `config.yaml` with your details:

```yaml
# Your Bunny.net API key
api_key: "your-actual-api-key-here"

# DNS Zones and Records
zones:
  - zone_id: "123456"  # Your actual zone ID
    domain: "yourdomain.com"
    records:
      - subdomain: "home"  # Creates home.yourdomain.com
        types:
          - type: "A"      # IPv4
            ttl: 300
          - type: "AAAA"   # IPv6
            ttl: 300
```

### Running the Updater

**Single Update** (run once and exit):
```bash
python3 bunny-ddns.py
```

## 🛠️ Automated Setup with Systemd

To run the updater automatically on a schedule, use the provided setup script to configure a systemd service and timer.

1. **Run the setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Follow the prompts**:
   - The script will ask for your preferred update interval (in minutes, e.g., `5` for every 5 minutes).
   - It will create and enable a systemd service and timer to run the updater automatically.

3. **Verify setup**:
   ```bash
   sudo systemctl status bunny-ddns.timer
   ```

4. **Useful commands**:
   ```bash
   # Check timer status
   sudo systemctl status bunny-ddns.timer

   # Check last run
   sudo systemctl status bunny-ddns.service

   # View logs
   sudo journalctl -u bunny-ddns.service -n 20

   # Run manually now
   sudo systemctl start bunny-ddns.service

   # Stop automatic runs
   sudo systemctl stop bunny-ddns.timer

   # Disable service
   sudo systemctl disable bunny-ddns.timer
   ```

## 📋 Configuration Reference

### Complete Configuration Example

```yaml
# Bunny.net API Configuration
api_key: "your-bunny-api-key-here"

# IP Detection Settings
ip_detection:
  ipv4:
    enabled: true
  ipv6:
    enabled: true        # Set to false if you don't have IPv6

# Logging Configuration
logging:
  enabled: true          # Set to false to disable all logging
  level: "INFO"         # DEBUG, INFO, WARNING, ERROR
  file: true            # Log to ddns.log file
  console: false        # Also log to console (useful for debugging)

# DNS Zones Configuration
zones:
  - zone_id: "your-zone-id-1"
    domain: "example.com"
    records:
      # Subdomain examples
      - subdomain: "home"
        types:
          - type: "A"     # IPv4 record
            ttl: 300
          - type: "AAAA"  # IPv6 record
            ttl: 300
      
      # Root domain (example.com)
      - subdomain: ""     # Empty string = root domain
        types:
          - type: "A"
            ttl: 300
      
      # IPv6-only record
      - subdomain: "ipv6only"
        types:
          - type: "AAAA"
            ttl: 600

  # Multiple domains supported
  - zone_id: "your-zone-id-2"
    domain: "anotherdomain.net"
    records:
      - subdomain: "www"
        types:
          - type: "A"
            ttl: 300
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `api_key` | Your Bunny.net API key | **Required** |
| `ip_detection.ipv4.enabled` | Enable IPv4 detection | `true` |
| `ip_detection.ipv6.enabled` | Enable IPv6 detection | `true` |
| `logging.enabled` | Enable logging | `true` |
| `logging.level` | Log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `logging.file` | Log to file | `true` |
| `logging.console` | Log to console | `false` |

## 🔧 Alternative: Cron Job Setup

For systems without systemd, you can use a cron job to run the updater periodically.

1. **Edit crontab**:
   ```bash
   crontab -e
   ```

2. **Add a cron job** (e.g., run every 5 minutes):
   ```bash
   */5 * * * * cd /home/pi/bunny-ddns && /usr/bin/python3 bunny-ddns.py >> /var/log/bunny-ddns-cron.log 2>&1
   ```

## 🛠️ Troubleshooting

### Common Issues

**Authentication Error (401)**
```
ERROR - Invalid API key. Check 'api_key' in config.yaml
```
- Verify your API key in the Bunny.net dashboard
- Ensure no extra spaces or characters in the config

**Zone Not Found (404)**
```
ERROR - Zone ID 123456 not found. Verify Zone ID in Bunny.net DNS panel
```
- Check the Zone ID in your DNS zone settings
- Ensure the domain is properly configured in Bunny.net

**No IP Address Retrieved**
```
WARNING - No IP addresses available for example.com
```
- Check your internet connection
- Verify firewall isn't blocking HTTP requests
- Try setting `logging.level: "DEBUG"` for more details

**Permission Denied**
```
PermissionError: [Errno 13] Permission denied: 'ddns.log'
```
- Ensure the script has write permissions to its directory
- Run with appropriate user permissions

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
logging:
  enabled: true
  level: "DEBUG"
  console: true  # See output in real-time
```

### Log Files

- **Log Location**: `ddns.log` (same directory as script)
- **Log Rotation**: Logs are appended, consider rotating large files
- **Viewing Logs**: `tail -f ddns.log` to monitor in real-time

## 📁 Project Structure

```
bunny-ddns/
├── bunny-ddns.py            # Main script
├── config.yaml              # Configuration file
├── config.yaml.example      # Example configuration
├── requirements.txt         # Python dependencies
├── setup.sh                 # Setup script for systemd service
├── ddns.log                 # Log file (created automatically)
├── README.md                # This documentation
└── LICENSE                  # MIT License
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Not affiliated with Bunny.net
