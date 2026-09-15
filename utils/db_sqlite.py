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
            status TEXT DEFAULT 'finished',
            rounds INTEGER
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
            kd REAL,
            kr REAL,
            mvp INTEGER,
            ud REAL,
            udpr REAL,
            ef INTEGER,
            clutch_1v1 INTEGER,
            clutch_1v2 INTEGER,
            entry_wins INTEGER,
            entry_success REAL,
            flash_success REAL,
            triple_kills INTEGER,
            quadro_kills INTEGER,
            penta_kills INTEGER,
            sniper_kills INTEGER,
            sniper_kr REAL,
            FOREIGN KEY (match_id) REFERENCES matches (match_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_pid ON match_history(player_id)')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_history_unique ON match_history(match_id, player_id)')

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
            archive_data TEXT,
            leaderboard_msg_id TEXT,
            leaderboard_channel_id TEXT
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
    migrate_schema()
    logger.info("Baza danych zoptymalizowana i gotowa.")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Funkcja do migracji (dodawania kolumn do istniejącej bazy)
def migrate_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Utworzenie unikalnego indeksu chroniącego przed duplikatami
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_history_unique ON match_history(match_id, player_id)')
    
    # Lista kolumn do dodania (tabela, kolumna, definicja)
    updates = [
        ("matches", "status", "TEXT DEFAULT 'finished'"),
        ("matches", "rounds", "INTEGER"),
        ("streaks", "last_updated", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("last_match_state", "last_check", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("match_history", "kd", "REAL"),
        ("match_history", "kr", "REAL"),
        ("match_history", "mvp", "INTEGER"),
        ("match_history", "ud", "REAL"),
        ("match_history", "udpr", "REAL"),
        ("match_history", "ef", "INTEGER"),
        ("match_history", "clutch_1v1", "INTEGER"),
        ("match_history", "clutch_1v2", "INTEGER"),
        ("match_history", "entry_wins", "INTEGER"),
        ("match_history", "entry_success", "REAL"),
        ("match_history", "flash_success", "REAL"),
        ("match_history", "triple_kills", "INTEGER"),
        ("match_history", "quadro_kills", "INTEGER"),
        ("match_history", "penta_kills", "INTEGER"),
        ("match_history", "sniper_kills", "INTEGER"),
        ("match_history", "sniper_kr", "REAL"),
        ("seasons", "leaderboard_msg_id", "TEXT"),
        ("seasons", "leaderboard_channel_id", "TEXT")
    ]
    
    for table, col, definition in updates:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            print(f"✅ Dodano kolumnę {col} do tabeli {table}")
        except sqlite3.OperationalError:
            # Kolumna już istnieje
            pass

    # Naprawa tekstowych dat (fallbacków) w tabeli matches
    cursor.execute("SELECT match_id, match_date FROM matches WHERE typeof(match_date) = 'text'")
    text_dates = cursor.fetchall()
    for m_id, m_date in text_dates:
        try:
            # Sprawdźmy, czy wygląda jak format datetime
            if "-" in m_date and ":" in m_date:
                # Ograniczamy do pierwszych 19 znaków "YYYY-MM-DD HH:MM:SS" zeby uniknąć różnic w milisekundach
                dt_str = m_date[:19]
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                unix_ts = int(dt.timestamp())
                cursor.execute("UPDATE matches SET match_date = ? WHERE match_id = ?", (unix_ts, m_id))
                print(f"🔧 Naprawiono tekstową datę meczu: {m_id}")
        except Exception as e:
            logger.error(f"Nie udało się naprawić daty dla {m_id}: {e}")

    # Automatyczna migracja i rekonstrukcja danych archiwalnych dla starych sezonów
    try:
        migrate_legacy_seasons(cursor)
    except Exception as e:
        logger.error(f"Błąd podczas migracji starych sezonów: {e}")

    conn.commit()
    conn.close()

def migrate_legacy_seasons(cursor):
    """
    Automatycznie normalizuje i uzupełnia archive_data dla historycznych sezonów.
    1. Konwertuje starszy format dict {'wyniki': [...]} na list [...].
    2. Dla sezonów bez archive_data rekonstruuje ranking z delty start_elo pomiędzy sezonami.
    """
    cursor.execute('SELECT guild_id, discord_id, player_id, nickname FROM guild_players')
    gp_rows = cursor.fetchall()
    p_to_d = {r[2]: r[1] for r in gp_rows}
    p_to_nick = {r[2]: (r[3] or r[1]) for r in gp_rows}
    d_to_nick = {r[1]: (r[3] or r[1]) for r in gp_rows}

    cursor.execute('SELECT id, guild_id, name, is_active, start_elo, archive_data FROM seasons ORDER BY id ASC')
    seasons = cursor.fetchall()

    for idx, (s_id, g_id, name, is_active, start_elo_raw, arch_raw) in enumerate(seasons):
        if name in ['123', 'test']:
            continue
            
        # Przypadek 1: archive_data to stary format dict ze słownikiem 'wyniki'
        if arch_raw:
            try:
                arch_parsed = json.loads(arch_raw)
                if isinstance(arch_parsed, dict) and 'wyniki' in arch_parsed and arch_parsed['wyniki']:
                    wyniki = arch_parsed['wyniki']
                    cursor.execute('UPDATE seasons SET archive_data = ? WHERE id = ?', (json.dumps(wyniki), s_id))
                    print(f"🔧 [MIGRACJA] Znormalizowano stary format archive_data dla sezonu '{name}' (ID: {s_id})")
                    continue
            except Exception:
                pass

        # Przypadek 2: Brak archive_data lub puste {}, ale jest start_elo i sezon jest zakończony
        if not is_active and start_elo_raw:
            try:
                arch_parsed = json.loads(arch_raw) if arch_raw else None
                has_archive = bool(arch_parsed and (
                    (isinstance(arch_parsed, list) and len(arch_parsed) > 0) or 
                    (isinstance(arch_parsed, dict) and bool(arch_parsed.get('wyniki')))
                ))
                if not has_archive:
                    s_start = json.loads(start_elo_raw)
                    next_start = None
                    for next_s in seasons[idx+1:]:
                        if str(next_s[1]) == str(g_id) and next_s[4]:
                            try:
                                next_start = json.loads(next_s[4])
                                if next_start:
                                    break
                            except Exception:
                                pass
                    
                    if s_start and next_start:
                        reconstructed = []
                        for p_key, elo_start in s_start.items():
                            d_id = p_to_d.get(p_key, p_key)
                            elo_end = next_start.get(p_key, next_start.get(d_id, elo_start))
                            progres = elo_end - elo_start
                            nick = d_to_nick.get(d_id, p_to_nick.get(p_key, d_id))
                            poziom = 10 if elo_end >= 2001 else (9 if elo_end >= 1751 else (8 if elo_end >= 1531 else (7 if elo_end >= 1351 else (6 if elo_end >= 1201 else (5 if elo_end >= 1051 else (4 if elo_end >= 901 else 3))))))
                            reconstructed.append({
                                'discord_id': str(d_id),
                                'nick': nick,
                                'progres': int(progres),
                                'obecne': int(elo_end),
                                'poziom': poziom
                            })
                        reconstructed.sort(key=lambda x: x['progres'], reverse=True)
                        cursor.execute('UPDATE seasons SET archive_data = ? WHERE id = ?', (json.dumps(reconstructed), s_id))
                        print(f"🔧 [MIGRACJA] Zrekonstruowano brakujące archive_data dla sezonu '{name}' (ID: {s_id})")
            except Exception as e:
                logger.error(f"Błąd podczas rekonstrukcji sezonu {s_id}: {e}")

if __name__ == "__main__":
    init_db()
    migrate_schema()
