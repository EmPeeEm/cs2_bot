import json
import discord
from discord.ext import commands
from utils.database import (
    wczytaj_sezon, zapisz_sezon, zakoncz_sezon, 
    pobierz_ostatni_zakonczony_sezon, zaktualizuj_leaderboard_msg_id,
    wczytaj_ekipe, wczytaj_ustawienia, get_cfg, get_connection
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

        # 5. Aktualizacja Hali Sław (w tym karty MVP Sezonów)
        records_cog = interaction.client.get_cog("RecordsCog")
        if records_cog:
            try:
                await records_cog.update_records_board(guild_id)
            except Exception as e:
                print(f"Błąd aktualizacji Hali Sław po zakończeniu sezonu: {e}")

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
            
        msg = await ctx.send("⏳ Wymuszam aktualizację rankingu...")
        await self.update_live_leaderboard(guild_id)
        await msg.edit(content="✅ Ranking sezonowy został pomyślnie zaktualizowany!")

    @commands.command(name="sezon_repost", aliases=["sezon_resend", "srepost"])
    @commands.has_permissions(administrator=True)
    async def panel_sezon_repost(self, ctx):
        """Usuwa poprzednią wiadomość z rankingiem i wysyła nową na dedykowanym kanale."""
        guild_id = ctx.guild.id
        sezon = wczytaj_sezon(guild_id)
        if not sezon or "nazwa" not in sezon:
            await ctx.send("❌ Brak aktywnego sezonu.")
            return

        status_msg = await ctx.send("⏳ Przenoszę tabelę sezonu na dół kanału...")

        ustawienia = wczytaj_ustawienia(guild_id)
        kanal_id = sezon.get("leaderboard_channel_id") or ustawienia.get("kanal_sezonu") or ctx.channel.id
        cel = ctx.guild.get_channel(int(kanal_id)) if kanal_id else ctx.channel
        if not cel:
            cel = ctx.channel

        # 1. Próba usunięcia starej wiadomości tabeli
        stare_msg_id = sezon.get("leaderboard_msg_id")
        if stare_msg_id:
            try:
                stara_wiadomosc = await cel.fetch_message(int(stare_msg_id))
                await stara_wiadomosc.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        # 2. Wygenerowanie i wysłanie nowej wiadomości tabeli
        embed = await self._generate_leaderboard_embed(guild_id, sezon['nazwa'], sezon.get('start_elo', {}))
        nowa_wiadomosc = await cel.send(embed=embed)

        # 3. Zaktualizowanie ID w bazie danych
        zaktualizuj_leaderboard_msg_id(guild_id, nowa_wiadomosc.id, cel.id)

        await status_msg.edit(content="✅ Tabela sezonu została pomyślnie wysłana na nowo na dedykowanym kanale, a poprzednia usunięta!")

    @commands.command(name="sezony", aliases=["sezon_lista", "seasons"])
    @commands.has_permissions(administrator=True)
    async def cmd_sezony_lista(self, ctx):
        """Wyświetla listę wszystkich sezonów w bazie danych."""
        guild_id = str(ctx.guild.id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, is_active, archive_data FROM seasons WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
            rows = cursor.fetchall()
            
        if not rows:
            await ctx.send("ℹ️ Brak zarejestrowanych sezonów dla tego serwera.")
            return
            
        embed = discord.Embed(
            title="📜 Lista Sezonów ELO",
            color=get_cfg(ctx.guild.id, "main_color", 0x2b2d31)
        )
        lines = []
        for s_id, s_name, is_active, archive_json in rows:
            status = "🟢 [AKTYWNY]" if is_active else "🏁 [ZAKOŃCZONY]"
            mvp_info = "Brak MVP"
            if archive_json:
                try:
                    archive = json.loads(archive_json)
                    if isinstance(archive, list) and len(archive) > 0:
                        mvp = archive[0]
                        d_id = mvp.get("discord_id")
                        progres = mvp.get("progres", 0)
                        znak = "+" if progres > 0 else ""
                        mvp_info = f"<@{d_id}> ({znak}{progres} ELO)"
                except Exception:
                    pass
            lines.append(f"`ID: {s_id}` **{s_name}** • {status} • MVP: {mvp_info}")
            
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Aby przypisać MVP: {ctx.prefix}sezon_set_mvp <ID> @gracz <progres_elo>")
        await ctx.send(embed=embed)

    @commands.command(name="sezon_set_mvp", aliases=["sezon_ustaw_mvp", "set_season_mvp"])
    @commands.has_permissions(administrator=True)
    async def cmd_sezon_set_mvp(self, ctx, id_lub_nazwa: str, member: discord.Member, progres_elo: int = 0):
        """Ręcznie przypisuje/poprawia MVP dla archiwalnego sezonu."""
        guild_id = str(ctx.guild.id)
        with get_connection() as conn:
            cursor = conn.cursor()
            if id_lub_nazwa.isdigit():
                cursor.execute("SELECT id, name FROM seasons WHERE guild_id = ? AND id = ?", (guild_id, int(id_lub_nazwa)))
            else:
                cursor.execute("SELECT id, name FROM seasons WHERE guild_id = ? AND LOWER(name) = LOWER(?)", (guild_id, id_lub_nazwa))
            row = cursor.fetchone()
            
            if not row:
                await ctx.send(f"❌ Nie znaleziono sezonu `{id_lub_nazwa}`. Użyj `{ctx.prefix}sezony`, aby sprawdzić listę ID.")
                return
                
            s_id, s_name = row
            archive_data = json.dumps([{
                "discord_id": str(member.id),
                "nick": member.display_name,
                "progres": progres_elo,
                "obecne": 0
            }])
            cursor.execute("UPDATE seasons SET archive_data = ?, is_active = 0 WHERE id = ?", (archive_data, s_id))
            conn.commit()
            
        # Aktualizacja tablicy rekordów / Hali Sław
        records_cog = self.bot.get_cog("RecordsCog")
        if records_cog:
            try:
                await records_cog.update_records_board(ctx.guild.id)
            except Exception as e:
                print(f"Błąd aktualizacji Hali Sław: {e}")
                
        znak = "+" if progres_elo > 0 else ""
        await ctx.send(f"✅ Pomyślnie ustawiono MVP dla sezonu **{s_name}** (`ID: {s_id}`): {member.mention} (*{znak}{progres_elo} ELO*)!\n🏆 Karta w Hali Sław została zaktualizowana.")

async def setup(bot):
    await bot.add_cog(SeasonUICog(bot))
