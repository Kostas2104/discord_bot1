import requests
from config import API_KEY_CRONOSCAN, CAW_CONTRACT_ADDRESS, CAW_ADDRESSES

DECIMALS = 18

# Define address titles
ADDRESS_TITLES = [
    "3DA3",
    "677F",
    "825B",
    "Burn"
]

def get_token_balance(address):
    api_url = f"https://api.cronoscan.com/api?module=account&action=tokenbalance&contractaddress={CAW_CONTRACT_ADDRESS}&address={address}&tag=latest&apikey={API_KEY_CRONOSCAN}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1":
            return int(data["result"]) / 10**DECIMALS
        else:
            print(f"Error fetching balance for {address}: {data['message']}")
            return 0  # Return 0 to avoid sum errors
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return 0  # Return 0 to handle errors smoothly

def get_caw_balances():
    return [get_token_balance(addr) for addr in CAW_ADDRESSES]  # Return list of balances
