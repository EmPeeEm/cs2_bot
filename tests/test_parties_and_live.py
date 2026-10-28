import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import os
import sys

# Dodaj katalog główny cs2_bot do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import utils.faceit_api as faceit_api
from cogs.live_matches import LiveMatchesCog

class TestPartiesAndLive(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Wyczyść cache partii przed każdym testem
        faceit_api._match_parties_cache.clear()

    async def test_get_match_parties_parsing(self):
        """Weryfikacja parsowania grup/premade z endpointu v2 Faceit."""
        mock_payload = {
            "parties": [
                {
                    "partyId": "party-duo-1",
                    "users": ["player-a", "player-b"]
                },
                {
                    "partyId": "party-trio-1",
                    "users": ["player-c", "player-d", "player-e"]
                },
                {
                    "partyId": "party-solo-1",
                    "users": ["player-f"]
                }
            ],
            "teams": {
                "faction1": {
                    "roster": [
                        {"id": "player-a", "partyId": "party-duo-1"},
                        {"id": "player-b", "partyId": "party-duo-1"},
                        {"id": "player-f", "partyId": "party-solo-1"}
                    ]
                },
                "faction2": {
                    "roster": [
                        {"id": "player-c", "partyId": "party-trio-1"},
                        {"id": "player-d", "partyId": "party-trio-1"},
                        {"id": "player-e", "partyId": "party-trio-1"}
                    ]
                }
            }
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"payload": mock_payload}

        with patch("utils.faceit_api.get_curl_session", new_callable=AsyncMock) as mock_get_curl:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_resp
            mock_get_curl.return_value = mock_session

            res = await faceit_api.get_match_parties("test-match-123")

            self.assertIn("player_party", res)
            self.assertIn("party_members", res)
            self.assertIn("premades", res)

            # Sprawdzenie powiązań graczy z partyId
            self.assertEqual(res["player_party"]["player-a"], "party-duo-1")
            self.assertEqual(res["player_party"]["player-b"], "party-duo-1")
            self.assertEqual(res["player_party"]["player-c"], "party-trio-1")

            # Sprawdzenie premades (tylko grupy >= 2)
            self.assertIn("party-duo-1", res["premades"])
            self.assertIn("party-trio-1", res["premades"])
            self.assertNotIn("party-solo-1", res["premades"])

            # Sprawdzenie czy wynik jest w pamięci podręcznej (cache)
            self.assertIn("test-match-123", faceit_api._match_parties_cache)

    async def test_get_match_parties_caching(self):
        """Weryfikacja czy get_match_parties nie odpytuje sieci gdy dane są w cache."""
        faceit_api._match_parties_cache["cached-match"] = (
            {
                "player_party": {"p1": "party-1"},
                "party_members": {"party-1": ["p1", "p2"]},
                "premades": {"party-1": ["p1", "p2"]}
            },
            faceit_api.time.time()
        )

        with patch("utils.faceit_api.get_curl_session", new_callable=AsyncMock) as mock_get_curl:
            res = await faceit_api.get_match_parties("cached-match")
            mock_get_curl.assert_not_called()
            self.assertEqual(res["player_party"]["p1"], "party-1")

    async def test_get_match_details_enriches_roster_with_parties(self):
        """Weryfikacja czy get_match_details wzbogaca listę graczy o party_id."""
        mock_faceit_data = {
            "match_id": "test-enrich",
            "status": "ONGOING",
            "voting": {"map": {"pick": ["de_mirage"]}},
            "teams": {
                "faction1": {
                    "name": "Team A",
                    "roster": [{"player_id": "p1", "nickname": "Player1"}]
                },
                "faction2": {
                    "name": "Team B",
                    "roster": [{"player_id": "p2", "nickname": "Player2"}]
                }
            }
        }

        with patch("utils.faceit_api.get_faceit_data", new_callable=AsyncMock) as mock_data:
            mock_data.return_value = mock_faceit_data
            with patch("utils.faceit_api.get_match_parties", new_callable=AsyncMock) as mock_parties:
                mock_parties.return_value = {
                    "player_party": {"p1": "party-duo", "p2": "party-duo"},
                    "party_members": {"party-duo": ["p1", "p2"]},
                    "premades": {"party-duo": ["p1", "p2"]}
                }

                details = await faceit_api.get_match_details("test-enrich")
                self.assertIsNotNone(details)
                f1_p = details["teams"]["faction1"]["roster"][0]
                self.assertEqual(f1_p["party_id"], "party-duo")
                self.assertIn("parties", details)

    def test_live_matches_embed_party_roster_formatting(self):
        """Weryfikacja formatowania składów (Duo, Trio, 5-Stack, Solo) w live trackerze."""
        with patch.object(LiveMatchesCog, "live_monitor"):
            cog = LiveMatchesCog(bot=MagicMock())

            # Mock ekipy i ustawień
            with patch("cogs.live_matches.wczytaj_ekipe", return_value={"111": "p-our1", "222": "p-our2"}):
                with patch("cogs.live_matches.get_cfg", side_effect=lambda g, k, default: default):
                    # 1. Test Duo i Solo
                    roster_f1 = [
                        {"player_id": "p-our1", "nickname": "Mateusz", "game_skill_level": "10", "party_id": "party-duo"},
                        {"player_id": "p-friend", "nickname": "Kumpel", "game_skill_level": "9", "party_id": "party-duo"},
                        {"player_id": "p-solo1", "nickname": "Random1", "game_skill_level": "8", "party_id": "solo1"},
                        {"player_id": "p-solo2", "nickname": "Random2", "game_skill_level": "7", "party_id": "solo2"},
                        {"player_id": "p-solo3", "nickname": "Random3", "game_skill_level": "8", "party_id": "solo3"},
                    ]
                    # Przeciwnicy: 5-stack
                    roster_f2 = [
                        {"player_id": f"enemy{i}", "nickname": f"Enemy{i}", "game_skill_level": "10", "party_id": "full-stack"}
                        for i in range(5)
                    ]

                    mock_data = {
                        "our_players": [("111", "p-our1")],
                        "details": {
                            "status": "LIVE",
                            "mapa": "Mirage",
                            "faceit_url": "https://faceit.com/test",
                            "score": {"faction1": 5, "faction2": 3},
                            "parties": {
                                "player_party": {"p-our1": "party-duo", "p-friend": "party-duo"}
                            },
                            "teams": {
                                "faction1": {"name": "Team Our", "roster": roster_f1, "stats": {}},
                                "faction2": {"name": "Team Enemy", "roster": roster_f2, "stats": {}}
                            }
                        }
                    }

                    embed, view = cog._build_single_match_embed("guild-1", "m1", mock_data)
                    self.assertIsNotNone(embed)
                    
                    # Sprawdź pole składów
                    sklady_field = None
                    for f in embed.fields:
                        if "Składy drużyn" in f.name:
                            sklady_field = f.value
                    self.assertIsNotNone(sklady_field)
                    
                    # Drużyna nasza ma Duo i Solo
                    self.assertIn("👥 **Duo:**", sklady_field)
                    self.assertIn("**Mateusz**", sklady_field)
                    self.assertIn("Kumpel", sklady_field)
                    self.assertIn("👤 **Solo:**", sklady_field)
                    # Drużyna przeciwna ma 5-Stack
                    self.assertIn("🔥 **5-Stack:**", sklady_field)

    def test_live_matches_our_players_synergy_and_duel(self):
        """Weryfikacja wykrywania wspólnego Duo/Trio oraz pojedynku klubowego."""
        with patch.object(LiveMatchesCog, "live_monitor"):
            cog = LiveMatchesCog(bot=MagicMock())

            # Test 1: Dwóch naszych graczy gra razem w Duo
            with patch("cogs.live_matches.wczytaj_ekipe", return_value={"111": "p-our1", "222": "p-our2"}):
                with patch("cogs.live_matches.get_cfg", side_effect=lambda g, k, default: default):
                    data_duo = {
                        "our_players": [("111", "p-our1"), ("222", "p-our2")],
                        "details": {
                            "status": "LIVE",
                            "mapa": "Inferno",
                            "score": {"faction1": 2, "faction2": 2},
                            "parties": {
                                "player_party": {"p-our1": "shared-party", "p-our2": "shared-party"}
                            },
                            "teams": {
                                "faction1": {
                                "name": "Team Nasi",
                                "roster": [
                                    {"player_id": "p-our1", "nickname": "Gracz1", "party_id": "shared-party"},
                                    {"player_id": "p-our2", "nickname": "Gracz2", "party_id": "shared-party"}
                                ]
                            },
                            "faction2": {"name": "Team Wrogi", "roster": []}
                        }
                    }
                }
                embed_duo, _ = cog._build_single_match_embed("guild-1", "m_duo", data_duo)
                info_field = embed_duo.fields[0].value
                self.assertIn("<@111>", info_field)
                self.assertIn("<@222>", info_field)
                self.assertIn("wspólne Duo", info_field)

                # Test 2: Pojedynek (jeden w faction1, drugi w faction2)
                data_duel = {
                    "our_players": [("111", "p-our1"), ("222", "p-our2")],
                    "details": {
                        "status": "LIVE",
                        "mapa": "Dust2",
                        "score": {"faction1": 7, "faction2": 7},
                        "parties": {"player_party": {}},
                        "teams": {
                            "faction1": {
                                "name": "Team A",
                                "roster": [{"player_id": "p-our1", "nickname": "Gracz1"}]
                            },
                            "faction2": {
                                "name": "Team B",
                                "roster": [{"player_id": "p-our2", "nickname": "Gracz2"}]
                            }
                        }
                    }
                }
                embed_duel, _ = cog._build_single_match_embed("guild-1", "m_duel", data_duel)
                info_duel = embed_duel.fields[0].value
                self.assertIn("⚔️", info_duel)
                self.assertIn("pojedynek klubowy", info_duel)

if __name__ == "__main__":
    unittest.main()
