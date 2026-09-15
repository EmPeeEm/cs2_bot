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

_api_sem = asyncio.Semaphore(4)

async def get_faceit_data(endpoint: str, retries: int = 2):
    """Pomocnicza funkcja do zapytań API z connection poolingiem i ponawianiem przy 429 (Rate Limit)"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    session = await get_session()
    
    for attempt in range(retries + 1):
        try:
            async with _api_sem:
                async with session.get(f"{BASE_URL}/{endpoint}", headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        if attempt < retries:
                            await asyncio.sleep(1.2 * (attempt + 1))
                            continue
                        print(f"⚠️ Faceit API Error (Status 429 - Rate Limit) dla endpointu: {endpoint}")
                        return None
                    elif response.status == 404:
                        return None
                    print(f"⚠️ Faceit API Error (Status {response.status}) dla endpointu: {endpoint}")
                    return None
        except aiohttp.ClientError as e:
            if attempt < retries:
                await asyncio.sleep(0.5)
                continue
            print(f"Faceit API Connection Error: {e}")
            return None
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

async def get_player_ongoing_match_id(player_id: str):
    """Sprawdza czy gracz jest w aktywnym meczu (obsługuje endpointy Faceit groupByState oraz Open API)"""
    session = await get_session()
    
    # 1. Sprawdzenie Faceit groupByState (natychmiastowe wykrywanie w czasie rzeczywistym)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Referer": "https://www.faceit.com/",
            "Origin": "https://www.faceit.com"
        }
        url_group = f"https://api.faceit.com/match/v1/matches/groupByState?userId={player_id}"
        async with session.get(url_group, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                payload = data.get("payload", {})
                for state in ["ONGOING", "MATCH", "SUBSTITUTION", "CHECKIN", "CALL", "VOTING", "CONFIGURING", "READY"]:
                    matches = payload.get(state, [])
                    if matches:
                        m_id = matches[0].get("id") or matches[0].get("matchId")
                        if m_id:
                            return m_id
            elif resp.status != 404:
                print(f"⚠️ [LIVE API] groupByState status {resp.status} dla {player_id}")
    except Exception as e:
        print(f"⚠️ [LIVE API] Błąd groupByState dla {player_id}: {e}")

    # 2. Fallback: Open Data API history
    try:
        historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit=1")
        if historia and historia.get("items"):
            item = historia["items"][0]
            m_id = item.get("match_id")
            if m_id:
                status = item.get("status", "").upper()
                if status in ["VOTING", "CONFIGURING", "READY", "ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                    return m_id
    except Exception:
        pass

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

MAP_IMAGES = {
    "Mirage": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_mirage.jpg",
    "Inferno": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_inferno.jpg",
    "Dust2": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_dust2.jpg",
    "Nuke": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_nuke.jpg",
    "Ancient": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_ancient.jpg",
    "Anubis": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_anubis.jpg",
    "Vertigo": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_vertigo.jpg",
    "Cache": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_cache.jpg",
    "Overpass": "https://raw.githubusercontent.com/lexogrine/csgocdn/master/public/images/maps/de_overpass.jpg",
}

async def get_match_details(match_id: str):
    """Pobiera pełne szczegóły meczu (status, mapa, drużyny, wynik)"""
    dane = await get_faceit_data(f"matches/{match_id}")
    if not dane: return None
    
    # Rozpoznawanie mapy
    voting = dane.get("voting", {})
    map_pick = voting.get("map", {}).get("pick", [])
    raw_map = map_pick[0] if map_pick else "W trakcie wyboru"
    mapa = raw_map.replace("de_", "").title() if raw_map.startswith("de_") else raw_map
    if mapa.lower() == "dust2": mapa = "Dust2"
    
    teams = dane.get("teams", {})
    faction1 = teams.get("faction1", {})
    faction2 = teams.get("faction2", {})
    
    # Wynik
    results = dane.get("results", {})
    score = results.get("score", {})
    score_f1 = score.get("faction1", 0) if isinstance(score, dict) else 0
    score_f2 = score.get("faction2", 0) if isinstance(score, dict) else 0
    winner = results.get("winner") if isinstance(results, dict) else None
    
    status = dane.get("status", "UNKNOWN")
    faceit_url = dane.get("faceit_url", "").replace("{lang}", "pl")
    if not faceit_url and match_id:
        faceit_url = f"https://www.faceit.com/pl/cs2/room/{match_id}"
        
    return {
        "match_id": match_id,
        "status": status,
        "mapa": mapa,
        "map_image": MAP_IMAGES.get(mapa),
        "faceit_url": faceit_url,
        "calculate_elo": dane.get("calculate_elo", True),
        "configured_at": dane.get("configured_at"),
        "started_at": dane.get("started_at"),
        "finished_at": dane.get("finished_at"),
        "teams": {
            "faction1": {
                "name": faction1.get("name", "Team 1"),
                "leader": faction1.get("leader"),
                "stats": faction1.get("stats", {}),
                "roster": faction1.get("roster", []),
            },
            "faction2": {
                "name": faction2.get("name", "Team 2"),
                "leader": faction2.get("leader"),
                "stats": faction2.get("stats", {}),
                "roster": faction2.get("roster", []),
            }
        },
        "score": {"faction1": score_f1, "faction2": score_f2},
        "winner": winner
    }