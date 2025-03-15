import discord
import requests
import os  # Import the os module
from discord.ext import commands

TOKEN = os.getenv("TOKEN")  # Fetch token from environment variable
CMC_API_KEY = os.getenv("CMC_API_KEY")  # Replace with your CoinMarketCap API key
API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def price(ctx, coin: str):
    coin = coin.upper()  # CoinMarketCap uses uppercase symbols

    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
    }

    params = {"symbol": coin, "convert": "USD"}
    response = requests.get(API_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and coin in data["data"]:
            coin_data = data["data"][coin]["quote"]["USD"]
            price = coin_data.get("price", 0)

            # Formatting the price with dynamic decimal places
            if price >= 0.1:
                price_str = f"{price:.2f}"  # 2 decimal places
            elif price >= 0.001:
                price_str = f"{price:.4f}"  # 4 decimal places
            elif price >= 0.0000001:
                price_str = f"{price:.8f}"  # 8 decimal places
            else:
                price_str = f"{price:.11f}"  # 11 decimal places

            await ctx.send(f'The current price of {coin} is ${price_str} USD')
        else:
            await ctx.send("Invalid cryptocurrency symbol or data unavailable.")
    else:
        await ctx.send("Error fetching data from CoinMarketCap. Try again later.")

@bot.command()
async def mc(ctx, coin: str):
    """Fetch the market cap of a cryptocurrency."""
    coin = coin.upper()  # CoinMarketCap uses uppercase symbols

    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
    }

    params = {"symbol": coin, "convert": "USD"}
    response = requests.get(API_URL, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and coin in data["data"]:
            coin_data = data["data"][coin]["quote"]["USD"]
            market_cap = coin_data.get("market_cap", 0)
# Formatting Market Cap
            if market_cap >= 1_000_000_000_000:  # Over 1 Trillion
                mc_str = f"{market_cap / 1_000_000_000_000:.2f}T"
            elif market_cap >= 1_000_000_000:  # Over 1 Billion
                mc_str = f"{market_cap / 1_000_000_000:.2f}B"
            elif market_cap >= 1_000_000:  # Over 1 Million
                mc_str = f"{market_cap / 1_000_000:.2f}M"
            else:
                mc_str = f"${market_cap:,.2f}"  # Regular format with commas

            await ctx.send(f'The market cap of {coin} is {mc_str} USD')
        else:
            await ctx.send("Invalid cryptocurrency symbol or data unavailable.")
    else:
        await ctx.send("Error fetching data from CoinMarketCap. Try again later.")


bot.run(TOKEN)
