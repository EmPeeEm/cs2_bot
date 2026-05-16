# utils/faceit_api.py

import aiohttp
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
FACEIT_KEY = os.getenv('FACEIT_API_KEY')
BASE_URL = "https://open.faceit.com/data/v4"

_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

async def close_faceit_session():
    global _session
    if _session and not _session.closed:
        await _session.close()

async def get_faceit_data(endpoint: str):
    """Pomocnicza funkcja do zapytań API (z connection pooling)"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    session = await get_session()
    try:
        async with session.get(f"{BASE_URL}/{endpoint}", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None
    except aiohttp.ClientError as e:
        print(f"Faceit API Connection Error: {e}")
        return None

async def get_player_id(identifier: str):
    """Szybkie pobieranie samego player_id na podstawie nicku lub ID"""
    if is_uuid(identifier):
        return identifier
    dane = await get_faceit_data(f"players?nickname={identifier}")
    return dane.get("player_id") if dane else None

async def get_latest_match_id(player_id: str):
    """Pobiera ID ostatniego meczu bez statystyk (bardzo lekkie zapytanie)"""
    historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit=1")
    if historia and historia.get("items"):
        return historia["items"][0].get("match_id")
    return None

import re

def is_uuid(identifier: str):
    """Sprawdza czy ciąg znaków jest w formacie UUID (player_id)"""
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str(identifier).lower()))

import time

_stats_cache = {}
CACHE_TTL = 60

async def get_player_stats(identifier: str, lifetime: bool = True):
    """Pobiera podstawowe info o graczu (ELO, Level). Opcjonalnie statystyki kariery."""
    cache_key = f"{identifier}_{lifetime}"
    now = time.time()
    
    if cache_key in _stats_cache:
        cached, timestamp = _stats_cache[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached

    if is_uuid(identifier):
        dane = await get_faceit_data(f"players/{identifier}")
    else:
        dane = await get_faceit_data(f"players?nickname={identifier}")
    if not dane: return None
    
    player_id = dane.get("player_id")
    cs2_dane = dane.get("games", {}).get("cs2", {})
    
    stats = {
        "player_id": player_id,
        "nick": dane.get("nickname"),
        "poziom": cs2_dane.get("skill_level", "Brak"),
        "elo": cs2_dane.get("faceit_elo", "Brak"),
        "avatar_url": dane.get("avatar") or "https://i.imgur.com/vHq100B.png",
        "url_profilu": f"https://www.faceit.com/pl/players/{dane.get('nickname')}",
        # Steam64 ID – używane przy parsowaniu demek (game_player_id w cs2)
        "steam_id": cs2_dane.get("game_player_id"),
    }

    if lifetime:
        # Pobierzmy też Lifetime z drugiej ścieżki
        lifetime_dane = await get_faceit_data(f"players/{player_id}/stats/cs2")
        lifetime_obj = lifetime_dane.get("lifetime", {}) if lifetime_dane else {}
        
        stats.update({
            "lifetime_clutches": int(lifetime_obj.get("Total 1v1 Wins", 0)) + int(lifetime_obj.get("Total 1v2 Wins", 0)),
            "lifetime_entry": lifetime_obj.get("Total Entry Wins", "0"),
            "lifetime_hs": lifetime_obj.get("Average Headshots %", "0"),
            "lifetime_winrate": lifetime_obj.get("Win Rate %", "0"),
            "lifetime_kd": lifetime_obj.get("Average K/D Ratio", "0"),
            "lifetime_adr": lifetime_obj.get("ADR", "0"),
            "lifetime_matches": lifetime_obj.get("Matches", "0"),
            "lifetime_wins": lifetime_obj.get("Wins", "0"),
            "lifetime_winstreak": lifetime_obj.get("Current Win Streak", "0")
        })
    
    if stats:
        _stats_cache[cache_key] = (stats, now)
        
    return stats

async def get_last_match_stats(player_id: str):
    """Pobiera statystyki ostatniego meczu gracza"""
    historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit=1")
    if not historia or not historia.get("items"): return None
    
    match_id = historia["items"][0]["match_id"]
    
    staty_meczu = await get_faceit_data(f"matches/{match_id}/stats")
    if not staty_meczu: return None

    for runda in staty_meczu.get("rounds", []):
        for team in runda.get("teams", []):
            for player in team.get("players", []):
                if player["player_id"] == player_id:
                    ps = player["player_stats"]
                    rs = runda.get("round_stats", {})
                    
                    kille = float(ps.get("Kills", 0))
                    asysty = float(ps.get("Assists", 0))
                    dedy = float(ps.get("Deaths", 1))
                    kpr = float(ps.get("K/R Ratio", 0.01))
                    
                    # Prosta kalkulacja rund
                    rundy = kille / kpr if kpr > 0 else 1.0
                    
                    hltv_rating = (kille + 0.7 * asysty + (rundy - dedy) * 0.6) / rundy if rundy > 0 else 0

                    return {
                        "match_id": match_id,
                        "finished_at": historia["items"][0].get("finished_at"),
                        "mapa": rs.get("Map", "Brak danych"),
                        "wynik": rs.get("Score", "Brak danych"),
                        "rounds": float(rs.get("Rounds", 0)),
                        "kille": kille,
                        "asysty": asysty,
                        "dedy": dedy,
                        "kd": float(ps.get("K/D Ratio", 1)),
                        "kr": kpr,
                        "hs_procent": float(ps.get("Headshots %", 0)),
                        "mvp": float(ps.get("MVPs", 0)),
                        "win": ps.get("Result") == "1",
                        "adr": float(ps.get("ADR", 0)),
                        "ud": float(ps.get("Utility Damage", 0)),
                        "udpr": float(ps.get("Utility Damage per Round in a Match", 0)),
                        "ef": float(ps.get("Enemies Flashed", 0)),
                        "clutch_1v1": float(ps.get("1v1Wins", 0)),
                        "clutch_1v2": float(ps.get("1v2Wins", 0)),
                        "entry_wins": float(ps.get("First Kills", 0)),
                        "entry_success": float(ps.get("Match Entry Success Rate", 0)) * 100,
                        "flash_success": float(ps.get("Flash Success Rate per Match", 0)) * 100,
                        "triple_kills": int(ps.get("Triple Kills", 0)),
                        "quadro_kills": int(ps.get("Quadro Kills", 0)),
                        "penta_kills": int(ps.get("Penta Kills", 0)),
                        "sniper_kills": int(ps.get("Sniper Kills", 0)),
                        "sniper_kr": float(ps.get("Sniper Kill Rate per Round", 0)),
                        "hltv": round(hltv_rating, 2)
                    }
    return None
    
async def get_match_details(match_id: str):
    """Pobiera pełne szczegóły meczu (w tym URL do dema)"""
    return await get_faceit_data(f"matches/{match_id}")

async def get_demo_url(match_id: str) -> str | None:
    """
    Pobiera URL do pliku dema dla danego meczu.
    Faceit dostarcza demo jako .dem.gz w polu demo_url (tablica, bierzemy pierwszy).
    Może zwrócić None jeśli demo nie jest jeszcze gotowe.
    """
    details = await get_match_details(match_id)
    if not details:
        return None
    urls = details.get("demo_url", [])
    return urls[0] if urls else None


async def get_multiple_matches_stats(player_id: str, limit: int = 30):
    historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit={limit}")
    if not historia or not historia.get("items"): 
        return []
        
    items = historia.get("items", [])
    
    sem = asyncio.Semaphore(5)
    
    async def fetch_single(match_id):
        async with sem:
            await asyncio.sleep(0.1)
            return await get_faceit_data(f"matches/{match_id}/stats")
        
    wyniki = []
    for item in items:
        m_id = item["match_id"]
        f_at = item.get("finished_at")
        staty = await fetch_single(m_id)
        if staty:
            wyniki.append((staty, f_at))
        
    podsumowanie = []
    # Parsowanie danych pod kątem konkretnego gracza
    for mecz_dane, finished_at in wyniki:
        if not mecz_dane:
            continue
        for runda in mecz_dane.get("rounds", []):
            for team in runda.get("teams", []):
                for player in team.get("players", []):
                    if player["player_id"] == player_id:
                        ps = player["player_stats"]
                        
                        kille = float(ps.get("Kills", 0))
                        asysty = float(ps.get("Assists", 0))
                        dedy = float(ps.get("Deaths", 1))
                        kpr = float(ps.get("K/R Ratio", 0.01))
                        rundy = kille / kpr if kpr > 0 else 1.0
                        hltv_rating = (kille + 0.7 * asysty + (rundy - dedy) * 0.6) / rundy if rundy > 0 else 0
                        
                        podsumowanie.append({
                            "match_id": mecz_dane.get("match_id"),
                            "finished_at": finished_at,
                            "kille": kille,
                            "asysty": asysty,
                            "dedy": dedy,
                            "kd": float(ps.get("K/D Ratio", 1)),
                            "kr": kpr,
                            "hs_procent": float(ps.get("Headshots %", 0)),
                            "mvp": float(ps.get("MVPs", 0)),
                            "win": ps.get("Result") == "1",
                            "score": runda.get("round_stats", {}).get("Score", "Brak"),
                            "mapa": runda.get("round_stats", {}).get("Map", "Nieznana"),
                            "adr": float(ps.get("ADR", 0)),
                            "ud": float(ps.get("Utility Damage", 0)),
                            "udpr": float(ps.get("Utility Damage per Round in a Match", 0)),
                            "ef": float(ps.get("Enemies Flashed", 0)),
                            "clutch_1v1": float(ps.get("1v1Wins", 0)),
                            "clutch_1v2": float(ps.get("1v2Wins", 0)),
                            "entry_wins": float(ps.get("First Kills", 0)), 
                            "entry_success": float(ps.get("Match Entry Success Rate", 0)),
                            "triple_kills": int(ps.get("Triple Kills", 0)),
                            "quadro_kills": int(ps.get("Quadro Kills", 0)),
                            "penta_kills": int(ps.get("Penta Kills", 0)),
                            "sniper_kills": int(ps.get("Sniper Kills", 0)),
                            "hltv": round(hltv_rating, 2)
                        })
    return podsumowanie

async def get_map_segments(player_id: str):
    """Pobiera zestawienie map gracza"""
    dane = await get_faceit_data(f"players/{player_id}/stats/cs2")
    if not dane: return []
    return dane.get("segments", [])