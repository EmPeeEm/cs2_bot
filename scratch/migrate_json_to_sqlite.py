# scratch/migrate_json_to_sqlite.py
import json
import sqlite3
import os
import sys

# Dodaj ścieżkę główną bota do sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_sqlite import init_db, DB_PATH

def migrate():
    print("🚀 Rozpoczynam migrację danych z JSON do SQLite...")
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Migracja ekipy (ekipa.json)
    if os.path.exists("data/ekipa.json"):
        with open("data/ekipa.json", "r", encoding="utf-8") as f:
            dane = json.load(f)
            gracze = dane.get("gracze", {})
            for d_id, p_id in gracze.items():
                cursor.execute('INSERT OR REPLACE INTO players (discord_id, player_id) VALUES (?, ?)', (d_id, p_id))
        print("✅ Przeniesiono ekipę.")

    # 2. Migracja ustawień (ustawienia.json)
    if os.path.exists("data/ustawienia.json"):
        with open("data/ustawienia.json", "r", encoding="utf-8") as f:
            ustawienia = json.load(f)
            for k, v in ustawienia.items():
                cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, json.dumps(v)))
        print("✅ Przeniesiono ustawienia.")

    # 3. Migracja streaków (tilt.json)
    if os.path.exists("data/tilt.json"):
        with open("data/tilt.json", "r", encoding="utf-8") as f:
            tilt = json.load(f)
            for p_id, streak in tilt.items():
                cursor.execute('INSERT OR REPLACE INTO streaks (player_id, current_streak) VALUES (?, ?)', (p_id, streak))
        print("✅ Przeniesiono tilt-meter.")

    # 4. Migracja stanu meczów (mecze.json)
    if os.path.exists("data/mecze.json"):
        with open("data/mecze.json", "r", encoding="utf-8") as f:
            mecze = json.load(f)
            for p_id, data in mecze.items():
                if isinstance(data, dict):
                    cursor.execute('''
                        INSERT OR REPLACE INTO last_match_state (player_id, match_id, elo, poziom, retry_count)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (p_id, data.get('match_id'), data.get('elo'), data.get('poziom'), data.get('retry_count', 0)))
        print("✅ Przeniesiono stan trackera.")

    # 5. Migracja sezonu (sezon.json)
    if os.path.exists("data/sezon.json"):
        with open("data/sezon.json", "r", encoding="utf-8") as f:
            sezon = json.load(f)
            if "nazwa" in sezon:
                cursor.execute('''
                    INSERT INTO seasons (name, is_active, start_elo)
                    VALUES (?, 1, ?)
                ''', (sezon['nazwa'], json.dumps(sezon.get('start_elo', {}))))
        print("✅ Przeniesiono aktywny sezon.")

    conn.commit()
    conn.close()
    print("\n🎉 Migracja zakończona sukcesem! Plik data/cs2_stats.db jest gotowy.")
    print("Możesz teraz usunąć stare pliki .json (ale zrób kopię na wszelki wypadek).")

if __name__ == "__main__":
    migrate()
