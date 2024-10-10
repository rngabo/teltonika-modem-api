import requests
import urllib3
import json
import time
from datetime import datetime  # Make sure this line is added to correctly import datetime

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
            response = requests.post(f"{base_url}/ubus", json=payload, verify=False, timeout=10)  # Added timeout
            response.raise_for_status()
            
            data = response.json()
            result = data.get('result')
            if result and result[0] == 0:
                session_info = result[1]
                session_id = session_info.get('ubus_rpc_session')
                return session_id, session_info  # Return both session ID and session info
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

def get_connected_devices(base_url, session_id):
    """Fetch wireless clients connected to the router."""
    payload = {
        "method": "call",
        "params": [
            session_id,
            "hostapd.wlan0",
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
            clients = result[1].get('clients', {})
            return clients
        else:
            print("Failed to retrieve wireless client information.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching wireless client information: {e}")
        return None

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
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching ARP table: {e}")
        return None

def main():
    session_id, session_info = login(base_url, username, password)
    connection_times = {}  # Dictionary to track connection times of devices

    if session_id:
        while True:  # Continuous loop to keep checking the device status
            # Fetch ARP table information
            arp_table = get_arp_table(base_url, session_id)
            arp_mapping = {entry['mac']: entry['ip'] for entry in arp_table} if arp_table else {}

            # Fetch connected wireless clients
            connected_clients = get_connected_devices(base_url, session_id)

            response_data = {"connected_devices": []}

            if connected_clients:
                for i, (mac_address, client_info) in enumerate(connected_clients.items(), start=1):
                    # Record the connection time if it's a newly connected device
                    if mac_address not in connection_times:
                        connection_times[mac_address] = datetime.now()

                    # Calculate the duration since the device connected
                    connected_since = connection_times[mac_address]
                    duration = datetime.now() - connected_since  # Corrected this line
                    duration_minutes = duration.total_seconds() // 60
                    duration_hours = int(duration_minutes // 60)
                    duration_minutes = int(duration_minutes % 60)
                    formatted_duration = f"{duration_hours} hour(s) {duration_minutes} minute(s)" if duration_hours > 0 else f"{duration_minutes} minute(s)"

                    # Get the device details
                    rx_packets = client_info.get('packets', {}).get('rx', 'N/A')
                    tx_packets = client_info.get('packets', {}).get('tx', 'N/A')
                    rx_bytes = client_info.get('bytes', {}).get('rx', 0)
                    tx_bytes = client_info.get('bytes', {}).get('tx', 0)
                    signal_strength = client_info.get('signal', 'N/A')

                    # Check ARP table for IP address
                    ip_address = arp_mapping.get(mac_address, 'N/A')

                    # Add device information to the response data
                    response_data["connected_devices"].append({
                        "device_number": i,
                        "mac_address": mac_address,
                        "ip_address": ip_address,
                        "packets": {"rx": rx_packets, "tx": tx_packets},
                        "signal_strength": signal_strength,
                        "duration": formatted_duration,
                        "bytes": {"downloaded": rx_bytes, "uploaded": tx_bytes}
                    })

                # Add overall usage to the response data
                total_devices = len(connected_clients)
                total_rx_bytes = sum(client_info.get('bytes', {}).get('rx', 0) for client_info in connected_clients.values())
                total_tx_bytes = sum(client_info.get('bytes', {}).get('tx', 0) for client_info in connected_clients.values())
                response_data["overall_usage"] = {
                    "total_devices": total_devices,
                    "total_rx_bytes": total_rx_bytes,
                    "total_tx_bytes": total_tx_bytes
                }

                # Print the response as a JSON object
                print(json.dumps(response_data, indent=4))

            else:
                print(json.dumps({"message": "No connected devices found."}, indent=4))

            # Wait for 10 seconds before checking again to avoid flooding the network
            time.sleep(10)
    else:
        print(json.dumps({"error": "Unable to retrieve session information due to login failure."}, indent=4))


if __name__ == "__main__":
    main()
