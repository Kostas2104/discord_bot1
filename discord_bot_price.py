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
- `!exchanges`
  *Fetches and compares the ask and bid prices for CAW/USDT on Gate.io and AscendEx.*

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
            return {"exchange": "Gate.io", "ask": f"{float(ask):.11f}" if ask else None, "bid": f"{float(bid):.11f}" if bid else None}
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
            return {"exchange": "AscendEx", "ask": f"{float(ask[0]):.11f}" if ask else None, "bid": f"{float(bid[0]):.11f}" if bid else None}
        else:
            return {"exchange": "AscendEx", "error": f"Could not retrieve ticker data for {symbol}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "AscendEx", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "AscendEx", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "AscendEx", "error": f"An unexpected error occurred: {e}"}

@bot.command()
async def exchanges(ctx):
    """Fetches and compares the ask and bid prices for CAW/USDT on Gate.io and AscendEx."""
    gateio_data = get_gateio_caw_data()
    ascendex_data = get_ascendex_caw_data()
    arbitrage_amount = 2000000000  # 2 billion CAW tokens

    message = "--- CAW/USDT Exchange Comparison ---\n"
    message += "---------------------------------------\n"

    # Gate.io Output
    message += "**Gate.io:**\n"
    if "error" in gateio_data:
        message += f"  Error: {gateio_data['error']}\n"
        gateio_buy_price = None
        gateio_sell_price = None
    else:
        gateio_sell_price = gateio_data['ask']
        gateio_buy_price = gateio_data['bid']
        message += f"  Selling Price (Ask): {gateio_sell_price}\n"
        message += f"  Buying Price (Bid): {gateio_buy_price}\n"
    message += "---------------------------------------\n"

    # AscendEx Output
    message += "**AscendEx:**\n"
    if "error" in ascendex_data:
        message += f"  Error: {ascendex_data['error']}\n"
        ascendex_buy_price = None
        ascendex_sell_price = None
    else:
        ascendex_sell_price = ascendex_data['ask']
        ascendex_buy_price = ascendex_data['bid']
        message += f"  Selling Price (Ask): {ascendex_sell_price}\n"
        message += f"  Buying Price (Bid): {ascendex_buy_price}\n"
    message += "---------------------------------------\n"

    # Potential Arbitrage Calculation
    message += "\n--- Potential Arbitrage Opportunity (for 2 Billion CAW) ---\n"

    if gateio_buy_price and ascendex_sell_price:
        gateio_buy_price_float = float(gateio_buy_price)
        ascendex_sell_price_float = float(ascendex_sell_price)
        if gateio_buy_price_float < ascendex_sell_price_float:
            cost_gateio = arbitrage_amount * gateio_buy_price_float
            revenue_ascendex = arbitrage_amount * ascendex_sell_price_float
            profit = revenue_ascendex - cost_gateio
            message += "Buy on Gate.io, sell on AscendEx:\n"
            message += f"  Buy Price on Gate.io: {gateio_buy_price}\n"
            message += f"  Sell Price on AscendEx: {ascendex_sell_price}\n"
            message += f"  Cost to buy: {cost_gateio:.8f} USDT\n"
            message += f"  Revenue from selling: {revenue_ascendex:.8f} USDT\n"
            message += f"  Potential Profit (without fees): {profit:.8f} USDT\n"
        else:
            message += "No direct arbitrage (Buy Gate.io < Sell AscendEx) at this moment.\n"

    if ascendex_buy_price and gateio_sell_price:
        ascendex_buy_price_float = float(ascendex_buy_price)
        gateio_sell_price_float = float(gateio_sell_price)
        if ascendex_buy_price_float < gateio_sell_price_float:
            cost_ascendex = arbitrage_amount * ascendex_buy_price_float
            revenue_gateio = arbitrage_amount * gateio_sell_price_float
            profit = revenue_gateio - cost_ascendex
            message += "\nBuy on AscendEx, sell on Gate.io:\n"
            message += f"  Buy Price on AscendEx: {ascendex_buy_price}\n"
            message += f"  Sell Price on Gate.io: {gateio_sell_price}\n"
            message += f"  Cost to buy: {cost_ascendex:.8f} USDT\n"
            message += f"  Revenue from selling: {revenue_gateio:.8f} USDT\n"
            message += f"  Potential Profit (without fees): {profit:.8f} USDT\n"
        else:
            message += "No direct arbitrage (Buy AscendEx < Sell Gate.io) at this moment.\n"

    if not gateio_buy_price or not ascendex_sell_price or not ascendex_buy_price or not gateio_sell_price:
        message += "Could not perform arbitrage calculation due to missing price data.\n"

    await ctx.send(message)

# 🟢 Run the Bot
bot.run(TOKEN)
