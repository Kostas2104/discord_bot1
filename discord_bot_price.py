import discord
import requests
import os  # Import the os module
from discord.ext import commands

TOKEN = os.getenv("TOKEN")  # Fetch token from environment variable
API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={}"

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def price(ctx, coin: str):
    coin = coin.lower()
    
    response = requests.get(API_URL.format(coin))

    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list):  # Ensure data is a list
            coin_data = data[0]  # First item in the list
            symbol = coin_data.get('symbol', '').upper()
            price = coin_data.get('current_price', 0)
            await ctx.send(f'The current price of {symbol} is ${price:.2f} USD')
        else:
            await ctx.send("Invalid cryptocurrency symbol or data unavailable.")
    else:
        await ctx.send("Error fetching data from CoinGecko. Try again later.")

bot.run(TOKEN)
