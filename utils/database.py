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
            except Exception:
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
            except Exception:
                val = domyslna
    else:
        try:
            val = getattr(config, klucz.upper(), domyslna)
        except Exception:
            val = domyslna

    # ZABEZPIECZENIE DLA KOLORÓW: Jeśli kolor jest stringiem (np. "0xffffff" lub "#ffffff"), zamień na int
    if klucz == "main_color" and isinstance(val, str):
        try:
            if val.startswith("#"):
                return int(val.replace("#", ""), 16)
            return int(val, 16) if val.startswith("0x") else int(val)
        except Exception:
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

def zapisz_historie_meczu(match_id, player_id, stats, elo, win, elo_gain=0, timestamp=None):
    """Zapisuje szczegółowe statystyki meczu do bazy."""
    import time
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Poprawka daty: UNIX timestamp dla zachowania chronologii
        m_date = timestamp if timestamp else int(time.time())

        # Dodajemy wpis do tabeli matches jeśli nie istnieje (lub aktualizujemy datę i rundy)
        cursor.execute('''
            INSERT INTO matches (match_id, map_name, score, match_date, rounds) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET 
                match_date = excluded.match_date,
                rounds = excluded.rounds
        ''', (match_id, stats.get('mapa', 'Nieznana'), stats.get('wynik', '0-0'), m_date, int(stats.get('rounds', 0))))

        # Nadpisujemy statystyki gracza korzystając z unikalnego indeksu i UPSERTu
        cursor.execute('''
            INSERT INTO match_history (
                match_id, player_id, kills, deaths, assists, adr, hltv, hs_percent, 
                elo_gain, current_elo, win, kd, kr, mvp, ud, udpr, ef, 
                clutch_1v1, clutch_1v2, entry_wins, entry_success, flash_success,
                triple_kills, quadro_kills, penta_kills, sniper_kills, sniper_kr
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, player_id) DO UPDATE SET
                kills=excluded.kills, deaths=excluded.deaths, assists=excluded.assists, 
                adr=excluded.adr, hltv=excluded.hltv, hs_percent=excluded.hs_percent, 
                elo_gain=excluded.elo_gain, current_elo=excluded.current_elo, win=excluded.win, 
                kd=excluded.kd, kr=excluded.kr, mvp=excluded.mvp, ud=excluded.ud, udpr=excluded.udpr, 
                ef=excluded.ef, clutch_1v1=excluded.clutch_1v1, clutch_1v2=excluded.clutch_1v2, 
                entry_wins=excluded.entry_wins, entry_success=excluded.entry_success, 
                flash_success=excluded.flash_success, triple_kills=excluded.triple_kills, 
                quadro_kills=excluded.quadro_kills, penta_kills=excluded.penta_kills, 
                sniper_kills=excluded.sniper_kills, sniper_kr=excluded.sniper_kr
        ''', (
            match_id, player_id, 
            int(stats.get('kille', 0)), int(stats.get('dedy', 0)), int(stats.get('asysty', 0)),
            stats.get('adr', 0), stats.get('hltv', 0), int(stats.get('hs_procent', 0)), 
            elo_gain, elo, 1 if win else 0,
            stats.get('kd', 0), stats.get('kr', 0), int(stats.get('mvp', 0)), 
            stats.get('ud', 0), stats.get('udpr', 0), int(stats.get('ef', 0)), 
            int(stats.get('clutch_1v1', 0)), int(stats.get('clutch_1v2', 0)), 
            int(stats.get('entry_wins', 0)), stats.get('entry_success', 0), stats.get('flash_success', 0),
            int(stats.get('triple_kills', 0)), int(stats.get('quadro_kills', 0)), int(stats.get('penta_kills', 0)),
            int(stats.get('sniper_kills', 0)), stats.get('sniper_kr', 0)
        ))
        
        conn.commit()

def pobierz_historie_elo(player_id, limit=20):
    """Pobiera historię ELO gracza do wykresu."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT mh.current_elo FROM match_history mh
            JOIN matches m ON mh.match_id = m.match_id
            WHERE mh.player_id = ? 
            ORDER BY m.match_date DESC LIMIT ?
        ''', (player_id, limit))
        rows = cursor.fetchall()
        # Zwracamy w kolejności chronologicznej (od najstarszego do najnowszego)
        return [row[0] for row in reversed(rows)]