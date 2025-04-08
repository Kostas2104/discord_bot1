import discord
import requests
import os
import psycopg2
from discord.ext import commands
from get_balances import get_caw_balances
from datetime import datetime

TOKEN = os.getenv("TOKEN")  # Discord Bot Token
CMC_API_KEY = os.getenv("CMC_API_KEY")  # CoinMarketCap API Key
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL Database URL
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to PostgreSQL
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Format numbers for display with commas
def format_large_number(value):
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T".replace(",", "")  # Trillions
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B".replace(",", "")  # Billions
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M".replace(",", "")  # Millions
    else:
        return f"{value:,.2f}"  # Numbers under a million with commas

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# 📌 Help Command
@bot.command()
async def helpme(ctx):
    help_message = """
**📌 Available Commands:**

**💰 Crypto Price & Market Cap**
- `!price <symbol>`
  *Get the current price of a cryptocurrency.*
  **Example:** `!price BTC` → Shows Bitcoin's price.

- `!mc <symbol>`
  *Get the market cap of a cryptocurrency.*
  **Example:** `!mc ETH` → Shows Ethereum's market cap.

**📂 CDC Wallet Balances**
- `!cdc`
  *Fetches and displays the latest CDC wallet balances and saves them to the database.*
  **Example:** `!cdc` → Shows balances and records them in the database.

- `!compare_cdc`
  *Compares the latest CDC wallet balances with the previous record.*

- `!compare_cdc_<number>`
  *Compares the latest CDC wallet balances with a specified number of entries back.*

- `!compare_cdc_last10`
  *Displays the last 10 records in a tabular format.*

**💱 Exchange Data**
- `!ex`
  *Fetches and compares the ask and bid prices for CAW/USDT on Gate.io, AscendEx, and Crypto.com.*

**ℹ️ Need Help?**
Use `!helpme` anytime to see this list again.
"""
    await ctx.send(help_message)

# 📌 CDC Wallet Titles (excluding Burn)
CDC_WALLET_TITLES = ["wallet_3da3", "wallet_667", "wallet_825b"]
BURN_WALLET_TITLE = "Burn"

# 📌 Format number to Trillions (T)
def format_trillions(value):
    return f"{value / 1_000_000_000_000:.2f} T"

# 📌 Format number to Trillions (T)
def format_billions(value):
    return f"{value / 1_000_000_000:.2f} B"

# 📌 Get Crypto Balances for CDC Wallets and Save to Database
@bot.command()
async def cdc(ctx):
    cdc_balances, burn_balance, cdc_total, cdc_percentage = get_caw_balances()

    if cdc_balances:
        message = "**📊 CDC Wallet Balances:**\n"

        # Print individual CDC balances
        for title, balance in zip(CDC_WALLET_TITLES, cdc_balances):
            message += f"- **{title}:** {format_trillions(balance)} CAW\n"

        # Print CDC total and percentage
        message += f"\n**Total CDC Holdings: {format_trillions(cdc_total)} CAW**"
        message += f"\n**Percentage of Total Supply: {cdc_percentage:.4f}%**"

        # Show Burn wallet separately
        message += f"\n\n🔥 **{BURN_WALLET_TITLE}: {format_trillions(burn_balance)} CAW** 🔥"

        # Save data to PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.now()
        cur.execute("""
            INSERT INTO caw_cdc (date, wallet_3da3, wallet_667, wallet_825b, sum)
            VALUES (%s, %s, %s, %s, %s)
        """, (now.date(), cdc_balances[0], cdc_balances[1], cdc_balances[2], cdc_total))
        conn.commit()
        cur.close()
        conn.close()

        await ctx.send(message)
    else:
        await ctx.send("❌ Unable to fetch balances!")

# 📊 Compare CDC Wallets
@bot.command()
async def compare_cdc_last10(ctx):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, wallet_3da3, wallet_667, wallet_825b, sum FROM caw_cdc
        ORDER BY date DESC
        LIMIT 10
    """)

    records = cur.fetchall()
    cur.close()
    conn.close()

    message = "**📊 Last 10 CDC Wallet Records:**\n"
    message += "```\nDate        | 3DA3          | 667F          | 825B          | Sum           \n"
    message += "-----------------------------------------------------------\n"
    for record in records:
        date, w3da3, w667f, w825b, total = record
        message += f"{date} | {format_trillions(w3da3):<13} | {format_trillions(w667f):<13} | {format_trillions(w825b):<13} | {format_trillions(total):<13}\n"
    message += "```"

    await ctx.send(message)

def get_gateio_caw_data():
    """Retrieves the ask and bid price of CAW/USDT from Gate.io with 11 decimal places."""
    base_url = "https://api.gateio.ws/api/v4"
    currency_pair = "CAW_USDT"

    try:
        ticker_endpoint = f"{base_url}/spot/tickers?currency_pair={currency_pair}"
        response = requests.get(ticker_endpoint)
        response.raise_for_status()
        data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            ticker_info = data[0]
            ask = ticker_info.get('lowest_ask')
            bid = ticker_info.get('highest_bid')
            return {"exchange": "Gate.io", "buy_price": f"{float(bid):.11f}" if bid else None, "sell_price": f"{float(ask):.11f}" if ask else None}
        else:
            return {"exchange": "Gate.io", "error": f"Could not retrieve ticker data for {currency_pair}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "Gate.io", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "Gate.io", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "Gate.io", "error": f"An unexpected error occurred: {e}"}

def get_ascendex_caw_data():
    """Retrieves the ask and bid price of CAW/USDT from AscendEx with 11 decimal places."""
    base_url = "https://ascendex.com/api/pro/v1"
    symbol = "$CAW/USDT"  # Corrected symbol

    try:
        ticker_endpoint = f"{base_url}/spot/ticker?symbol={symbol}"
        response = requests.get(ticker_endpoint)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and isinstance(data['data'], dict):
            ticker_info = data['data']
            ask = ticker_info.get('ask')
            bid = ticker_info.get('bid')
            return {"exchange": "AscendEx", "buy_price": f"{float(bid[0]):.11f}" if bid else None, "sell_price": f"{float(ask[0]):.11f}" if ask else None}
        else:
            return {"exchange": "AscendEx", "error": f"Could not retrieve ticker data for {symbol}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "AscendEx", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "AscendEx", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "AscendEx", "error": f"An unexpected error occurred: {e}"}

def get_crypto_com_caw_data():
    """Retrieves the ask and bid price of CAW_USDT from Crypto.com with 11 decimal places."""
    base_url = "https://api.crypto.com/v2"
    instrument_name = "CAW_USDT"

    try:
        ticker_endpoint = f"{base_url}/public/get-ticker?instrument_name={instrument_name}"
        response = requests.get(ticker_endpoint)
        response.raise_for_status()
        data = response.json()

        if data and data.get('result') and data['result'].get('data') and len(data['result']['data']) > 0:
            ticker_info = data['result']['data'][0]
            ask = ticker_info.get('a')
            bid = ticker_info.get('b')
            return {"exchange": "Crypto.com", "buy_price": f"{float(bid):.11f}" if bid else None, "sell_price": f"{float(ask):.11f}" if ask else None}
        else:
            return {"exchange": "Crypto.com", "error": f"Could not retrieve ticker data for {instrument_name}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "Crypto.com", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "Crypto.com", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "Crypto.com", "error": f"An unexpected error occurred: {e}"}

@bot.command()
async def ex(ctx):
    """Fetches and compares the ask and bid prices for CAW/USDT on Gate.io, AscendEx, and Crypto.com."""
    gateio_data = get_gateio_caw_data()
    ascendex_data = get_ascendex_caw_data()
    crypto_com_data = get_crypto_com_caw_data()
    arbitrage_amount = 2000000000  # 2 billion CAW tokens

    message = "--- CAW/USDT Exchange Comparison ---\n"
    message += "---------------------------------------\n"
    has_data = False  # Flag to check if any data was successfully fetched

    # Gate.io Output
    message += "**Gate.io:**\n"
    if "error" in gateio_data:
        message += f"  Error: {gateio_data['error']}\n"
        gateio_sell_price = None
        gateio_buy_price = None
    else:
        gateio_buy_price = gateio_data['buy_price']
        gateio_sell_price = gateio_data['sell_price']
        message += f"  Selling Price (Ask): {gateio_sell_price}\n"
        message += f"  Buying Price (Bid): {gateio_buy_price}\n"
        has_data = True
    message += "---------------------------------------\n"

    # AscendEx Output
    message += "**AscendEx:**\n"
    if "error" in ascendex_data:
        message += f"  Error: {ascendex_data['error']}\n"
        ascendex_sell_price = None
        ascendex_buy_price = None
    else:
        ascendex_buy_price = ascendex_data['buy_price']
        ascendex_sell_price = ascendex_data['sell_price']
        message += f"  Selling Price (Ask): {ascendex_sell_price}\n"
        message += f"  Buying Price (Bid): {ascendex_buy_price}\n"
        has_data = True
    message += "---------------------------------------\n"

    # Crypto.com Output
    message += "**Crypto.com:**\n"
    if "error" in crypto_com_data:
        message += f"  Error: {crypto_com_data['error']}\n"
        crypto_com_sell_price = None
        crypto_com_buy_price = None
    else:
        crypto_com_buy_price = crypto_com_data['buy_price']
        crypto_com_sell_price = crypto_com_data['sell_price']
        message += f"  Selling Price (Ask): {crypto_com_sell_price}\n"
        message += f"  Buying Price (Bid): {crypto_com_buy_price}\n"
        has_data = True
    message += "---------------------------------------\n"

    # Comparison and Potential Arbitrage
    message += "\n--- Potential Arbitrage Opportunity (for 2 Billion CAW) ---\n"

    def check_arbitrage(buy_exchange, sell_price, sell_exchange, buy_price):
        nonlocal message
        if sell_price and buy_price:
            try:
                sell_price_float = float(sell_price)
                buy_price_float = float(buy_price)
                if sell_price_float < buy_price_float:
                    cost = arbitrage_amount * sell_price_float
                    revenue = arbitrage_amount * buy_price_float
                    profit = revenue - cost
                    message += f"Buy on {buy_exchange}, sell on {sell_exchange}:\n"
                    message += f"  Buy Price on {buy_exchange}: {sell_price}\n"
                    message += f"  Sell Price on {sell_exchange}: {buy_price}\n"
                    message += f"  Cost to buy {format_billions(arbitrage_amount)} CAW: {cost:.2f} USDT\n"
                    message += f"  Revenue from selling {format_billions(arbitrage_amount)} CAW: {revenue:.2f} USDT\n"
                    message += f"  Potential Profit (without fees): {profit:.2f} USDT\n"
                    message += "---------------------------------------\n"
                else:
                    message += f"No direct arbitrage (Buy from {buy_exchange} -> Sell to {sell_exchange}) at this moment.\n"
                    message += "---------------------------------------\n"
            except ValueError:
                message += f"Error converting price to float for arbitrage check between {buy_exchange} and {sell_exchange}.\n"
        else:
            message += f"Could not check arbitrage between {buy_exchange} and {sell_exchange} due to missing price data.\n"

    message += "\n--- Arbitrage Opportunities ---\n"
    check_arbitrage("Gate.io", gateio_sell_price, "AscendEx", ascendex_buy_price)
    check_arbitrage("Gate.io", gateio_sell_price, "Crypto.com", crypto_com_buy_price)
    check_arbitrage("AscendEx", ascendex_sell_price, "Gate.io", gateio_buy_price)
    check_arbitrage("AscendEx", ascendex_sell_price, "Crypto.com", crypto_com_buy_price)
    check_arbitrage("Crypto.com", crypto_com_sell_price, "Gate.io", gateio_buy_price)
    check_arbitrage("Crypto.com", crypto_com_sell_price, "AscendEx", ascendex_buy_price)

    if has_data:
        await ctx.send(message)
    else:
        await ctx.send("❌ Failed to fetch exchange data from all sources.")

# 🟢 Run the Bot
bot.run(TOKEN)
