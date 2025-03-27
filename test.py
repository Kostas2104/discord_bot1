import requests
import os 
from config import CAW_CONTRACT_ADDRESS, CAW_ADDRESSES

API_KEY_CRONOSCAN = os.getenv("API_KEY_CRONOSCAN")  # CoinMarketCap API Key

DECIMALS = 18
TOTAL_SUPPLY = 777_777_777_777_777  # 777.777 Trillion CAW

# Define address titles (last one is Burn)
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
    balances = [get_token_balance(addr) for addr in CAW_ADDRESSES]

    # Separate Burn balance
    burn_balance = balances[-1]  # Last address (Burn)
    cdc_balances = balances[:-1]  # All except Burn

    # Sum only CDC balances (exclude Burn)
    cdc_total = sum(cdc_balances)

    # Calculate percentage from total supply
    cdc_percentage = (cdc_total / TOTAL_SUPPLY) * 100

    return cdc_balances, burn_balance, cdc_total, cdc_percentage
