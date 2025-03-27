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
    message += "```
    Date    | wallet_3da3 | wallet_667 | wallet_825b | Sum        \n"
    message += "------------------------------------------------\n"
    for record in records:
        date, w3da3, w667, w825b, total = record
        message += f"{date} | {format_trillions(w3da3)} | {format_trillions(w667)} | {format_trillions(w825b)} | {format_trillions(total)}\n"
    message += "```"
    await ctx.send(message)

# 🟢 Run the Bot
bot.run(TOKEN)
