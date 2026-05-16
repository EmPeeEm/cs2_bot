# utils/db_sqlite.py
import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "data/cs2_stats.db"

def init_db():
    """Inicjalizuje bazę danych z obsługą wielu serwerów i optymalizacjami."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Tabela graczy na serwerach
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_players (
            guild_id TEXT,
            discord_id TEXT,
            player_id TEXT,
            nickname TEXT,
            PRIMARY KEY (guild_id, discord_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_guild ON guild_players(guild_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_pid ON guild_players(player_id)')

    # 2. Tabela meczów
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            map_name TEXT,
            score TEXT,
            match_date DATETIME,
            status TEXT DEFAULT 'finished'
        )
    ''')

    # 3. Tabela wyników
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            player_id TEXT,
            kills INTEGER,
            deaths INTEGER,
            assists INTEGER,
            adr REAL,
            hltv REAL,
            hs_percent INTEGER,
            elo_gain INTEGER,
            current_elo INTEGER,
            win INTEGER,
            FOREIGN KEY (match_id) REFERENCES matches (match_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_pid ON match_history(player_id)')

    # 4. Tabela ustawień
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            guild_id TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (guild_id, key)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_settings_guild ON settings(guild_id)')

    # 5. Tabela sezonów
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            name TEXT,
            is_active INTEGER DEFAULT 0,
            start_elo TEXT,
            archive_data TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_seasons_guild ON seasons(guild_id)')

    # 6. Tabela serii (Streaki)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streaks (
            player_id TEXT PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 7. Ostatnie mecze (Globalne)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_match_state (
            player_id TEXT PRIMARY KEY,
            match_id TEXT,
            elo INTEGER,
            poziom INTEGER,
            retry_count INTEGER DEFAULT 0,
            last_check DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Baza danych zoptymalizowana i gotowa.")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Funkcja do migracji (dodawania kolumn do istniejącej bazy)
def migrate_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Lista kolumn do dodania (tabela, kolumna, definicja)
    updates = [
        ("matches", "status", "TEXT DEFAULT 'finished'"),
        ("streaks", "last_updated", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("last_match_state", "last_check", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for table, col, definition in updates:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            print(f"✅ Dodano kolumnę {col} do tabeli {table}")
        except sqlite3.OperationalError:
            # Kolumna już istnieje
            pass
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    migrate_schema()
