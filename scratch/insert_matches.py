
import asyncio
from utils.faceit_api import get_player_id, get_faceit_data, get_player_stats
from utils.database import zapisz_historie_meczu

async def main():
    nickname = "EmPeeEm27"
    p_id = await get_player_id(nickname)
    if not p_id:
        print(f"Player {nickname} not found.")
        return
    
    # Pobieramy aktualne ELO jako punkt odniesienia
    gracz = await get_player_stats(p_id, lifetime=False)
    current_elo_now = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0

    historia = await get_faceit_data(f"players/{p_id}/history?game=cs2&offset=0&limit=6")
    if not historia or not historia.get("items"):
        print("No matches found.")
        return
    
    print(f"Inserting 6 matches for {nickname}...")
    for item in reversed(historia["items"]): # Od najstarszego, żeby historia miała sens
        match_id = item["match_id"]
        finished_at = item.get("finished_at")
        staty_meczu = await get_faceit_data(f"matches/{match_id}/stats")
        if not staty_meczu: continue
        
        for runda in staty_meczu.get("rounds", []):
            for team in runda.get("teams", []):
                for player in team.get("players", []):
                    if player["player_id"] == p_id:
                        ps = player["player_stats"]
                        rs = runda.get("round_stats", {})
                        
                        mecz_stats = {
                            "kille": float(ps.get("Kills", 0)),
                            "dedy": float(ps.get("Deaths", 0)),
                            "asysty": float(ps.get("Assists", 0)),
                            "adr": float(ps.get("ADR", 0)),
                            "hltv": 0, 
                            "hs_procent": float(ps.get("Headshots %", 0)),
                            "mapa": rs.get("Map", "Unknown"),
                            "wynik": rs.get("Score", "0-0")
                        }
                        
                        # Liczymy HLTV
                        k = mecz_stats["kille"]
                        a = mecz_stats["asysty"]
                        d = mecz_stats["dedy"]
                        score_parts = mecz_stats["wynik"].split("/")
                        total_rounds = sum(int(p.strip()) for p in score_parts) if len(score_parts) == 2 else 24
                        mecz_stats["hltv"] = round((k + 0.7 * a + (total_rounds - d) * 0.6) / total_rounds, 2) if total_rounds > 0 else 0
                        
                        win = ps.get("Result") == "1"
                        
                        try:
                            # Przekazujemy timestamp!
                            zapisz_historie_meczu(match_id, p_id, mecz_stats, current_elo_now, win, 0, finished_at)
                            print(f"Saved/Updated match {match_id} ({mecz_stats['mapa']}) with time {finished_at}")
                        except Exception as e:
                            print(f"Failed to save {match_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
