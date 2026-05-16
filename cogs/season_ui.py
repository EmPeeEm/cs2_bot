# cogs/season_ui.py
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
        if "nazwa" not in sezon_obecny:
            await interaction.response.send_message("⚠️ Brak aktywnego sezonu.", ephemeral=True)
            return

        await interaction.response.defer()
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
            await interaction.followup.send("❌ Brak danych.")
            return

        mvp = wyniki[0]
        rola_mvp = discord.utils.get(interaction.guild.roles, name="✨ MVP Sezonu")
        if not rola_mvp:
            try: rola_mvp = await interaction.guild.create_role(name="✨ MVP Sezonu", color=0xFFD700, hoist=True)
            except: pass
                
        if rola_mvp:
            for member in rola_mvp.members:
                try: await member.remove_roles(rola_mvp)
                except: pass
            mvp_member = interaction.guild.get_member(int(mvp['discord_id']))
            if mvp_member:
                try: await mvp_member.add_roles(rola_mvp)
                except: pass
        
        opis = f"🏁 **KONIEC SEZONU: {sezon_obecny['nazwa']}**\n\n"
        for i, res in enumerate(wyniki, 1):
            znak = "+" if res['progres'] > 0 else ""
            oznaczenie = "🥇 MVP" if i == 1 else f"{i}."
            emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
            emotka_levelu = emotki.get(str(res['poziom']), get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
            opis += f"{oznaczenie} <@{res['discord_id']}> {emotka_levelu} — **{res['obecne']}** ELO *({znak}{res['progres']} pkt)*\n"

        embed = discord.Embed(title=f"Podsumowanie Sezonu", description=opis, color=get_cfg(guild_id, "main_color", 0x2b2d31))
        
        # Archiwizacja (Logika uproszczona pod SQL)
        zapisz_sezon(guild_id, {}) # Czyścimy aktywny sezon
        
        await interaction.followup.send(embed=embed)

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
        if not sezon or "nazwa" not in sezon or "leaderboard_msg_id" not in sezon:
            return

        embed = await self._generate_leaderboard_embed(guild_id, sezon['nazwa'], sezon.get('start_elo', {}))
        channel = self.bot.get_channel(int(sezon["leaderboard_channel_id"]))
        if not channel: return

        try:
            msg = await channel.fetch_message(int(sezon["leaderboard_msg_id"]))
            await msg.edit(embed=embed)
        except: pass

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

async def setup(bot):
    await bot.add_cog(SeasonUICog(bot))
