import requests
import urllib3
import json

# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Device credentials
base_url = "http://10.51.35.151"  # Adjust to your router's IP address
username = "admin"
password = "Salvi.2024"

def login(base_url, username, password):
    """Login to the router and obtain the full session information."""
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
    try:
        response = requests.post(f"{base_url}/ubus", json=payload, verify=False)
        response.raise_for_status()
        # Print the full response text
        print("Response Text:")
        print(json.dumps(response.json(), indent=4))
        
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
        print(f"An error occurred during login: {e}")
        return None, None

def main():
    session_id, session_info = login(base_url, username, password)
    if session_id:
        # Session info has been printed in the login function
        # You can process session_info further if needed
        pass
    else:
        print("Unable to retrieve session information due to login failure.")

if __name__ == "__main__":
    main()
