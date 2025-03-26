import discord
import os
from discord.ext import commands
from get_balances import get_caw_balances

TOKEN = os.getenv("TOKEN")  # Discord Bot Token

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 📌 CDC Wallet Titles
CDC_WALLET_TITLES = ["3DA3", "677F", "825B", "Burn"]

# 📌 Format number to Trillions (T)
def format_trillions(value):
    return f"{value / 1_000_000_000_000:.2f} T"

# 📌 Get Crypto Balances for CDC Wallets
@bot.command()
async def cdc(ctx):
    balances = get_caw_balances()
    
    if balances:
        message = "**📊 CDC Wallet Balances:**\n"
        total_balance = sum(balances)
        
        for title, balance in zip(CDC_WALLET_TITLES, balances):
            message += f"- **{title}:** {format_trillions(balance)} CAW\n"
        
        message += f"\n**Total: {format_trillions(total_balance)} CAW**"
        await ctx.send(message)
    else:
        await ctx.send("❌ Unable to fetch balances!")

# 🟢 Run the Bot
bot.run(TOKEN)
