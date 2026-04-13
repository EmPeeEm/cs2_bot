import discord
from discord.ext import commands, tasks
import config
import random
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

    @commands.command(name="config", aliases=["ustawienia", "settings", "cfg"])
    @commands.has_permissions(administrator=True)
    async def zarzadzaj_configiem(self, ctx, klucz: str = None, wartosc: str = None):
        """Podgląd i zmiana ustawień bota zapisanych w JSON."""
        ustawienia = wczytaj_ustawienia()
        
        # Jeśli brak argumentów - pokazujemy obecny stan
        if not klucz:
            embed = discord.Embed(
                title="⚙️ Konfiguracja Systemu",
                description="Oto aktualne parametry operacyjne bota. Możesz je zmienić wpisując: `?config [klucz] [wartość]`",
                color=0x2b2d31
            )
            
            for k, v in ustawienia.items():
                nazwa = k.replace("_", " ").title()
                val = f"`{v}`" if v else "*Nieustawione*"
                if k == "kanal_eventow" and v:
                    val = f"<#{v}> (`{v}`)"
                
                embed.add_field(name=nazwa, value=val, inline=False)
            
            # Jeśli prefixu brakuje w JSON, dopiszmy informację o domyślnym
            if "prefix" not in ustawienia:
                embed.add_field(name="Domyślny Prefix", value=f"`{config.PREFIX}` (Użyj `?config prefix [znak]`, aby zmienić)", inline=False)
            
            embed.set_footer(text="Zmiany są zapisywane natychmiastowo w data/ustawienia.json")
            await ctx.send(embed=embed)
            return

        # Jeśli podano klucz, ale nie podano wartości - błąd
        if not wartosc:
            await ctx.send(f"❌ Musisz podać wartość dla klucza `{klucz}`! Przykład: `?config tilt_limit 5`")
            return

        # Próba zmiany
        stara_wartosc = ustawienia.get(klucz, "Brak")
        
        # Konwersja typów (prymitywna detekcja liczb)
        if wartosc.isdigit():
            nowa_wartosc = int(wartosc)
        else:
            nowa_wartosc = wartosc

        ustawienia[klucz] = nowa_wartosc
        zapisz_ustawienia(ustawienia)
        
        await ctx.send(f"✅ Zmieniono ustawienie: **{klucz}**\nPoprzednio: `{stara_wartosc}` ➔ Teraz: `{nowa_wartosc}`")

    @tasks.loop(minutes=0.1)
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
            
            zapis_bazy = mecze_baza.get(id_gracza)
            zapisany_match_id = zapis_bazy if isinstance(zapis_bazy, str) else zapis_bazy.get("match_id") if isinstance(zapis_bazy, dict) else None
            
            # Główna weryfikacja
            if zapisany_match_id != aktualny_match_id:
                # Blokujemy spam starymi meczami przy starcie programu.
                # Pisze on powiadomienia TYLKO jeśli baza już go w ogóle zna.
                if id_gracza in mecze_baza:
                    win = mecz['win']
                    # Logika Tilt-Metera
                    stary_streak = tilt_baza.get(id_gracza, 0)
                    nowy_streak = (max(0, stary_streak) + 1) if win else (min(0, stary_streak) - 1)
                    tilt_baza[id_gracza] = nowy_streak
                    zmieniono_tilt = True
                    
                    tilt_limit = ustawienia.get("tilt_limit", 3)
                    
                    alert_msg = None
                    if tilt_limit and str(tilt_limit).lower() != "off":
                        limit_int = int(tilt_limit)
                        # Sprawdzamy przekroczenia
                        if nowy_streak <= -limit_int:
                            alert_msg = f"**{random.choice(config.LOSE_STREAK_TEXTS)}**\n<@{discord_id}> przegrywa **{abs(nowy_streak)}** mecz z rzędu."
                        elif nowy_streak >= limit_int:
                            alert_msg = f"**{random.choice(config.WIN_STREAK_TEXTS)}**\n<@{discord_id}> wygrywa **{nowy_streak}** mecz z rzędu."

                    # Obliczanie ELO Diff i Level Up
                    stare_elo = zapis_bazy.get("elo") if isinstance(zapis_bazy, dict) else None
                    stary_level = zapis_bazy.get("poziom") if isinstance(zapis_bazy, dict) else None
                    obecne_elo = int(gracz.get('elo', 0)) if str(gracz.get('elo', '')).isdigit() else 0
                    obecny_level = int(gracz.get('poziom', 0)) if str(gracz.get('poziom', '')).isdigit() else 0

                    elo_tekst = f"**{obecne_elo}**"
                    if stare_elo and obecne_elo > 0 and stare_elo > 0:
                        roznica = obecne_elo - stare_elo
                        znak = "+" if roznica > 0 else ""
                        if roznica != 0:
                            elo_tekst += f" *({znak}{roznica} ELO)*"
                            
                    # Nadpisywanie alert_msg przy awansie/spadku
                    if stary_level and obecny_level > 0 and stary_level > 0:
                        if obecny_level > stary_level:
                            alert_msg = f"🎉 **{random.choice(config.AWANS_TEXTS)}**\n<@{discord_id}> właśnie wbił **{obecny_level} LEVEL** na Faceit!"
                        elif obecny_level < stary_level:
                            alert_msg = f"💀 **{random.choice(config.SPADEK_TEXTS)}**\n<@{discord_id}> spadł na **{obecny_level} LEVEL** na Faceit."

                    kolor = 0x00FF00 if win else 0xFF0000
                    wynik_tekst = "WYGRANA" if win else "PRZEGRANA"

                    poziom = str(gracz.get('poziom', '0'))
                    emotka_levelu = getattr(config, 'LEVEL_EMOJIS', {}).get(poziom, getattr(config, 'LEVEL_DEFAULT', ''))

                    hltv = float(mecz.get('hltv', 0))
                    if hltv >= 1.3: 
                        ocena_tekst = random.choice(config.HLTV_BEAST_TEXTS)
                    elif hltv >= 1.05: 
                        ocena_tekst = "Solidna Gra"
                    elif hltv >= 0.85: 
                        ocena_tekst = "Przeciętnie"
                    else: 
                        ocena_tekst = random.choice(config.HLTV_BOT_TEXTS)

                    embed = discord.Embed(
                        title=f"{wynik_tekst}: Mecz na {mecz['mapa']} ({mecz['wynik']})",
                        description=f"{emotka_levelu} **{gracz['nick']}** | **{ocena_tekst}** (HLTV: **{hltv:.2f}**)\nBieżące punkty: {elo_tekst}",
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
                    
                    try:
                        await kanal.send(content=alert_msg, embed=embed)
                    except discord.Forbidden:
                        pass # Brak uprawnień do postowania na danym kanale

                # Zapisujemy mu ten mecz jako SZERSZY SŁOWNIK
                mecze_baza[id_gracza] = {
                    "match_id": aktualny_match_id,
                    "elo": int(gracz.get('elo', 0)) if str(gracz.get('elo', '')).isdigit() else 0,
                    "poziom": int(gracz.get('poziom', 0)) if str(gracz.get('poziom', '')).isdigit() else 0
                }
                zmieniono_baze = True
                
        if zmieniono_baze:
            zapisz_ostatnie_mecze(mecze_baza)
        if zmieniono_tilt:
            zapisz_tilt(tilt_baza)

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
