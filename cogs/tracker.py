import discord
from discord.ext import commands, tasks
import config
import random
from utils.database import (
    wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia,
    wczytaj_ostatnie_mecze, zapisz_ostatnie_mecze,
    wczytaj_tilt, zapisz_tilt, get_cfg
)
from utils.faceit_api import get_player_stats, get_last_match_stats

class TrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_matches.start()  # Uruchamia pętlę przy załadowaniu pliku

    def cog_unload(self):
        self.check_matches.cancel()  # Zatrzymuje pętlę, gdy bot gaśnie



    @commands.command(name="config", aliases=["ustawienia", "settings", "cfg"])
    @commands.has_permissions(administrator=True)
    async def zarzadzaj_configiem(self, ctx, klucz: str = None, operacja: str = None, *, wartosc: str = None):
        """Zaawansowane zarządzanie konfiguracją bota."""
        ustawienia = wczytaj_ustawienia()
        
        # 1. Podgląd ogólny
        if not klucz:
            embed = discord.Embed(
                title="⚙️ Konfiguracja Systemu",
                description=f"Użyj: `{ctx.prefix}config [klucz] [wartość]`\n\n"
                            "**Klucze:** `prefix`, `tilt_limit`, `main_color`, `kanal_eventow`, `kanal_sezonu`\n"
                            "**Klucze wizualne:** `level_emojis`, `level_default`\n\n"
                            f"*Zdania (_texts) edytuj bezpośrednio w config.py!*",
                color=get_cfg("main_color", 0x2b2d31)
            )
            
            pola_tekstowe = ["prefix", "tilt_limit", "main_color"]
            for p in pola_tekstowe:
                v = ustawienia.get(p, f"*Domyślny (`{getattr(config, p.upper(), '?')}`)*")
                embed.add_field(name=p.replace("_", " ").title(), value=str(v), inline=True)

            embed.add_field(name="Kanał Eventów", value=f"<#{ustawienia.get('kanal_eventow')}>" if ustawienia.get('kanal_eventow') else "Brak", inline=True)
            embed.add_field(name="Kanał Sezonu", value=f"<#{ustawienia.get('kanal_sezonu')}>" if ustawienia.get('kanal_sezonu') else "Brak", inline=True)
            
            await ctx.send(embed=embed)
            return

        # 2. Blokada modyfikacji tekstów (_texts)
        if klucz and klucz.endswith("_texts"):
            await ctx.send(f"⚠️ Zdania `{klucz}` można zmieniać tylko bezpośrednio w pliku `config.py`.")
            return

        # 3. Standardowa zmiana (Klucz -> Wartość)
        # Przesuwamy argumenty jeśli ktoś nie podał operacji (np. ?config prefix !)
        if operacja and not wartosc:
            wartosc = operacja
            operacja = None

        if not wartosc:
            if klucz in ["kanal_eventow", "kanal_sezonu"]:
                nowa_wartosc = ctx.channel.id
            else:
                await ctx.send(f"❌ Musisz podać wartość dla `{klucz}`.")
                return
        else:
            # Sanitacja ID kanałów
            if wartosc.startswith("<") and wartosc.endswith(">"):
                for char in ["<", ">", "#", "@", "!"]:
                    wartosc = wartosc.replace(char, "")
            
            # Konwersja kolorów HEX
            if klucz == "main_color" and wartosc.startswith("#"):
                nowa_wartosc = int(wartosc.replace("#", ""), 16)
            elif wartosc.isdigit():
                nowa_wartosc = int(wartosc)
            else:
                nowa_wartosc = wartosc

        stara = ustawienia.get(klucz, "Domyślna")
        ustawienia[klucz] = nowa_wartosc
        zapisz_ustawienia(ustawienia)
        await ctx.send(f"✅ Zmieniono `{klucz}`: `{stara}` ➔ `{nowa_wartosc}`")

    @tasks.loop(minutes=2.0)
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
                    
                    tilt_limit = get_cfg("tilt_limit", 3)
                    
                    # --- OBLICZENIA ELO I POZIOMÓW ---
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

                    # --- LOGIKA GENEROWANIA KOMENTARZA (ALERT MSG) ---
                    hltv = float(mecz.get('hltv', 0))
                    ocena_tekst = "Przeciętnie"
                    heading_roast = None
                    
                    # --- LOGIKA WYBORU KOMENTARZA (HEADING ROAST) ---
                    hltv = float(mecz.get('hltv', 0))
                    ocena_tekst = "Przeciętnie"
                    heading_roast = None
                    
                    # Ustalanie statusu do Embeda
                    if hltv >= 1.30: ocena_tekst = "⭐ BESTIA"
                    elif hltv >= 1.10: ocena_tekst = "✅ Bardzo dobrze"
                    elif hltv >= 0.90: ocena_tekst = "😐 Solidnie"
                    elif hltv >= 0.70: ocena_tekst = "📉 Słabo"
                    else: ocena_tekst = "💀 BOT"

                    # 1. Bezwzględny priorytet: Awans / Spadek
                    if stary_level and obecny_level != stary_level and stary_level > 0:
                        if obecny_level > stary_level:
                            heading_roast = random.choice(get_cfg('awans_texts', config.AWANS_TEXTS))
                        else:
                            heading_roast = random.choice(get_cfg('spadek_texts', config.SPADEK_TEXTS))
                    else:
                        # 2. Losowanie połączone: HLTV + Streaks
                        pula_tekstow = []
                        
                        # Dodajemy teksty HLTV (tylko Bestia/Bot)
                        if hltv >= 1.30:
                            pula_tekstow.extend(get_cfg('hltv_beast_texts', config.HLTV_BEAST_TEXTS))
                        elif hltv < 0.70:
                            pula_tekstow.extend(get_cfg('hltv_bot_texts', config.HLTV_BOT_TEXTS))
                            
                        # Dodajemy teksty serii (Streaki)
                        if tilt_limit and str(tilt_limit).lower() != "off":
                            limit_int = int(tilt_limit)
                            if nowy_streak <= -limit_int:
                                pula_tekstow.extend(get_cfg('lose_streak_texts', config.LOSE_STREAK_TEXTS))
                            elif nowy_streak >= limit_int:
                                pula_tekstow.extend(get_cfg('win_streak_texts', config.WIN_STREAK_TEXTS))
                                
                        if pula_tekstow:
                            heading_roast = random.choice(pula_tekstow)

                    # 3. Budowanie szczegółów pingu (Body)
                    details = []
                    
                    # Zmiana poziomu
                    if stary_level and obecny_level != stary_level and stary_level > 0:
                        type_str = "wbija" if obecny_level > stary_level else "spada na"
                        details.append(f"{type_str} **{obecny_level} LEVEL**")

                    # Streak
                    if tilt_limit and str(tilt_limit).lower() != "off":
                        limit_int = int(tilt_limit)
                        if abs(nowy_streak) >= limit_int:
                            type_s = "wygrywa" if win else "przegrywa"
                            details.append(f"{type_s} **{abs(nowy_streak)}** mecz z rzędu")

                    # Finalny montaż - Tylko jeśli mamy jakiś powód do pingu (nagłówek)
                    alert_msg = None
                    if heading_roast:
                        if not details: # Jeśli mamy roast za HLTV ale nic innego
                            details.append(f"kończy z HLTV **{hltv:.2f}**")
                        alert_msg = f"**{heading_roast}**\n<@{discord_id}> {' i '.join(details)}!"

                    kolor = 0x00FF00 if win else 0xFF0000
                    wynik_tekst = "WYGRANA" if win else "PRZEGRANA"

                    poziom_str = str(gracz.get('poziom', '0'))
                    emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
                    emotka_levelu = emotki.get(poziom_str, get_cfg("level_default", config.LEVEL_DEFAULT))

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
                        # Wysyłamy kartę zawsze
                        await kanal.send(embed=embed)
                        # Pingujemy tylko jeśli mamy coś ważnego do powiedzenia (ekstremum, awans lub streak)
                        if alert_msg:
                            await kanal.send(content=alert_msg)
                    except discord.Forbidden:
                        pass # Brak uprawnień do postowania na danym kanale
                    except Exception as e:
                        print(f"⚠️ Błąd przy wysyłaniu powiadomienia trackera: {e}")

                # Zapisujemy mu ten mecz jako SZERSZY SŁOWNIK
                mecze_baza[id_gracza] = {
                    "match_id": aktualny_match_id,
                    "elo": int(gracz.get('elo', 0)) if str(gracz.get('elo', '')).isdigit() else 0,
                    "poziom": int(gracz.get('poziom', 0)) if str(gracz.get('poziom', '')).isdigit() else 0
                }
                zmieniono_baze = True
                
        if zmieniono_baze:
            zapisz_ostatnie_mecze(mecze_baza)
            # Odświeżamy tabelę sezonową na żywo
            season_cog = self.bot.get_cog("SeasonUICog")
            if season_cog:
                await season_cog.update_live_leaderboard()
                
        if zmieniono_tilt:
            zapisz_tilt(tilt_baza)

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
