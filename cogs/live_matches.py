# cogs/live_matches.py
import discord
from discord.ext import commands, tasks
import asyncio
import time
import datetime
import config
from utils.database import wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia, get_cfg
from utils.faceit_api import get_latest_match_id, get_match_details, get_player_stats

STATUS_LABELS = {
    "VOTING": "🟡 Faza Veto / Wybór mapy",
    "CONFIGURING": "🟠 Konfiguracja serwera",
    "READY": "🟠 Rozgrzewka / Łączenie z serwerem",
    "ON_GOING": "🔴 W trakcie meczu (LIVE)",
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

        # 1. Sprawdzamy najnowsze mecze graczy
        for discord_id, player_id in ekipa.items():
            try:
                latest_match_id = await get_latest_match_id(player_id)
                if not latest_match_id:
                    continue

                if latest_match_id in found_matches_this_tick:
                    found_matches_this_tick[latest_match_id]["our_players"].append((discord_id, player_id))
                    continue

                details = await get_match_details(latest_match_id)
                if not details:
                    continue

                status = details.get("status")
                # Interesują nas mecze w toku lub te, które już wcześniej śledziliśmy
                if status in ["VOTING", "CONFIGURING", "READY", "ON_GOING"] or latest_match_id in current_active:
                    found_matches_this_tick[latest_match_id] = {
                        "details": details,
                        "our_players": [(discord_id, player_id)],
                        "finished_at": current_active.get(latest_match_id, {}).get("finished_at")
                    }
            except Exception as e:
                print(f"Błąd podczas sprawdzania gracza {player_id}: {e}")

        # 2. Aktualizujemy stan i obsługujemy zakończenie meczu
        now = time.time()
        updated_active = {}

        for match_id, match_data in found_matches_this_tick.items():
            status = match_data["details"].get("status")
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
        """Buduje embed z listą trwających meczów lub stanem czuwania."""
        main_color = get_cfg(guild_id, "main_color", 0x2b2d31)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        if not active_matches:
            embed = discord.Embed(
                title="🟢 MECZE NA ŻYWO: Brak aktywnych gier",
                description="*Żaden z zarejestrowanych graczy nie rozgrywa obecnie meczu na Faceicie.*\n\n"
                            "Gdy ktoś rozpocznie mecz, karta spotkania pojawi się tutaj automatycznie.",
                color=0x2ecc71
            )
            embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~35s")
            return embed, None

        embed = discord.Embed(
            title=f"🔴 TRWAJĄCE MECZE EKIPY ({len(active_matches)})",
            description="Aktualnie trwające spotkania graczy z naszego serwera na platformie Faceit:",
            color=0xe74c3c
        )

        match_urls = []
        thumbnail_set = False

        for match_id, data in active_matches.items():
            details = data["details"]
            status = details.get("status", "UNKNOWN")
            status_text = STATUS_LABELS.get(status, f"Status: {status}")
            mapa = details.get("mapa", "W trakcie wyboru")
            
            # Gracze z naszego serwera w tym meczu
            our_mentions = [f"<@{d_id}>" for d_id, p_id in data["our_players"]]
            our_str = ", ".join(our_mentions) if our_mentions else "Gracze ekipy"

            # Drużyny i wynik
            teams = details.get("teams", {})
            f1 = teams.get("faction1", {})
            f2 = teams.get("faction2", {})
            f1_name = f1.get("name", "Drużyna 1")
            f2_name = f2.get("name", "Drużyna 2")

            score = details.get("score", {})
            s1 = score.get("faction1", 0)
            s2 = score.get("faction2", 0)
            score_str = f"**{s1} : {s2}**" if status in ["ON_GOING", "FINISHED"] else "*Przed meczem*"

            # Miniaturka pierwszej mapy
            if not thumbnail_set and details.get("map_image"):
                embed.set_thumbnail(url=details["map_image"])
                thumbnail_set = True

            pole_nazwa = f"🗺️ Mapa: {mapa} | {status_text}"
            pole_wartosc = (
                f"👥 **Nasi gracze:** {our_str}\n"
                f"⚔️ **Mecz:** `{f1_name}` vs `{f2_name}`\n"
                f"📊 **Wynik:** {score_str}\n"
                f"🔗 [Przejdź do pokoju meczowego]({details['faceit_url']})"
            )
            
            if data.get("finished_at"):
                pozostalo = max(0, int(180 - (time.time() - data["finished_at"])))
                pole_wartosc += f"\n*(Karta zniknie za ~{pozostalo}s)*"

            embed.add_field(name=pole_nazwa, value=pole_wartosc, inline=False)
            match_urls.append((f"Mecz: {mapa}", details.get("faceit_url")))

        embed.set_footer(text=f"Stan na {now_str} • Auto-odświeżanie co ~35s")
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
            return

        active = await self._fetch_guild_active_matches(guild_id)
        embed, view = self._build_dashboard_embed(guild_id, active)

        msg_id = ustawienia.get("live_msg_id")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(embed=embed, view=view)
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                msg = None

        # Jeśli wiadomości nie ma lub usunięto, wysyłamy nową i zapisujemy ID
        try:
            nowa_wiadomosc = await channel.send(embed=embed, view=view)
            ustawienia["live_msg_id"] = nowa_wiadomosc.id
            zapisz_ustawienia(guild_id, ustawienia)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @tasks.loop(seconds=35)
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
