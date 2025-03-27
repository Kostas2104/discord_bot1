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

**ℹ️ Need Help?**  
Use `!helpme` anytime to see this list again.  
"""
    await ctx.send(help_message)

# 📌 CDC Wallet Titles (excluding Burn)
CDC_WALLET_TITLES = ["3DA3", "677F", "825B"]
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
            INSERT INTO caw_cdc ("3da3", "667F", "825b", sum, date, time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (cdc_balances[0], cdc_balances[1], cdc_balances[2], cdc_total, now.date(), now.time()))
        conn.commit()
        cur.close()
        conn.close()

        await ctx.send(message)
    else:
        await ctx.send("❌ Unable to fetch balances!")

# 💰 Get Crypto Price
@bot.command()
async def price(ctx, symbol: str):
    coin_data = get_coin_data(symbol.upper())

    if coin_data:
        price = coin_data["quote"]["USD"]["price"]
        if price >= 0.1:
            price_str = f"{price:,.2f}"  # Format with commas
        elif price >= 0.001:
            price_str = f"{price:,.4f}"  # Format with commas
        elif price >= 0.0000001:
            price_str = f"{price:,.8f}"  # Format with commas
        else:
            price_str = f"{price:,.11f}"  # Format with commas

        await ctx.send(f'The current price of {symbol.upper()} is **${price_str} USD**')
    else:
        await ctx.send("Invalid cryptocurrency symbol or data unavailable.")

# 📊 Get Market Cap
@bot.command()
async def mc(ctx, symbol: str):
    coin_data = get_coin_data(symbol.upper())

    if coin_data:
        market_cap = coin_data["quote"]["USD"]["market_cap"]
        formatted_mc = format_large_number(market_cap)
        await ctx.send(f"The market cap of {symbol.upper()} is **${formatted_mc} USD**")
    else:
        await ctx.send("Invalid cryptocurrency symbol or data unavailable.")

# 🟢 Run the Bot
bot.run(TOKEN)
