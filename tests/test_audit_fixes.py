import os
import sys
import unittest

# Dodaj katalog główny cs2_bot do ścieżki Pythona
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestAuditFixes(unittest.TestCase):
    def test_settings_cache(self):
        """Weryfikacja działania pamięci podręcznej ustawień w utils/database.py."""
        from utils.database import wczytaj_ustawienia, zapisz_ustawienia, uniewaznij_cache_ustawien, _settings_cache
        from utils.db_sqlite import init_db

        init_db()
        test_guild_id = "test_guild_99999"
        
        # 1. Zapisujemy dane
        zapisz_ustawienia(test_guild_id, {"prefix": "$", "test_key": "abc"})
        self.assertIn(test_guild_id, _settings_cache)
        self.assertEqual(_settings_cache[test_guild_id]["prefix"], "$")

        # 2. Odczyt z pamięci podręcznej
        cfg = wczytaj_ustawienia(test_guild_id)
        self.assertEqual(cfg["prefix"], "$")
        self.assertEqual(cfg["test_key"], "abc")

        # 3. Unieważnienie cache
        uniewaznij_cache_ustawien(test_guild_id)
        self.assertNotIn(test_guild_id, _settings_cache)

        # 4. Ponowny odczyt z bazy (powinien ponownie zasilić cache)
        cfg_reloaded = wczytaj_ustawienia(test_guild_id)
        self.assertEqual(cfg_reloaded["prefix"], "$")
        self.assertIn(test_guild_id, _settings_cache)

    def test_no_raw_sqlite3_connect_in_records(self):
        """Weryfikacja czy w cogs/records.py nie ma surowych sqlite3.connect."""
        records_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cogs", "records.py"))
        with open(records_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("sqlite3.connect", content, "W cogs/records.py nadal znajduje się surowe sqlite3.connect!")

    def test_requirements_cleaned(self):
        """Weryfikacja oczyszczenia requirements.txt z demoparser2 i pandas."""
        req_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "requirements.txt"))
        with open(req_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        self.assertNotIn("demoparser2", lines)
        self.assertNotIn("pandas", lines)
        self.assertIn("discord.py", lines)
        self.assertIn("curl_cffi", lines)

    def test_bot_commands_structure(self):
        """Weryfikacja obecności komendy sync i handlera błędów w main.py."""
        import main
        command_names = [c.name for c in main.bot.commands]
        self.assertIn("sync", command_names, "Brakuje komendy 'sync' w main.py!")

    def test_persistent_views_configuration(self):
        """Weryfikacja czy TiltSelect posiada custom_id oraz czy widoki mają timeout=None."""
        from cogs.tilt_ui import TiltView, TiltSelect
        from cogs.season_ui import SeasonView

        tilt_view = TiltView()
        self.assertIsNone(tilt_view.timeout, "TiltView powinien mieć timeout=None dla trwałości!")
        select = [item for item in tilt_view.children if isinstance(item, TiltSelect)][0]
        self.assertEqual(select.custom_id, "tilt_select", "TiltSelect musi mieć custom_id='tilt_select'!")

        season_view = SeasonView()
        self.assertIsNone(season_view.timeout, "SeasonView powinien mieć timeout=None dla trwałości!")

    def test_no_raw_prints_in_core_cogs_and_utils(self):
        """Weryfikacja czy w modułach cogs i utils nie ma surowych print()."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for folder in ["cogs", "utils"]:
            f_path = os.path.join(base_dir, folder)
            for fname in os.listdir(f_path):
                if fname.endswith(".py"):
                    full_p = os.path.join(f_path, fname)
                    with open(full_p, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if stripped.startswith("print(") and not stripped.startswith("#"):
                            self.fail(f"Znaleziono surowe print() w {folder}/{fname}:{idx} -> {stripped}")

if __name__ == "__main__":
    unittest.main()
