import discord
import requests
import os
import psycopg2
from discord.ext import commands

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

# Format numbers for display
def format_large_number(value):
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    else:
        return f"{value:.2f}"

# Get coin data from CoinMarketCap
def get_coin_data(symbol):
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol, "convert": "USD"}
    response = requests.get(CMC_API_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        return data["data"].get(symbol.upper(), {})
    return {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# 📌 Help Command
@bot.command()
async def helpme(ctx):
    help_message = """
**💰 Crypto Commands**
- `!price <symbol>` → Get the current price of a cryptocurrency.
- `!mc <symbol>` → Get the market cap of a cryptocurrency.

**📂 Wallet Commands**
- `!new_wallet <symbol> <amount>` → Create a new wallet with initial amount.
- `!add_funds <wallet_id> <amount>` → Add funds to an existing wallet.
- `!wallets` → View all your wallets.
- `!wallet_value` → Check the value of your wallets in USD.
"""
    await ctx.send(help_message)

# 💰 Get Crypto Price
@bot.command()
async def price(ctx, symbol: str):
    coin_data = get_coin_data(symbol.upper())

    if coin_data:
        price = coin_data["quote"]["USD"]["price"]
        if price >= 0.1:
            price_str = f"{price:.2f}"
        elif price >= 0.001:
            price_str = f"{price:.4f}"
        elif price >= 0.0000001:
            price_str = f"{price:.8f}"
        else:
            price_str = f"{price:.11f}"

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

# 📂 Create a New Wallet
@bot.command()
async def new_wallet(ctx, symbol: str, amount: float):
    user_id = ctx.author.id
    symbol = symbol.upper()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wallets (user_id, coin, amount)
        VALUES (%s, %s, %s)
        RETURNING wallet_id
    """, (user_id, symbol, amount))
    
    wallet_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    await ctx.send(f"✅ Created new wallet #{wallet_id} with {amount} {symbol}.")

# ➕ Add Funds to an Existing Wallet
@bot.command()
async def add_funds(ctx, wallet_id: int, amount: float):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE wallets SET amount = amount + %s
        WHERE wallet_id = %s
        RETURNING amount, coin
    """, (amount, wallet_id))

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if result:
        updated_amount, symbol = result
        await ctx.send(f"✅ Updated wallet #{wallet_id}. New balance: {updated_amount} {symbol}.")
    else:
        await ctx.send("❌ Wallet not found!")

# 📜 View All Wallets
@bot.command()
async def wallets(ctx):
    user_id = ctx.author.id

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT wallet_id, coin, amount FROM wallets WHERE user_id = %s", (user_id,))
    user_wallets = cur.fetchall()
    cur.close()
    conn.close()

    if not user_wallets:
        await ctx.send("🛑 You have no wallets.")
        return

    message = "**📂 Your Wallets:**\n"
    for wallet_id, symbol, amount in user_wallets:
        message += f"- **Wallet #{wallet_id}**: {amount} {symbol}\n"

    await ctx.send(message)

# 💵 Check Wallet Value in USD
@bot.command()
async def wallet_value(ctx):
    user_id = ctx.author.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT wallet_id, coin, amount FROM wallets WHERE user_id = %s", (user_id,))
    user_wallets = cur.fetchall()
    cur.close()
    conn.close()

    if not user_wallets:
        await ctx.send("🛑 You have no wallets.")
        return

    total_value = 0
    message = "**💵 Your Wallet Value:**\n"
    
    for wallet_id, symbol, amount in user_wallets:
        coin_data = get_coin_data(symbol)
        if coin_data:
            price = coin_data["quote"]["USD"]["price"]
            worth = price * amount
            total_value += worth
            message += f"- **Wallet #{wallet_id}**: {amount} {symbol} = **${format_large_number(worth)} USD**\n"
    
    message += f"\n**Total Portfolio Value: ${format_large_number(total_value)} USD**"
    await ctx.send(message)

# 🟢 Run the Bot
bot.run(TOKEN)
