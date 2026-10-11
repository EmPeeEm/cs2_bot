# main.py

import os
import logging
from logging.handlers import RotatingFileHandler
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import get_cfg
from utils.db_sqlite import init_db

# Konfiguracja centralnego logowania
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler("data/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    ]
)
logger = logging.getLogger("CSBot")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

async def get_prefix(bot, message):
    guild_id = message.guild.id if message.guild else None
    pfx = get_cfg(guild_id, "prefix", "!")
    return commands.when_mentioned_or(pfx)(bot, message)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Na potrzeby ról i wzmianek członków

class CSBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, intents=intents, help_command=None)

    async def setup_hook(self):
        logger.info("Uruchamianie systemów bota...")
        init_db()
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f'✅ Załadowano moduł: {filename}')
                except Exception as e:
                    logger.error(f'❌ Błąd w {filename}: {e}', exc_info=True)

        # Synchronizacja Slash / Hybrid Commands z Discordem
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Zsynchronizowano {len(synced)} komend aplikacji (Slash / Hybrid Commands).")
        except Exception as e:
            logger.error(f"❌ Błąd synchronizacji komend aplikacji: {e}", exc_info=True)

bot = CSBot()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Debug log dla tradycyjnych komend prefiksowych
    pfx_list = await get_prefix(bot, message)
    if any(message.content.startswith(p) for p in pfx_list):
        used_pfx = min(pfx_list, key=len)
        logger.info(f"🔍 Wykryto komendę tekstową: '{message.content}' od {message.author} (Prefix: {used_pfx})")
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info('-----------------------------------')
    logger.info(f'BOT AKTYWNY: {bot.user.name}')
    logger.info(f'Obsługiwane serwery: {len(bot.guilds)}')
    logger.info('-----------------------------------')
    await bot.change_presence(activity=discord.Game(name="Counter-Strike 2 z ziomkami"))

if __name__ == '__main__':
    bot.run(TOKEN)