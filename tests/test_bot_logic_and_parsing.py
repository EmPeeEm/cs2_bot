import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Dodaj katalog główny cs2_bot do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import utils.db_sqlite as db_sqlite
import utils.database as database
import utils.faceit_api as faceit_api
from cogs.cs import CSCommands

class TestBotLogicAndParsing(unittest.TestCase):
    def setUp(self):
        """Tymczasowa baza danych dla testów logiki."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_logic.db")
        
        self.orig_db_sqlite_path = db_sqlite.DB_PATH
        self.orig_database_path = database.DB_PATH
        db_sqlite.DB_PATH = self.test_db_path
        database.DB_PATH = self.test_db_path
        
        database._settings_cache.clear()
        db_sqlite.init_db()

    def tearDown(self):
        db_sqlite.DB_PATH = self.orig_db_sqlite_path
        database.DB_PATH = self.orig_database_path
        database._settings_cache.clear()
        self.temp_dir.cleanup()

    def test_uuid_validation(self):
        """Weryfikacja sprawdzania czy identyfikator to UUID czy nick."""
        valid_uuid = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
        nickname = "NiKo_CS2"
        short_id = "12345"

        self.assertTrue(faceit_api.is_uuid(valid_uuid))
        self.assertFalse(faceit_api.is_uuid(nickname))
        self.assertFalse(faceit_api.is_uuid(short_id))

    def test_parse_identifier_with_mentions_and_nicks(self):
        """Weryfikacja parsera identyfikatorów (wzmianki Discord, nicki, autor)."""
        guild_id = 999111
        cog = CSCommands(bot=MagicMock())
        
        # Przygotuj powiązanie w bazie: discord_id -> player_id
        database.zapisz_ekipe(guild_id, {"123456789": "uuid-player-123"})

        # Mock kontekstu Discord
        ctx = MagicMock()
        ctx.guild.id = guild_id
        ctx.author.id = 123456789
        ctx.author.display_name = "DiscordUserAuthor"
        
        member_mock = MagicMock()
        member_mock.display_name = "PingedUserDisplay"
        ctx.guild.get_member.return_value = member_mock

        # 1. Przekazano wzmiankę: <@123456789>
        p_id, display_name = cog.parse_identifier(ctx, ["<@123456789>"])
        self.assertEqual(p_id, "uuid-player-123")
        self.assertEqual(display_name, "PingedUserDisplay")

        # 2. Przekazano czysty nick Faceit: "m0NESY"
        p_id, display_name = cog.parse_identifier(ctx, ["m0NESY"])
        self.assertEqual(p_id, "m0NESY")
        self.assertEqual(display_name, "m0NESY")

        # 3. Brak argumentów (domyślnie autor)
        p_id, display_name = cog.parse_identifier(ctx, [])
        self.assertEqual(p_id, "uuid-player-123")
        self.assertEqual(display_name, "DiscordUserAuthor")

        # 4. Brak argumentów z default_to_author=False
        p_id, display_name = cog.parse_identifier(ctx, [], default_to_author=False)
        self.assertIsNone(p_id)
        self.assertIsNone(display_name)

    async def _async_test_check_nick(self):
        """Weryfikacja asynchronicznego pomocnika check_nick."""
        cog = CSCommands(bot=MagicMock())
        ctx = MagicMock()
        ctx.prefix = "!"
        ctx.send = AsyncMock()

        # 1. Prawidłowy nick
        res_ok = await cog.check_nick(ctx, "s1mple")
        self.assertTrue(res_ok)
        ctx.send.assert_not_called()

        # 2. Nieznaleziony nick przy pingu
        res_fail_ping = await cog.check_nick(ctx, None, "<@999999>")
        self.assertFalse(res_fail_ping)
        self.assertIn("nie ma jeszcze połączonego konta", ctx.send.call_args[0][0])

        # 3. Brak nicku bez pingu
        ctx.send.reset_mock()
        res_fail_noparam = await cog.check_nick(ctx, None, None)
        self.assertFalse(res_fail_noparam)
        self.assertIn("Podaj nick gracza", ctx.send.call_args[0][0])

    def test_check_nick(self):
        import asyncio
        asyncio.run(self._async_test_check_nick())

    def test_level_and_elo_boundaries(self):
        """Weryfikacja przedziałów ELO dla poziomów Faceit (Level 1 - 10)."""
        poziomy = [
            (1, 0, 500), (2, 501, 750), (3, 751, 900), (4, 901, 1050),
            (5, 1051, 1200), (6, 1201, 1350), (7, 1351, 1530),
            (8, 1531, 1750), (9, 1751, 1999), (10, 2000, 99999)
        ]

        def get_calc(obecne_elo):
            for lvl, min_elo, max_elo in poziomy:
                if min_elo <= obecne_elo <= max_elo:
                    do_awansu = max_elo - obecne_elo + 1
                    do_spadku = obecne_elo - min_elo
                    return lvl, do_awansu, do_spadku
            return 10, 0, 0

        # Poziom 1 (300 ELO): 201 do awansu na lvl 2, 300 zapasu
        lvl, awans, spadek = get_calc(300)
        self.assertEqual(lvl, 1)
        self.assertEqual(awans, 201)
        self.assertEqual(spadek, 300)

        # Poziom 5 (1100 ELO): 101 do awansu na lvl 6, 49 zapasu
        lvl, awans, spadek = get_calc(1100)
        self.assertEqual(lvl, 5)
        self.assertEqual(awans, 101)
        self.assertEqual(spadek, 49)

        # Poziom 10 (2450 ELO)
        lvl, awans, spadek = get_calc(2450)
        self.assertEqual(lvl, 10)

    def test_live_matches_phases_and_halves(self):
        """Weryfikacja logiki rozpoznawania fazy meczu i połówek w live trackerze."""
        def get_half_str(status, total_rounds):
            if status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                if total_rounds <= 12:
                    return "1. połowa"
                elif total_rounds <= 24:
                    return "2. połowa"
                else:
                    return "Dogrywka (OT)"
            elif status == "PAUSED":
                return "Pauza"
            elif status == "FINISHED":
                return "Mecz zakończony"
            elif status in ["CANCELLED", "ABORTED"]:
                return "Mecz anulowany"
            else:
                return "Veto / Łączenie z serwerem"

        self.assertEqual(get_half_str("LIVE", 6), "1. połowa")
        self.assertEqual(get_half_str("LIVE", 12), "1. połowa")
        self.assertEqual(get_half_str("LIVE", 18), "2. połowa")
        self.assertEqual(get_half_str("LIVE", 24), "2. połowa")
        self.assertEqual(get_half_str("LIVE", 25), "Dogrywka (OT)")
        self.assertEqual(get_half_str("PAUSED", 10), "Pauza")
        self.assertEqual(get_half_str("FINISHED", 24), "Mecz zakończony")
        self.assertEqual(get_half_str("CANCELLED", 0), "Mecz anulowany")
        self.assertEqual(get_half_str("VOTING", 0), "Veto / Łączenie z serwerem")

if __name__ == "__main__":
    unittest.main()
