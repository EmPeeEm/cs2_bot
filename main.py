# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.database import get_cfg
from utils.db_sqlite import init_db

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

async def get_prefix(bot, message):
    guild_id = message.guild.id if message.guild else None
    pfx = get_cfg(guild_id, "prefix", "!")
    return commands.when_mentioned_or(pfx)(bot, message)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Na wszelki wypadek

class CSBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, intents=intents, help_command=None)

    async def setup_hook(self):
        print("Uruchamianie systemów...")
        init_db()
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Załadowano moduł: {filename}')
                except Exception as e:
                    print(f'❌ Błąd w {filename}: {e}')

bot = CSBot()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # DEBUG LOG
    pfx = get_prefix(bot, message)
    if message.content.startswith(pfx) or bot.user.mentioned_in(message):
        print(f"🔍 Wykryto komendę: '{message.content}' od {message.author} (Prefix: {pfx})")
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print('-----------------------------------')
    print(f'BOT AKTYWNY: {bot.user.name}')
    print(f'Obsługiwane serwery: {len(bot.guilds)}')
    print('-----------------------------------')
    await bot.change_presence(activity=discord.Game(name="Counter-Strike 2 z ziomkami"))

if __name__ == '__main__':
    bot.run(TOKEN)