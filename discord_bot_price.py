import discord
import requests
import os  # Import the os module
import psycopg2
from discord.ext import commands

# Environment Variables
TOKEN = os.getenv("TOKEN")  # Discord Bot Token
CMC_API_KEY = os.getenv("CMC_API_KEY")  # CoinMarketCap API Key
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL Database URL
CMC_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to PostgreSQL Database
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Format numbers for display
def format_large_number(value):
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"  # Trillions
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"  # Billions
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"  # Millions
    else:
        return f"{value:.2f}"

# Fetch coin data from CoinMarketCap
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
    print(f'✅ Logged in as {bot.user}')

# Get Crypto Price
@bot.command()
async def price(ctx, symbol: str):
    coin_data = get_coin_data(symbol.upper())

    if coin_data:
        price = coin_data["quote"]["USD"]["price"]

        # Formatting price based on value
        if price >= 0.1:
            price_str = f"{price:.2f}"  # 2 decimal places
        elif price >= 0.001:
            price_str = f"{price:.4f}"  # 4 decimal places
        elif price >= 0.0000001:
            price_str = f"{price:.8f}"  # 8 decimal places
        else:
            price_str = f"{price:.11f}"  # 11 decimal places

        await ctx.send(f'💰 The current price of {symbol.upper()} is **${price_str} USD**')
    else:
        await ctx.send("⚠️ Invalid cryptocurrency symbol or data unavailable.")

# Get Market Cap
@bot.command()
async def mc(ctx, symbol: str):
    coin_data = get_coin_data(symbol.upper())

    if coin_data:
        market_cap = coin_data["quote"]["USD"]["market_cap"]
        formatted_mc = format_large_number(market_cap)
        await ctx.send(f"📊 The market cap of {symbol.upper()} is **${formatted_mc} USD**")
    else:
        await ctx.send("⚠️ Invalid cryptocurrency symbol or data unavailable.")

# Add Coins to Portfolio
@bot.command()
async def buy(ctx, symbol: str, amount: float):
    user_id = ctx.author.id
    symbol = symbol.upper()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO portfolio (user_id, coin, amount)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, coin)
        DO UPDATE SET amount = portfolio.amount + EXCLUDED.amount
    """, (user_id, symbol, amount))
    conn.commit()
    cur.close()
    conn.close()

    await ctx.send(f"✅ Added **{amount} {symbol}** to your portfolio!")

# Show Portfolio Worth
@bot.command()
async def portfolio(ctx):
    user_id = ctx.author.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT coin, amount FROM portfolio WHERE user_id = %s", (user_id,))
    holdings = cur.fetchall()
    cur.close()
    conn.close()

    if not holdings:
        await ctx.send("⚠️ You have no holdings in your portfolio.")
        return

    total_value = 0
    message = "📊 **Your Portfolio:**\n"
    
    for symbol, amount in holdings:
        coin_data = get_coin_data(symbol)
        if coin_data:
            price = coin_data["quote"]["USD"]["price"]
            worth = price * amount
            total_value += worth
            message += f"- {symbol}: {amount} ({format_large_number(worth)} USD)\n"
    
    message += f"\n💰 **Total Portfolio Value: ${format_large_number(total_value)} USD**"
    await ctx.send(message)

# Run the Bot
bot.run(TOKEN)
