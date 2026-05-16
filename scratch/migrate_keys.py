# scratch/migrate_keys.py
import sqlite3
import os

DB_PATH = "data/cs2_stats.db"

MAPOWANIE = {
    "main_color": "kolor",
    "tilt_limit": "tilt",
    "kanal_eventow": "eventy",
    "kanal_sezonu": "sezon",
    "kanal_podsumowan_elo": "tydzien",
    "kanal_elo": "licznik"
}

def migrate():
    if not os.path.exists(DB_PATH):
        print("Baza danych nie istnieje.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Rozpoczynam migrację kluczy na krótkie nazwy...")

    # Pobieramy wszystkie obecne ustawienia
    cursor.execute("SELECT guild_id, key, value FROM settings")
    rows = cursor.fetchall()

    for guild_id, key, value in rows:
        if key in MAPOWANIE:
            nowy_klucz = MAPOWANIE[key]
            print(f"  [{guild_id}] {key} -> {nowy_klucz}")
            
            # Wstawiamy nowy klucz (lub nadpisujemy jeśli już istnieje)
            cursor.execute(
                "INSERT INTO settings (guild_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value",
                (guild_id, nowy_klucz, value)
            )
            
            # Usuwamy stary klucz
            cursor.execute("DELETE FROM settings WHERE guild_id = ? AND key = ?", (guild_id, key))

    conn.commit()
    conn.close()
    print("✅ Migracja zakończona sukcesem!")

if __name__ == "__main__":
    migrate()
