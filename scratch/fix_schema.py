# scratch/fix_schema.py
import sqlite3
import os

DB_PATH = "data/cs2_stats.db"

def fix():
    if not os.path.exists(DB_PATH):
        print("Baza nie istnieje, nic do naprawy.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🛠️ Rozpoczynam przebudowę schematu bazy danych...")

    # 1. Naprawa tabeli players -> guild_players
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='players'")
    if cursor.fetchone()[0] == 1:
        print("Migracja tabeli players do guild_players...")
        cursor.execute("CREATE TABLE IF NOT EXISTS guild_players (guild_id TEXT, discord_id TEXT, player_id TEXT, nickname TEXT, PRIMARY KEY (guild_id, discord_id))")
        cursor.execute("INSERT INTO guild_players (guild_id, discord_id, player_id) SELECT 'GLOBAL', discord_id, player_id FROM players")
        cursor.execute("DROP TABLE players")

    # 2. Naprawa tabeli settings
    print("Przebudowa tabeli settings...")
    cursor.execute("ALTER TABLE settings RENAME TO settings_old")
    cursor.execute("CREATE TABLE settings (guild_id TEXT, key TEXT, value TEXT, PRIMARY KEY (guild_id, key))")
    cursor.execute("INSERT INTO settings (guild_id, key, value) SELECT 'GLOBAL', key, value FROM settings_old")
    cursor.execute("DROP TABLE settings_old")

    # 3. Naprawa tabeli seasons
    print("Przebudowa tabeli seasons...")
    cursor.execute("ALTER TABLE seasons RENAME TO seasons_old")
    cursor.execute("CREATE TABLE seasons (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, name TEXT, is_active INTEGER DEFAULT 0, start_elo TEXT, archive_data TEXT)")
    # Sprawdzamy czy tabela seasons_old ma stare kolumny
    cursor.execute("PRAGMA table_info(seasons_old)")
    cols = [column[1] for column in cursor.fetchall()]
    
    if 'name' in cols:
        cursor.execute("INSERT INTO seasons (guild_id, name, is_active, start_elo) SELECT 'GLOBAL', name, is_active, start_elo FROM seasons_old")
    
    cursor.execute("DROP TABLE seasons_old")

    conn.commit()
    conn.close()
    print("✅ Schemat bazy został pomyślnie zaktualizowany do wersji Multi-Guild!")

if __name__ == "__main__":
    fix()
