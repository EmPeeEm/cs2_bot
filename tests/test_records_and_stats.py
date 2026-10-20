import os
import sys
import tempfile
import unittest

# Dodaj katalog główny cs2_bot do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import utils.db_sqlite as db_sqlite
import utils.database as database
import cogs.records as records_module

class TestRecordsAndStats(unittest.TestCase):
    def setUp(self):
        """Utwórz izolowaną tymczasową bazę danych SQLite dla każdego testu."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_records.db")
        
        # Przekieruj DB_PATH
        self.orig_db_sqlite_path = db_sqlite.DB_PATH
        self.orig_database_path = database.DB_PATH
        self.orig_records_path = records_module.DB_PATH
        
        db_sqlite.DB_PATH = self.test_db_path
        database.DB_PATH = self.test_db_path
        records_module.DB_PATH = self.test_db_path
        
        database._settings_cache.clear()
        db_sqlite.init_db()

    def tearDown(self):
        """Przywróć oryginalne ścieżki i usuń tymczasowy katalog."""
        db_sqlite.DB_PATH = self.orig_db_sqlite_path
        database.DB_PATH = self.orig_database_path
        records_module.DB_PATH = self.orig_records_path
        database._settings_cache.clear()
        self.temp_dir.cleanup()

    def test_extract_new_value(self):
        """Weryfikacja wyciągania wartości metryk z payloadu statystyk."""
        cog = records_module.RecordsCog(None)
        
        sample_stats = {
            "kille": 28,
            "hltv": 1.45,
            "ud": 120.0,
            "dedy": 19
        }
        
        self.assertEqual(cog.extract_new_value("max_kills", sample_stats), 28)
        self.assertEqual(cog.extract_new_value("min_kills", sample_stats), 28)
        self.assertAlmostEqual(cog.extract_new_value("max_hltv", sample_stats), 1.45)
        self.assertAlmostEqual(cog.extract_new_value("min_hltv", sample_stats), 1.45)
        self.assertAlmostEqual(cog.extract_new_value("max_ud", sample_stats), 120.0)
        self.assertEqual(cog.extract_new_value("max_deaths", sample_stats), 19)
        self.assertIsNone(cog.extract_new_value("max_winstreak", sample_stats))

    def test_extreme_values_and_record_holders(self):
        """Weryfikacja obliczania rekordów MAX/MIN oraz listy ich posiadaczy."""
        guild_id = "guild_test_records"
        p1 = "pid_gracz1"
        p2 = "pid_gracz2"
        
        # Dodajemy obu graczy do ekipy
        database.zapisz_ekipe(guild_id, {"discord_p1": p1, "discord_p2": p2})
        
        # Mecz 1: Gracz 1 robi 30 killi, HLTV 1.60
        mecz1_stats = {
            "mapa": "de_mirage",
            "wynik": "13-7",
            "kille": 30,
            "dedy": 10,
            "asysty": 4,
            "adr": 115.0,
            "hltv": 1.60,
            "hs_procent": 60,
            "rounds": 20
        }
        database.zapisz_historie_meczu("m1", p1, mecz1_stats, elo=1800, win=True, timestamp=1700000000)
        
        # Mecz 2: Gracz 2 robi 25 killi, HLTV 1.20
        mecz2_stats = {
            "mapa": "de_anubis",
            "wynik": "13-11",
            "kille": 25,
            "dedy": 18,
            "asysty": 6,
            "adr": 85.0,
            "hltv": 1.20,
            "hs_procent": 45,
            "rounds": 24
        }
        database.zapisz_historie_meczu("m2", p2, mecz2_stats, elo=1650, win=True, timestamp=1700003600)
        
        # 1. Sprawdzamy max_kills dla gildii
        max_k = records_module.get_extreme_value(guild_id, "max_kills")
        self.assertEqual(max_k, 30)

        # 2. Sprawdzamy max_kills wykluczając mecz m1
        prev_k = records_module.get_extreme_value_excluding(guild_id, "max_kills", "m1")
        self.assertEqual(prev_k, 25)

        # 3. Posiadacz rekordu 30 killi
        holders = records_module.get_record_holders(guild_id, "max_kills", 30)
        self.assertEqual(len(holders), 1)
        self.assertEqual(holders[0]["discord_id"], "discord_p1")
        self.assertEqual(holders[0]["map_name"], "de_mirage")
        self.assertEqual(holders[0]["score"], "13-7")

        # 4. Sprawdzamy min_kills
        min_k = records_module.get_extreme_value(guild_id, "min_kills")
        self.assertEqual(min_k, 25)

        # 5. Sprawdzamy max_hltv
        max_h = records_module.get_extreme_value(guild_id, "max_hltv")
        self.assertAlmostEqual(max_h, 1.60)

    def test_overtime_filter_ignores_non_regulation_matches(self):
        """Weryfikacja czy mecze spoza zakresu 13-24 rund (np. dogrywki 29 rund) nie psują bazy rekordów regulaminowych."""
        guild_id = "guild_ot_test"
        p1 = "pid_ot_player"
        database.zapisz_ekipe(guild_id, {"discord_ot": p1})

        # Mecz z dogrywką: 45 killi, ale 36 rund (poza zakresem regulaminowym 13-24)
        mecz_ot_stats = {
            "mapa": "de_dust2",
            "wynik": "19-17",
            "kille": 45,
            "dedy": 25,
            "asysty": 8,
            "adr": 120.0,
            "hltv": 1.75,
            "hs_procent": 50,
            "rounds": 36
        }
        database.zapisz_historie_meczu("m_ot", p1, mecz_ot_stats, elo=1700, win=True, timestamp=1700000000)

        # Powinno zwrócić None, ponieważ mecz miał 36 rund
        max_k = records_module.get_extreme_value(guild_id, "max_kills")
        self.assertIsNone(max_k)

    def test_streak_records_computation(self):
        """Weryfikacja poprawnego liczenia rekordowych serii wygranych i przegranych."""
        guild_id = "guild_streak_test"
        p1 = "pid_streak_1"
        p2 = "pid_streak_2"
        database.zapisz_ekipe(guild_id, {"discord_s1": p1, "discord_s2": p2})

        # Gracz 1: 3 wygrane z rzędu, potem 1 porażka, potem 1 wygrana
        m1_base = {"mapa": "de_mirage", "wynik": "13-5", "kille": 20, "dedy": 10, "rounds": 18}
        database.zapisz_historie_meczu("str_m1", p1, m1_base, elo=1500, win=True, timestamp=1700001000)
        database.zapisz_historie_meczu("str_m2", p1, m1_base, elo=1525, win=True, timestamp=1700002000)
        database.zapisz_historie_meczu("str_m3", p1, m1_base, elo=1550, win=True, timestamp=1700003000)
        database.zapisz_historie_meczu("str_m4", p1, m1_base, elo=1525, win=False, timestamp=1700004000)
        database.zapisz_historie_meczu("str_m5", p1, m1_base, elo=1550, win=True, timestamp=1700005000)

        # Gracz 2: 2 porażki z rzędu
        database.zapisz_historie_meczu("str_m6", p2, m1_base, elo=1400, win=False, timestamp=1700006000)
        database.zapisz_historie_meczu("str_m7", p2, m1_base, elo=1375, win=False, timestamp=1700007000)

        streaks = records_module.get_streak_records(guild_id)
        
        # Max winstreak dla gildii powinien wynosić 3 (Gracz 1)
        max_w_val, w_holders = streaks["max_winstreak"]
        self.assertEqual(max_w_val, 3)
        self.assertEqual(len(w_holders), 1)
        self.assertEqual(w_holders[0]["discord_id"], "discord_s1")

        # Max lossstreak dla gildii powinien wynosić 2 (Gracz 2)
        max_l_val, l_holders = streaks["max_lossstreak"]
        self.assertEqual(max_l_val, 2)
        self.assertEqual(len(l_holders), 1)
        self.assertEqual(l_holders[0]["discord_id"], "discord_s2")

if __name__ == "__main__":
    unittest.main()
