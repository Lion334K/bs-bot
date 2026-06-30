import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from datetime import datetime, timezone

# ───────────────────────────────────────────────
#  AYARLAR VE ID'LER
# ───────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID                   = 1480303038408425764
WELCOME_CHANNEL_ID         = 1480314604713414757
BUMP_CHANNEL_ID            = 1517972647126761624
IMAGE_LOG_CHANNEL_ID       = 1480317488456536166

BUMP_BOT_ID                = 302050872383242240 
WELCOME_MESSAGE            = "Gırrnaydın {member}! Harikalar Diyarına hoş geldin. <:emoji:1519431905743994900>"
BUMP_MESSAGE               = "Burp"

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bump_task = None
welcome_message_log: dict = {}

# ───────────────────────────────────────────────
#  EVENTS
# ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Giriş yapıldı: {bot.user}")
    
    # Bot çalıştığında log kanalına emoji gönder
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel:
        try:
            await log_channel.send("<:emoji:1519431905743994900>")
        except Exception as e:
            print(f"⚠️ Emoji gönderilemedi: {e}")

    # Komutları senkronize et
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Komutlar başarıyla senkronize edildi.")
    except Exception as e:
        print(f"⚠️ Senkronizasyon hatası: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = WELCOME_MESSAGE.replace("{member}", member.mention)
        sent = await channel.send(msg)
        welcome_message_log[member.id] = sent.id

@bot.event
async def on_message(message: discord.Message):
    global bump_task
    if message.author == bot.user:
        return

    # Görsel Loglama
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel and message.channel.id != IMAGE_LOG_CHANNEL_ID and not message.author.bot:
        if message.attachments:
            for attachment in message.attachments:
                await log_channel.send(f"📎 **{message.author.display_name}**", file=await attachment.to_file())

    # Bump Kontrol
    if message.channel.id == BUMP_CHANNEL_ID and message.author.id == BUMP_BOT_ID:
        if bump_task and not bump_task.done():
            bump_task.cancel()
        bump_task = asyncio.ensure_future(asyncio.sleep(2 * 60 * 60)) # Basit 2 saatlik döngü

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS
# ───────────────────────────────────────────────

@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = WELCOME_MESSAGE.replace("{member}", interaction.user.mention)
    await interaction.response.send_message(f"**Ön İzleme:**\n{msg}", ephemeral=True)

@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target_channel = bot.get_channel(int(channel_id))
        if not target_channel:
            await interaction.response.send_message("❌ Kanal bulunamadı!", ephemeral=True)
            return
        await target_channel.send(message)
        await interaction.response.send_message(f"✅ Mesaj gönderildi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
