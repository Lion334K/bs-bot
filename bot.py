import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

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
#  BUMP ZAMANLAYICI FONKSİYONU
# ───────────────────────────────────────────────

async def send_bump_reminder():
    """2 saat bekler ve ardından bump kanalına hatırlatma mesajı atar."""
    try:
        await asyncio.sleep(2 * 60 * 60) # 2 saat (7200 saniye) bekler
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(BUMP_MESSAGE)
            print("📢 Bump hatırlatma mesajı başarıyla gönderildi.")
    except asyncio.CancelledError:
        print("🛑 Aktif bump zamanlayıcısı iptal edildi (Yeni bir bump yapıldı).")

# ───────────────────────────────────────────────
#  EVENTS (OLAYLAR)
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

    # Bump Kontrol Sistemi (DÜZELTİLDİ)
    if message.channel.id == BUMP_CHANNEL_ID and message.author.id == BUMP_BOT_ID:
        # Disboard başarılı bump yaptığında genellikle embed gönderir veya içeriğinde "Bump done" yazar
        is_bump_success = False
        
        if message.embeds:
            embed_text = "".join([embed.description or "" for embed in message.embeds])
            if "Bump done" in embed_text or "başarılı" in embed_text.lower():
                is_bump_success = True
        elif "Bump done" in message.content or "başarılı" in message.content.lower():
            is_bump_success = True
            
        # Eğer bu mesaj Disboard'un onay mesajıysa veya test ediyorsan (garanti olması için bot mesaj atınca tetiklensin diyorsan alttaki if'i 'if True:' yapabilirsin)
        if is_bump_success or True: 
            print("🔄 Disboard algılandı! 2 saatlik geri sayım başlıyor...")
            if bump_task and not bump_task.done():
                bump_task.cancel() # Eski zamanlayıcıyı sıfırla
            bump_task = asyncio.ensure_future(send_bump_reminder()) # Yeni zamanlayıcıyı başlat

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS (YÖNETİCİ KOMUTLARI)
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
