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

BUMP_BOT_ID                = 302050872383242240 # Disboard botunun varsayılan ID'si (Değişmez)

# Emoji formatı sorunsuz çalışması için <:isim:ID> şeklinde ayarlandı
WELCOME_MESSAGE = "Gırrnaydın {member}! Harikalar Diyarına hoş geldin. <:emoji:1519431905743994900>"
BUMP_MESSAGE    = "Burp"

# ───────────────────────────────────────────────
#  BOT SETUP & STATE
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bump_task = None
welcome_message_log: dict = {}

# ───────────────────────────────────────────────
#  BUMP YARDIMCILARI
# ───────────────────────────────────────────────

async def schedule_bump():
    try:
        await asyncio.sleep(2 * 60 * 60) # 2 saat bekler
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(BUMP_MESSAGE)
    except asyncio.CancelledError:
        pass

async def schedule_bump_in(seconds: float):
    try:
        await asyncio.sleep(max(0, seconds))
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(BUMP_MESSAGE)
    except asyncio.CancelledError:
        pass

# ───────────────────────────────────────────────
#  EVENTS (OLAYLAR)
# ───────────────────────────────────────────────

@bot.event
async def on_ready():
    global bump_task
    print(f"✅ Giriş yapıldı: {bot.user} (ID: {bot.user.id})")
    
    # Slash komutlarını senkronize et
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Slash komutları senkronize edildi.")
    except Exception as e:
        print(f"⚠️ Slash komut senkronizasyon hatası: {e}")

    # Sunucu açıldığında mevcut bump durumunu kontrol et
    try:
        bump_channel = bot.get_channel(BUMP_CHANNEL_ID)
        if bump_channel:
            messages = [msg async for msg in bump_channel.history(limit=10)]
            last_bump = next((m for m in messages if m.author.id == BUMP_BOT_ID), None)
            if last_bump:
                elapsed = (datetime.now(timezone.utc) - last_bump.created_at).total_seconds()
                remaining = (2 * 60 * 60) - elapsed
                if remaining > 0:
                    bump_task = asyncio.ensure_future(schedule_bump_in(remaining))
                else:
                    bump_task = asyncio.ensure_future(schedule_bump_in(0))
    except Exception as e:
        print(f"⚠️ Bump kontrol hatası: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = WELCOME_MESSAGE.replace("{member}", member.mention)
        sent = await channel.send(msg)
        welcome_message_log[member.id] = sent.id

@bot.event
async def on_member_remove(member: discord.Member):
    if member.id not in welcome_message_log:
        return
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        try:
            msg = await channel.fetch_message(welcome_message_log[member.id])
            await msg.edit(content=f"{member.mention} geri gitti... 🥺")
        except discord.NotFound:
            pass
        finally:
            del welcome_message_log[member.id]

@bot.event
async def on_message(message: discord.Message):
    global bump_task

    # Kendi mesajlarını yoksay
    if message.author == bot.user:
        return

    # Görsel Loglama Sistemi
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel and message.channel.id != IMAGE_LOG_CHANNEL_ID and not message.author.bot:
        if message.attachments:
            for attachment in message.attachments:
                await log_channel.send(
                    f"📎 **{message.author.display_name}** (#{message.channel.name})",
                    file=await attachment.to_file()
                )

    # Bump Tetikleme Kontrolü
    if message.channel.id == BUMP_CHANNEL_ID:
        if message.author.id == BUMP_BOT_ID:
            if bump_task and not bump_task.done():
                bump_task.cancel()
            bump_task = asyncio.ensure_future(schedule_bump())

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS (YÖNETİM KOMUTLARI)
# ───────────────────────────────────────────────

@bot.tree.command(name="setwelcome", description="Hoş geldin mesajını değiştirir. Yeni üyeyi etiketlemek için {member} kullan.")
@app_commands.checks.has_permissions(administrator=True) # Sadece yöneticiler kullanabilir
async def set_welcome(interaction: discord.Interaction, message: str):
    global WELCOME_MESSAGE
    WELCOME_MESSAGE = message
    await interaction.response.send_message(f"✅ Güncellendi:\n> {WELCOME_MESSAGE}", ephemeral=True)

@bot.tree.command(name="testwelcome", description="Mevcut hoş geldin mesajını ön izle.")
@app_commands.checks.has_permissions(administrator=True) # Sadece yöneticiler kullanabilir
async def test_welcome(interaction: discord.Interaction):
    msg = WELCOME_MESSAGE.replace("{member}", interaction.user.mention)
    # ephemeral=True olduğu için mesajı sadece komutu kullanan kişi görebilir
    await interaction.response.send_message(f"**Ön İzleme:**\n{msg}", ephemeral=True)

@bot.tree.command(name="setbump", description="Bump hatırlatma mesajını değiştirir.")
@app_commands.checks.has_permissions(administrator=True) # Sadece yöneticiler kullanabilir
async def set_bump(interaction: discord.Interaction, message: str):
    global BUMP_MESSAGE
    BUMP_MESSAGE = message
    await interaction.response.send_message(f"✅ Güncellendi:\n> {BUMP_MESSAGE}", ephemeral=True)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
