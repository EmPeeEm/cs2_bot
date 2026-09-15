# cogs/live_matches.py
import discord
from discord.ext import commands, tasks
import asyncio
import time
import datetime
import config
from utils.database import wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia, get_cfg
from utils.faceit_api import get_latest_match_id, get_player_ongoing_match_id, get_match_details, get_player_stats

STATUS_LABELS = {
    "VOTING": "🟡 Faza Veto / Wybór mapy",
    "CONFIGURING": "🟠 Konfiguracja serwera",
    "READY": "🟠 Rozgrzewka / Łączenie z serwerem",
    "ON_GOING": "🔴 W trakcie meczu (LIVE)",
    "ONGOING": "🔴 W trakcie meczu (LIVE)",
    "LIVE": "🔴 W trakcie meczu (LIVE)",
    "MATCH": "🔴 W trakcie meczu (LIVE)",
    "PAUSED": "⏸️ Pauza / Mecz wstrzymany",
    "FINISHED": "🏁 Mecz zakończony",
    "CANCELLED": "❌ Mecz anulowany",
    "ABORTED": "❌ Mecz przerwany"
}

class LiveMatchView(discord.ui.View):
    def __init__(self, match_url, label="Pokój meczowy Faceit"):
        super().__init__(timeout=None)
        if match_url:
            self.add_item(discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.link,
                url=match_url,
                emoji="🎮"
            ))

class LiveMatchesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # active_matches[guild_id] = {match_id: {"details": ..., "our_players": [...], "finished_at": timestamp or None, "fail_count": 0}}
        self.active_matches = {}
        self.channel_rename_history = {} # channel_id -> list of timestamps in last 10m
        self._locks = {} # guild_id -> asyncio.Lock()
        self.live_monitor.start()

    def cog_unload(self):
        self.live_monitor.cancel()

    async def _safe_rename_channel(self, channel: discord.TextChannel, target_name: str):
        """Bezpiecznie zmienia nazwę kanału z uwzględnieniem limitu Discorda (max 2 na 10 min)."""
        channel_id = channel.id
        now = time.time()
        
        # Filtrujemy historię zmian z ostatnich 10 minut (600s)
        history = self.channel_rename_history.get(channel_id, [])
        history = [t for t in history if now - t < 610]
        self.channel_rename_history[channel_id] = history

        # Discord pozwala na maksymalnie 2 zmiany nazwy kanału na 10 minut
        if len(history) >= 2:
            return

        if channel.name == target_name:
            return

        try:
            await channel.edit(name=target_name)
            self.channel_rename_history[channel_id].append(time.time())
        except discord.Forbidden:
            print(f"⚠️ [LIVE] Bot nie ma uprawnienia 'Zarządzanie kanałami' (Manage Channels) dla kanału {channel.id}")
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"ℹ️ [LIVE] Discord rate limit (429) przy zmianie nazwy kanału {channel.id} - zignorowano, kolejna próba po upływie limitu.")
            else:
                print(f"⚠️ [LIVE] Błąd zmiany nazwy kanału {channel.id}: {e}")
        except Exception as e:
            print(f"⚠️ [LIVE] Błąd zmiany nazwy kanału {channel.id}: {e}")

    async def _fetch_guild_active_matches(self, guild_id):
        """Skanuje ekipę z danej gildii i stabilnie śledzi trwające mecze."""
        ekipa = wczytaj_ekipe(guild_id)
        if not ekipa:
            self.active_matches[guild_id] = {}
            return {}

        if guild_id not in self.active_matches:
            self.active_matches[guild_id] = {}

        current_active = self.active_matches[guild_id]
        now = time.time()
        updated_active = {}

        # 1. KROK 1: Najpierw sprawdzamy stan MECZÓW, które JUŻ SĄ ŚLEDZONE
        # Bezpośrednio pytamy o match_id, dzięki czemu nie tracimy stanu gry przy chwilowych błędach API
        for match_id, match_data in list(current_active.items()):
            try:
                details = await get_match_details(match_id)
                if details:
                    match_data["details"] = details
                    match_data["fail_count"] = 0
                    status = str(details.get("status", "")).upper()

                    # Aktualizujemy listę naszych graczy na podstawie aktualnego składu w meczu
                    our_players = []
                    for f_key in ["faction1", "faction2"]:
                        roster = details.get("teams", {}).get(f_key, {}).get("roster", [])
                        for p in roster:
                            p_id = p.get("player_id")
                            for d_id, e_pid in ekipa.items():
                                if e_pid == p_id and (d_id, p_id) not in our_players:
                                    our_players.append((d_id, p_id))
                    if our_players:
                        match_data["our_players"] = our_players

                    if status in ["FINISHED", "CANCELLED", "ABORTED"]:
                        if not match_data.get("finished_at"):
                            match_data["finished_at"] = now
                        # Trzymamy zakończony mecz przez 180 sekund (3 minuty)
                        if now - match_data["finished_at"] <= 180:
                            updated_active[match_id] = match_data
                    else:
                        match_data["finished_at"] = None
                        updated_active[match_id] = match_data
                else:
                    # Chwilowy błąd API / rate limit - zachowujemy mecz w pamięci podręcznej (do 6 ticków = ~60s)
                    fail_count = match_data.get("fail_count", 0) + 1
                    match_data["fail_count"] = fail_count
                    if fail_count <= 6:
                        updated_active[match_id] = match_data
            except Exception as e:
                print(f"⚠️ [LIVE] Błąd sprawdzania aktywnego meczu {match_id}: {e}")
                updated_active[match_id] = match_data

        # 2. KROK 2: Sprawdzamy graczy, którzy NIE SĄ w żadnym z aktualnie śledzonych meczów
        players_in_tracked = set()
        for m_data in updated_active.values():
            for _, p_id in m_data.get("our_players", []):
                players_in_tracked.add(p_id)

        for discord_id, player_id in ekipa.items():
            if player_id in players_in_tracked:
                continue

            try:
                await asyncio.sleep(0.08)
                # Sprawdzamy czy wolny gracz rozpoczął nowy mecz
                match_id = await get_player_ongoing_match_id(player_id)
                if not match_id:
                    continue

                if match_id in updated_active:
                    if (discord_id, player_id) not in updated_active[match_id]["our_players"]:
                        updated_active[match_id]["our_players"].append((discord_id, player_id))
                    players_in_tracked.add(player_id)
                    continue

                details = await get_match_details(match_id)
                if not details:
                    continue

                status = str(details.get("status", "")).upper()
                if status in ["VOTING", "CONFIGURING", "READY", "ON_GOING", "ONGOING", "LIVE", "MATCH", "PAUSED"]:
                    # Znajdujemy wszystkich graczy z naszej ekipy w tym meczu
                    our_players = []
                    for f_key in ["faction1", "faction2"]:
                        roster = details.get("teams", {}).get(f_key, {}).get("roster", [])
                        for p in roster:
                            p_id = p.get("player_id")
                            for d_id, e_pid in ekipa.items():
                                if e_pid == p_id and (d_id, p_id) not in our_players:
                                    our_players.append((d_id, p_id))

                    if not our_players:
                        our_players = [(discord_id, player_id)]

                    updated_active[match_id] = {
                        "details": details,
                        "our_players": our_players,
                        "finished_at": None,
                        "fail_count": 0
                    }
                    for _, p_id in our_players:
                        players_in_tracked.add(p_id)
            except Exception as e:
                print(f"⚠️ [LIVE] Błąd podczas sprawdzania gracza {player_id}: {e}")

        self.active_matches[guild_id] = updated_active
        return updated_active

    def _build_idle_embed(self, guild_id):
        """Buduje embed informujący o braku aktywnych gier."""
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        embed = discord.Embed(
            title="🟢 MECZE NA ŻYWO: Brak aktywnych gier",
            description="*Żaden z zarejestrowanych graczy nie rozgrywa obecnie meczu na Faceicie.*\n\n"
                        "Gdy ktoś rozpocznie mecz, oddzielna karta spotkania ze składami, ELO i wynikiem na żywo pojawi się tutaj automatycznie.",
            color=0x2ecc71
        )
        embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~10s")
        return embed

    def _build_single_match_embed(self, guild_id, match_id, data):
        """Buduje bogaty embed dedykowany pojedynczemu meczowi."""
        level_emojis = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        level_default = get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT)
        ekipa = wczytaj_ekipe(guild_id)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        now = time.time()

        details = data["details"]
        status = str(details.get("status", "UNKNOWN")).upper()
        status_text = STATUS_LABELS.get(status, f"Status: {status}")
        mapa = details.get("mapa", "W trakcie wyboru")
        
        # Gracze z naszego serwera w tym meczu
        our_mentions = [f"<@{d_id}>" for d_id, p_id in data.get("our_players", [])]
        our_str = " ".join(our_mentions) if our_mentions else "Gracze ekipy"

        # Drużyny i składy
        teams = details.get("teams", {})
        f1 = teams.get("faction1", {})
        f2 = teams.get("faction2", {})
        f1_roster = f1.get("roster", [])
        f2_roster = f2.get("roster", [])

        # Sprawdzamy, w której drużynie grają nasi gracze
        f1_our_count = sum(1 for p in f1_roster if any(e_pid == p.get("player_id") for e_pid in ekipa.values()))
        f2_our_count = sum(1 for p in f2_roster if any(e_pid == p.get("player_id") for e_pid in ekipa.values()))

        score = details.get("score", {})
        s1 = score.get("faction1", 0)
        s2 = score.get("faction2", 0)
        total_rounds = s1 + s2

        # Rozpoznanie fazy gry
        if status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
            if total_rounds <= 12:
                half_str = "1. połowa"
            elif total_rounds <= 24:
                half_str = "2. połowa"
            else:
                half_str = "Dogrywka (OT)"
        elif status == "PAUSED":
            half_str = "Pauza"
        elif status == "FINISHED":
            half_str = "Mecz zakończony"
        elif status in ["CANCELLED", "ABORTED"]:
            half_str = "Mecz anulowany"
        else:
            half_str = "Veto / Łączenie z serwerem"

        def format_roster(roster):
            formatted = []
            for p in roster[:5]:
                p_id = p.get("player_id")
                nick = str(p.get("nickname") or p.get("game_player_name") or "Gracz")[:20]
                lvl = str(p.get("game_skill_level", ""))
                emoji = level_emojis.get(lvl, level_default)
                is_our = any(e_pid == p_id for e_pid in ekipa.values())
                if is_our:
                    formatted.append(f"{emoji} **{nick}**")
                else:
                    formatted.append(f"{emoji} {nick}")
            return " • ".join(formatted) if formatted else "*Brak danych o składzie*"

        # Logika przypisania "Nasi" vs "Przeciwnicy" do wyeksponowania wyniku
        embed_color = 0xe74c3c
        if f1_our_count > 0 and f2_our_count > 0:
            # Pojedynek wewnętrzny
            t1_name = f1.get("name", "Drużyna 1")
            t2_name = f2.get("name", "Drużyna 2")
            team1_label, team2_label = f"🔹 **{t1_name}:**", f"🔸 **{t2_name}:**"
            team1_roster, team2_roster = f1_roster, f2_roster
            t1_stats, t2_stats = f1.get("stats", {}), f2.get("stats", {})

            if status in ["CANCELLED", "ABORTED"]:
                score_header = "# ❌ Mecz anulowany"
                sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                embed_color = 0x95a5a6
            elif status == "FINISHED":
                score_header = f"# 🏁 {s1} : {s2}"
                sub_badge = "⚔️ **Pojedynek klubowy** • *Koniec spotkania*"
                embed_color = 0x3498db
            elif status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                score_header = f"# 📊 {s1} : {s2}"
                sub_badge = f"⚔️ **Pojedynek klubowy** • *{half_str}*"
                embed_color = 0xe74c3c
            else:
                score_header = "# ⏳ Przed meczem"
                sub_badge = f"⚔️ **Pojedynek klubowy** • *{half_str}*"
                embed_color = 0xf39c12

        elif f2_our_count > f1_our_count and f2_our_count > 0:
            # Nasi są w faction 2
            our_team_name = f2.get("name", "Nasi")
            enemy_team_name = f1.get("name", "Przeciwnicy")
            team1_label, team2_label = f"🔹 **Nasza drużyna ({our_team_name}):**", f"🔸 **Przeciwnicy ({enemy_team_name}):**"
            team1_roster, team2_roster = f2_roster, f1_roster
            t1_stats, t2_stats = f2.get("stats", {}), f1.get("stats", {})

            if status in ["CANCELLED", "ABORTED"]:
                score_header = "# ❌ Mecz anulowany"
                sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                embed_color = 0x95a5a6
            elif status == "FINISHED":
                if s2 > s1:
                    lead_badge = f"🏆 **Zwycięstwo (+{s2 - s1})**"
                    embed_color = 0x2ecc71
                elif s2 < s1:
                    lead_badge = f"💀 **Porażka (-{s1 - s2})**"
                    embed_color = 0xe74c3c
                else:
                    lead_badge = "🤝 **Remis**"
                    embed_color = 0x95a5a6
                score_header = f"# 🏁 {s2} : {s1}"
                sub_badge = f"{lead_badge} • *Koniec spotkania*"
            elif status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                if s2 > s1:
                    lead_badge = f"🟢 **Prowadzenie (+{s2 - s1})**"
                elif s2 < s1:
                    lead_badge = f"🔴 **Strata (-{s1 - s2})**"
                else:
                    lead_badge = "🟡 **Remis**"
                score_header = f"# 📊 {s2} : {s1}"
                sub_badge = f"{lead_badge} • *{half_str}*"
                embed_color = 0xe74c3c
            else:
                score_header = "# ⏳ Przed meczem"
                sub_badge = f"🟠 **{half_str}**"
                embed_color = 0xf39c12

        else:
            # Nasi są w faction 1 (lub domyślnie)
            our_team_name = f1.get("name", "Nasi")
            enemy_team_name = f2.get("name", "Przeciwnicy")
            team1_label, team2_label = f"🔹 **Nasza drużyna ({our_team_name}):**", f"🔸 **Przeciwnicy ({enemy_team_name}):**"
            team1_roster, team2_roster = f1_roster, f2_roster
            t1_stats, t2_stats = f1.get("stats", {}), f2.get("stats", {})

            if status in ["CANCELLED", "ABORTED"]:
                score_header = "# ❌ Mecz anulowany"
                sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                embed_color = 0x95a5a6
            elif status == "FINISHED":
                if s1 > s2:
                    lead_badge = f"🏆 **Zwycięstwo (+{s1 - s2})**"
                    embed_color = 0x2ecc71
                elif s1 < s2:
                    lead_badge = f"💀 **Porażka (-{s2 - s1})**"
                    embed_color = 0xe74c3c
                else:
                    lead_badge = "🤝 **Remis**"
                    embed_color = 0x95a5a6
                score_header = f"# 🏁 {s1} : {s2}"
                sub_badge = f"{lead_badge} • *Koniec spotkania*"
            elif status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                if s1 > s2:
                    lead_badge = f"🟢 **Prowadzenie (+{s1 - s2})**"
                elif s1 < s2:
                    lead_badge = f"🔴 **Strata (-{s2 - s1})**"
                else:
                    lead_badge = "🟡 **Remis**"
                score_header = f"# 📊 {s1} : {s2}"
                sub_badge = f"{lead_badge} • *{half_str}*"
                embed_color = 0xe74c3c
            else:
                score_header = "# ⏳ Przed meczem"
                sub_badge = f"🟠 **{half_str}**"
                embed_color = 0xf39c12

        # Statystyki ELO
        t1_elo = t1_stats.get("rating")
        t2_elo = t2_stats.get("rating")
        t1_elo_str = f"{t1_elo} ELO" if t1_elo else "Brak ELO"
        t2_elo_str = f"{t2_elo} ELO" if t2_elo else "Brak ELO"

        t1_lvl = str(t1_stats.get("skillLevel", {}).get("average", ""))
        t2_lvl = str(t2_stats.get("skillLevel", {}).get("average", ""))
        t1_lvl_emoji = level_emojis.get(t1_lvl, "") if t1_lvl else ""
        t2_lvl_emoji = level_emojis.get(t2_lvl, "") if t2_lvl else ""

        t1_prob = int(round(float(t1_stats.get("winProbability", 0.5)) * 100))
        t2_prob = int(round(float(t2_stats.get("winProbability", 0.5)) * 100))

        # Czas gry
        started_at = details.get("started_at")
        configured_at = details.get("configured_at")
        if status in ["CANCELLED", "ABORTED"]:
            time_str = "Spotkanie odwołane (nierozegrane)"
        elif status == "FINISHED":
            if started_at:
                start_str = datetime.datetime.fromtimestamp(started_at).strftime("%H:%M")
                elapsed_min = int((now - started_at) // 60)
                time_str = f"Zakończony (~{elapsed_min} min gry, start: {start_str})"
            else:
                time_str = "Zakończony"
        elif started_at:
            elapsed_min = int((now - started_at) // 60)
            start_str = datetime.datetime.fromtimestamp(started_at).strftime("%H:%M")
            time_str = f"**{elapsed_min} min** (od {start_str})"
        elif configured_at:
            elapsed_min = int((now - configured_at) // 60)
            time_str = f"Rozgrzewka (od {elapsed_min} min)"
        else:
            time_str = "Veto / Przygotowanie"

        team1_roster_str = format_roster(team1_roster)
        team2_roster_str = format_roster(team2_roster)

        # Dobór tytułu embeda
        if status in ["CANCELLED", "ABORTED"]:
            embed_title = f"❌ MECZ ANULOWANY: {mapa.upper()}"
        elif status == "FINISHED":
            embed_title = f"🏁 MECZ ZAKOŃCZONY: {mapa.upper()}"
        elif status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
            embed_title = f"🔴 MECZ NA ŻYWO: {mapa.upper()}"
        elif status == "PAUSED":
            embed_title = f"⏸️ MECZ WSTRZYMANY: {mapa.upper()}"
        else:
            embed_title = f"🟠 MECZ W PRZYGOTOWANIU: {mapa.upper()}"

        embed = discord.Embed(
            title=embed_title,
            description=f"Status: **{status_text}**",
            color=embed_color
        )

        if details.get("map_image"):
            embed.set_thumbnail(url=details["map_image"])

        pole_info = (
            f"{score_header}\n"
            f"{sub_badge}\n"
            f"👥 **W meczu:** {our_str}\n\n"
            f"> ⏱️ **Czas gry:** {time_str}\n"
            f"> 📈 **Średnie ELO:** `{t1_elo_str}` {t1_lvl_emoji} ({t1_prob}%) vs `{t2_elo_str}` {t2_lvl_emoji} ({t2_prob}%)"
        )
        
        pole_sklady = (
            f"{team1_label}\n"
            f"{team1_roster_str}\n\n"
            f"{team2_label}\n"
            f"{team2_roster_str}\n\n"
            f"🔗 [Kliknij, aby otworzyć pokój meczowy Faceit]({details.get('faceit_url', '#')})"
        )
        
        if data.get("finished_at"):
            pozostalo = max(0, int(180 - (now - data["finished_at"])))
            pole_sklady += f"\n*(Karta zniknie za ~{pozostalo}s)*"

        embed.add_field(name="📊 Wynik i Informacje", value=pole_info[:1024], inline=False)
        embed.add_field(name="👥 Składy drużyn", value=pole_sklady[:1024], inline=False)
        embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~10s")

        view = LiveMatchView(details.get("faceit_url"), label=f"Pokój meczowy: {mapa}") if details.get("faceit_url") else None
        return embed, view

    async def _delete_all_tracked_messages(self, guild_id, channel, ustawienia=None):
        """Usuwa wszystkie aktywne wiadomości live (zarówno idle jak i mecze)."""
        if ustawienia is None:
            ustawienia = wczytaj_ustawienia(guild_id)

        # 1. Usuwamy idle_msg_id i stary live_msg_id
        for key in ["live_idle_msg_id", "live_msg_id"]:
            mid = ustawienia.get(key)
            if mid:
                try:
                    msg = await channel.fetch_message(int(mid))
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
                ustawienia[key] = None

        # 2. Usuwamy wiadomości poszczególnych meczów
        match_msgs = ustawienia.get("live_matches_msg_ids")
        if isinstance(match_msgs, dict):
            for mid in match_msgs.values():
                try:
                    msg = await channel.fetch_message(int(mid))
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
        ustawienia["live_matches_msg_ids"] = {}
        zapisz_ustawienia(guild_id, ustawienia)

    async def update_live_dashboard(self, guild_id):
        """Aktualizuje lub tworzy oddzielne wiadomości dla każdego trwającego meczu."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self._locks:
            self._locks[guild_id_str] = asyncio.Lock()

        lock = self._locks[guild_id_str]
        if lock.locked():
            # Jeśli poprzednia aktualizacja dla tej gildii wciąż trwa, pomijamy ten tick
            return

        async with lock:
            ustawienia = wczytaj_ustawienia(guild_id)
            kanal_id = ustawienia.get("kanal_live")
            if not kanal_id:
                return

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return

            channel = guild.get_channel(int(kanal_id))
            if not channel:
                print(f"⚠️ [LIVE] Nie znaleziono kanału o ID {kanal_id} w gildii {guild_id}")
                return

            active = await self._fetch_guild_active_matches(guild_id)

            # Aktualizacja nazwy kanału w tle (🔴 tylko gdy mecz trwa, 🟢 gdy brak lub zakończony)
            try:
                has_live = any(
                    str(m["details"].get("status", "")).upper() not in ["FINISHED", "CANCELLED", "ABORTED"]
                    for m in active.values()
                )
                target_emoji = "🔴" if has_live else "🟢"
                current_name = channel.name
                clean_name = current_name
                for em in ["🔴", "🟢"]:
                    if clean_name.startswith(em):
                        clean_name = clean_name[len(em):]
                        break
                clean_name = clean_name.lstrip("・-—_ ")
                if not clean_name:
                    clean_name = "mecze-live"
                target_name = f"{target_emoji}・{clean_name}"

                if current_name != target_name:
                    asyncio.create_task(self._safe_rename_channel(channel, target_name))
            except Exception as e:
                print(f"⚠️ [LIVE] Błąd przygotowania zmiany nazwy kanału {channel.id}: {e}")

            live_matches_msg_ids = ustawienia.get("live_matches_msg_ids")
            if not isinstance(live_matches_msg_ids, dict):
                live_matches_msg_ids = {}

            idle_msg_id = ustawienia.get("live_idle_msg_id") or ustawienia.get("live_msg_id")

            if not active:
                # BRAK AKTYWNYCH MECZÓW
                # 1. Usuwamy wszelkie pozostałe wiadomości meczowe
                for m_id, m_msg_id in list(live_matches_msg_ids.items()):
                    try:
                        old_msg = await channel.fetch_message(int(m_msg_id))
                        await old_msg.delete()
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        print(f"⚠️ [LIVE] Nie udało się usunąć starej wiadomości meczu {m_id}: {e}")
                live_matches_msg_ids = {}

                # 2. Wyświetlamy lub aktualizujemy wiadomość stanu czuwania (idle)
                idle_embed = self._build_idle_embed(guild_id)
                if idle_msg_id:
                    try:
                        idle_msg = await channel.fetch_message(int(idle_msg_id))
                        await idle_msg.edit(embed=idle_embed, view=None)
                    except discord.NotFound:
                        try:
                            new_idle = await channel.send(embed=idle_embed)
                            idle_msg_id = new_idle.id
                        except Exception as e:
                            print(f"⚠️ [LIVE] Błąd wysyłania nowej wiadomości idle: {e}")
                    except discord.HTTPException as e:
                        # Chwilowy błąd Discorda (np. rate limit/500) - nie duplikujemy wiadomości
                        print(f"⚠️ [LIVE] Chwilowy błąd edycji wiadomości idle: {e}")
                else:
                    try:
                        new_idle = await channel.send(embed=idle_embed)
                        idle_msg_id = new_idle.id
                    except Exception as e:
                        print(f"⚠️ [LIVE] Błąd wysyłania wiadomości idle: {e}")

            else:
                # SĄ AKTYWNE MECZE (oddzielne wiadomości per mecz)
                # 1. Usuwamy wiadomość czuwania (idle)
                if idle_msg_id:
                    try:
                        idle_msg = await channel.fetch_message(int(idle_msg_id))
                        await idle_msg.delete()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass
                    idle_msg_id = None

                # 2. Usuwamy wiadomości meczów, które już nie są śledzone
                for m_id in list(live_matches_msg_ids.keys()):
                    if m_id not in active:
                        old_mid = live_matches_msg_ids.pop(m_id)
                        try:
                            old_msg = await channel.fetch_message(int(old_mid))
                            await old_msg.delete()
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            pass

                # 3. Dla każdego meczu aktualizujemy lub tworzymy osobną wiadomość
                for match_id, match_data in active.items():
                    embed, view = self._build_single_match_embed(guild_id, match_id, match_data)
                    m_msg_id = live_matches_msg_ids.get(match_id)

                    if m_msg_id:
                        try:
                            msg = await channel.fetch_message(int(m_msg_id))
                            await msg.edit(embed=embed, view=view)
                        except discord.NotFound:
                            try:
                                new_msg = await channel.send(embed=embed, view=view)
                                live_matches_msg_ids[match_id] = new_msg.id
                            except Exception as e:
                                print(f"⚠️ [LIVE] Błąd wysyłania wiadomości dla meczu {match_id}: {e}")
                        except discord.HTTPException as e:
                            # Chwilowy błąd - nie tworzymy nowej wiadomości, spróbujemy w kolejnym ticku
                            print(f"⚠️ [LIVE] Chwilowy błąd edycji wiadomości dla meczu {match_id}: {e}")
                    else:
                        try:
                            new_msg = await channel.send(embed=embed, view=view)
                            live_matches_msg_ids[match_id] = new_msg.id
                        except Exception as e:
                            print(f"⚠️ [LIVE] Błąd wysyłania wiadomości dla meczu {match_id}: {e}")

            # Zapisujemy zaktualizowane ID w bazie
            ustawienia["live_idle_msg_id"] = idle_msg_id
            ustawienia["live_msg_id"] = idle_msg_id
            ustawienia["live_matches_msg_ids"] = live_matches_msg_ids
            zapisz_ustawienia(guild_id, ustawienia)

    @tasks.loop(seconds=10)
    async def live_monitor(self):
        """Główna pętla sprawdzania meczów na żywo."""
        for guild in self.bot.guilds:
            try:
                ustawienia = wczytaj_ustawienia(guild.id)
                if ustawienia.get("kanal_live"):
                    await self.update_live_dashboard(guild.id)
            except Exception as e:
                print(f"Błąd w live_monitor dla gildii {guild.id}: {e}")

    @live_monitor.before_loop
    async def before_live_monitor(self):
        await self.bot.wait_until_ready()

    @commands.command(name="live_setup", aliases=["ls", "na_zywo_setup"])
    @commands.has_permissions(administrator=True)
    async def cmd_live_setup(self, ctx, kanal: discord.TextChannel = None):
        """Konfiguruje dedykowany kanał do śledzenia meczów na żywo."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)

        target_channel = kanal or ctx.channel
        
        # Jeśli zmieniamy kanał, czyścimy stare wiadomości
        stary_kanal_id = ustawienia.get("kanal_live")
        if stary_kanal_id:
            stary_kanal = ctx.guild.get_channel(int(stary_kanal_id))
            if stary_kanal:
                await self._delete_all_tracked_messages(guild_id, stary_kanal, ustawienia)

        ustawienia["kanal_live"] = target_channel.id
        ustawienia["live_idle_msg_id"] = None
        ustawienia["live_msg_id"] = None
        ustawienia["live_matches_msg_ids"] = {}
        zapisz_ustawienia(guild_id, ustawienia)

        msg = await ctx.send(f"⏳ Inicjalizuję dashboard na żywo na kanale {target_channel.mention}...")
        await self.update_live_dashboard(guild_id)
        await msg.edit(content=f"✅ Dashboard meczów na żywo został pomyślnie skonfigurowany na kanale {target_channel.mention}!")

    @commands.command(name="live_reload", aliases=["lr"])
    @commands.has_permissions(administrator=True)
    async def cmd_live_reload(self, ctx):
        """Natychmiastowo odświeża dashboard meczów na żywo."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        if not ustawienia.get("kanal_live"):
            await ctx.send(f"❌ Brak skonfigurowanego kanału live. Użyj `{ctx.prefix}live_setup`.", delete_after=6)
            return

        msg = await ctx.send("⏳ Odświeżam stan meczów na żywo...")
        await self.update_live_dashboard(guild_id)
        await msg.edit(content="✅ Dashboard meczów na żywo został zaktualizowany!")

    @commands.command(name="live_repost")
    @commands.has_permissions(administrator=True)
    async def cmd_live_repost(self, ctx):
        """Usuwa poprzednie wiadomości dashboardu i wysyła nowe na sam dół kanału."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = ustawienia.get("kanal_live")
        if not kanal_id:
            await ctx.send(f"❌ Brak skonfigurowanego kanału live. Użyj `{ctx.prefix}live_setup`.", delete_after=6)
            return

        channel = ctx.guild.get_channel(int(kanal_id)) or ctx.channel
        await self._delete_all_tracked_messages(guild_id, channel, ustawienia)

        msg = await ctx.send("⏳ Przenoszę dashboard na żywo na dół kanału...")
        await self.update_live_dashboard(guild_id)
        await msg.edit(content="✅ Dashboard na żywo został pomyślnie przeniesiony na dół kanału!")

async def setup(bot):
    await bot.add_cog(LiveMatchesCog(bot))
