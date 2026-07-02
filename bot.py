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
#  BUMP ZAMANLAYICI VE GEÇMİŞ KONTROLÜ
# ───────────────────────────────────────────────

async def schedule_bump_in(seconds: float):
    """Belirtilen saniye kadar bekler, mesajı atar ve otomatik döngüyü sürdürür."""
    global bump_task
    try:
        await asyncio.sleep(seconds)
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(BUMP_MESSAGE)
            print("📢 Bump hatırlatma mesajı gönderildi. Disboard mesaj atmazsa 2 saat sonra tekrar çalışacak şekilde döngü yenileniyor...")
            
            # Kendi mesajından 2 saat sonrası için otomatik olarak tekrar kuruyor (Fallback güvencesi)
            bump_task = asyncio.ensure_future(schedule_bump_in(2 * 60 * 60))
    except asyncio.CancelledError:
        print("🛑 Aktif bump zamanlayıcısı iptal edildi.")

async def check_last_bump_and_schedule():
    """Hem Disboard hem de Bot geçmişini kontrol ederek akıllı zamanlayıcıyı başlatır."""
    global bump_task
    await asyncio.sleep(3) # Bot önbelleğinin dolması için kısa bir bekleme
    
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not channel:
        print("⚠️ Bump kanalı bulunamadı, geçmiş kontrolü iptal edildi.")
        return

    print("🔍 Son aktivite (Disboard mesajı veya Bot hatırlatıcısı) kanal geçmişinden kontrol ediliyor...")
    try:
        async for message in channel.history(limit=50):
            is_target = False
            
            # 1. Durum: Mesaj Disboard'un başarılı bump mesajı mı?
            if message.author.id == BUMP_BOT_ID:
                if message.embeds:
                    embed_text = "".join([embed.description or "" for embed in message.embeds]).lower()
                    if "bump done" in embed_text or "başarılı" in embed_text or "👍" in embed_text:
                        is_target = True
                elif "bump done" in message.content.lower() or "başarılı" in message.content.lower() or "👍" in message.content:
                    is_target = True
            
            # 2. Durum: Mesaj bizim botun kendi hatırlatma mesajı mı?
            elif message.author.id == bot.user.id and message.content == BUMP_MESSAGE:
                is_target = True

            # Eğer en güncel hedef mesajı bulduysak hesaplamayı yapıyoruz
            if is_target:
                now = datetime.now(timezone.utc)
                elapsed = (now - message.created_at).total_seconds()
                two_hours = 2 * 60 * 60  # 7200 saniye
                
                if bump_task and not bump_task.done():
                    bump_task.cancel()

                if elapsed >= two_hours:
                    print("⏰ Son aktivitenin üzerinden 2 saatten fazla süre geçmiş! Hatırlatıcı hemen gönderiliyor.")
                    await channel.send(BUMP_MESSAGE)
                    # Mesaj atıldığı için yeni 2 saatlik döngüyü başlatıyoruz
                    bump_task = asyncio.ensure_future(schedule_bump_in(two_hours))
                else:
                    remaining = two_hours - elapsed
                    print(f"⏳ Son aktiviteden {elapsed/60:.1f} dakika geçmiş. Hatırlatıcı {remaining/60:.1f} dakika sonra gönderilecek.")
                    bump_task = asyncio.ensure_future(schedule_bump_in(remaining))
                return
                
        print("📭 Kanal geçmişinde ne Disboard ne de bota ait bir iz bulunamadı.")
    except Exception as e:
        print(f"⚠️ Geçmiş kontrolü sırasında hata: {e}")

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

    # Bot her yeniden başladığında geçmişi kontrol eden akıllı fonksiyonu tetikle
    asyncio.ensure_future(check_last_bump_and_schedule())

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

    # Canlıde Disboard Mesaj Takibi
    if message.channel.id == BUMP_CHANNEL_ID and message.author.id == BUMP_BOT_ID:
        is_bump_success = False
        if message.embeds:
            embed_text = "".join([embed.description or "" for embed in message.embeds]).lower()
            if "bump done" in embed_text or "başarılı" in embed_text or "👍" in embed_text:
                is_bump_success = True
        elif "bump done" in message.content.lower() or "başarılı" in message.content.lower() or "👍" in message.content:
            is_bump_success = True
            
        if is_bump_success:
            print("🔄 Canlıda yeni bir başarılı bump algılandı! Sayaç Disboard saatine göre sıfırlanıyor...")
            if bump_task and not bump_task.done():
                bump_task.cancel() # Önceki tüm sayaçları (botun kendi döngüsü dahil) iptal et
            bump_task = asyncio.ensure_future(schedule_bump_in(2 * 60 * 60)) # Temiz 2 saat başlat

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
