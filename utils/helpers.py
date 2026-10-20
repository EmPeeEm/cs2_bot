# utils/helpers.py
import time
import discord
import logging

logger = logging.getLogger(__name__)

# Globalny bufor historii edycji per kanał: channel_id -> list of float timestamps
_channel_rename_history = {}

async def safe_rename_channel(channel: discord.abc.GuildChannel, target_name: str) -> bool:
    """
    Bezpiecznie zmienia nazwę kanału (tekstowego lub głosowego) z uwzględnieniem
    twardego limitu Discorda (maksymalnie 2 edycje nazwy danego kanału na 10 minut).
    Zwraca True jeśli zmiana się powiodła, False w przeciwnym razie.
    """
    if not channel:
        return False

    channel_id = channel.id
    now = time.time()
    
    # Usuwamy wpisy starsze niż 610 sekund (10 minut z buforem)
    history = [t for t in _channel_rename_history.get(channel_id, []) if now - t < 610]
    _channel_rename_history[channel_id] = history

    if len(history) >= 2:
        logger.debug(f"[RateLimitGuard] Zmiana nazwy kanału {channel_id} pominięta - osiągnięto limit 2 edycji w 10 min.")
        return False

    if channel.name == target_name:
        return True

    try:
        await channel.edit(name=target_name)
        _channel_rename_history[channel_id].append(time.time())
        logger.info(f"Zmieniono nazwę kanału {channel_id} na: '{target_name}'")
        return True
    except discord.Forbidden:
        logger.warning(f"Brak uprawnienia 'Manage Channels' dla kanału {channel_id}")
        return False
    except discord.HTTPException as e:
        if e.status == 429:
            logger.info(f"Rate limit Discorda (429) przy edycji nazwy kanału {channel_id} - zmiana odłożona.")
        else:
            logger.warning(f"Błąd HTTP przy zmianie nazwy kanału {channel_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd przy zmianie nazwy kanału {channel_id}: {e}")
        return False
