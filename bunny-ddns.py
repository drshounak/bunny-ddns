#!/usr/bin/env python3

import requests
import yaml
import time
import sys
import logging
from pathlib import Path
import os

# Configuration paths (machine-agnostic)
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = Path(os.getenv("BUNNY_DDNS_CONFIG_DIR", SCRIPT_DIR))
CONFIG_FILE = CONFIG_DIR / "config.yaml"
LOG_FILE = CONFIG_DIR / "ddns.log"

# Bunny.net API base URL
BASE_URL = "https://api.bunny.net"

# IP detection services
IP_SERVICES = {
    "ipv4": ["https://ipv4.icanhazip.com", "https://api.ipify.org"],
    "ipv6": ["https://ipv6.icanhazip.com", "https://api6.ipify.org"]
}

class DDNSUpdater:
    def __init__(self):
        # Ensure config/log directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
        self.setup_logging()
        self.session = requests.Session()
        self.session.timeout = 10
        self.session.headers.update({
            "Accept": "application/json"
        })

    def load_config(self):
        """Load YAML configuration."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
            if not config.get('api_key'):
                raise ValueError("Missing api_key in config")
            return config
        except Exception as e:
            print(f"Config error: {e}")
            sys.exit(1)

    def setup_logging(self):
        """Setup logging based on config."""
        if not self.config.get('logging', {}).get('enabled', True):
            logging.getLogger().handlers = []
            logging.getLogger().setLevel(logging.CRITICAL + 1)
            return

        level = getattr(logging, self.config.get('logging', {}).get('level', 'INFO').upper(), logging.INFO)
        handlers = []

        if self.config.get('logging', {}).get('file', True):
            handlers.append(logging.FileHandler(LOG_FILE))
        if self.config.get('logging', {}).get('console', False):
            handlers.append(logging.StreamHandler())

        if handlers:
            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
        else:
            logging.getLogger().handlers = []
            logging.getLogger().setLevel(logging.CRITICAL + 1)

    def get_ip(self, ip_type):
        """Get current public IP address."""
        if not self.config.get('ip_detection', {}).get(ip_type, {}).get('enabled', True):
            logging.debug(f"{ip_type} detection disabled in config")
            return None

        for service in IP_SERVICES[ip_type]:
            try:
                response = self.session.get(service, timeout=5)
                response.raise_for_status()
                ip = response.text.strip()
                if ip and ('.' in ip if ip_type == 'ipv4' else ':' in ip):
                    logging.debug(f"Got {ip_type}: {ip} from {service}")
                    return ip
            except requests.RequestException as e:
                logging.warning(f"Failed to fetch {ip_type} from {service}: {e}")
        logging.error(f"No {ip_type} address retrieved from any API")
        return None

    def get_records(self, zone_id):
        """Get all DNS records for a zone."""
        try:
            response = self.session.get(
                f"{BASE_URL}/dnszone/{zone_id}",
                headers={"AccessKey": self.config['api_key']}
            )
            response.raise_for_status()
            return response.json().get('Records', [])
        except requests.RequestException as e:
            logging.error(f"Failed to get records for zone {zone_id}: {e}")
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    logging.error("Invalid API key. Check 'api_key' in config.yaml")
                elif e.response.status_code == 404:
                    logging.error(f"Zone ID {zone_id} not found. Verify Zone ID in Bunny.net DNS panel")
            return []

    def update_record(self, zone_id, record_id, name, domain, record_type, value, ttl):
        """Update a DNS record."""
        data = {
            "Type": 0 if record_type == 'A' else 1,
            "Name": name,
            "Value": value,
            "Ttl": ttl
        }
        full_name = f"{name}.{domain}" if name else domain
        try:
            response = self.session.post(
                f"{BASE_URL}/dnszone/{zone_id}/records/{record_id}",
                headers={"AccessKey": self.config['api_key']},
                json=data
            )
            response.raise_for_status()
            logging.info(f"Updated {record_type} record for {full_name} in zone {zone_id} to {value}")
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to update {record_type} record for {full_name} in zone {zone_id}: {e}")
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    logging.error("Invalid API key. Check 'api_key' in config.yaml")
                elif e.response.status_code == 404:
                    logging.error(f"Record ID {record_id} or Zone ID {zone_id} not found")
            return False

    def create_record(self, zone_id, name, domain, record_type, value, ttl):
        """Create a new DNS record."""
        data = {
            "Type": 0 if record_type == 'A' else 1,
            "Name": name,
            "Value": value,
            "Ttl": ttl
        }
        full_name = f"{name}.{domain}" if name else domain
        try:
            response = self.session.put(
                f"{BASE_URL}/dnszone/{zone_id}/records",
                headers={"AccessKey": self.config['api_key']},
                json=data
            )
            response.raise_for_status()
            logging.info(f"Created {record_type} record for {full_name} in zone {zone_id} with {value}")
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to create {record_type} record for {full_name} in zone {zone_id}: {e}")
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    logging.error("Invalid API key. Check 'api_key' in config.yaml")
                elif e.response.status_code == 404:
                    logging.error(f"Zone ID {zone_id} not found. Verify Zone ID in Bunny.net DNS panel")
            return False

    def process_zone(self, zone_config):
        """Process all records in a zone."""
        zone_id = zone_config['zone_id']
        domain = zone_config['domain']

        # Get current IPs
        current_ips = {}
        if self.config.get('ip_detection', {}).get('ipv4', {}).get('enabled', True):
            current_ips['ipv4'] = self.get_ip('ipv4')
        if self.config.get('ip_detection', {}).get('ipv6', {}).get('enabled', True):
            current_ips['ipv6'] = self.get_ip('ipv6')

        if not any(current_ips.values()):
            logging.warning(f"No IP addresses available for {domain}")
            return

        # Get existing records
        existing_records = self.get_records(zone_id)
        record_map = {(r['Name'], r['Type']): r for r in existing_records}

        # Process each configured record
        for record_config in zone_config.get('records', []):
            subdomain = record_config.get('subdomain', '')
            for rec_type in record_config.get('types', []):
                record_type = rec_type.get('type', 'A')
                ttl = rec_type.get('ttl', 300)

                # Get IP for this record type
                ip = current_ips.get('ipv4' if record_type == 'A' else 'ipv6')
                if not ip:
                    logging.warning(f"No {record_type} address available for {subdomain}.{domain}")
                    continue

                # Check if record exists
                type_id = 0 if record_type == 'A' else 1
                existing = record_map.get((subdomain, type_id))

                if existing:
                    # Update if IP changed
                    if existing['Value'] != ip:
                        self.update_record(zone_id, existing['Id'], subdomain, domain, record_type, ip, ttl)
                    else:
                        logging.debug(f"{subdomain}.{domain} ({record_type}) already up to date")
                else:
                    # Create new record
                    self.create_record(zone_id, subdomain, domain, record_type, ip, ttl)

    def run_once(self):
        """Run DDNS update once."""
        logging.info("Starting DDNS update")

        for zone_config in self.config.get('zones', []):
            try:
                self.process_zone(zone_config)
            except Exception as e:
                logging.error(f"Error processing zone {zone_config.get('domain')}: {e}")

        logging.info("DDNS update completed")

    def run_daemon(self):
        """Run as daemon with configurable interval."""
        interval = self.config.get('daemon', {}).get('interval', 1800)  # 30 minutes default
        logging.info(f"Starting DDNS daemon (interval: {interval}s)")

        while True:
            try:
                self.run_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("DDNS daemon stopped")
                break
            except Exception as e:
                logging.error(f"Daemon error: {e}")
                time.sleep(60)  # Wait 1 minute before retry

def main():
    updater = DDNSUpdater()

    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        updater.run_daemon()
    else:
        updater.run_once()

if __name__ == "__main__":
    main()
