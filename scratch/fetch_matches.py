
import asyncio
from utils.faceit_api import get_player_id, get_multiple_matches_stats

async def main():
    nickname = "EmPeeEm27"
    p_id = await get_player_id(nickname)
    if not p_id:
        print(f"Player {nickname} not found.")
        return
    
    # Pobieramy historię najpierw, żeby mieć match_id
    from utils.faceit_api import get_faceit_data
    historia = await get_faceit_data(f"players/{p_id}/history?game=cs2&offset=0&limit=6")
    if not historia or not historia.get("items"):
        print("No matches found.")
        return
    
    from utils.faceit_api import get_last_match_stats
    print(f"Ostatnie 6 meczy dla {nickname}:\n")
    for item in historia["items"]:
        match_id = item["match_id"]
        # Używamy istniejącej funkcji get_last_match_stats, ale musimy ją lekko zmodyfikować lub wywołać sprytnie
        # Właściwie możemy po prostu pobrać staty dla tego konkretnego match_id
        staty_meczu = await get_faceit_data(f"matches/{match_id}/stats")
        if not staty_meczu: continue
        
        for runda in staty_meczu.get("rounds", []):
            for team in runda.get("teams", []):
                for player in team.get("players", []):
                    if player["player_id"] == p_id:
                        ps = player["player_stats"]
                        rs = runda.get("round_stats", {})
                        res = "WYGRANA" if ps.get("Result") == "1" else "PRZEGRANA"
                        print(f"Match ID: {match_id}")
                        print(f"Mapa: {rs.get('Map')} | Wynik: {rs.get('Score')} | Rezultat: {res}")
                        print(f"K/D: {ps.get('K/D Ratio')} | ADR: {ps.get('ADR')} | HS: {ps.get('Headshots %')}%")
                        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
