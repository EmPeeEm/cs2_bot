import discord
from discord.ext import commands
from utils.database import wczytaj_sezon, zapisz_sezon, wczytaj_ekipe, wczytaj_ustawienia, get_cfg
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
        await interaction.response.send_message("⏳ Zbieram aktualne dane graczy. Proszę czekać...", ephemeral=True)
        
        ekipa = wczytaj_ekipe()
        start_elo = {}
        for discord_id, nick in ekipa.items():
            gracz = await get_player_stats(nick)
            if gracz and gracz != "error" and str(gracz['elo']).isdigit():
                start_elo[gracz['player_id']] = int(gracz['elo'])

        nowy_sezon = {
            "nazwa": self.nazwa_sezonu.value,
            "start_elo": start_elo
        }
        
        # Wybór kanału do ogłoszenia
        ustawienia = wczytaj_ustawienia()
        kanal_id = ustawienia.get("kanal_sezonu")
        cel = interaction.channel
        if kanal_id:
            target = interaction.guild.get_channel(int(kanal_id))
            if target:
                cel = target

        await cel.send(f"🏆 **UROCZYŚCIE ROZPOCZYNAMY NOWY SEZON:** `{self.nazwa_sezonu.value}`!\nStatystyki (ELO startowe) dla obecnej ekipy zostały wpisane do bazy. Powodzenia!")
        
        # Inicjalizacja Tabela Wyników Na Żywo
        leaderboard_embed = discord.Embed(
            title=f"📊 RANKING SEZONOWY: {self.nazwa_sezonu.value}",
            description="⏳ Generowanie tabeli startowej...",
            color=get_cfg("main_color", 0x2b2d31)
        )
        leaderboard_msg = await cel.send(embed=leaderboard_embed)
        
        # Zapisujemy ID wiadomości do bazy sezonu
        nowy_sezon["leaderboard_msg_id"] = leaderboard_msg.id
        nowy_sezon["leaderboard_channel_id"] = cel.id
        zapisz_sezon(nowy_sezon)

        # Od razu odświeżamy tabelę, żeby nie była pusta
        cog = interaction.client.get_cog("SeasonUICog")
        if cog:
            await cog.update_live_leaderboard()

class SeasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Rozpocznij Nowy Sezon", style=discord.ButtonStyle.green, custom_id="season_start")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tylko administratorzy mogą zarządzać sezonami.", ephemeral=True)
            return
            
        await interaction.response.send_modal(SeasonStartModal())

    @discord.ui.button(label="Zakończ i Ogłoś Wyniki", style=discord.ButtonStyle.red, custom_id="season_end")
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tylko administratorzy mogą zarządzać sezonami.", ephemeral=True)
            return

        sezon_obecny = wczytaj_sezon()
        if "nazwa" not in sezon_obecny:
            await interaction.response.send_message("⚠️ Żaden sezon nie jest w tej chwili aktywny.", ephemeral=True)
            return

        await interaction.response.defer()

        # Wyliczamy wyniki
        start_elo = sezon_obecny.get("start_elo", {})
        ekipa = wczytaj_ekipe()
        wyniki = []

        for discord_id, nick in ekipa.items():
            gracz = await get_player_stats(nick)
            pid = gracz.get('player_id') if gracz and gracz != "error" else None
            
            if pid and pid in start_elo:
                obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                progres = obecne - start_elo[pid]
                wyniki.append({
                    "discord_id": discord_id, 
                    "nick": gracz['nick'], 
                    "progres": progres, 
                    "obecne": obecne,
                    "poziom": gracz.get('poziom', 0)
                })

        # Sortujemy (progres -> obecne)
        wyniki.sort(key=lambda x: (x["progres"], x["obecne"]), reverse=True)
        
        if not wyniki:
            await interaction.followup.send("❌ Nie udało się podsumować sezonu (brak danych graczy).")
            return

        mvp = wyniki[0]
        
        # PROCES NADAWANIA ROLI
        rola_mvp = discord.utils.get(interaction.guild.roles, name="✨ MVP Sezonu")
        if not rola_mvp:
            try:
                rola_mvp = await interaction.guild.create_role(name="✨ MVP Sezonu", color=0xFFD700, hoist=True, reason="Zwycięzca w Faceit")
            except discord.Forbidden:
                pass
                
        if rola_mvp:
            for member in rola_mvp.members:
                try:
                    await member.remove_roles(rola_mvp)
                except discord.Forbidden:
                    pass
            
            mvp_member = interaction.guild.get_member(int(mvp['discord_id']))
            if mvp_member:
                try:
                    await mvp_member.add_roles(rola_mvp)
                except discord.Forbidden:
                    pass
        
        opis = f"Dziękujemy wszystkim za wzięcie udziału w rozgrywkach **{sezon_obecny['nazwa']}**!\nZyskane punkty podliczono. Oto oficjalny wyrok:\n\n"
        
        last_rank = 0
        last_val = (None, None)
        
        for i, res in enumerate(wyniki, 1):
            curr_val = (res['progres'], res['obecne'])
            if curr_val == last_val:
                display_rank = last_rank
            else:
                display_rank = i
                last_rank = i
                last_val = curr_val

            znak = "+" if res['progres'] > 0 else ""
            oznaczenie = "🥇 MVP" if display_rank == 1 else f"{display_rank}."
            
            emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
            emotka_levelu = emotki.get(str(res['poziom']), get_cfg("level_default", config.LEVEL_DEFAULT))
            
            opis += f"{oznaczenie} <@{res['discord_id']}> {emotka_levelu} — **{res['obecne']}** ELO *({znak}{res['progres']} pkt)*\n"

        embed = discord.Embed(
            title=f"🏁 KONIEC SEZONU: {sezon_obecny['nazwa']}",
            description=opis,
            color=get_cfg("main_color", 0x2b2d31)
        )
        embed.set_footer(text="Gratulacje! Ranking został zarchiwizowany.")

        # ARCHIWIZACJA I POBRANIE ID DO EDYCJI
        from utils.database import wczytaj_archiwum_sezonow, zapisz_archiwum_sezonow
        archiwum = wczytaj_archiwum_sezonow()
        
        msg_id_to_edit = sezon_obecny.get("leaderboard_msg_id")
        channel_id_to_edit = sezon_obecny.get("leaderboard_channel_id")

        sezon_obecny["wyniki"] = wyniki
        archiwum.append(sezon_obecny)
        zapisz_archiwum_sezonow(archiwum)

        zapisz_sezon({})

        # Próba edycji starej wiadomości
        success_edit = False
        if msg_id_to_edit and channel_id_to_edit:
            channel = interaction.guild.get_channel(int(channel_id_to_edit))
            if channel:
                try:
                    old_msg = await channel.fetch_message(int(msg_id_to_edit))
                    await old_msg.edit(embed=embed)
                    success_edit = True
                except:
                    pass

        # Informowanie o zakończeniu
        ustawienia = wczytaj_ustawienia()
        kanal_id = ustawienia.get("kanal_sezonu")
        cel = interaction.channel
        if kanal_id:
            target = interaction.guild.get_channel(int(kanal_id))
            if target: cel = target

        final_ping = f"🎉 **Sezon zakończony!** Ranking został zaktualizowany powyżej.\nGratulacje dla najwybitniejszego gracza ligi: <@{mvp['discord_id']}>!"
        distance = f"*** ***\n*** ***\n*** ***"
        
        if success_edit:
            await cel.send(content=final_ping)
            await cel.send(content=distance)
        else:
            await cel.send(content=final_ping, embed=embed)
            await cel.send(content=distance)

class SeasonUICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _generate_leaderboard_embed(self, nazwa, start_elo):
        ekipa = wczytaj_ekipe()
        wyniki = []

        for discord_id, nick in ekipa.items():
            gracz = await get_player_stats(nick)
            pid = gracz.get('player_id') if gracz and gracz != "error" else None
            
            if pid and pid in start_elo:
                obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                progres = obecne - start_elo[pid]
                wyniki.append({
                    "discord_id": discord_id, 
                    "nick": gracz['nick'], 
                    "progres": progres, 
                    "obecne": obecne,
                    "poziom": gracz.get('poziom', 0)
                })

        # Sortowanie: najpierw progres, potem aktualne ELO
        wyniki.sort(key=lambda x: (x["progres"], x["obecne"]), reverse=True)
        
        opis = f"Kto wykazuje najlepszy współczynnik postępu w **{nazwa}**?\n\n"
        if not wyniki:
            opis += "*Oczekiwanie na pierwsze mecze członków ekipy...*"
        else:
            last_rank = 0
            last_val = (None, None)
            
            for i, gracz in enumerate(wyniki, 1):
                current_val = (gracz['progres'], gracz['obecne'])
                
                # Logika remisów
                if current_val == last_val:
                    display_rank = last_rank
                else:
                    display_rank = i
                    last_rank = i
                    last_val = current_val

                # Wybór ikonki/numeru
                if display_rank == 1: pozycja = "🥇"
                elif display_rank == 2: pozycja = "🥈"
                elif display_rank == 3: pozycja = "🥉"
                else: pozycja = f"**{display_rank}.**"
                
                emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
                emotka_levelu = emotki.get(str(gracz['poziom']), get_cfg("level_default", config.LEVEL_DEFAULT))
                znak = "+" if gracz['progres'] > 0 else ""
                
                opis += f"{pozycja} <@{gracz['discord_id']}> {emotka_levelu} — {gracz['obecne']} ELO *({znak}{gracz['progres']})*\n"
            
        embed = discord.Embed(
            title=f"📊 RANKING SEZONOWY: {nazwa}",
            description=opis,
            color=get_cfg("main_color", 0x2b2d31)
        )
        embed.set_footer(text="Tabela aktualizowana automatycznie po każdym meczu.")
        return embed

    async def update_live_leaderboard(self):
        """Metoda odświeżająca przypiętą wiadomość z rankingiem."""
        sezon = wczytaj_sezon()
        if not sezon or "nazwa" not in sezon or "leaderboard_msg_id" not in sezon:
            return

        embed = await self._generate_leaderboard_embed(sezon['nazwa'], sezon.get('start_elo', {}))
        
        channel_id = sezon.get("leaderboard_channel_id")
        msg_id = sezon.get("leaderboard_msg_id")
        
        if not channel_id or not msg_id: return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            # Próbujemy pobrać kanał z Discorda jeśli nie ma w cache
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except:
                return

        try:
            msg = await channel.fetch_message(int(msg_id))
            await msg.edit(embed=embed)
        except discord.NotFound:
            # Wiadomość została usunięta - moglibyśmy wysłać nową i zaktualizować ID
            pass
        except Exception as e:
            print(f"⚠️ Błąd podczas aktualizacji tabeli sezonowej: {e}")

    @commands.command(name="sezon")
    @commands.has_permissions(administrator=True)
    async def panel_sezon(self, ctx):
        sezon_obecny = wczytaj_sezon()
        nazwa = sezon_obecny.get('nazwa')
        
        if not nazwa:
            embed = discord.Embed(
                title="🏆 Panel Zarządzania Sezonem",
                description="Obecnie nie trwa żaden sezon.\nNaciśnij przycisk poniżej, aby wystartować nową wojnę o punkty ELO.",
                color=get_cfg("main_color", 0x2b2d31)
            )
            await ctx.send(embed=embed, view=SeasonView())
            return
            
        msg = await ctx.send(f"⏳ Przeliczam aktualną stawkę bieżącego sezonu: **{nazwa}**...")
        embed = await self._generate_leaderboard_embed(nazwa, sezon_obecny.get('start_elo', {}))
        await msg.edit(content=None, embed=embed, view=SeasonView())

async def setup(bot):
    await bot.add_cog(SeasonUICog(bot))
