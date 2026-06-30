import discord
import os  # Bu kütüphaneyi eklemeyi unutma
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')

# Token'ı ortam değişkeninden çekiyoruz
token = os.getenv('DISCORD_TOKEN')

bot.run(token)