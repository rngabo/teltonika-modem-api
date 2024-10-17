import requests
import urllib3
import json
import time
import platform
import subprocess
from datetime import datetime
from urllib.parse import urlparse

# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Device credentials
base_url = "https://105.178.106.81"  # Adjust to your router's IP address
username = "admin"
password = "Salvi.2024"

def login(base_url, username, password, retries=3, delay=5):
    """Login to the router and obtain the full session information with retry capability."""
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
                return session_id, session_info
            else:
                print("Failed to obtain session ID.")
                return None, None
        except requests.exceptions.RequestException as e:
            attempt += 1
            print(f"Login attempt {attempt} failed. Error: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    print("Unable to login after multiple attempts.")
    return None, None

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
                else:
                    print(f"Failed to get frequency info for interface {interface}.")
            print("Wireless interfaces and their bands:", interface_frequencies)
            return interface_frequencies
        else:
            print("Failed to retrieve wireless interfaces.")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching wireless interfaces: {e}")
        return {}

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
            else:
                print(f"Failed to retrieve wireless client information from {hostapd_interface}.")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching wireless client information from {hostapd_interface}: {e}")

    return clients

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
            return arp_table
        else:
            print("Failed to retrieve ARP table.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching ARP table: {e}")
        return []

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
                return 1  # Router is reachable
            else:
                print(f"Attempt {attempt}: Ping failed with output:\n{result.stdout}\nError:\n{result.stderr}")
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        except Exception as e:
            print(f"An error occurred while checking router status: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    return 0  # Router is not reachable after retries

def main():
    # Extract IP address from base_url
    parsed_url = urlparse(base_url)
    router_ip = parsed_url.hostname

    connection_times = {}  # Dictionary to track connection times of devices

    while True:  # Continuous loop to keep checking the device status
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] Checking router status...")
        # Check router status
        router_status = check_router_status(router_ip)

        response_data = {
            "router_status": router_status,
            "total_devices": 0,
            "total_devices_2.4ghz": 0,
            "total_devices_5ghz": 0,
            "total_rx_bytes": 0,
            "total_tx_bytes": 0,
            "device_2.4ghz": [],
            "device_5ghz": []
        }

        if router_status == 1:
            # Try to login
            session_id, session_info = login(base_url, username, password)
            if session_id:
                # Get wireless interfaces using iwinfo service
                interface_frequencies = get_wireless_interfaces(base_url, session_id)
                print("Available wireless interfaces:", interface_frequencies)

                if not interface_frequencies:
                    print("No wireless interfaces found. Will retry in 10 seconds.")
                    time.sleep(10)
                    continue  # Go back to the beginning of the loop

                # Fetch ARP table information
                arp_table = get_arp_table(base_url, session_id)
                arp_mapping = {entry['mac'].lower(): entry['ip'] for entry in arp_table} if arp_table else {}

                # Fetch connected wireless clients
                connected_clients = get_connected_devices(base_url, session_id, interface_frequencies)

                total_rx_bytes = 0
                total_tx_bytes = 0

                # Process devices on 2.4GHz band
                devices_2ghz = []
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
                        rx_packets = client_info.get('packets', {}).get('rx', 0)
                        tx_packets = client_info.get('packets', {}).get('tx', 0)
                        rx_bytes = client_info.get('bytes', {}).get('rx', 0)
                        tx_bytes = client_info.get('bytes', {}).get('tx', 0)
                        signal_strength = client_info.get('signal', 0)

                        total_rx_bytes += rx_bytes
                        total_tx_bytes += tx_bytes

                        # Check ARP table for IP address
                        ip_address = arp_mapping.get(mac_address.lower(), 'N/A')

                        # Add device information to the list
                        devices_2ghz.append({
                            "device": i,
                            "mac_address": mac_address,
                            "ip_address": ip_address,
                            "packets_rx_bytes": rx_bytes,
                            "packets_tx_bytes": tx_bytes,
                            "signal_strength": signal_strength,
                            "duration": formatted_duration
                        })

                # Process devices on 5GHz band
                devices_5ghz = []
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
                        rx_packets = client_info.get('packets', {}).get('rx', 0)
                        tx_packets = client_info.get('packets', {}).get('tx', 0)
                        rx_bytes = client_info.get('bytes', {}).get('rx', 0)
                        tx_bytes = client_info.get('bytes', {}).get('tx', 0)
                        signal_strength = client_info.get('signal', 0)

                        total_rx_bytes += rx_bytes
                        total_tx_bytes += tx_bytes

                        # Check ARP table for IP address
                        ip_address = arp_mapping.get(mac_address.lower(), 'N/A')

                        # Add device information to the list
                        devices_5ghz.append({
                            "device": i,
                            "mac_address": mac_address,
                            "ip_address": ip_address,
                            "packets_rx_bytes": rx_bytes,
                            "packets_tx_bytes": tx_bytes,
                            "signal_strength": signal_strength,
                            "duration": formatted_duration
                        })

                # Update response data
                response_data["total_devices_2.4ghz"] = len(devices_2ghz)
                response_data["total_devices_5ghz"] = len(devices_5ghz)
                response_data["total_devices"] = response_data["total_devices_2.4ghz"] + response_data["total_devices_5ghz"]
                response_data["total_rx_bytes"] = total_rx_bytes
                response_data["total_tx_bytes"] = total_tx_bytes
                response_data["device_2.4ghz"] = devices_2ghz
                response_data["device_5ghz"] = devices_5ghz
            else:
                # Unable to login
                print("Unable to login to the router.")
                time.sleep(10)
                continue  # Retry after delay
        else:
            # Router is not reachable
            print("Router is not reachable.")
            time.sleep(10)
            continue  # Retry after delay

        # Print the response as a JSON object
        print(f"[{current_time}] Response Data:\n{json.dumps(response_data, indent=4)}")

        # Wait for 10 seconds before checking again to avoid flooding the network
        time.sleep(10)

if __name__ == "__main__":
    main()
