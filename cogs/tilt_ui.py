import discord
from discord.ext import commands
from utils.database import wczytaj_ustawienia, zapisz_ustawienia
import config

class TiltSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="3 mecze z rzędu", description="Wskaźnik odpala się po 3 winach/lossach", value="3"),
            discord.SelectOption(label="4 mecze z rzędu", description="Wskaźnik odpala się po 4 winach/lossach", value="4"),
            discord.SelectOption(label="5 meczów z rzędu", description="Wskaźnik odpala się po 5 winach/lossach", value="5"),
            discord.SelectOption(label="10 meczów z rzędu", description="Tylko dla totalnych wariatów", value="10"),
            discord.SelectOption(label="Włącz tylko do testów (1 runda)", description="Zareaguje od razu na 1", value="1"),
            discord.SelectOption(label="Wyłącz zupełnie", description="Wyłącz Tilt Meter", value="Off")
        ]
        super().__init__(placeholder="Wybierz limit po którym działa alert...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Sprawdzenie uprawnień admina pod maską interakcji
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tylko administratorzy mogą zmieniać to ustawienie.", ephemeral=True)
            return

        wartosc = self.values[0]
        ustawienia = wczytaj_ustawienia()
        if wartosc == "Off":
            ustawienia["tilt_limit"] = wartosc
            odp = "🛑 Tilt-Meter został całkowicie wyłączony."
        else:
            ustawienia["tilt_limit"] = int(wartosc)
            odp = f"✅ Tilt limit ustawiony pomyślnie na **{wartosc}**. Bot będzie informował po paśmie {wartosc} wygranych/przegranych meczy."

        zapisz_ustawienia(ustawienia)
        await interaction.response.send_message(odp, ephemeral=True)


class TiltView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Nie psuje się po określonym czasie
        self.add_item(TiltSelect())

class TiltUICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tilt_config")
    @commands.has_permissions(administrator=True)
    async def tilt_config(self, ctx):
        embed = discord.Embed(
            title="⚙️ Tilt-Meter Konfiguracja", 
            description="Zdecyduj po jakiej liczbie rozegranych meczy (np. po ilu porażkach lub wygranych z rzędu) bot ma powiadamiać Ekipę na kanale eventowym.",
            color=config.MAIN_COLOR
        )
        aw = await ctx.send(embed=embed, view=TiltView())

async def setup(bot):
    await bot.add_cog(TiltUICog(bot))
