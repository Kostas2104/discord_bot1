import discord
import requests
import os  # Import the os module
from discord.ext import commands

TOKEN = os.getenv("TOKEN")  # Fetch token from environment variable
CMC_API_KEY = "a8fd7838-7f35-4f17-8e5a-c8af39ef18ba"  # Replace with your CoinMarketCap API key
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

bot.run(TOKEN)
