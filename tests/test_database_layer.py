import os
import sys
import tempfile
import unittest
import sqlite3

# Dodaj katalog główny cs2_bot do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import utils.db_sqlite as db_sqlite
import utils.database as database

class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        """Utwórz izolowaną tymczasową bazę danych SQLite dla każdego testu."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_cs2_stats.db")
        
        # Przekieruj DB_PATH w modułach
        self.orig_db_sqlite_path = db_sqlite.DB_PATH
        self.orig_database_path = database.DB_PATH
        db_sqlite.DB_PATH = self.test_db_path
        database.DB_PATH = self.test_db_path
        
        # Wyczyść cache ustawień
        database._settings_cache.clear()
        
        # Zainicjalizuj strukturę bazy danych
        db_sqlite.init_db()

    def tearDown(self):
        """Przywróć oryginalne ścieżki i usuń tymczasowy katalog."""
        db_sqlite.DB_PATH = self.orig_db_sqlite_path
        database.DB_PATH = self.orig_database_path
        database._settings_cache.clear()
        self.temp_dir.cleanup()

    def test_schema_initialization_and_tables(self):
        """Weryfikacja czy init_db tworzy wszystkie wymagane tabele i indeksy."""
        with db_sqlite.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row["name"] for row in cursor.fetchall()}
            
            expected_tables = {
                "guild_players",
                "matches",
                "match_history",
                "streaks",
                "last_match_state",
                "settings",
                "seasons"
            }
            for table in expected_tables:
                self.assertIn(table, tables, f"Tabela {table} nie została utworzona!")

    def test_guild_players_crud(self):
        """Weryfikacja operacji na ekipie serwera (guild_players)."""
        guild_id = "test_guild_100"
        
        # 1. Pusta ekipa na starcie
        ekipa = database.wczytaj_ekipe(guild_id)
        self.assertEqual(ekipa, {})

        # 2. Zapisanie graczy
        nowa_ekipa = {
            "discord_1": "player_id_1",
            "discord_2": "player_id_2"
        }
        database.zapisz_ekipe(guild_id, nowa_ekipa)

        # 3. Odczyt ekipy
        wczytana = database.wczytaj_ekipe(guild_id)
        self.assertEqual(wczytana, nowa_ekipa)

        # 4. Usunięcie jednego gracza i ponowny odczyt
        del nowa_ekipa["discord_1"]
        database.zapisz_ekipe(guild_id, nowa_ekipa)
        wczytana_po_usunieciu = database.wczytaj_ekipe(guild_id)
        self.assertEqual(wczytana_po_usunieciu, {"discord_2": "player_id_2"})

        # 5. Izolacja pomiędzy serwerami (inny guild_id)
        inna_ekipa = database.wczytaj_ekipe("inna_gildia_200")
        self.assertEqual(inna_ekipa, {})

    def test_settings_caching_and_defaults(self):
        """Weryfikacja pamięci podręcznej ustawień oraz pobierania domyślnych wartości (get_cfg)."""
        guild_id = "test_guild_settings"

        # 1. Domyślne wartości gdy brak w bazie
        prefix = database.get_cfg(guild_id, "prefix", "!")
        self.assertEqual(prefix, "!")

        # 2. Zapisanie własnych ustawień
        nowe_ustawienia = {
            "prefix": "?",
            "tilt_limit": 5,
            "main_color": 0xFF0000
        }
        database.zapisz_ustawienia(guild_id, nowe_ustawienia)

        # 3. Odczyt przez get_cfg i wczytaj_ustawienia
        self.assertEqual(database.get_cfg(guild_id, "prefix", "!"), "?")
        self.assertEqual(database.get_cfg(guild_id, "tilt_limit", 3), 5)
        self.assertEqual(database.get_cfg(guild_id, "main_color", 0), 0xFF0000)

        # 4. Sprawdzenie czy cache działa
        self.assertIn(str(guild_id), database._settings_cache)

        # 5. Unieważnienie cache i ponowny odczyt
        database.uniewaznij_cache_ustawien(guild_id)
        self.assertNotIn(str(guild_id), database._settings_cache)
        odczyt_po_uniewaznieniu = database.wczytaj_ustawienia(guild_id)
        self.assertEqual(odczyt_po_uniewaznieniu.get("prefix"), "?")

    def test_seasons_lifecycle(self):
        """Weryfikacja cyklu życia sezonu (start, odczyt, aktualizacja ID wiadomości)."""
        guild_id = "test_guild_season"

        # 1. Brak sezonu na starcie
        s = database.wczytaj_sezon(guild_id)
        self.assertEqual(s, {})

        # 2. Utworzenie sezonu
        sezon_dane = {
            "nazwa": "Sezon Zimowy 2026",
            "start_elo": {
                "player_1": 1500,
                "player_2": 2100
            }
        }
        database.zapisz_sezon(guild_id, sezon_dane)

        # 3. Odczyt sezonu
        odczytany = database.wczytaj_sezon(guild_id)
        self.assertEqual(odczytany["nazwa"], "Sezon Zimowy 2026")
        self.assertEqual(odczytany["start_elo"]["player_1"], 1500)
        self.assertEqual(odczytany["start_elo"]["player_2"], 2100)

        # 4. Aktualizacja ID wiadomości tabeli
        database.zaktualizuj_leaderboard_msg_id(guild_id, 123456789, 987654321)
        po_aktualizacji = database.wczytaj_sezon(guild_id)
        self.assertEqual(po_aktualizacji["leaderboard_msg_id"], 123456789)
        self.assertEqual(po_aktualizacji["leaderboard_channel_id"], 987654321)

    def test_tilt_streaks_storage(self):
        """Weryfikacja zapisu i odczytu passy zwycięstw/porażek (tilt)."""
        # 1. Pusta baza tilt
        tilt = database.wczytaj_tilt()
        self.assertEqual(tilt, {})

        # 2. Zapis serii graczy
        nowy_tilt = {
            "pid_winstreak": 4,
            "pid_lossstreak": -3,
            "pid_zero": 0
        }
        database.zapisz_tilt(nowy_tilt)

        # 3. Odczyt
        odczytany_tilt = database.wczytaj_tilt()
        self.assertEqual(odczytany_tilt.get("pid_winstreak"), 4)
        self.assertEqual(odczytany_tilt.get("pid_lossstreak"), -3)
        self.assertEqual(odczytany_tilt.get("pid_zero"), 0)

    def test_match_history_and_elo_graph_queries(self):
        """Weryfikacja zapisu historii meczu i pobierania historii ELO do wykresów."""
        match_id_1 = "m-001"
        player_id = "test-player-uuid"
        
        mecz_stats_1 = {
            "mapa": "de_mirage",
            "wynik": "13-8",
            "kille": 22,
            "dedy": 14,
            "asysty": 5,
            "adr": 92.5,
            "hltv": 1.35,
            "hs_procent": 55,
            "rounds": 21
        }
        
        # 1. Zapis pierwszego meczu
        database.zapisz_historie_meczu(
            match_id=match_id_1,
            player_id=player_id,
            stats=mecz_stats_1,
            elo=1620,
            win=True,
            elo_gain=25,
            timestamp=1700000000
        )

        # 2. Zapis drugiego meczu
        match_id_2 = "m-002"
        mecz_stats_2 = {
            "mapa": "de_inferno",
            "wynik": "11-13",
            "kille": 18,
            "dedy": 17,
            "asysty": 3,
            "adr": 78.0,
            "hltv": 0.98,
            "hs_procent": 40,
            "rounds": 24
        }
        database.zapisz_historie_meczu(
            match_id=match_id_2,
            player_id=player_id,
            stats=mecz_stats_2,
            elo=1595,
            win=False,
            elo_gain=-25,
            timestamp=1700003600
        )

        # 3. Pobranie historii ELO (lista intów dla wykresu)
        historia_elo = database.pobierz_historie_elo(player_id, limit=10)
        self.assertEqual(historia_elo, [1620, 1595])

        # 4. Pobranie szczegółowych meczów z bazy
        mecze_z_bazy = database.pobierz_mecze_z_bazy(player_id, limit=10)
        self.assertEqual(len(mecze_z_bazy), 2)
        # Najnowszy mecz pierwszy
        self.assertEqual(mecze_z_bazy[0]["current_elo"], 1595)
        self.assertEqual(mecze_z_bazy[0]["mapa"], "de_inferno")
        self.assertEqual(mecze_z_bazy[1]["current_elo"], 1620)
        self.assertEqual(mecze_z_bazy[1]["mapa"], "de_mirage")

if __name__ == "__main__":
    unittest.main()
