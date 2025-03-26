import requests
from config import API_KEY_CRONOSCAN, CAW_CONTRACT_ADDRESS, CAW_ADDRESSES

DECIMALS = 18

# Define address titles
address_titles = {
    "0x25aA97464F38a1506a16160bbc03cfC6DD863da3": "3DA3",
    "0x069E536d2429172e402A8c0DDCE822FC60a3677f": "677F",
    "0x8995909DC0960FC9c75B6031D683124a4016825b": "825B",
    "0x000000000000000000000000000000000000dead": "Burn"
}

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
    balances = {address_titles[addr]: get_token_balance(addr) for addr in CAW_ADDRESSES}
    return balances

# Fetch balances
balances = get_caw_balances()

# Print balances with titles
print("CAW Balances:")
for title, balance in balances.items():
    print(f"{title}: {balance}")

# Print total sum
print(f"Total CAW: {sum(balances.values())}")
