# cogs/season_ui.py
import discord
from discord.ext import commands
from utils.database import (
    wczytaj_sezon, zapisz_sezon, zakoncz_sezon, 
    pobierz_ostatni_zakonczony_sezon, zaktualizuj_leaderboard_msg_id,
    wczytaj_ekipe, wczytaj_ustawienia, get_cfg
)
from utils.faceit_api import get_player_stats
import config

class SeasonStartModal(discord.ui.Modal, title='Rozpocznij nowy sezon ELO'):
    nazwa_sezonu = discord.ui.TextInput(
        label='Nazwa Sezonu (np. Sezon Jesienny)',
        placeholder='Wpisz tutaj nazwę...',
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        await interaction.response.send_message("⏳ Zbieram aktualne dane graczy. Proszę czekać...", ephemeral=True)
        
        ekipa = wczytaj_ekipe(guild_id)
        start_elo = {}
        for d_id, p_id in ekipa.items():
            gracz = await get_player_stats(p_id, lifetime=False)
            if gracz and gracz != "error" and str(gracz['elo']).isdigit():
                start_elo[p_id] = int(gracz['elo'])

        nowy_sezon = {"nazwa": self.nazwa_sezonu.value, "start_elo": start_elo}
        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = ustawienia.get("kanal_sezonu")
        cel = interaction.channel
        if kanal_id:
            target = interaction.guild.get_channel(int(kanal_id))
            if target: cel = target

        await cel.send(f"🏆 **UROCZYŚCIE ROZPOCZYNAMY NOWY SEZON:** `{self.nazwa_sezonu.value}`!")
        
        leaderboard_embed = discord.Embed(
            title=f"📊 RANKING SEZONOWY: {self.nazwa_sezonu.value}",
            description="⏳ Generowanie tabeli startowej...",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        leaderboard_msg = await cel.send(embed=leaderboard_embed)
        
        nowy_sezon["leaderboard_msg_id"] = leaderboard_msg.id
        nowy_sezon["leaderboard_channel_id"] = cel.id
        zapisz_sezon(guild_id, nowy_sezon)

        cog = interaction.client.get_cog("SeasonUICog")
        if cog: await cog.update_live_leaderboard(guild_id)

class SeasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Rozpocznij Nowy Sezon", style=discord.ButtonStyle.green, custom_id="season_start")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return
        await interaction.response.send_modal(SeasonStartModal())

    @discord.ui.button(label="Zakończ i Ogłoś Wyniki", style=discord.ButtonStyle.red, custom_id="season_end")
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        sezon_obecny = wczytaj_sezon(guild_id)
        if not sezon_obecny or "nazwa" not in sezon_obecny:
            await interaction.response.send_message("⚠️ Brak aktywnego sezonu.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        start_elo = sezon_obecny.get("start_elo", {})
        ekipa = wczytaj_ekipe(guild_id)
        wyniki = []

        for d_id, p_id in ekipa.items():
            gracz = await get_player_stats(p_id, lifetime=False)
            if p_id in start_elo and gracz and gracz != "error":
                obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                progres = obecne - start_elo[p_id]
                wyniki.append({"discord_id": d_id, "nick": gracz['nick'], "progres": progres, "obecne": obecne, "poziom": gracz.get('poziom', 0)})

        wyniki.sort(key=lambda x: (x["progres"], x["obecne"]), reverse=True)
        if not wyniki:
            await interaction.followup.send("❌ Brak danych graczy do podsumowania sezonu.", ephemeral=True)
            return

        mvp = wyniki[0]
        rola_mvp = discord.utils.get(interaction.guild.roles, name="✨ MVP Sezonu")
        if not rola_mvp:
            try: rola_mvp = await interaction.guild.create_role(name="✨ MVP Sezonu", color=0xFFD700, hoist=True)
            except discord.HTTPException: pass
                
        if rola_mvp:
            for member in rola_mvp.members:
                try: await member.remove_roles(rola_mvp)
                except (discord.Forbidden, discord.HTTPException): pass
            mvp_member = interaction.guild.get_member(int(mvp['discord_id']))
            if mvp_member:
                try: await mvp_member.add_roles(rola_mvp)
                except (discord.Forbidden, discord.HTTPException): pass
        
        opis = f"🏁 **Oficjalne wyniki sezonu: {sezon_obecny['nazwa']}**\n\n"
        for i, res in enumerate(wyniki, 1):
            znak = "+" if res['progres'] > 0 else ""
            oznaczenie = "🥇 MVP" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"**{i}.**"))
            emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
            emotka_levelu = emotki.get(str(res['poziom']), get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
            opis += f"{oznaczenie} <@{res['discord_id']}> {emotka_levelu} — **{res['obecne']}** ELO *({znak}{res['progres']} pkt)*\n"

        embed = discord.Embed(
            title=f"🏁 PODSUMOWANIE SEZONU: {sezon_obecny['nazwa']}", 
            description=opis, 
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        embed.set_footer(text="Sezon zakończony • Gratulacje dla wszystkich graczy!")

        # 1. Określenie dedykowanego kanału sezonu
        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = sezon_obecny.get("leaderboard_channel_id") or ustawienia.get("kanal_sezonu")
        cel = interaction.guild.get_channel(int(kanal_id)) if kanal_id else interaction.channel
        if not cel:
            cel = interaction.channel

        # 2. Edycja pierwotnej wiadomości z rankingiem (lub wysłanie nowej na dedykowany kanał w razie błędu)
        msg_id = sezon_obecny.get("leaderboard_msg_id")
        msg_edited = False
        if msg_id and cel:
            try:
                msg = await cel.fetch_message(int(msg_id))
                await msg.edit(embed=embed, view=None)
                msg_edited = True
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                msg_edited = False

        if not msg_edited and cel:
            await cel.send(embed=embed)

        # 3. Wysłanie wiadomości z gratulacjami na dedykowany kanał
        progres_znak = "+" if mvp['progres'] > 0 else ""
        gratulacje_tekst = (
            f"🎉 **OFICJALNE ZAKOŃCZENIE SEZONU: `{sezon_obecny['nazwa']}`!** 🎉\n\n"
            f"👑 Wielkie brawa i gratulacje dla <@{mvp['discord_id']}> za zdobycie tytułu **✨ MVP Sezonu**!\n"
            f"📈 Wynik końcowy: **{mvp['obecne']}** ELO (*{progres_znak}{mvp['progres']} pkt w trakcie sezonu*).\n\n"
            f"Dziękujemy wszystkim za walkę i emocje w tym sezonie! 🏆🔥"
        )
        if cel:
            await cel.send(gratulacje_tekst)

        # 4. Zapisanie archiwum i dezaktywacja sezonu
        zakoncz_sezon(guild_id, wyniki)

        await interaction.followup.send("✅ Sezon został pomyślnie zakończony! Tabela wyników została zaktualizowana, a gratulacje wysłane na dedykowany kanał.", ephemeral=True)

class SeasonUICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _generate_leaderboard_embed(self, guild_id, nazwa, start_elo):
        ekipa = wczytaj_ekipe(guild_id)
        wyniki = []
        for d_id, p_id in ekipa.items():
            gracz = await get_player_stats(p_id, lifetime=False)
            if p_id in start_elo and gracz and gracz != "error":
                obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                progres = obecne - start_elo[p_id]
                wyniki.append({"discord_id": d_id, "nick": gracz['nick'], "progres": progres, "obecne": obecne, "poziom": gracz.get('poziom', 0)})

        wyniki.sort(key=lambda x: (x["progres"], x["obecne"]), reverse=True)
        opis = f"Ranking postępu w **{nazwa}**\n\n"
        if not wyniki: opis += "*Czekamy na pierwsze mecze...*"
        else:
            for i, gracz in enumerate(wyniki, 1):
                pozycja = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"**{i}.**"))
                emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
                emotka_levelu = emotki.get(str(gracz['poziom']), get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
                znak = "+" if gracz['progres'] > 0 else ""
                opis += f"{pozycja} <@{gracz['discord_id']}> {emotka_levelu} — {gracz['obecne']} ELO *({znak}{gracz['progres']})*\n"
            
        embed = discord.Embed(title=f"📊 RANKING SEZONOWY: {nazwa}", description=opis, color=get_cfg(guild_id, "main_color", 0x2b2d31))
        return embed

    async def update_live_leaderboard(self, guild_id):
        sezon = wczytaj_sezon(guild_id)
        if not sezon or "nazwa" not in sezon or not sezon.get("leaderboard_msg_id") or not sezon.get("leaderboard_channel_id"):
            return

        embed = await self._generate_leaderboard_embed(guild_id, sezon['nazwa'], sezon.get('start_elo', {}))
        channel = self.bot.get_channel(int(sezon["leaderboard_channel_id"]))
        if not channel: return

        try:
            msg = await channel.fetch_message(int(sezon["leaderboard_msg_id"]))
            await msg.edit(embed=embed)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException): pass

    @commands.command(name="sezon")
    @commands.has_permissions(administrator=True)
    async def panel_sezon(self, ctx):
        guild_id = ctx.guild.id
        sezon_obecny = wczytaj_sezon(guild_id)
        nazwa = sezon_obecny.get('nazwa')
        
        if not nazwa:
            embed = discord.Embed(title="🏆 Panel Sezonu", description="Brak aktywnego sezonu.", color=get_cfg(guild_id, "main_color", 0x2b2d31))
            await ctx.send(embed=embed, view=SeasonView())
            return
            
        embed = await self._generate_leaderboard_embed(guild_id, nazwa, sezon_obecny.get('start_elo', {}))
        await ctx.send(embed=embed, view=SeasonView())

    @commands.command(name="sezon_reload", aliases=["sr"])
    @commands.has_permissions(administrator=True)
    async def panel_sezon_reload(self, ctx):
        """Ręcznie wymusza aktualizację wiadomości z rankingiem sezonowym."""
        guild_id = ctx.guild.id
        sezon = wczytaj_sezon(guild_id)
        if not sezon or "nazwa" not in sezon:
            await ctx.send("❌ Brak aktywnego sezonu.", delete_after=5)
            return
            
        if not sezon.get("leaderboard_msg_id") or not sezon.get("leaderboard_channel_id"):
            await ctx.send("❌ Brak powiązanej wiadomości z rankingiem.", delete_after=5)
            return
            
    @commands.command(name="sezon_napraw", aliases=["sezon_fix", "sf"])
    @commands.has_permissions(administrator=True)
    async def panel_sezon_napraw(self, ctx, stary_msg_id: int = None, nowy_start_msg_id: int = None):
        """
        Porządkuje wiadomości na kanale sezonowym:
        - Edytuje starą tabelę na oficjalne podsumowanie
        - Wysyła gratulacje dla MVP
        - Odświeża i przenosi aktywny sezon pod spód z zachowaniem danych
        """
        guild_id = ctx.guild.id
        status_msg = await ctx.send("⏳ Trwa naprawianie i reorganizacja sezonów...")
        
        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = ustawienia.get("kanal_sezonu") or ctx.channel.id
        cel = ctx.guild.get_channel(int(kanal_id)) if kanal_id else ctx.channel
        if not cel: cel = ctx.channel

        # 1. Pobieramy dane starego sezonu
        stary_sezon = pobierz_ostatni_zakonczony_sezon(guild_id)
        if not stary_msg_id and stary_sezon:
            stary_msg_id = stary_sezon.get("leaderboard_msg_id")

        if not stary_msg_id:
            await status_msg.edit(content="❌ Nie znaleziono ID starej wiadomości tabeli. Użyj: `!sezon_napraw <id_starej_tabeli>`")
            return

        # Generujemy wyniki starego sezonu na podstawie archive_data lub start_elo
        wyniki_stare = []
        nazwa_stara = stary_sezon.get("nazwa", "Stary Sezon") if stary_sezon else "Poprzedni Sezon"
        start_elo_stare = stary_sezon.get("start_elo", {}) if stary_sezon else {}
        
        # Jeśli mamy zapisane archive_data, używamy ich w pierwszej kolejności
        if stary_sezon and stary_sezon.get("archive") and isinstance(stary_sezon["archive"], list):
            wyniki_stare = stary_sezon["archive"]
        else:
            # W przeciwnym razie przeliczamy na podstawie bazy i start_elo
            ekipa = wczytaj_ekipe(guild_id)
            for d_id, p_id in ekipa.items():
                gracz = await get_player_stats(p_id, lifetime=False)
                if gracz and gracz != "error" and p_id in start_elo_stare:
                    obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                    progres = obecne - start_elo_stare[p_id]
                    wyniki_stare.append({"discord_id": d_id, "nick": gracz['nick'], "progres": progres, "obecne": obecne, "poziom": gracz.get('poziom', 0)})

        wyniki_stare.sort(key=lambda x: (x["progres"], x["obecne"]), reverse=True)

        if wyniki_stare:
            opis_stary = f"🏁 **Oficjalne wyniki sezonu: {nazwa_stara}**\n\n"
            for i, res in enumerate(wyniki_stare, 1):
                znak = "+" if res['progres'] > 0 else ""
                oznaczenie = "🥇 MVP" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"**{i}.**"))
                emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
                emotka_levelu = emotki.get(str(res['poziom']), get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
                opis_stary += f"{oznaczenie} <@{res['discord_id']}> {emotka_levelu} — **{res['obecne']}** ELO *({znak}{res['progres']} pkt)*\n"

            embed_stary = discord.Embed(
                title=f"🏁 PODSUMOWANIE SEZONU: {nazwa_stara}", 
                description=opis_stary, 
                color=get_cfg(guild_id, "main_color", 0x2b2d31)
            )
            embed_stary.set_footer(text="Sezon zakończony • Gratulacje dla wszystkich graczy!")

            try:
                msg_old = await cel.fetch_message(int(stary_msg_id))
                await msg_old.edit(embed=embed_stary, view=None)
            except Exception as e:
                await ctx.send(f"⚠️ Nie udało się wyedytować starej wiadomości: {e}")

            # Wysłanie gratulacji
            mvp = wyniki_stare[0]
            progres_znak = "+" if mvp['progres'] > 0 else ""
            gratulacje_tekst = (
                f"🎉 **OFICJALNE ZAKOŃCZENIE SEZONU: `{nazwa_stara}`!** 🎉\n\n"
                f"👑 Wielkie brawa i gratulacje dla <@{mvp['discord_id']}> za zdobycie tytułu **✨ MVP Sezonu**!\n"
                f"📈 Wynik końcowy: **{mvp['obecne']}** ELO (*{progres_znak}{mvp['progres']} pkt w trakcie sezonu*).\n\n"
                f"Dziękujemy wszystkim za walkę i emocje w tym sezonie! 🏆🔥"
            )
            await cel.send(gratulacje_tekst)

        # 2. Obsługa aktywnego sezonu (np. Konfeszjonal)
        aktywny_sezon = wczytaj_sezon(guild_id)
        if aktywny_sezon and "nazwa" in aktywny_sezon:
            stare_akt_msg_id = aktywny_sezon.get("leaderboard_msg_id")
            if stare_akt_msg_id:
                try:
                    m_to_del = await cel.fetch_message(int(stare_akt_msg_id))
                    await m_to_del.delete()
                except Exception: pass

            if nowy_start_msg_id:
                try:
                    s_to_del = await cel.fetch_message(int(nowy_start_msg_id))
                    await s_to_del.delete()
                except Exception: pass

            # Wysyłamy ogłoszenie nowego sezonu i nową tabelę na dole
            await cel.send(f"🏆 **UROCZYŚCIE ROZPOCZYNAMY NOWY SEZON:** `{aktywny_sezon['nazwa']}`!")
            nowy_embed = await self._generate_leaderboard_embed(guild_id, aktywny_sezon['nazwa'], aktywny_sezon.get('start_elo', {}))
            nowa_tabela_msg = await cel.send(embed=nowy_embed)

            # Przepinamy ID wiadomości w bazie
            zaktualizuj_leaderboard_msg_id(guild_id, nowa_tabela_msg.id, cel.id)

        await status_msg.edit(content="✅ Pomyślnie uporządkowano kolejność wiadomości na kanale i zaktualizowano podsumowanie starego sezonu!")

async def setup(bot):
    await bot.add_cog(SeasonUICog(bot))
