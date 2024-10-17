import requests
import urllib3
import json
import time
import platform
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, jsonify, request, abort
 
# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
app = Flask(__name__)
 
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
                app.logger.info(f"Logged in successfully. Session ID: {session_id}")
                return session_id, session_info
            else:
                app.logger.error("Failed to obtain session ID.")
                return None, None
        except requests.exceptions.RequestException as e:
            attempt += 1
            app.logger.warning(f"Login attempt {attempt} failed. Error: {e}")
            if attempt < retries:
                app.logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
 
    app.logger.error("Unable to login after multiple attempts.")
    return None, None
 
# Function to get wireless interfaces and their frequency bands
def get_wireless_interfaces(base_url, session_id):
    """Fetch the list of wireless interfaces and their frequencies using iwinfo service."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": [
            session_id,
            "iwinfo",
            "devices",
            {}
        ],
        "id": 1
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        result = data.get('result')
        if result and result[0] == 0:
            interfaces = result[1].get('devices', [])
            interface_frequencies = {}

            # Get frequency information for each interface
            for interface in interfaces:
                freq_payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": [
                        session_id,
                        "iwinfo",
                        "info",
                        {"device": interface}
                    ],
                    "id": 1
                }
                freq_response = requests.post(f"{base_url}/ubus", json=freq_payload, verify=False)
                freq_response.raise_for_status()
                freq_data = freq_response.json()
                freq_result = freq_data.get('result')
                if freq_result and freq_result[0] == 0:
                    info = freq_result[1]
                    frequency = info.get('frequency', 0)
                    if frequency < 3000:
                        band = '2.4ghz'
                    else:
                        band = '5ghz'
                    interface_frequencies[interface] = band
                    app.logger.info(f"Interface '{interface}' operates on {band} band.")
                else:
                    app.logger.error(f"Failed to get frequency info for interface '{interface}'.")
            app.logger.info(f"Wireless interfaces and their bands: {interface_frequencies}")
            return interface_frequencies
        else:
            app.logger.error("Failed to retrieve wireless interfaces.")
            return {}
    except requests.exceptions.RequestException as e:
        app.logger.error(f"An error occurred while fetching wireless interfaces: {e}")
        return {}
 
# Function to get connected devices
def get_connected_devices(base_url, session_id, interface_frequencies):
    """Fetch wireless clients connected to the router from specified wireless interfaces."""
    clients = {'2.4ghz': {}, '5ghz': {}}

    for interface, band in interface_frequencies.items():
        hostapd_interface = f"hostapd.{interface}"
        payload = {
            "method": "call",
            "params": [
                session_id,
                hostapd_interface,
                "get_clients",
                {}
            ],
            "jsonrpc": "2.0",
            "id": 1
        }
        try:
            response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
            response.raise_for_status()

            data = response.json()
            result = data.get('result')
            if result and result[0] == 0:
                interface_clients = result[1].get('clients', {})
                clients[band].update(interface_clients)
                app.logger.info(f"Retrieved {len(interface_clients)} client(s) from interface '{interface}'.")
            else:
                app.logger.error(f"Failed to retrieve wireless client information from '{hostapd_interface}'.")
        except requests.exceptions.RequestException as e:
            app.logger.error(f"An error occurred while fetching wireless client information from '{hostapd_interface}': {e}")

    app.logger.info(f"Connected clients: {clients}")
    return clients
 
# Function to get ARP table
def get_arp_table(base_url, session_id):
    """Fetch the ARP table to find IP to MAC mappings."""
    payload = {
        "method": "call",
        "params": [
            session_id,
            "network.interface.lan",
            "status",
            {}
        ],
        "jsonrpc": "2.0",
        "id": 1
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        response.raise_for_status()

        data = response.json()
        result = data.get('result')
        if result and result[0] == 0:
            arp_table = result[1].get('neighbors', [])
            app.logger.info(f"ARP table entries: {len(arp_table)}")
            return arp_table
        else:
            app.logger.error("Failed to retrieve ARP table.")
            return []
    except requests.exceptions.RequestException as e:
        app.logger.error(f"An error occurred while fetching ARP table: {e}")
        return []
 
# Function to check router status
def check_router_status(ip_address, retries=3, delay=2):
    """Check if the router is reachable by pinging its IP address."""
    for attempt in range(1, retries + 1):
        try:
            # Determine the parameter depending on the OS
            param = '-n' if platform.system().lower() == 'windows' else '-c'

            # Build the command
            command = ['ping', param, '1', ip_address]

            # Run the command and capture the output
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                app.logger.info(f"Ping successful on attempt {attempt}.")
                return 1  # Router is reachable
            else:
                app.logger.warning(f"Attempt {attempt}: Ping failed with output:\n{result.stdout}\nError:\n{result.stderr}")
                if attempt < retries:
                    app.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        except Exception as e:
            app.logger.error(f"An error occurred while checking router status: {e}")
            if attempt < retries:
                app.logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    app.logger.error("Router is not reachable after retries.")
    return 0  # Router is not reachable after retries
 
# Function to convert bytes to human-readable format (Optional)
def format_bytes(bytes_value):
    """Convert bytes to a human-readable format."""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < (1024 ** 2):
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < (1024 ** 3):
        return f"{bytes_value / (1024 ** 2):.2f} MB"
    else:
        return f"{bytes_value / (1024 ** 3):.2f} GB"
 
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
                app.logger.error("No wireless interfaces found. Exiting data collection.")
                return response_data

            # Fetch ARP table information
            arp_table = get_arp_table(base_url, session_id)
            arp_mapping = {entry['mac'].lower(): entry['ip'] for entry in arp_table} if arp_table else {}

            # Fetch connected wireless clients
            connected_clients = get_connected_devices(base_url, session_id, interface_frequencies)

            # Define main devices (lan and wan)
            main_interfaces = ['lan', 'wan']
            main_devices = []

            for iface in main_interfaces:
                payload = {
                    "method": "call",
                    "params": [
                        session_id,
                        f"network.interface.{iface}",
                        "status",
                        {}
                    ],
                    "jsonrpc": "2.0",
                    "id": 1
                }
                try:
                    response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
                    response.raise_for_status()

                    data = response.json()
                    result = data.get('result')
                    if result and result[0] == 0:
                        status = result[1]
                        device_name = status.get('device')
                        if device_name:
                            main_devices.append(device_name)
                            app.logger.info(f"Interface '{iface}' is associated with device '{device_name}'.")
                        else:
                            app.logger.error(f"No device associated with interface '{iface}'.")
                    else:
                        app.logger.error(f"Failed to retrieve status for interface '{iface}'.")
                except requests.exceptions.RequestException as e:
                    app.logger.error(f"An error occurred while fetching status for interface '{iface}': {e}")

            # Combine main devices with wireless devices
            devices_to_collect = main_devices + list(interface_frequencies.keys())

            if not devices_to_collect:
                app.logger.warning("No devices to collect stats from.")
            else:
                # Initialize device lists
                devices_2ghz = []
                devices_5ghz = []

                # Process devices on 2.4GHz band
                if connected_clients.get('2.4ghz'):
                    for i, (mac_address, client_info) in enumerate(connected_clients['2.4ghz'].items(), start=1):
                        # Record the connection time if it's a newly connected device
                        if mac_address not in connection_times:
                            connection_times[mac_address] = datetime.now()

                        # Calculate the duration since the device connected
                        connected_since = connection_times[mac_address]
                        duration = datetime.now() - connected_since
                        duration_minutes = duration.total_seconds() // 60
                        duration_hours = int(duration_minutes // 60)
                        duration_minutes = int(duration_minutes % 60)
                        formatted_duration = f"{duration_hours} hour(s) {duration_minutes} minute(s)" if duration_hours > 0 else f"{duration_minutes} minute(s)"

                        # Get the device details
                        device_rx_packets = client_info.get('packets', {}).get('rx', 0)
                        device_tx_packets = client_info.get('packets', {}).get('tx', 0)
                        signal_strength = client_info.get('signal', 0)

                        # Check ARP table for IP address
                        ip_address = arp_mapping.get(mac_address.lower(), 'N/A')

                        # Add device information to the list
                        devices_2ghz.append({
                            "device_id": i,
                            "mac_address": mac_address,
                            "ip_address": ip_address,
                            "rx_packets": device_rx_packets,  # Packet counts
                            "tx_packets": device_tx_packets,  # Packet counts
                            "signal_strength_dbm": signal_strength,
                            "connection_duration": formatted_duration
                        })

                # Process devices on 5GHz band
                if connected_clients.get('5ghz'):
                    for i, (mac_address, client_info) in enumerate(connected_clients['5ghz'].items(), start=1):
                        # Record the connection time if it's a newly connected device
                        if mac_address not in connection_times:
                            connection_times[mac_address] = datetime.now()

                        # Calculate the duration since the device connected
                        connected_since = connection_times[mac_address]
                        duration = datetime.now() - connected_since
                        duration_minutes = duration.total_seconds() // 60
                        duration_hours = int(duration_minutes // 60)
                        duration_minutes = int(duration_minutes % 60)
                        formatted_duration = f"{duration_hours} hour(s) {duration_minutes} minute(s)" if duration_hours > 0 else f"{duration_minutes} minute(s)"

                        # Get the device details
                        device_rx_packets = client_info.get('packets', {}).get('rx', 0)
                        device_tx_packets = client_info.get('packets', {}).get('tx', 0)
                        signal_strength = client_info.get('signal', 0)

                        # Check ARP table for IP address
                        ip_address = arp_mapping.get(mac_address.lower(), 'N/A')

                        # Add device information to the list
                        devices_5ghz.append({
                            "device_id": i,
                            "mac_address": mac_address,
                            "ip_address": ip_address,
                            "rx_packets": device_rx_packets,  # Packet counts
                            "tx_packets": device_tx_packets,  # Packet counts
                            "signal_strength_dbm": signal_strength,
                            "connection_duration": formatted_duration
                        })

                # Update response data with device lists
                response_data["devices_2_4ghz"] = devices_2ghz
                response_data["devices_5ghz"] = devices_5ghz

                # Update device counts
                response_data["total_devices_2.4ghz"] = len(devices_2ghz)
                response_data["total_devices_5ghz"] = len(devices_5ghz)
                response_data["total_devices"] = response_data["total_devices_2.4ghz"] + response_data["total_devices_5ghz"]

                # Aggregate packet counts
                total_rx_packets = sum(device.get('rx_packets', 0) for device in devices_2ghz + devices_5ghz)
                total_tx_packets = sum(device.get('tx_packets', 0) for device in devices_2ghz + devices_5ghz)

                # Update response data with total packet counts
                response_data["total_rx_packets"] = total_rx_packets
                response_data["total_tx_packets"] = total_tx_packets

                app.logger.info(f"Total RX Packets: {response_data['total_rx_packets']}")
                app.logger.info(f"Total TX Packets: {response_data['total_tx_packets']}")

    return response_data
 
# Route to serve the JSON data at versioned URL
@app.route('/api/v1/devices', methods=['GET'])
def get_devices():
    """
    Retrieve a summary of all connected devices categorized by their wireless frequency bands.
    
    Returns:
        JSON: A JSON object containing router status, total devices, device counts per band, 
              total received and transmitted packets, and detailed information for each device.
    """
    data = get_router_data()
    return jsonify(data), 200
 
# Error Handlers for Improved API Responses
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": {"code": 400, "message": "Bad Request"}}), 400
 
@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": {"code": 401, "message": "Unauthorized"}}), 401
 
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": {"code": 404, "message": "Resource Not Found"}}), 404
 
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": {"code": 500, "message": "Internal Server Error"}}), 500
 
# Run the application
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)