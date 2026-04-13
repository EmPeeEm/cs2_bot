import discord
from discord.ext import commands
from utils.database import wczytaj_sezon, zapisz_sezon, wczytaj_ekipe
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
        zapisz_sezon(nowy_sezon)
        
        await interaction.channel.send(f"🏆 **UROCZYŚCIE ROZPOCZYNAMY NOWY SEZON:** `{self.nazwa_sezonu.value}`!\nStatystyki (ELO startowe) dla obecnej ekipy zostały wpisane do bazy. Powodzenia!")

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
                wyniki.append({"discord_id": discord_id, "nick": gracz['nick'], "progres": progres, "obecne": obecne})

        # Sortujemy od najlepszego wyniku
        wyniki.sort(key=lambda x: x["progres"], reverse=True)
        
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
        for i, res in enumerate(wyniki, 1):
            znak = "+" if res['progres'] > 0 else ""
            oznaczenie = "🥇 MVP" if i == 1 else f"{i}."
            opis += f"{oznaczenie} <@{res['discord_id']}> zakończył grę z ELO {res['obecne']} ({znak}{res['progres']} pkt)\n"

        embed = discord.Embed(
            title="🏁 ZAKOŃCZENIE SEZONU!",
            description=opis,
            color=0x2b2d31
        )
        embed.set_footer(text="Gratulacje dla wygranego i życzymy powodzenia w następnym sezonie!")

        # ARCHIWIZACJA I RESET
        from utils.database import wczytaj_archiwum_sezonow, zapisz_archiwum_sezonow
        archiwum = wczytaj_archiwum_sezonow()
        sezon_obecny["wyniki"] = wyniki
        archiwum.append(sezon_obecny)
        zapisz_archiwum_sezonow(archiwum)

        zapisz_sezon({})

        await interaction.channel.send(content=f"🎉 Gratulacje dla najwybitniejszego gracza ligi: <@{mvp['discord_id']}>!", embed=embed)

class SeasonUICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sezon")
    @commands.has_permissions(administrator=True)
    async def panel_sezon(self, ctx):
        sezon_obecny = wczytaj_sezon()
        nazwa = sezon_obecny.get('nazwa')
        
        if not nazwa:
            embed = discord.Embed(
                title="🏆 Panel Zarządzania Sezonem",
                description="Obecnie nie trwa żaden sezon.\nNaciśnij przycisk poniżej, aby wystartować nową wojnę o punkty ELO.",
                color=0x2b2d31
            )
            await ctx.send(embed=embed, view=SeasonView())
            return
            
        msg = await ctx.send(f"⏳ Przeliczam aktualną stawkę bieżącego sezonu: **{nazwa}**...")
        
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

        wyniki.sort(key=lambda x: x["progres"], reverse=True)
        
        opis = f"Kto wykazuje najlepszy współczynnik postępu w **{nazwa}**?\n\n"
        for i, gracz in enumerate(wyniki, 1):
            pozycja = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            emotka_levelu = config.LEVEL_EMOJIS.get(str(gracz['poziom']), config.LEVEL_DEFAULT)
            znak = "+" if gracz['progres'] > 0 else ""
            
            opis += f"{pozycja} <@{gracz['discord_id']}> {emotka_levelu} — {gracz['obecne']} ELO *({znak}{gracz['progres']})*\n"
            
        embed = discord.Embed(
            title="Tabela Wyników Na Żywo",
            description=opis,
            color=0x2b2d31
        )
        embed.set_footer(text="Panel Wydziału Kontroli (Zarządzaj)")
        await msg.edit(content=None, embed=embed, view=SeasonView())

async def setup(bot):
    await bot.add_cog(SeasonUICog(bot))
