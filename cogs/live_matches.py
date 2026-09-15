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
    "FINISHED": "🏁 Mecz zakończony",
    "CANCELLED": "❌ Mecz anulowany"
}

class LiveMatchView(discord.ui.View):
    def __init__(self, match_urls):
        super().__init__(timeout=None)
        # Dodajemy przyciski z linkami do pokoi meczowych (max 5 przycisków w rzędzie)
        for i, (label, url) in enumerate(match_urls[:5]):
            if url:
                self.add_item(discord.ui.Button(
                    label=label[:80],
                    style=discord.ButtonStyle.link,
                    url=url,
                    emoji="🎮"
                ))

class LiveMatchesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # active_matches[guild_id] = {match_id: {"details": ..., "our_players": [...], "finished_at": timestamp or None}}
        self.active_matches = {}
        self.live_monitor.start()

    def cog_unload(self):
        self.live_monitor.cancel()

    async def _fetch_guild_active_matches(self, guild_id):
        """Skanuje ekipę z danej gildii i wykrywa trwające mecze."""
        ekipa = wczytaj_ekipe(guild_id)
        if not ekipa:
            return {}

        if guild_id not in self.active_matches:
            self.active_matches[guild_id] = {}

        current_active = self.active_matches[guild_id]
        found_matches_this_tick = {}

        # 1. Sprawdzamy stan meczowy graczy
        for discord_id, player_id in ekipa.items():
            try:
                await asyncio.sleep(0.08)
                # Najpierw sprawdzamy endpoint czasu rzeczywistego (groupByState)
                match_id = await get_player_ongoing_match_id(player_id)
                if not match_id:
                    # Fallback na ostatni mecz z historii (gdy trwa lub był już śledzony)
                    match_id = await get_latest_match_id(player_id)

                if not match_id:
                    continue

                if match_id in found_matches_this_tick:
                    if (discord_id, player_id) not in found_matches_this_tick[match_id]["our_players"]:
                        found_matches_this_tick[match_id]["our_players"].append((discord_id, player_id))
                    continue

                details = await get_match_details(match_id)
                if not details:
                    continue

                status = str(details.get("status", "")).upper()
                # Interesują nas mecze w toku lub te, które już wcześniej śledziliśmy
                if status in ["VOTING", "CONFIGURING", "READY", "ON_GOING", "ONGOING", "LIVE", "MATCH"] or match_id in current_active:
                    found_matches_this_tick[match_id] = {
                        "details": details,
                        "our_players": [(discord_id, player_id)],
                        "finished_at": current_active.get(match_id, {}).get("finished_at")
                    }
            except Exception as e:
                print(f"⚠️ [LIVE] Błąd podczas sprawdzania gracza {player_id}: {e}")

        # 2. Aktualizujemy stan i obsługujemy zakończenie meczu
        now = time.time()
        updated_active = {}

        for match_id, match_data in found_matches_this_tick.items():
            status = str(match_data["details"].get("status", "")).upper()
            if status in ["FINISHED", "CANCELLED"]:
                if not match_data["finished_at"]:
                    match_data["finished_at"] = now
                
                # Trzymamy zakończony mecz przez 180 sekund (3 minuty), po czym usuwamy
                if now - match_data["finished_at"] <= 180:
                    updated_active[match_id] = match_data
            else:
                match_data["finished_at"] = None
                updated_active[match_id] = match_data

        self.active_matches[guild_id] = updated_active
        return updated_active

    def _build_dashboard_embed(self, guild_id, active_matches):
        """Buduje bogaty embed z pełnymi informacjami o trwających meczach lub stanem czuwania."""
        main_color = get_cfg(guild_id, "main_color", 0x2b2d31)
        level_emojis = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        level_default = get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT)
        ekipa = wczytaj_ekipe(guild_id)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        now = time.time()

        if not active_matches:
            embed = discord.Embed(
                title="🟢 MECZE NA ŻYWO: Brak aktywnych gier",
                description="*Żaden z zarejestrowanych graczy nie rozgrywa obecnie meczu na Faceicie.*\n\n"
                            "Gdy ktoś rozpocznie mecz, karta spotkania ze składami, ELO i wynikiem pojawi się tutaj automatycznie.",
                color=0x2ecc71
            )
            embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~30s")
            return embed, None

        has_live = any(
            str(m["details"].get("status", "")).upper() not in ["FINISHED", "CANCELLED"]
            for m in active_matches.values()
        )

        if has_live:
            embed = discord.Embed(
                title=f"🔴 TRWAJĄCE MECZE EKIPY ({len(active_matches)})",
                description="Aktualnie trwające spotkania graczy z naszego serwera na platformie Faceit:",
                color=0xe74c3c
            )
        else:
            embed = discord.Embed(
                title="🟢 MECZE EKIPY: Zakończone spotkania",
                description="*Wszystkie mecze dobiegły końca. Karty z wynikami znikną za chwilę:*",
                color=0x2ecc71
            )

        match_urls = []
        thumbnail_set = False

        def format_roster(roster):
            formatted = []
            for p in roster:
                p_id = p.get("player_id")
                nick = p.get("nickname") or p.get("game_player_name") or "Gracz"
                lvl = str(p.get("game_skill_level", ""))
                emoji = level_emojis.get(lvl, level_default)
                is_our = any(e_pid == p_id for e_pid in ekipa.values())
                if is_our:
                    formatted.append(f"{emoji} **{nick}**")
                else:
                    formatted.append(f"{emoji} {nick}")
            return " • ".join(formatted) if formatted else "*Brak danych o składzie*"

        for match_id, data in active_matches.items():
            details = data["details"]
            status = str(details.get("status", "UNKNOWN")).upper()
            status_text = STATUS_LABELS.get(status, f"Status: {status}")
            mapa = details.get("mapa", "W trakcie wyboru")
            
            # Gracze z naszego serwera w tym meczu
            our_mentions = [f"<@{d_id}>" for d_id, p_id in data["our_players"]]
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
            elif status == "FINISHED":
                half_str = "Mecz zakończony"
            elif status == "CANCELLED":
                half_str = "Mecz anulowany"
            else:
                half_str = "Veto / Łączenie z serwerem"

            # Logika przypisania "Nasi" vs "Przeciwnicy" do wyeksponowania wyniku
            if f1_our_count > 0 and f2_our_count > 0:
                # Pojedynek wewnętrzny
                t1_name = f1.get("name", "Drużyna 1")
                t2_name = f2.get("name", "Drużyna 2")
                team1_label, team2_label = f"🔹 **{t1_name}:**", f"🔸 **{t2_name}:**"
                team1_roster, team2_roster = f1_roster, f2_roster
                t1_stats, t2_stats = f1.get("stats", {}), f2.get("stats", {})

                if status == "CANCELLED":
                    score_header = "# ❌ Mecz anulowany"
                    sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                elif status == "FINISHED":
                    score_header = f"# 🏁 {s1} : {s2}"
                    sub_badge = "⚔️ **Pojedynek klubowy** • *Koniec spotkania*"
                elif status in ["ON_GOING", "ONGOING", "LIVE", "MATCH"]:
                    score_header = f"# 📊 {s1} : {s2}"
                    sub_badge = f"⚔️ **Pojedynek klubowy** • *{half_str}*"
                else:
                    score_header = "# ⏳ Przed meczem"
                    sub_badge = f"⚔️ **Pojedynek klubowy** • *{half_str}*"

            elif f2_our_count > f1_our_count and f2_our_count > 0:
                # Nasi są w faction 2
                our_team_name = f2.get("name", "Nasi")
                enemy_team_name = f1.get("name", "Przeciwnicy")
                team1_label, team2_label = f"🔹 **Nasza drużyna ({our_team_name}):**", f"🔸 **Przeciwnicy ({enemy_team_name}):**"
                team1_roster, team2_roster = f2_roster, f1_roster
                t1_stats, t2_stats = f2.get("stats", {}), f1.get("stats", {})

                if status == "CANCELLED":
                    score_header = "# ❌ Mecz anulowany"
                    sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                elif status == "FINISHED":
                    if s2 > s1:
                        lead_badge = f"🏆 **Zwycięstwo (+{s2 - s1})**"
                    elif s2 < s1:
                        lead_badge = f"💀 **Porażka (-{s1 - s2})**"
                    else:
                        lead_badge = "🤝 **Remis**"
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
                else:
                    score_header = "# ⏳ Przed meczem"
                    sub_badge = f"🟠 **{half_str}**"

            else:
                # Nasi są w faction 1 (lub domyślnie)
                our_team_name = f1.get("name", "Nasi")
                enemy_team_name = f2.get("name", "Przeciwnicy")
                team1_label, team2_label = f"🔹 **Nasza drużyna ({our_team_name}):**", f"🔸 **Przeciwnicy ({enemy_team_name}):**"
                team1_roster, team2_roster = f1_roster, f2_roster
                t1_stats, t2_stats = f1.get("stats", {}), f2.get("stats", {})

                if status == "CANCELLED":
                    score_header = "# ❌ Mecz anulowany"
                    sub_badge = "🚫 **Spotkanie anulowane przez Faceit** *(nierozegrane)*"
                elif status == "FINISHED":
                    if s1 > s2:
                        lead_badge = f"🏆 **Zwycięstwo (+{s1 - s2})**"
                    elif s1 < s2:
                        lead_badge = f"💀 **Porażka (-{s2 - s1})**"
                    else:
                        lead_badge = "🤝 **Remis**"
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
                else:
                    score_header = "# ⏳ Przed meczem"
                    sub_badge = f"🟠 **{half_str}**"

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
            if status == "CANCELLED":
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

            # Formatuje składy z emotkami leveli
            team1_roster_str = format_roster(team1_roster)
            team2_roster_str = format_roster(team2_roster)

            # Miniaturka pierwszej mapy
            if not thumbnail_set and details.get("map_image"):
                embed.set_thumbnail(url=details["map_image"])
                thumbnail_set = True

            pole_nazwa = f"🗺️ MAPA: {mapa.upper()}  ┃  {status_text}"
            pole_wartosc = (
                f"{score_header}\n"
                f"{sub_badge}\n"
                f"👥 **W meczu:** {our_str}\n\n"
                f"> ⏱️ **Czas gry:** {time_str}\n"
                f"> 📈 **Średnie ELO:** `{t1_elo_str}` {t1_lvl_emoji} ({t1_prob}%) vs `{t2_elo_str}` {t2_lvl_emoji} ({t2_prob}%)\n\n"
                f"{team1_label}\n"
                f"{team1_roster_str}\n\n"
                f"{team2_label}\n"
                f"{team2_roster_str}\n\n"
                f"🔗 [Kliknij, aby otworzyć pokój meczowy Faceit]({details['faceit_url']})"
            )
            
            if data.get("finished_at"):
                pozostalo = max(0, int(180 - (time.time() - data["finished_at"])))
                pole_wartosc += f"\n*(Karta zniknie za ~{pozostalo}s)*"

            embed.add_field(name=pole_nazwa, value=pole_wartosc, inline=False)
            match_urls.append((f"Mecz: {mapa}", details.get("faceit_url")))

        embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~30s")
        view = LiveMatchView(match_urls) if match_urls else None
        return embed, view

    async def update_live_dashboard(self, guild_id):
        """Aktualizuje lub tworzy wiadomość z dashboardem na kanale."""
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
        embed, view = self._build_dashboard_embed(guild_id, active)

        # Aktualizacja nazwy kanału (🔴 tylko gdy mecz faktycznie trwa, 🟢 gdy brak lub zakończony)
        try:
            has_live = any(
                str(m["details"].get("status", "")).upper() not in ["FINISHED", "CANCELLED"]
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
                await channel.edit(name=target_name)
        except discord.Forbidden:
            print(f"⚠️ [LIVE] Bot nie ma uprawnienia 'Zarządzanie kanałami' (Manage Channels), aby zmienić nazwę kanału {channel.id}")
        except Exception as e:
            print(f"⚠️ [LIVE] Błąd zmiany nazwy kanału {channel.id}: {e}")

        msg_id = ustawienia.get("live_msg_id")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(embed=embed, view=view)
                return
            except (discord.NotFound, discord.HTTPException):
                msg = None

        # Jeśli wiadomości nie ma lub usunięto, wysyłamy nową i zapisujemy ID
        try:
            nowa_wiadomosc = await channel.send(embed=embed, view=view)
            ustawienia["live_msg_id"] = nowa_wiadomosc.id
            zapisz_ustawienia(guild_id, ustawienia)
        except discord.Forbidden:
            print(f"⚠️ [LIVE] Brak uprawnień do wysłania wiadomości na kanale {channel.id}")
        except Exception as e:
            print(f"⚠️ [LIVE] Błąd wysyłania wiadomości live na kanale {channel.id}: {e}")

    @tasks.loop(seconds=30)
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
        ustawienia["kanal_live"] = target_channel.id
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
        """Usuwa poprzednią wiadomość dashboardu i wysyła nową na sam dół kanału."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = ustawienia.get("kanal_live")
        if not kanal_id:
            await ctx.send(f"❌ Brak skonfigurowanego kanału live. Użyj `{ctx.prefix}live_setup`.", delete_after=6)
            return

        channel = ctx.guild.get_channel(int(kanal_id)) or ctx.channel
        stare_msg_id = ustawienia.get("live_msg_id")
        if stare_msg_id:
            try:
                stara = await channel.fetch_message(int(stare_msg_id))
                await stara.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        ustawienia["live_msg_id"] = None
        zapisz_ustawienia(guild_id, ustawienia)

        msg = await ctx.send("⏳ Przenoszę dashboard na żywo na dół kanału...")
        await self.update_live_dashboard(guild_id)
        await msg.edit(content="✅ Dashboard na żywo został pomyślnie przeniesiony na dół kanału!")

async def setup(bot):
    await bot.add_cog(LiveMatchesCog(bot))
