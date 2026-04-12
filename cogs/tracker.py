import discord
from discord.ext import commands, tasks
import config
from utils.database import (
    wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia,
    wczytaj_ostatnie_mecze, zapisz_ostatnie_mecze,
    wczytaj_tilt, zapisz_tilt
)
from utils.faceit_api import get_player_stats, get_last_match_stats

class TrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_matches.start()  # Uruchamia pętlę przy załadowaniu pliku

    def cog_unload(self):
        self.check_matches.cancel()  # Zatrzymuje pętlę, gdy bot gaśnie

    @commands.command(name="ustaw_kanal")
    @commands.has_permissions(administrator=True)
    async def ustaw_kanal(self, ctx):
        """Ustawia obecny kanał jako docelowy dla eventów meczowych."""
        ustawienia = wczytaj_ustawienia()
        ustawienia["kanal_eventow"] = ctx.channel.id
        zapisz_ustawienia(ustawienia)
        await ctx.send("✅ Ten kanał został pomyślnie ustawiony jako domyślny dla powiadomień Faceit! Gdy ktokolwiek z ekipy zagra nowy mecz, napiszę tutaj.")

    @tasks.loop(minutes=5.0)
    async def check_matches(self):
        # Czekamy, aż bot zsynchronizuje się z siecią Discord
        await self.bot.wait_until_ready()
        
        # Wczytujemy z bazy danych
        ustawienia = wczytaj_ustawienia()
        kanal_id = ustawienia.get("kanal_eventow")
        
        if not kanal_id:
            # Kanał jeszcze nie zaistniał, nie marnujemy requestów do API
            return
            
        kanal = self.bot.get_channel(kanal_id)
        if not kanal:
            return  # Możliwe, że kanał ustawiony kiedyś tam został usunięty z Discorda
            
        ekipa = wczytaj_ekipe()
        mecze_baza = wczytaj_ostatnie_mecze()
        tilt_baza = wczytaj_tilt()
        zmieniono_baze = False
        zmieniono_tilt = False
        
        for discord_id, nick in ekipa.items():
            gracz = await get_player_stats(nick)
            if not gracz or gracz == "error":
                continue
                
            mecz = await get_last_match_stats(gracz["player_id"])
            if not mecz:
                continue
                
            # Sprawdzamy czy ten sam match id już istnieje w lokalnej bazie
            id_gracza = gracz["player_id"]
            aktualny_match_id = mecz["match_id"]
            
            # Główna weryfikacja
            if mecze_baza.get(id_gracza) != aktualny_match_id:
                # Blokujemy spam starymi meczami przy starcie programu.
                # Pisze on powiadomienia TYLKO jeśli baza już go w ogóle zna.
                if id_gracza in mecze_baza:
                    win = mecz['win']
                    # Logika Tilt-Metera
                    stary_streak = tilt_baza.get(id_gracza, 0)
                    nowy_streak = (max(0, stary_streak) + 1) if win else (min(0, stary_streak) - 1)
                    tilt_baza[id_gracza] = nowy_streak
                    zmieniono_tilt = True
                    
                    tilt_limit = ustawienia.get("tilt_limit", 3) # Domyślnie 3
                    
                    alert_msg = None
                    if tilt_limit and str(tilt_limit).lower() != "off":
                        limit_int = int(tilt_limit)
                        # Sprawdzamy przekroczenia
                        if nowy_streak <= -limit_int:
                            alert_msg = f"📉 **UWAGA!** <@{discord_id}> przegrywa **{abs(nowy_streak)}** mecz z rzędu! Tryb węgla aktywowany! Zróbcie mu herbaty 🫖"
                        elif nowy_streak >= limit_int:
                            alert_msg = f"🔥 **ON FIRE!** <@{discord_id}> wygrywa **{nowy_streak}** mecz z rzędu! Czysta dominacja! 👑"

                    kolor = 0x00FF00 if win else 0xFF0000
                    wynik_tekst = "WYGRANA" if win else "PRZEGRANA"

                    embed = discord.Embed(
                        title=f"Ktoś ukończył mecz: {gracz['nick']} — {wynik_tekst}",
                        description=f"🗺️ Mapa: **{mecz['mapa']}** | 🏆 Wynik: **{mecz['wynik']}**",
                        color=kolor
                    )
                    
                    embed.add_field(name="K/D/A", value=f"**{mecz['kille']}** / **{mecz['dedy']}** / **{mecz['asysty']}**", inline=True)
                    embed.add_field(name="K/D Ratio", value=f"**{mecz['kd']}**", inline=True)
                    embed.add_field(name="Headshots", value=f"**{mecz['hs_procent']}%**", inline=True)
                    embed.add_field(name="MVPs", value=f"⭐ **{mecz['mvp']}**", inline=True)
                    
                    embed.set_thumbnail(url=gracz['avatar_url'])
                    embed.set_footer(text=f"Aktualne ELO: {gracz['elo']} — {gracz['poziom']} level")
                    
                    try:
                        await kanal.send(content=alert_msg, embed=embed)
                    except discord.Forbidden:
                        pass # Brak uprawnień do postowania na danym kanale

                # Zapisujemy mu ten mecz, by nie wysłać go drugi raz
                mecze_baza[id_gracza] = aktualny_match_id
                zmieniono_baze = True
                
        if zmieniono_baze:
            zapisz_ostatnie_mecze(mecze_baza)
        if zmieniono_tilt:
            zapisz_tilt(tilt_baza)

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
