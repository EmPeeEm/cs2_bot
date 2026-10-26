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

class TerminalColorFormatter(logging.Formatter):
    """Jednolinijkowy formater ANSI dla konsoli ze wskaźnikami krawędziowymi i kolumnami."""
    GREY = "\033[90m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"
    RESET = "\033[0m"

    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        bar = f"{color}▌{self.RESET}"
        time_part = f"{self.GREY}{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}{self.RESET}"
        level_part = f"{color}{record.levelname:<8}{self.RESET}"
        name_part = f"{self.CYAN}{record.name:<13}{self.RESET}"
        sep = f"{self.GREY}│{self.RESET}"
        msg = record.getMessage()

        if record.levelno >= logging.ERROR:
            msg = f"{self.RED}{msg}{self.RESET}"
        elif record.levelno == logging.WARNING:
            msg = f"{self.YELLOW}{msg}{self.RESET}"

        line = f"{bar} {time_part} {sep} {level_part} {sep} {name_part} {sep} {msg}"
        if record.exc_info:
            line += f"\n{self.formatException(record.exc_info)}"
        return line

console_handler = logging.StreamHandler()
console_handler.setFormatter(TerminalColorFormatter())

file_handler = RotatingFileHandler(
    "data/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-13s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
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
        self.ipc_client = None

    async def setup_hook(self):
        logger.info("Uruchamianie systemów bota...")
        init_db()

        # Inicjalizacja modułu muzycznego (Vocard / Voicelink)
        try:
            import function as func
            from voicelink import Config, MongoDBHandler, LangHandler, IPCClient
            bot_config = Config(func.open_json("settings.json"))
            LangHandler.init()
            await MongoDBHandler.init(bot_config.mongodb_url, bot_config.mongodb_name)
            if bot_config.ipc_client.get("enable", False):
                self.ipc_client = IPCClient(self, **bot_config.ipc_client)
            else:
                self.ipc_client = None
            logger.info("Zainicjalizowano moduł muzyczny Vocard (Voicelink & LangHandler)")
        except Exception as e:
            logger.warning(f"Ostrzeżenie przy inicjalizacji modułu muzycznego: {e}")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f'Załadowano moduł: {filename[:-3]}')
                except Exception as e:
                    logger.error(f'Błąd ładowania {filename}: {e}', exc_info=True)

        # Rejestracja widoków trwałych (Persistent Views)
        try:
            from cogs.season_ui import SeasonView
            from cogs.tilt_ui import TiltView
            self.add_view(SeasonView())
            self.add_view(TiltView())
            logger.info("Zarejestrowano widoki trwałe: SeasonView, TiltView")
        except Exception as e:
            logger.error(f"Błąd rejestracji widoków trwałych: {e}", exc_info=True)

bot = CSBot()

# --- Komenda bezpiecznej synchronizacji drzewa komend (/sync) ---
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_commands(ctx: commands.Context, spec: str = None):
    """
    Ręczna synchronizacja komend aplikacji z Discordem.
    Użycie:
      !sync        -> synchronizuje komendy natychmiastowo z bieżącym serwerem (zalecane)
      !sync global -> synchronizuje globalnie (może zająć do 1h)
      !sync clear  -> czyści zarejestrowane komendy z bieżącego serwera
    """
    msg = await ctx.send("⏳ Trwa synchronizacja drzewa komend z Discordem...")
    try:
        if spec == "global":
            synced = await bot.tree.sync()
            await msg.edit(content=f"🌍 Zsynchronizowano **{len(synced)}** komend aplikacji globalnie z Discordem.")
            logger.info(f"Ręczna synchronizacja globalna ({len(synced)} komend) wykonana przez {ctx.author}.")
        elif spec == "clear":
            bot.tree.clear_commands(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
            await msg.edit(content="🧹 Wyczyszczono komendy aplikacji dla tego serwera.")
            logger.info(f"Wyczyszczono komendy gildii {ctx.guild.id} przez {ctx.author}.")
        else:
            bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
            await msg.edit(content=f"✅ Zsynchronizowano **{len(synced)}** komend aplikacji natychmiast dla serwera **{ctx.guild.name}**.")
            logger.info(f"Ręczna synchronizacja dla gildii {ctx.guild.id} ({len(synced)} komend) wykonana przez {ctx.author}.")
    except Exception as e:
        logger.error(f"Błąd podczas synchronizacji komend: {e}", exc_info=True)
        await msg.edit(content=f"❌ Błąd synchronizacji komend: `{e}`")

# --- Centralny Error Handler ---
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Obsługa błędów komend tradycyjnych i hybrydowych."""
    # Ignoruj brak komendy (np. przypadkowe wywołanie prefiksu w tekście)
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Ta komenda może być używana tylko na serwerze Discord.")
        return

    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        await ctx.send(f"❌ Nie posiadasz wymaganych uprawnień: {perms}")
        return

    if isinstance(error, commands.BotMissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        await ctx.send(f"❌ Bot nie posiada uprawnień do wykonania tej operacji: {perms}")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Brakujący argument: `{error.param.name}`. Sprawdź `{ctx.prefix}pomoc {ctx.command.name}`.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Niepoprawny argument: {error}")
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Poczekaj jeszcze {error.retry_after:.1f}s przed ponownym użyciem tej komendy.")
        return

    # Błędy modułu muzycznego (Voicelink)
    original = getattr(error, "original", error)
    try:
        import voicelink
        if isinstance(original, voicelink.exceptions.NoNodesAvailable):
            await ctx.send("⚠️ Węzeł muzyczny (Lavalink) nie jest jeszcze gotowy lub trwa ponowne łączenie. Spróbuj ponownie za chwilę!")
            return
        if isinstance(original, voicelink.exceptions.VoicelinkException):
            await ctx.send(f"⚠️ {original}")
            return
    except ImportError:
        pass

    # Pozostałe błędy
    logger.error(f"Nieobsłużony błąd w komendzie '{ctx.command}': {error}", exc_info=error)
    try:
        await ctx.send("❌ Wystąpił niespodziewany błąd podczas wykonywania komendy. Szczegóły zapisano w logach.")
    except Exception:
        pass

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Obsługa błędów komend aplikacji (Slash Commands)."""
    original = getattr(error, "original", error)
    try:
        import voicelink
        is_no_node = isinstance(original, voicelink.exceptions.NoNodesAvailable)
        is_voicelink_err = isinstance(original, voicelink.exceptions.VoicelinkException)
    except ImportError:
        is_no_node = False
        is_voicelink_err = False

    if is_no_node:
        msg = "⚠️ Węzeł muzyczny (Lavalink) nie jest jeszcze gotowy lub trwa ponowne łączenie. Spróbuj ponownie za chwilę!"
    elif is_voicelink_err:
        msg = f"⚠️ {original}"
    elif isinstance(error, discord.app_commands.MissingPermissions):
        msg = "❌ Nie posiadasz uprawnień administratora do wykonania tej operacji."
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        msg = f"❌ Bot nie posiada uprawnień do wykonania tej operacji ({', '.join(error.missing_permissions)})."
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = f"⏳ Poczekaj jeszcze {error.retry_after:.1f}s przed ponownym użyciem."
    else:
        logger.error(f"Błąd komendy aplikacji Slash: {error}", exc_info=error)
        msg = "❌ Wystąpił błąd podczas wykonywania polecenia."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Nie udało się wysłać komunikatu błędu do użytkownika: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Obsługa dedykowanego kanału żądań muzycznych
    try:
        if message.guild:
            from voicelink import MongoDBHandler
            settings = MongoDBHandler.get_cached_settings(message.guild.id)
            if settings and (request_channel := settings.get("music_request_channel")):
                if message.channel.id == request_channel.get("text_channel_id"):
                    ctx = await bot.get_context(message)
                    if not ctx.prefix:
                        play_cmd = bot.get_command("play")
                        if play_cmd:
                            try:
                                await ctx.invoke(play_cmd, query=message.content)
                            finally:
                                try:
                                    await message.delete()
                                except Exception:
                                    pass
                            return
    except Exception as e:
        logger.debug(f"Pominięto przetwarzanie auto-request w kanale: {e}")
    
    # Debug log dla tradycyjnych komend prefiksowych
    pfx_list = await get_prefix(bot, message)
    if any(message.content.startswith(p) for p in pfx_list):
        used_pfx = min(pfx_list, key=len)
        logger.info(f"Komenda tekstowa: '{message.content}' od {message.author} (prefix: {used_pfx})")
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info("----------------------------------------")
    logger.info(f"Bot aktywny: {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Obsługiwane serwery: {len(bot.guilds)}")
    logger.info("Synchronizacja komend slash: !sync")
    logger.info("----------------------------------------")
    await bot.change_presence(activity=discord.Game(name="Counter-Strike 2 z ziomkami"))

if __name__ == '__main__':
    if not TOKEN:
        logger.critical("Brak DISCORD_TOKEN w zmiennych środowiskowych (.env)")
    else:
        bot.run(TOKEN)