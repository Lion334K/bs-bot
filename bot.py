import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
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
CONFIG_FILE                = "config.json"

# ───────────────────────────────────────────────
#  SİSTEM VE YANIT MESAJLARI
# ───────────────────────────────────────────────
# Botun komutlara ve hatalara vereceği tepkileri buradan kolayca değiştirebilirsin.
# Süslü parantez içindeki kelimeleri (örn: {error}) silme, bot oraları otomatik doldurur.

SYSTEM_MESSAGES = {
    "setwelcome_success": "✨ **oldu tmm!**\nYeni sey:\n> {yeni_mesaj}",
    "setbump_success": "⏳ **oldu tmm!**\nYeni sey:\n> {yeni_mesaj}",
    "testwelcome_title": "🔮 **hoop test:**\n{msg}",
    "sendmsg_not_found": "🌌 **napiyon** oyle bi kanal yok.",
    "sendmsg_success": "🦋 **gonderdim tmm.**",
    "sendmsg_error": "⛓️ **hata varmis:** `{error}`",
    "err_missing_permissions": "🛡️ **yetkin yok** maal.",
    "err_generic": "🌑 **hata hata düt:** `{error}`"
}

# ───────────────────────────────────────────────
#  DİNAMİK MESAJ SİSTEMİ (JSON KONTROLÜ)
# ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "WELCOME_MESSAGE": "Gırrnaydın {member}! Harikalar Diyarına hoş geldin. <:emoji:1519431905743994900>",
    "BUMP_MESSAGE": "Burp"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Config dosyası okunamadı: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

config = load_config()

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
#  BUMP ZAMANLAYICI VE GEÇMİŞ KONTROLÜ
# ───────────────────────────────────────────────

async def schedule_bump_in(seconds: float):
    global bump_task
    try:
        await asyncio.sleep(seconds)
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(config["BUMP_MESSAGE"])
            print("📢 Bump hatırlatma mesajı gönderildi. Yeni bump yapılana kadar sessiz modda bekleniyor...")
    except asyncio.CancelledError:
        print("🛑 Aktif bump zamanlayıcısı iptal edildi.")

async def check_last_bump_and_schedule():
    global bump_task
    await asyncio.sleep(3) 
    
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not channel:
        print("⚠️ Bump kanalı bulunamadı, geçmiş kontrolü iptal edildi.")
        return

    print("🔍 Son başarılı Disboard bump mesajı kontrol ediliyor...")
    try:
        async for message in channel.history(limit=50):
            is_target = False
            
            if message.author.id == BUMP_BOT_ID:
                if message.embeds:
                    embed_text = "".join([embed.description or "" for embed in message.embeds]).lower()
                    if "bump done" in embed_text or "başarılı" in embed_text or "👍" in embed_text:
                        is_target = True
                elif "bump done" in message.content.lower() or "başarılı" in message.content.lower() or "👍" in message.content:
                    is_target = True
            
            if is_target:
                now = datetime.now(timezone.utc)
                elapsed = (now - message.created_at).total_seconds()
                two_hours = 2 * 60 * 60  
                
                if bump_task and not bump_task.done():
                    bump_task.cancel()

                if elapsed >= two_hours:
                    print("⏰ Son aktivitenin üzerinden 2 saatten fazla süre geçmiş! Hatırlatıcı hemen gönderiliyor.")
                    await channel.send(config["BUMP_MESSAGE"])
                else:
                    remaining = two_hours - elapsed
                    print(f"⏳ Son aktiviteden {elapsed/60:.1f} dakika geçmiş. Hatırlatıcı {remaining/60:.1f} dakika sonra 1 kez gönderilecek.")
                    bump_task = asyncio.ensure_future(schedule_bump_in(remaining))
                return
                
        print("📭 Kanal geçmişinde Disboard'a ait başarılı bir bump izi bulunamadı.")
    except Exception as e:
        print(f"⚠️ Geçmiş kontrolü sırasında hata: {e}")

# ───────────────────────────────────────────────
#  EVENTS (OLAYLAR)
# ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Giriş yapıldı: {bot.user}")
    
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel:
        try:
            await log_channel.send("<:emoji:1519431905743994900>")
        except Exception as e:
            print(f"⚠️ Emoji gönderilemedi: {e}")

    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Komutlar başarıyla senkronize edildi.")
    except Exception as e:
        print(f"⚠️ Senkronizasyon hatası: {e}")

    asyncio.ensure_future(check_last_bump_and_schedule())

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
        sent = await channel.send(msg)
        welcome_message_log[member.id] = sent.id

@bot.event
async def on_message(message: discord.Message):
    global bump_task
    if message.author == bot.user:
        return

    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel and message.channel.id != IMAGE_LOG_CHANNEL_ID and not message.author.bot:
        if message.attachments:
            for attachment in message.attachments:
                await log_channel.send(f"📎 **{message.author.display_name}**", file=await attachment.to_file())

    if message.channel.id == BUMP_CHANNEL_ID and message.author.id == BUMP_BOT_ID:
        is_bump_success = False
        if message.embeds:
            embed_text = "".join([embed.description or "" for embed in message.embeds]).lower()
            if "bump done" in embed_text or "başarılı" in embed_text or "👍" in embed_text:
                is_bump_success = True
        elif "bump done" in message.content.lower() or "başarılı" in message.content.lower() or "👍" in message.content:
            is_bump_success = True
            
        if is_bump_success:
            print("🔄 Canlıda yeni bir başarılı bump algılandı! Tek seferlik yeni hatırlatıcı kuruluyor...")
            if bump_task and not bump_task.done():
                bump_task.cancel() 
            bump_task = asyncio.ensure_future(schedule_bump_in(2 * 60 * 60))

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS (YÖNETİCİ KOMUTLARI)
# ───────────────────────────────────────────────

@bot.tree.command(name="setwelcome", description="Hoş geldin mesajını değiştirir. (Üye etiketi için {member} yazın)")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, yeni_mesaj: str):
    config["WELCOME_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(SYSTEM_MESSAGES["setwelcome_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True)

@bot.tree.command(name="setbump", description="Bump hatırlatma mesajını değiştirir.")
@app_commands.checks.has_permissions(administrator=True)
async def set_bump(interaction: discord.Interaction, yeni_mesaj: str):
    config["BUMP_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(SYSTEM_MESSAGES["setbump_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True)

@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = config["WELCOME_MESSAGE"].replace("{member}", interaction.user.mention)
    await interaction.response.send_message(SYSTEM_MESSAGES["testwelcome_title"].format(msg=msg), ephemeral=True)

@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target_channel = bot.get_channel(int(channel_id))
        if not target_channel:
            await interaction.response.send_message(SYSTEM_MESSAGES["sendmsg_not_found"], ephemeral=True)
            return
        await target_channel.send(message)
        await interaction.response.send_message(SYSTEM_MESSAGES["sendmsg_success"], ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(SYSTEM_MESSAGES["sendmsg_error"].format(error=e), ephemeral=True)

# ───────────────────────────────────────────────
#  HATA YAKALAYICI (YETKİSİZ KULLANIM İÇİN)
# ───────────────────────────────────────────────

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(SYSTEM_MESSAGES["err_missing_permissions"], ephemeral=True)
    else:
        await interaction.response.send_message(SYSTEM_MESSAGES["err_generic"].format(error=error), ephemeral=True)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
