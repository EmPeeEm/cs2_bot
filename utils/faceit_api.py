# utils/faceit_api.py

import aiohttp
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
FACEIT_KEY = os.getenv('FACEIT_API_KEY')
BASE_URL = "https://open.faceit.com/data/v4"

async def get_faceit_data(endpoint: str):
    """Pomocnicza funkcja do zapytań API"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/{endpoint}", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None

async def get_player_stats(nickname: str):
    """Pobiera podstawowe info o graczu (ELO, Level)"""
    dane = await get_faceit_data(f"players?nickname={nickname}")
    if not dane: return None
    
    player_id = dane.get("player_id")
    cs2_dane = dane.get("games", {}).get("cs2", {})
    
    # Pobierzmy też Lifetime z drugiej ścieżki
    lifetime_dane = await get_faceit_data(f"players/{player_id}/stats/cs2")
    lifetime = lifetime_dane.get("lifetime", {}) if lifetime_dane else {}
    
    return {
        "player_id": player_id,
        "nick": dane.get("nickname"),
        "poziom": cs2_dane.get("skill_level", "Brak"),
        "elo": cs2_dane.get("faceit_elo", "Brak"),
        "avatar_url": dane.get("avatar") or "https://i.imgur.com/vHq100B.png",
        "url_profilu": f"https://www.faceit.com/pl/players/{dane.get('nickname')}",
        "lifetime_clutches": int(lifetime.get("Total 1v1 Wins", 0)) + int(lifetime.get("Total 1v2 Wins", 0)),
        "lifetime_entry": lifetime.get("Total Entry Wins", "0"),
        "lifetime_hs": lifetime.get("Average Headshots %", "0"),
        "lifetime_winrate": lifetime.get("Win Rate %", "0"),
        "lifetime_kd": lifetime.get("Average K/D Ratio", "0"),
        "lifetime_adr": lifetime.get("ADR", "0"),
        "lifetime_matches": lifetime.get("Matches", "0"),
        "lifetime_wins": lifetime.get("Wins", "0"),
        "lifetime_winstreak": lifetime.get("Current Win Streak", "0")
    }

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
                        "mapa": rs.get("Map", "Brak danych"),
                        "wynik": rs.get("Score", "Brak danych"),
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
                        "entry_wins": float(ps.get("First Kills", 0)),  # Można z First Kills albo Entry Wins
                        "hltv": round(hltv_rating, 2)
                    }
    return None

async def get_multiple_matches_stats(player_id: str, limit: int = 30):
    historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit={limit}")
    if not historia or not historia.get("items"): 
        return []
        
    items = historia.get("items", [])
    
    async def fetch_single(match_id):
        return await get_faceit_data(f"matches/{match_id}/stats")
        
    wyniki = await asyncio.gather(*(fetch_single(item["match_id"]) for item in items))
    
    podsumowanie = []
    # Parsowanie danych pod kątem konkretnego gracza
    for mecz_dane in wyniki:
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
                            "hltv": round(hltv_rating, 2)
                        })
    return podsumowanie

async def get_map_segments(player_id: str):
    """Pobiera zestawienie map gracza"""
    dane = await get_faceit_data(f"players/{player_id}/stats/cs2")
    if not dane: return []
    return dane.get("segments", [])