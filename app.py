import requests
import urllib3
import json
import time
import platform
import subprocess
import logging
from datetime import datetime
from urllib.parse import urlparse

# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Device credentials (Consider storing these securely)
base_url = "https://105.178.106.81"  # Adjust to your router's IP address
username = "admin"
password = "Salvi.2024"

# Global variable to track connection times
connection_times = {}  # Dictionary to track connection times of devices

# Function to login to the router
def login(base_url, username, password, retries=3, delay=5):
    """Login to the router and obtain the session ID with retry capability."""
    credentials = {"username": username, "password": password}
    payload = {
        "method": "call",
        "params": [
            "00000000000000000000000000000000",
            "session",
            "login",
            credentials
        ],
        "jsonrpc": "2.0",
        "id": 1
    }
    attempt = 0

    while attempt < retries:
        try:
            response = requests.post(f"{base_url}/ubus", json=payload, verify=False, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            result = data.get('result')
            if result and result[0] == 0:
                session_info = result[1]
                session_id = session_info.get('ubus_rpc_session')
                logger.info(f"Logged in successfully. Session ID: {session_id}")
                return session_id, session_info
            else:
                logger.error("Failed to obtain session ID.")
                return None, None
        except requests.exceptions.RequestException as e:
            attempt += 1
            logger.warning(f"Login attempt {attempt} failed. Error: {e}")
            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    logger.error("Unable to login after multiple attempts.")
    return None, None

# Other functions here (e.g., get_wireless_interfaces, get_connected_devices, etc.)...
# Make sure to replace all `app.logger` calls with `logger` instead.

# Function to get router data
def get_router_data():
    # Extract IP address from base_url
    parsed_url = urlparse(base_url)
    router_ip = parsed_url.hostname

    # Check router status
    router_status = check_router_status(router_ip)

    response_data = {
        "router_status": router_status,
        "total_devices": 0,
        "total_devices_2.4ghz": 0,
        "total_devices_5ghz": 0,
        "total_rx_packets": 0,
        "total_tx_packets": 0,
        "devices_2_4ghz": [],
        "devices_5ghz": []
    }

    if router_status == 1:
        # Try to login
        session_id, session_info = login(base_url, username, password)
        if session_id:
            # Get wireless interfaces using iwinfo service
            interface_frequencies = get_wireless_interfaces(base_url, session_id)
            if not interface_frequencies:
                logger.error("No wireless interfaces found. Exiting data collection.")
                return response_data

            # Fetch ARP table information
            arp_table = get_arp_table(base_url, session_id)
            arp_mapping = {entry['mac'].lower(): entry['ip'] for entry in arp_table} if arp_table else {}

            # Fetch connected wireless clients
            connected_clients = get_connected_devices(base_url, session_id, interface_frequencies)

            # Similar logic for data aggregation as in the original code

    logger.info(f"Collected router data: {json.dumps(response_data, indent=2)}")
    return response_data

# Main loop
if __name__ == "__main__":
    while True:
        get_router_data()
        time.sleep(3600)  # Run every hour
