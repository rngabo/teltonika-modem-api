import requests
import urllib3
import json
import time

# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Device credentials
base_url = "https://10.51.35.151"  # Adjust to your router's IP address
username = "admin"
password = "Salvi.2024"

def login(base_url, username, password):
    """Login to the router and obtain a session ID."""
    credentials = {"username": username, "password": password}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            "00000000000000000000000000000000",
            "session",
            "login",
            credentials
        ]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        result = data.get('result')
        if result and result[0] == 0:
            session_id = result[1].get('ubus_rpc_session')
            print(f"Session ID obtained: {session_id}")
            return session_id
        else:
            print("Failed to obtain session ID.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during login: {e}")
        return None

def get_connected_devices(base_url, session_id, interface="wlan0"):
    """Retrieve the list of connected devices."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            session_id,
            "iwinfo",
            "assoclist",
            {"device": interface}
        ]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        data = response.json()
        devices_info = []
        if data.get('result') and data['result'][0] == 0:
            devices = data['result'][1].get('results', [])
            num_devices = len(devices)
            print(f"Number of Connected Devices on {interface}: {num_devices}")
            for device in devices:
                mac = device.get('mac')
                signal = device.get('signal')
                print(f"Device MAC: {mac}, Signal Strength: {signal} dBm")
                devices_info.append({'mac': mac, 'signal': signal})
        else:
            print("Failed to retrieve connected devices.")
        return devices_info
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving connected devices: {e}")
        return []

def get_modem_info(base_url, session_id):
    """Retrieve modem information."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            session_id,
            "modem.manager",
            "get_modems",
            {}
        ]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        data = response.json()
        if data.get('result') and data['result'][0] == 0:
            modems = data['result'][1].get('modems', [])
            for modem in modems:
                print("\nModem Information:")
                # Extract desired fields
                print(f"Modem ID: {modem.get('id', 'N/A')}")
                print(f"APN: {modem.get('apn', 'N/A')}")
                print(f"SIM Slot: {modem.get('sim_id', 'N/A')}")
                print(f"IP Address: {modem.get('ipaddr', 'N/A')}")
                print(f"RX Bytes: {modem.get('rx_bytes', 0)}")
                print(f"TX Bytes: {modem.get('tx_bytes', 0)}")
        else:
            print("Failed to retrieve modem information.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving modem information: {e}")

def get_modem_network_info(base_url, session_id, modem_id=0):
    """Retrieve modem network information."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            session_id,
            "modem.network",
            "status",
            {"modem": modem_id}
        ]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        data = response.json()
        if data.get('result') and data['result'][0] == 0:
            network_info = data['result'][1]
            print("\nModem Network Information:")
            # Extract desired fields
            print(f"APN: {network_info.get('apn', 'N/A')}")
            print(f"IP Address: {network_info.get('ipaddr', 'N/A')}")
            print(f"Operator: {network_info.get('operator', 'N/A')}")
            print(f"SIM Slot: {network_info.get('sim_id', 'N/A')}")
        else:
            print("Failed to retrieve modem network information.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving modem network information: {e}")

def get_modem_signal_info(base_url, session_id, modem_id=0):
    """Retrieve modem signal information."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            session_id,
            "modem.signal",
            "status",
            {"modem": modem_id}
        ]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        data = response.json()
        if data.get('result') and data['result'][0] == 0:
            signal_info = data['result'][1]
            print("\nModem Signal Information:")
            # Extract desired fields
            print(f"Signal Strength (RSSI): {signal_info.get('rssi', 'N/A')} dBm")
            print(f"Signal Quality (RSRQ): {signal_info.get('rsrq', 'N/A')} dB")
            print(f"Signal-to-Noise Ratio (SNR): {signal_info.get('snr', 'N/A')} dB")
            print(f"Reference Signal Received Power (RSRP): {signal_info.get('rsrp', 'N/A')} dBm")
        else:
            print("Failed to retrieve modem signal information.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving modem signal information: {e}")
        
def list_ubus_services(base_url, session_id):
    """List all available UBUS services and methods."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list",
        "params": [session_id, "*"]
    }
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        print("Available UBUS Services and Methods:")
        result = data.get('result')
        if result and result[0] == 0:
            services = result[1]
            for service, methods in services.items():
                print(f"Service: {service}")
                for method_name in methods.keys():
                    print(f"  Method: {method_name}")
        else:
            print("Failed to list UBUS services.")
            print("Response Data:")
            print(json.dumps(data, indent=4))
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while listing UBUS services: {e}")


def get_mobile_status(base_url, session_id):
    """Retrieve mobile interface status."""
    # First, get the interface status
    payload_iface = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": [
            session_id,
            "network.interface",
            "status",
            {"interface": "mob1s2a1"}  # Adjust the interface name if necessary
        ]
    }
    try:
        response_iface = requests.post(f"{base_url}/ubus", json=payload_iface, verify=False)
        data_iface = response_iface.json()
        if data_iface.get('result') and data_iface['result'][0] == 0:
            iface_data = data_iface['result'][1]
            print("\nMobile Interface Status:")
            print(json.dumps(iface_data, indent=4))
            # Use l3_device as interface name
            iface_name = iface_data.get('l3_device', 'N/A')
            print(f"Interface: {iface_name}")
            print(f"Status: {'Up' if iface_data.get('up') else 'Down'}")
            uptime_seconds = iface_data.get('uptime', 0)
            uptime_str = time.strftime('%Hh %Mm %Ss', time.gmtime(uptime_seconds))
            print(f"Uptime: {uptime_str}")

            # Now, get the device status to retrieve IP and statistics
            if iface_name != 'N/A':
                payload_dev = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "call",
                    "params": [
                        session_id,
                        "network.device",
                        "status",
                        {"name": iface_name}
                    ]
                }
                response_dev = requests.post(f"{base_url}/ubus", json=payload_dev, verify=False)
                data_dev = response_dev.json()
                print("\nDevice Status Response:")
                print(json.dumps(data_dev, indent=4))
                if data_dev.get('result') and data_dev['result'][0] == 0:
                    dev_data = data_dev['result'][1]
                    # Attempt to get IP address from here
                    # Get statistics
                    stats = dev_data.get('statistics', {})
                    rx_bytes = int(stats.get('rx_bytes', 0))
                    tx_bytes = int(stats.get('tx_bytes', 0))
                    tx_mb = tx_bytes / (1024 * 1024)
                    rx_mb = rx_bytes / (1024 * 1024)
                    print(f"TX: {tx_mb:.2f} MB")
                    print(f"RX: {rx_mb:.2f} MB")
                else:
                    print("Failed to retrieve device status.")
                    print("Device Response Data:")
                    print(json.dumps(data_dev, indent=4))
            else:
                print("Interface name is not available.")
        else:
            print("Failed to retrieve mobile interface status.")
            print("Response Data:")
            print(json.dumps(data_iface, indent=4))
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving mobile interface status: {e}")



def main():
    session_id = login(base_url, username, password)
    if session_id:
        devices_interface = "wlan0"  # Adjust to your wireless interface
        previous_devices = set()
        try:
            while True:
                print("\n--- Monitoring Network ---")
                # Get connected devices
                devices_info = get_connected_devices(base_url, session_id, interface=devices_interface)
                current_devices = set(device['mac'] for device in devices_info)

                # Check for new devices
                new_devices = current_devices - previous_devices
                if new_devices:
                    print("New device(s) connected:")
                    for mac in new_devices:
                        print(f" - {mac}")
                else:
                    print("No new devices connected.")
                previous_devices = current_devices

                # Get mobile interface status
                get_mobile_status(base_url, session_id)

                # Wait before next iteration
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print("Unable to start monitoring due to login failure.")

if __name__ == "__main__":
    main()