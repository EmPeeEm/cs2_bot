# utils/music_helpers.py
import math
import discord
from config import MAIN_COLOR

def format_duration(ms: int) -> str:
    """Konwertuje milisekundy na czytelny format MM:SS lub HH:MM:SS."""
    if not ms or ms <= 0:
        return "00:00"
    
    total_seconds = int(ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def create_progress_bar(position_ms: int, duration_ms: int, length: int = 14) -> str:
    """Generuje estetyczny, tekstowy pasek postępu."""
    if not duration_ms or duration_ms <= 0:
        return "🔴 LIVE 🔘" + "─" * (length - 1)
    
    progress = max(0.0, min(1.0, position_ms / duration_ms))
    filled_blocks = int(math.floor(progress * length))
    
    bar = ""
    for i in range(length):
        if i == filled_blocks:
            bar += "🔘"
        else:
            bar += "▬"
            
    pos_str = format_duration(position_ms)
    dur_str = format_duration(duration_ms)
    return f"`{pos_str}` {bar} `{dur_str}`"

def create_now_playing_embed(track, position_ms: int, is_paused: bool, volume: int, loop_mode: str, filter_name: str = "Brak") -> discord.Embed:
    """Tworzy bogaty embed z informacjami o aktualnie granym utworze."""
    embed = discord.Embed(
        title="🎵 Teraz Odtwarzane",
        description=f"**[{track.title}]({track.uri})**",
        color=MAIN_COLOR
    )
    
    # Wykonawca / Autor
    author = track.author if hasattr(track, 'author') and track.author else "Nieznany"
    embed.add_field(name="👤 Wykonawca", value=f"`{author}`", inline=True)
    
    # Kto zamówił (jeśli przypisano do tracka jako requester)
    requester = getattr(track, 'requester', None)
    req_val = requester.mention if requester else "`Automatycznie`"
    embed.add_field(name="🎧 Zamówione przez", value=req_val, inline=True)
    
    # Status i głośność
    status_emoji = "⏸️ Wstrzymano" if is_paused else "▶️ Odtwarzanie"
    embed.add_field(name="📊 Status / Głośność", value=f"{status_emoji} • `🔊 {volume}%`", inline=True)
    
    # Pasek postępu
    duration_ms = track.length if hasattr(track, 'length') else 0
    pbar = create_progress_bar(position_ms, duration_ms)
    embed.add_field(name="⏳ Postęp utworu", value=pbar, inline=False)
    
    # Tryb pętli i filtr
    loop_display = {
        "off": "❌ Wyłączona",
        "track": "🔂 Utwór",
        "queue": "🔁 Cała kolejka"
    }.get(loop_mode, "❌ Wyłączona")
    
    embed.add_field(name="🔁 Pętla", value=f"`{loop_display}`", inline=True)
    embed.add_field(name="🎛️ Aktywny Filtr", value=f"`{filter_name}`", inline=True)
    
    # Miniaturka / grafika
    artwork = getattr(track, 'artwork', None)
    if artwork:
        embed.set_thumbnail(url=artwork)
        
    embed.set_footer(text="Użyj przycisków poniżej, aby sterować odtwarzaczem.")
    return embed

async def resolve_youtube_title(url: str) -> str | None:
    """Pobiera dokładny tytuł wideo z YouTube oEmbed API bez ryzyka blokady IP."""
    import aiohttp
    try:
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=4)) as response:
                if response.status == 200:
                    data = await response.json()
                    title = data.get("title")
                    author = data.get("author_name")
                    if title:
                        if author and author not in title:
                            return f"{title} {author}"
                        return title
    except Exception:
        pass
    return None

async def resolve_spotify_title(url: str) -> str | None:
    """Pobiera dokładny tytuł ze Spotify oEmbed API bez wymogu logowania i kluczy."""
    import aiohttp
    try:
        api_url = f"https://open.spotify.com/oembed?url={url}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=4)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("title")
    except Exception:
        pass
    return None


