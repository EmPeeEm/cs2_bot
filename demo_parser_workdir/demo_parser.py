# utils/demo_parser.py
#
# Moduł odpowiedzialny za pobieranie demek z Faceit i parsowanie ich
# w celu obliczenia zaawansowanych statystyk meczu.
#
# Wymagania:
#   pip install demoparser2 requests
#
# Funkcja główna: parse_demo_for_player(demo_url, player_steam_id) -> dict | None

import os
import gzip
import shutil
import asyncio
import logging
import tempfile
import pandas as pd

logger = logging.getLogger(__name__)

# --- Ustawienia ---
# Limit czasu oczekiwania na dema (w sekundach od zakończenia meczu).
# Faceit potrzebuje do ~3 minut na wygenerowanie dema.
DEMO_WAIT_TIMEOUT_S = 180
DEMO_WAIT_INTERVAL_S = 20

# Okno czasowe (sekundy) dla uznania kill'a za "trade" (pomszczenie śmierci kolegi/drużynowego)
TRADE_WINDOW_S = 2.0

# -----------------------------------------------------------------------
# Utilities do pobierania pliku dema
# -----------------------------------------------------------------------

def _is_demoparser2_available() -> bool:
    """Sprawdza czy biblioteka demoparser2 jest dostępna."""
    try:
        import demoparser2  # noqa: F401
        return True
    except ImportError:
        return False


def _check_dns(hostname: str) -> bool:
    """Szybki test DNS – zwraca True jeśli hostname resolwuje się poprawnie."""
    import socket
    try:
        socket.getaddrinfo(hostname, 443)
        return True
    except socket.gaierror:
        return False


def _download_demo_sync(url: str, dest_path: str) -> bool:
    """
    Synchroniczne pobieranie pliku dema przy użyciu urllib.request (stdlib).
    Uruchamiana w thread pool – nie blokuje event loop.
    """
    import urllib.request
    import ssl
    import urllib.parse

    # Hack: Podmiana zepsutego hosta Faceit CDN na bezpośredni adres B2 podany przez usera
    if "demos-europe-central.backblaze.faceit-cdn.net" in url:
        logger.info("Podmieniam zepsuty host Faceit na bezpośredni host Backblaze B2.")
        url = url.replace(
            "demos-europe-central.backblaze.faceit-cdn.net",
            "demos-europe-central-faceit-cdn.s3.eu-central-003.backblazeb2.com"
        )

    # Sprawdzamy DNS przed próbą połączenia (szybki fail zamiast 2-minutowego timeout)
    hostname = urllib.parse.urlparse(url).hostname or ""
    logger.info(f"Pobieranie dema z: {url}")
    if not _check_dns(hostname):
        logger.error(
            f"Faceit CDN DNS nie działa dla hosta: {hostname}\n"
            f"  Pełny URL: {url}\n"
            f"  To jest problem po stronie Faceit CDN – brak rekordu DNS."
        )
        return False

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={"User-Agent": "cs2-discord-bot/1.0"})
        with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
            if response.status != 200:
                logger.warning(f"Demo download HTTP {response.status}: {url}")
                return False
            with open(dest_path, "wb") as f:
                shutil.copyfileobj(response, f, length=256 * 1024)
        return True
    except urllib.error.HTTPError as e:
        logger.error(f"Błąd pobierania dema (HTTP {e.code}): {url}")
        if e.code == 401:
            logger.error("Dostęp do dema wymaga autoryzacji (401 Unauthorized). Bucket Faceit może być prywatny.")
        return False
    except Exception as e:
        logger.error(f"Błąd pobierania dema: {e}")
        return False


def _decompress_zst(zst_path: str, out_path: str) -> bool:
    """Rozpakowuje plik .dem.zst (Zstandard) -> .dem."""
    try:
        import zstandard as zstd
        with open(zst_path, "rb") as f_in:
            dctx = zstd.ZstdDecompressor()
            with open(out_path, "wb") as f_out:
                dctx.copy_stream(f_in, f_out)
        return True
    except ImportError:
        # Fallback: zstandard nie zainstalowany, spróbuj przez subprocess
        import subprocess
        try:
            result = subprocess.run(
                ["zstd", "-d", zst_path, "-o", out_path, "--force"],
                capture_output=True, timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Błąd dekompresji .zst: {e}")
            return False
    except Exception as e:
        logger.error(f"Błąd dekompresji .zst: {e}")
        return False



def _decompress_gz(gz_path: str, out_path: str) -> bool:
    """Rozpakowuje plik .dem.gz -> .dem. Zwraca True jeśli sukces."""
    try:
        with gzip.open(gz_path, "rb") as f_in:
            with open(out_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return True
    except Exception as e:
        logger.error(f"Błąd dekompresji dema: {e}")
        return False


# -----------------------------------------------------------------------
# Logika obliczania statystyk
# -----------------------------------------------------------------------

def _compute_kast(kills_df, deaths_df, assists_df, rounds_total: int, player_steam_id: str) -> float:
    """Oblicza % rund K/A/S/T."""
    kast_rounds = set()
    
    # K - Kills (wykluczamy tylko samobójstwa)
    player_kills = kills_df[
        (kills_df["attacker_steamid"] == player_steam_id) &
        (kills_df["user_steamid"] != player_steam_id)
    ]
    if not player_kills.empty:
        kast_rounds.update(player_kills["total_rounds_played"].astype(int).tolist())
        
    # A - Assists
    player_assists = assists_df[assists_df["assister_steamid"] == player_steam_id]
    if not player_assists.empty:
        kast_rounds.update(player_assists["total_rounds_played"].astype(int).tolist())
        
    # --- S: rundy, w których gracz przeżył ---
    # Znajdujemy rundy, w których gracz zginął
    player_deaths = deaths_df[deaths_df["user_steamid"] == player_steam_id]
    rounds_died = set(player_deaths["total_rounds_played"].astype(int).tolist())
    
    # Wszystkie rundy w meczu (0-indexed)
    all_rounds = set(range(0, rounds_total))
    survived_rounds = all_rounds - rounds_died
    kast_rounds.update(survived_rounds)

    # --- T: rundy, w których gracz zginął, ale został pomszczony ---
    player_deaths = deaths_df[deaths_df["user_steamid"] == player_steam_id]
    for _, death_row in player_deaths.iterrows():
        runda = death_row["total_rounds_played"]
        death_tick = death_row["tick"]
        # Czy ktoś z drużyny gracza zabił jego zabójcę w oknie TRADE_WINDOW_S?
        killer_steamid = death_row.get("attacker_steamid")
        if killer_steamid is None:
            continue

        # Pobieramy zgony zabójcy gracza w tej samej rundzie, po śmierci gracza
        # (tick rate CS2 = 64, więc TRADE_WINDOW_S * 64 ticków)
        trade_window_ticks = TRADE_WINDOW_S * 64
        avenge_kills = kills_df[
            (kills_df["total_rounds_played"] == runda) &
            (kills_df["user_steamid"] == killer_steamid) &
            (kills_df["tick"] > death_tick) &
            (kills_df["tick"] <= death_tick + trade_window_ticks)
        ]
        if not avenge_kills.empty:
            kast_rounds.add(runda)

    # print(f"DEBUG: KAST for {player_steam_id}: rounds_total={rounds_total}, K={len(player_kills)}, A={len(player_assists)}, S={len(survived_rounds)}")
    kast_count = len(kast_rounds)
    res = round(kast_count / rounds_total * 100, 1) if rounds_total > 0 else 0.0
    # print(f"DEBUG: KAST result={res}")
    return res


def _compute_trading_stats(kills_df, deaths_df, player_steam_id: str, player_team_id) -> dict:
    """
    Oblicza statystyki tradingowe:
    - traded_kills: ile razy gracz zabił wroga w oknie TRADE_WINDOW_S po śmierci kolegi
    - traded_deaths: ile razy gracz zginął i był pomszczony przez kolegę
    """
    trade_window_ticks = TRADE_WINDOW_S * 64
    traded_kills = 0
    traded_deaths = 0

    # Traded kills: gracz zabił kogoś po tym, jak kolega zginął w oknie czasu
    player_kills = kills_df[kills_df["attacker_steamid"] == player_steam_id]
    for _, kill_row in player_kills.iterrows():
        kill_tick = kill_row["tick"]
        kill_round = kill_row["total_rounds_played"]
        # Czy jakiś kolega zginął chwilę przed tym w tej samej rundzie?
        teammate_deaths = deaths_df[
            (deaths_df["total_rounds_played"] == kill_round) &
            (deaths_df["user_team_num"] == player_team_id) &
            (deaths_df["user_steamid"] != player_steam_id) &
            (deaths_df["tick"] >= kill_tick - trade_window_ticks) &
            (deaths_df["tick"] < kill_tick)
        ]
        if not teammate_deaths.empty:
            traded_kills += 1

    # Traded deaths: gracz zginął i kolega pomszcza go w oknie
    player_deaths = deaths_df[deaths_df["user_steamid"] == player_steam_id]
    for _, death_row in player_deaths.iterrows():
        death_tick = death_row["tick"]
        death_round = death_row["total_rounds_played"]
        killer_id = death_row.get("attacker_steamid")
        if killer_id is None:
            continue
        # Czy kolega zabił zabójcę w oknie TRADE_WINDOW_S?
        avenge = kills_df[
            (kills_df["total_rounds_played"] == death_round) &
            (kills_df["user_steamid"] == killer_id) &
            (kills_df["attacker_team_num"] == player_team_id) &
            (kills_df["tick"] > death_tick) &
            (kills_df["tick"] <= death_tick + trade_window_ticks)
        ]
        if not avenge.empty:
            traded_deaths += 1

    return {"traded_kills": traded_kills, "traded_deaths": traded_deaths}


def _compute_opening_duels(kills_df, deaths_df, player_steam_id: str, rounds_total: int) -> dict:
    """
    Oblicza udział gracza w pierwszych pojedynkach rundy (opening duels).
    Zwraca:
    - opening_kills: ile razy gracz zanotował pierwszy kill rundy
    - opening_deaths: ile razy gracz zginął jako pierwszy w rundzie  
    - opening_win_rate: skuteczność w %
    """
    opening_kills = 0
    opening_deaths = 0

    for runda in range(1, rounds_total + 1):
        round_kills = kills_df[kills_df["total_rounds_played"] == runda].sort_values("tick")
        if round_kills.empty:
            continue
        first_kill = round_kills.iloc[0]
        if first_kill["attacker_steamid"] == player_steam_id:
            opening_kills += 1
        elif first_kill["user_steamid"] == player_steam_id:
            opening_deaths += 1

    total = opening_kills + opening_deaths
    win_rate = round(opening_kills / total * 100, 1) if total > 0 else 0.0

    return {
        "opening_kills": opening_kills,
        "opening_deaths": opening_deaths,
        "opening_win_rate": win_rate
    }


def _compute_utility_stats(grenades_df, player_steam_id: str) -> dict:
    """
    Oblicza statystyki utility:
    - flash_blind_duration_avg: średni czas oślepienia przeciwnika przez flash gracza (s)
    - flash_blind_enemies: łączna liczba oślepionych wrogów
    - he_damage_avg: średnie obrażenia HE na granat
    """
    # Flashbangi - zdarzenia 'player_blind'
    player_flashes = grenades_df[
        (grenades_df["type"] == "flashbang") &
        (grenades_df["attacker_steamid"] == player_steam_id) &
        (grenades_df["blind_duration"] > 0.5)  # Ignorujemy krótkie mignięcia
    ]

    flash_blind_enemies = len(player_flashes)
    flash_blind_duration_avg = 0.0
    if not player_flashes.empty:
        flash_blind_duration_avg = round(player_flashes["blind_duration"].mean(), 2)

    # HE grenades - zdarzenia 'he_grenade_detonate'
    player_he = grenades_df[
        (grenades_df["type"] == "he_grenade") &
        (grenades_df["attacker_steamid"] == player_steam_id)
    ]
    he_damage_avg = 0.0
    if not player_he.empty and "damage" in player_he.columns:
        he_damage_avg = round(player_he["damage"].mean(), 1)

    return {
        "flash_blind_enemies": flash_blind_enemies,
        "flash_blind_duration_avg": flash_blind_duration_avg,
        "he_damage_avg": he_damage_avg,
    }


# -----------------------------------------------------------------------
# Główna funkcja parsująca
# -----------------------------------------------------------------------

def _parse_demo_sync(dem_path: str, player_steam_id: int) -> dict | None:
    """
    Synchroniczna funkcja parsująca plik .dem przy użyciu demoparser2.
    Uruchamiana w executorze thread pool (nie blokuje event loop asyncio).
    """
    try:
        from demoparser2 import DemoParser
        import pandas as pd
    except ImportError:
        logger.error("demoparser2 lub pandas nie są zainstalowane. Uruchom: pip install demoparser2 pandas")
        return None

    try:
        parser = DemoParser(dem_path)

        # Pobieramy zdarzenia
        kills_df = parser.parse_event("player_death", player=[
            "team_num"
        ], other=["total_rounds_played"])

        # Asysty – filtrujemy z kills_df gdzie assister_steamid to nasz gracz
        assists_df = kills_df[kills_df["assister_steamid"].notna()].copy()

        # Zejścia gracza
        deaths_df = kills_df.copy()

        # Zdarzenia z granatami
        try:
            blind_df = parser.parse_event("player_blind", player=["team_num"],
                                          other=["total_rounds_played"])
            if not blind_df.empty:
                blind_df["type"] = "flashbang"
        except Exception:
            blind_df = None

        try:
            he_df = parser.parse_event("player_hurt", player=["team_num"],
                                        other=["total_rounds_played"])
            if not he_df.empty:
                he_df = he_df[he_df["weapon"] == "hegrenade"].copy()
                he_df = he_df.rename(columns={"dmg_health": "damage"})
                he_df["type"] = "he_grenade"
        except Exception:
            he_df = None

        # Łączymy dane granatów
        grenades_parts = [df for df in [blind_df, he_df] if df is not None and not df.empty]
        if grenades_parts:
            grenades_df = pd.concat(grenades_parts, ignore_index=True)
        else:
            grenades_df = pd.DataFrame()

        # Liczba rund - pobieramy z kills_df, zakładając 0-indexing
        if kills_df.empty:
            rounds_total = 1
        else:
            rounds_total = int(kills_df["total_rounds_played"].max()) + 1
        
        # Pobieramy ticki zakończenia rund, aby odfiltrować zdarzenia "po czasie" (exit frags itp.)
        # KAST i inne staty meczowe liczą się tylko do momentu zakończenia rundy.
        try:
            round_ends = parser.parse_event("round_end")
            # Mapujemy runda -> tick_zakonczenia
            # W CS2 'total_rounds_played' w kills_df odpowiada zazwyczaj 'round' w round_end
            round_end_map = dict(zip(round_ends["round"], round_ends["tick"]))
        except:
            round_end_map = {}

        def filter_mid_round(df):
            if df.empty or not round_end_map: return df
            def is_mid_round(row):
                r = row.get("total_rounds_played")
                if r in round_end_map:
                    return row["tick"] <= round_end_map[r]
                return True
            return df[df.apply(is_mid_round, axis=1)].copy()

        kills_df = filter_mid_round(kills_df)
        assists_df = kills_df[kills_df["assister_steamid"].notna()].copy()
        deaths_df = kills_df.copy() # Bo deaths to po prostu wszystkie wpisy w player_death

        # Zapewniamy, że steam ID jest traktowane jako string
        player_steam_id_str = str(player_steam_id)
        
        for col in ["attacker_steamid", "user_steamid", "assister_steamid"]:
            if col in kills_df.columns:
                kills_df[col] = kills_df[col].astype(str)
        if grenades_df is not None and not grenades_df.empty:
            if "user_steamid" in grenades_df.columns:
                grenades_df["user_steamid"] = grenades_df["user_steamid"].astype(str)
            if "attacker_steamid" in grenades_df.columns:
                grenades_df["attacker_steamid"] = grenades_df["attacker_steamid"].astype(str)

        # Pobieramy team_id gracza (konieczne do statystyk tradingowych)
        player_rows = kills_df[kills_df["attacker_steamid"] == player_steam_id_str]
        player_team_id = player_rows["attacker_team_num"].iloc[0] if not player_rows.empty else None

        # Obliczamy statystyki
        kast = _compute_kast(kills_df, deaths_df, assists_df, rounds_total, player_steam_id_str)
        trading = _compute_trading_stats(kills_df, deaths_df, player_steam_id_str, player_team_id)
        opening = _compute_opening_duels(kills_df, deaths_df, player_steam_id_str, rounds_total)
        utility = _compute_utility_stats(grenades_df, player_steam_id_str) if not grenades_df.empty else {
            "flash_blind_enemies": 0, "flash_blind_duration_avg": 0.0, "he_damage_avg": 0.0
        }

        return {
            "kast": kast,
            **trading,
            **opening,
            **utility,
        }

    except Exception as e:
        logger.error(f"Błąd parsowania dema: {e}", exc_info=True)
        return None


def _parse_all_players_sync(dem_path: str) -> dict | None:
    """
    Parsuje demo i zwraca statystyki dla WSZYSTKICH graczy znalezionych w meczu.
    Zwraca słownik: { steam_id: { "name": nick, "stats": {...} } }
    """
    try:
        from demoparser2 import DemoParser
        import pandas as pd
    except ImportError:
        return None

    try:
        parser = DemoParser(dem_path)
        
        # Pobieramy zdarzenia (to samo co w _parse_demo_sync, ale dla wszystkich)
        kills_df = parser.parse_event("player_death", player=["team_num"], other=["total_rounds_played"])
        
        # 1. Pobieramy wszystkie zdarzenia jednym wywołaniem dla wydajności
        event_names = [
            "begin_new_match", "round_announce_match_start", "round_end", 
            "player_death", "weapon_fire", "player_hurt", "player_blind"
        ]
        all_events_list = parser.parse_events(event_names, player=["team_num"], other=["total_rounds_played"])
        all_events = {name: df for name, df in all_events_list}

        # 2. Znajdujemy start meczu
        m_starts = all_events.get("begin_new_match", pd.DataFrame())
        if m_starts.empty:
            m_starts = all_events.get("round_announce_match_start", pd.DataFrame())
        match_start_tick = m_starts["tick"].max() if not m_starts.empty else 0

        # 3. Filtrujemy zdarzenia i budujemy mapę rund
        r_ends = all_events.get("round_end", pd.DataFrame()).sort_values("tick")
        match_r_ends = r_ends[r_ends["tick"] >= match_start_tick].copy()
        
        # 3. Filtrujemy zdarzenia i budujemy mapę rund
        r_ends = all_events.get("round_end", pd.DataFrame()).sort_values("tick")
        match_r_ends = r_ends[r_ends["tick"] >= match_start_tick].copy()
        
        # Mapa: runda -> tick końca tej rundy
        # W CS2 round_end zdarza się GDY runda się kończy, a total_rounds_played to liczba rund JUŻ skończonych.
        # Więc dla rundy 0, round_end ma total_rounds_played = 1.
        round_limits = {}
        for _, row in match_r_ends.iterrows():
            r_num = int(row["total_rounds_played"])
            round_limits[r_num - 1] = row["tick"]

        def is_in_round(row):
            r_num = int(row["total_rounds_played"])
            limit = round_limits.get(r_num)
            # Jeśli nie mamy limitu dla tej rundy (np. ostatnia runda meczu), pozwalamy na wszystko
            return limit is None or row["tick"] <= (limit + 64) # 1s bufora na animację wybuchu/koniec

        # Pobieramy zdarzenia meczowe
        all_deaths = all_events.get("player_death", pd.DataFrame())
        all_deaths = all_deaths[all_deaths["tick"] >= match_start_tick].copy()
        
        # Filtrujemy kille/asysty (wykluczamy fragi po czasie)
        valid_kills = all_deaths[all_deaths.apply(is_in_round, axis=1)].copy()
        
        hurt_df = all_events.get("player_hurt", pd.DataFrame())
        fire_df = all_events.get("weapon_fire", pd.DataFrame())
        
        # 4. Stan końcowy
        max_tick = r_ends["tick"].max() if not r_ends.empty else 0
        tick_props = ["kills_total", "deaths_total", "assists_total", "mvps", "score", "crosshair_code", "team_num", "steamid", "name"]
        ticks_df = parser.parse_ticks(tick_props, ticks=[max_tick])
        
        players_info = {}
        for _, row in ticks_df.iterrows():
            s_id = str(row["steamid"])
            if s_id and s_id != "nan":
                players_info[s_id] = {
                    "name": row["name"],
                    "team": row["team_num"],
                    "crosshair": row.get("crosshair_code", ""),
                    "score": int(row.get("score", 0)),
                    "kills": int(row.get("kills_total", 0)),
                    "deaths": int(row.get("deaths_total", 0)),
                    "assists": int(row.get("assists_total", 0)),
                    "mvps": int(row.get("mvps", 0))
                }

        rounds_total = len(round_limits)
        if rounds_total == 0: rounds_total = 1

        results = {}
        for s_id, info in players_info.items():
            # KAST
            assists_df = valid_kills[valid_kills["assister_steamid"].astype(str) == s_id].copy()
            kast = _compute_kast(valid_kills, all_deaths, assists_df, rounds_total, s_id)
            
            # Celność i Headshoty
            p_fire = fire_df[fire_df["user_steamid"].astype(str) == s_id]
            p_hits = hurt_df[(hurt_df["attacker_steamid"].astype(str) == s_id) & (hurt_df["user_steamid"].astype(str) != s_id)]
            shots_count = len(p_fire)
            hits_count = len(p_hits)
            
            # W CS2 hitgroup 1 to zazwyczaj Head. Sprawdzamy oba typy (str/int)
            hs_hits = len(p_hits[p_hits["hitgroup"].astype(str).isin(["1", "head"])]) if not p_hits.empty else 0

            accuracy = round(hits_count / shots_count * 100, 1) if shots_count > 0 else 0.0
            hs_ratio = round(hs_hits / hits_count * 100, 1) if hits_count > 0 else 0.0

            # --- Statystyki do Ratingu 2.0 ---
            p_kills = valid_kills[valid_kills["attacker_steamid"].astype(str) == s_id]
            p_deaths = all_deaths[all_deaths["user_steamid"].astype(str) == s_id]
            
            # ADR (Damage)
            p_damage_df = hurt_df[(hurt_df["attacker_steamid"].astype(str) == s_id) & 
                                 (hurt_df["user_steamid"].astype(str) != s_id)]
            # Filtrujemy obrażenia po czasie (tak jak kille)
            p_damage_df = p_damage_df[p_damage_df.apply(is_in_round, axis=1)]
            total_damage = p_damage_df["dmg_health"].sum() if not p_damage_df.empty else 0
            adr = round(total_damage / rounds_total, 1) if rounds_total > 0 else 0.0

            # KPR, DPR, AssistPR (używamy valid_stats dla spójności z Ratingiem)
            p_kills_count = len(p_kills)
            # Pamiętamy, że all_deaths to niefiltrowane zgony dla przetrwania, ale dla DPR HLTV używa mid-round deaths.
            valid_p_deaths = p_deaths[p_deaths.apply(is_in_round, axis=1)]
            p_deaths_count = len(valid_p_deaths)
            p_assists_count = len(assists_df)
            
            kpr = p_kills_count / rounds_total if rounds_total > 0 else 0.0
            dpr = p_deaths_count / rounds_total if rounds_total > 0 else 0.0
            apr = p_assists_count / rounds_total if rounds_total > 0 else 0.0

            # Impact Rating (Approximation: 2.13*KPR + 0.42*AssistPR - 0.41)
            impact = max(0, 2.13 * kpr + 0.42 * apr - 0.41)
            
            # Rating 2.0 (Formula provided by user)
            # 0.0073*KAST + 0.3591*KPR + -0.5329*DPR + 0.2372*Impact + 0.0032*ADR + 0.1587
            rating = (0.0073 * kast) + (0.3591 * kpr) + (-0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr) + 0.1587
            rating = round(rating, 2)

            # Multi-kills
            round_kills = p_kills.groupby("total_rounds_played").size()
            mk_rounds = len(round_kills[round_kills >= 2])
            mk_pct = round(mk_rounds / rounds_total * 100, 1) if rounds_total > 0 else 0.0

            # RS (Rounds Survived) - oparte na niefiltrowanych zgonach (all_deaths)
            rs = rounds_total - len(p_deaths["total_rounds_played"].unique())

            results[s_id] = {
                "name": info["name"],
                "stats": {
                    "rating": rating,
                    "impact": round(impact, 2),
                    "kast": kast,
                    "adr": adr,
                    "accuracy": accuracy,
                    "hs_accuracy": hs_ratio,
                    "shots": shots_count,
                    "hits": hits_count,
                    "mk_rounds": mk_rounds,
                    "mk_pct": mk_pct,
                    "rounds_survived": rs,
                    "total_rounds": rounds_total,
                    "crosshair_code": info["crosshair"],
                    "kills": p_kills_count,  # Zmieniamy na filtrowane dla spójności
                    "deaths": p_deaths_count,
                    "assists": p_assists_count,
                    "mvps": info["mvps"],
                    "score": info["score"],
                    **_compute_trading_stats(valid_kills, valid_kills, s_id, info["team"])
                }
            }
        
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Błąd _parse_all_players_sync: {e}")
        return None


async def parse_demo_all_players(demo_path: str) -> dict | None:
    """Async wrapper dla _parse_all_players_sync."""
    if not _is_demoparser2_available(): return None
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _parse_all_players_sync, demo_path)


async def parse_demo_for_player(demo_url: str, player_steam_id: int | str) -> dict | None:
    """
    Główna funkcja do wywołania z bota.
    """
    if not _is_demoparser2_available():
        logger.warning("demoparser2 nie jest zainstalowany.")
        return None

    player_steam_id = str(player_steam_id)
    tmp_dir = tempfile.mkdtemp(prefix="cs2_demo_")
    gz_path = os.path.join(tmp_dir, "demo.dem.gz")
    dem_path = os.path.join(tmp_dir, "demo.dem")

    try:
        loop = asyncio.get_running_loop()
        downloaded = await loop.run_in_executor(None, _download_demo_sync, demo_url, gz_path)
        if not downloaded: return None
        
        # Dekompresja
        await loop.run_in_executor(None, _decompress_zst, gz_path, dem_path)
        
        # Parsowanie wszystkich
        all_stats = await parse_demo_all_players(dem_path)
        if all_stats and player_steam_id in all_stats:
            return all_stats[player_steam_id]["stats"]
        return None
    except Exception as e:
        logger.error(f"Błąd w parse_demo_for_player: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)



def _is_gzip(path: str) -> bool:
    """Sprawdza nagłówek pliku czy jest to gzip."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"\x1f\x8b"
    except Exception:
        return False
