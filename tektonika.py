import requests
import urllib3
import json
import time

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


def get_traffic_statistics(base_url, session_id):
    """Fetch RX and TX traffic statistics for network interfaces."""
    payload = {
        "method": "call",
        "params": [
            session_id,
            "network.device",
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
            device_data = result[1]
            return device_data
        else:
            print("Failed to retrieve traffic statistics.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching traffic statistics: {e}")
        return None

def get_connected_devices(base_url, session_id):
    """Attempt to fetch the list of connected devices using a different method."""
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
        
        # Log the full response for debugging purposes
        print("Connected Devices Response (Alternative Method):", response.json())
        
        data = response.json()
        result = data.get('result')
        if result and result[0] == 0:
            clients = result[1].get('clients', {})
            return clients  # Return the dictionary of connected clients
        else:
            print("Failed to retrieve connected devices using the alternative method.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching connected devices: {e}")
        return None

def main():
    session_id, session_info = login(base_url, username, password)
    if session_id:
        while True:
            # Fetch RX and TX statistics for network interfaces
            device_data = get_traffic_statistics(base_url, session_id)
            if device_data:
                print("Network Traffic Statistics:")
                for device, details in device_data.items():
                    rx_bytes = details.get('statistics', {}).get('rx_bytes', 'N/A')
                    tx_bytes = details.get('statistics', {}).get('tx_bytes', 'N/A')
                    print(f'Device: {device}')
                    print(f'  RX bytes (Downloaded): {rx_bytes}')
                    print(f'  TX bytes (Uploaded): {tx_bytes}')
                    print('---')
            else:
                print("No traffic statistics found.")

            # Fetch the number of connected devices
            connected_clients = get_connected_devices(base_url, session_id)
            if connected_clients is not None:
                print(f"Connected devices: {len(connected_clients)}")
                for mac_address, client_info in connected_clients.items():
                    rx_bytes = client_info.get('bytes', {}).get('rx', 'N/A')
                    tx_bytes = client_info.get('bytes', {}).get('tx', 'N/A')
                    signal_strength = client_info.get('signal', 'N/A')
                    print(f"Device MAC Address: {mac_address}")
                    print(f"  RX bytes (Downloaded): {rx_bytes}")
                    print(f"  TX bytes (Uploaded): {tx_bytes}")
                    print(f"  Signal Strength: {signal_strength} dBm")
                    print('---')
            else:
                print("No connected devices found.")
            
            # Wait for 5 seconds before fetching data again
            time.sleep(5)
    else:
        print("Unable to retrieve session information due to login failure.")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
