
import asyncio
from utils.faceit_api import get_faceit_data

async def main():
    player_id = "c896e72a-728f-47bd-b878-0a3a18b16d67"
    historia = await get_faceit_data(f"players/{player_id}/history?game=cs2&offset=0&limit=1")
    if historia and historia.get("items"):
        item = historia["items"][0]
        print(f"Match ID: {item.get('match_id')}")
        print(f"Finished at: {item.get('finished_at')}")
        # print(item)
    else:
        print("No history found.")

if __name__ == "__main__":
    asyncio.run(main())
