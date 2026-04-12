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
        await ctx.send("Ten kanał został pomyślnie ustawiony jako domyślny dla powiadomień Faceit! Gdy ktokolwiek z ekipy zagra nowy mecz, napiszę tutaj.")

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
                            alert_msg = f"**UWAGA!** <@{discord_id}> przegrywa **{abs(nowy_streak)}** mecz z rzędu. Tryb węgla aktywowany."
                        elif nowy_streak >= limit_int:
                            alert_msg = f"**ON FIRE!** <@{discord_id}> wygrywa **{nowy_streak}** mecz z rzędu. Czysta dominacja!"

                    kolor = 0x00FF00 if win else 0xFF0000
                    wynik_tekst = "WYGRANA" if win else "PRZEGRANA"

                    import config
                    poziom = str(gracz.get('poziom', '0'))
                    emotka_levelu = getattr(config, 'LEVEL_EMOJIS', {}).get(poziom, getattr(config, 'LEVEL_DEFAULT', ''))

                    # Dynamiczna karta meczowa w oparciu o ocenę
                    hltv = float(mecz.get('hltv', 0))
                    if hltv >= 1.5:
                        ocena_tekst = "Totalna Dominacja"
                    elif hltv >= 1.3:
                        ocena_tekst = "Rewelacyjny Występ"
                    elif hltv >= 1.05:
                        ocena_tekst = "Solidna Gra"
                    elif hltv >= 0.85:
                        ocena_tekst = "Przeciętnie"
                    else:
                        ocena_tekst = "Słaby Występ"

                    embed = discord.Embed(
                        title=f"{wynik_tekst}: Mecz na {mecz['mapa']} ({mecz['wynik']})",
                        description=f"{emotka_levelu} **{gracz['nick']}** | Est. Rating (HLTV): **{hltv:.2f}** ({ocena_tekst})",
                        color=kolor
                    )
                    
                    embed.add_field(
                        name="Rezultaty Strzeleckie", 
                        value=f"K/D/A: **{mecz['kille']} / {mecz['dedy']} / {mecz['asysty']}**\n"
                              f"K/D Ratio: **{mecz['kd']}**\n"
                              f"Entry Kills: **{int(mecz.get('entry_wins', 0))}**\n"
                              f"ADR: **{mecz.get('adr', 0)}**", 
                        inline=True
                    )
                    
                    suma_clutches = int(mecz.get('clutch_1v1', 0) + mecz.get('clutch_1v2', 0))
                    
                    embed.add_field(
                        name="Utility i Zgranie", 
                        value=f"Headshoty: **{mecz['hs_procent']}%**\n"
                              f"Wygrane Clutche: **{suma_clutches}**\n"
                              f"Utility Dmg: **{mecz.get('ud', 0)}**\n"
                              f"MVPs: **{mecz['mvp']}**", 
                        inline=True
                    )
                    
                    embed.set_thumbnail(url=gracz['avatar_url'])
                    embed.set_footer(text=f"Aktualne ELO wpisane w Faceit: {gracz['elo']}")
                    
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
