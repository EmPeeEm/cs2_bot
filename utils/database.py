# utils/database.py
import sqlite3
import json
import os
import datetime
import config

DB_PATH = "data/cs2_stats.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def wczytaj_ekipe(guild_id):
    """Pobiera listę graczy (Discord ID -> Faceit ID) dla danej gildii."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_id, player_id FROM guild_players WHERE guild_id = ?', (str(guild_id),))
        return {row[0]: row[1] for row in cursor.fetchall()}

def zapisz_ekipe(guild_id, ekipa):
    """Zapisuje listę graczy dla danej gildii."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM guild_players WHERE guild_id = ?', (str(guild_id),))
        for d_id, p_id in ekipa.items():
            cursor.execute('INSERT INTO guild_players (guild_id, discord_id, player_id) VALUES (?, ?, ?)', (str(guild_id), d_id, p_id))
        conn.commit()

def wczytaj_ustawienia(guild_id):
    """Pobiera ustawienia serwera."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings WHERE guild_id = ?', (str(guild_id),))
        rows = cursor.fetchall()
        ustawienia = {}
        for k, v in rows:
            try:
                ustawienia[k] = json.loads(v)
            except:
                ustawienia[k] = v
        return ustawienia

def zapisz_ustawienia(guild_id, dane):
    """Zapisuje ustawienia serwera."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for k, v in dane.items():
            cursor.execute('''
                INSERT OR REPLACE INTO settings (guild_id, key, value) 
                VALUES (?, ?, ?)
            ''', (str(guild_id), k, json.dumps(v)))
        conn.commit()

def get_cfg(guild_id, klucz, domyslna=None):
    """Pobiera ustawienie per serwer, lub globalne z config.py."""
    GLOBAL_ONLY = ["level_emojis", "level_default"]
    val = domyslna
    
    if guild_id and klucz not in GLOBAL_ONLY:
        ustawienia = wczytaj_ustawienia(guild_id)
        if klucz in ustawienia:
            val = ustawienia[klucz]
        else:
            try:
                val = getattr(config, klucz.upper(), domyslna)
            except:
                val = domyslna
    else:
        try:
            val = getattr(config, klucz.upper(), domyslna)
        except:
            val = domyslna

    # ZABEZPIECZENIE DLA KOLORÓW: Jeśli kolor jest stringiem (np. "0xffffff" lub "#ffffff"), zamień na int
    if klucz == "main_color" and isinstance(val, str):
        try:
            if val.startswith("#"):
                return int(val.replace("#", ""), 16)
            return int(val, 16) if val.startswith("0x") else int(val)
        except:
            return 0x2b2d31 # Domyślny kolor w razie błędu
            
    return val

def wczytaj_ostatnie_mecze():
    """Pobiera globalny stan ostatnio sprawdzonych meczów."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT player_id, match_id, elo, poziom, retry_count FROM last_match_state")
        rows = cursor.fetchall()
        return {row[0]: {"match_id": row[1], "elo": row[2], "poziom": row[3], "retry_count": row[4]} for row in rows}

def zapisz_ostatnie_mecze(dane):
    """Zapisuje globalny stan meczów."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for p_id, val in dane.items():
            if isinstance(val, dict):
                cursor.execute('''
                    INSERT OR REPLACE INTO last_match_state (player_id, match_id, elo, poziom, retry_count) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (p_id, val.get('match_id'), val.get('elo'), val.get('poziom'), val.get('retry_count', 0)))
            else:
                cursor.execute('INSERT OR REPLACE INTO last_match_state (player_id, match_id) VALUES (?, ?)', (p_id, val))
        conn.commit()

def wczytaj_tilt():
    """Pobiera globalny stan serii (Streaki)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT player_id, current_streak FROM streaks")
        return {row[0]: row[1] for row in cursor.fetchall()}

def zapisz_tilt(dane):
    """Zapisuje globalny stan serii."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for p_id, val in dane.items():
            cursor.execute("INSERT OR REPLACE INTO streaks (player_id, current_streak) VALUES (?, ?)", (p_id, val))
        conn.commit()

def wczytaj_sezon(guild_id):
    """Pobiera dane aktywnego sezonu gildii."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, start_elo, archive_data FROM seasons WHERE guild_id = ? AND is_active = 1", (str(guild_id),))
        row = cursor.fetchone()
        if not row: return {}
        return {
            "nazwa": row[0],
            "start_elo": json.loads(row[1]) if row[1] else {},
            "archive": json.loads(row[2]) if row[2] else {}
        }

def zapisz_sezon(guild_id, dane):
    """Zapisuje dane sezonu gildii."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Najpierw sprawdzamy czy sezon już istnieje
        cursor.execute("SELECT id FROM seasons WHERE guild_id = ? AND is_active = 1", (str(guild_id),))
        exists = cursor.fetchone()
        
        name = dane.get("nazwa", "Nowy Sezon")
        start_elo = json.dumps(dane.get("start_elo", {}))
        archive = json.dumps(dane.get("archive", {}))
        
        if exists:
            cursor.execute("UPDATE seasons SET name = ?, start_elo = ?, archive_data = ? WHERE id = ?", (name, start_elo, archive, exists[0]))
        else:
            cursor.execute("INSERT INTO seasons (guild_id, name, is_active, start_elo, archive_data) VALUES (?, ?, 1, ?, ?)", (str(guild_id), name, start_elo, archive))
        conn.commit()

def get_all_guilds_players():
    """Mapuje player_id na listę (guild_id, discord_id)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id, discord_id, player_id FROM guild_players")
        rows = cursor.fetchall()
        result = {}
        for g_id, d_id, p_id in rows:
            if p_id not in result: result[p_id] = []
            result[p_id].append((int(g_id), d_id))
        return result

def zapisz_historie_meczu(match_id, player_id, stats, elo, win):
    """Zapisuje szczegółowe statystyki meczu do bazy."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Sprawdzamy czy mecz dla tego gracza już istnieje
        cursor.execute("SELECT id FROM match_history WHERE match_id = ? AND player_id = ?", (match_id, player_id))
        if cursor.fetchone():
            return

        cursor.execute('''
            INSERT INTO match_history (
                match_id, player_id, kills, deaths, assists, 
                adr, hltv, hs_percent, elo_gain, current_elo, win
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            match_id, player_id, stats.get('kille', 0), stats.get('dedy', 0), stats.get('asysty', 0),
            stats.get('adr', 0), stats.get('hltv', 0), stats.get('hs_procent', 0),
            0, # elo_gain - na razie 0, bo wyliczamy z różnicy current_elo
            elo, 1 if win else 0
        ))
        
        # Dodajemy wpis do tabeli matches jeśli nie istnieje
        cursor.execute("INSERT OR IGNORE INTO matches (match_id, map_name, score, match_date) VALUES (?, ?, ?, ?)",
                       (match_id, stats.get('mapa', 'Nieznana'), stats.get('wynik', '0-0'), datetime.datetime.now()))
        
        conn.commit()

def pobierz_historie_elo(player_id, limit=20):
    """Pobiera historię ELO gracza do wykresu."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT current_elo, id FROM match_history 
            WHERE player_id = ? 
            ORDER BY id DESC LIMIT ?
        ''', (player_id, limit))
        rows = cursor.fetchall()
        # Zwracamy w kolejności chronologicznej (od najstarszego do najnowszego)
        return [row[0] for row in reversed(rows)]