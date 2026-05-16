
import asyncio
from utils.faceit_api import get_faceit_data

async def main():
    match_id = "1-0d784a14-0f2e-4cfa-95fa-befd430d5adc"
    details = await get_faceit_data(f"matches/{match_id}")
    if details:
        print(f"Match ID: {match_id}")
        print(f"Started at: {details.get('started_at')}")
        print(f"Finished at: {details.get('finished_at')}")
        # print(details) # Zakomentowane, żeby nie śmiecić, ale sprawdźmy te dwa pola
    else:
        print("Match not found.")

if __name__ == "__main__":
    asyncio.run(main())
