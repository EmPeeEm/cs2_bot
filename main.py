# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import config

from utils.database import wczytaj_ustawienia

# Załaduj środowisko
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Funkcja pobierająca prefix z bazy danych
def get_prefix(bot, message):
    ustawienia = wczytaj_ustawienia()
    return ustawienia.get("prefix", config.PREFIX)

# Skonfiguruj intencje
intents = discord.Intents.default()
intents.message_content = True

class CSBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_prefix, intents=intents)

    # Handler ładujący wszystkie pliki z folderu cogs/
    async def setup_hook(self):
        print("Uruchamianie systemów...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Załadowano moduł: {filename}')
                except Exception as e:
                    print(f'❌ Błąd w {filename}: {e}')

# Odpalamy!
bot = CSBot()

@bot.event
async def on_ready():
    print('-----------------------------------')
    print(f'BOT AKTYWNY: {bot.user.name}')
    print('-----------------------------------')
    # Opcjonalnie: ustawiamy status bota
    await bot.change_presence(activity=discord.Game(name="Counter-Strike 2 z ziomkami"))

if __name__ == '__main__':
    bot.run(TOKEN)