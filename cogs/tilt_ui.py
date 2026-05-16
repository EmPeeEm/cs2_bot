# cogs/tilt_ui.py
import discord
from discord.ext import commands
from utils.database import wczytaj_ustawienia, zapisz_ustawienia, get_cfg
import config

class TiltSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="3 mecze z rzędu", value="3"),
            discord.SelectOption(label="4 mecze z rzędu", value="4"),
            discord.SelectOption(label="5 meczów z rzędu", value="5"),
            discord.SelectOption(label="Wyłącz zupełnie", value="Off")
        ]
        super().__init__(placeholder="Wybierz limit po którym działa alert...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        wartosc = self.values[0]
        ustawienia = wczytaj_ustawienia(guild_id)
        
        if wartosc == "Off":
            ustawienia["tilt_limit"] = wartosc
            odp = "🛑 Tilt-Meter wyłączony."
        else:
            ustawienia["tilt_limit"] = int(wartosc)
            odp = f"✅ Limit ustawiony na **{wartosc}**."

        zapisz_ustawienia(guild_id, ustawienia)
        await interaction.response.send_message(odp, ephemeral=True)

class TiltView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TiltSelect())

class TiltUICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tilt_config")
    @commands.has_permissions(administrator=True)
    async def tilt_config(self, ctx):
        guild_id = ctx.guild.id
        embed = discord.Embed(
            title="⚙️ Tilt-Meter Konfiguracja", 
            description="Wybierz czułość alertów o seriach zwycięstw/porażek.",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        await ctx.send(embed=embed, view=TiltView())

async def setup(bot):
    await bot.add_cog(TiltUICog(bot))
