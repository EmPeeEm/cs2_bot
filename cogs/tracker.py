import discord
from discord.ext import commands, tasks
import config
import random
import datetime
import asyncio
from utils.database import (
    wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia,
    wczytaj_ostatnie_mecze, zapisz_ostatnie_mecze,
    wczytaj_tilt, zapisz_tilt, get_cfg, get_all_guilds_players,
    zapisz_historie_meczu
)
from utils.faceit_api import get_player_stats, get_last_match_stats, get_player_id, get_latest_match_id

class TrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player_id_cache = {} # Cache Nickname -> PlayerID
        self.check_matches.start()  # Monitorowanie meczów
        self.update_team_elo_channel.start()  # Średnie ELO ekipy

    def cog_unload(self):
        self.check_matches.cancel()
        self.update_team_elo_channel.cancel()

    @commands.command(name="config", aliases=["ustawienia", "settings", "cfg"])
    @commands.has_permissions(administrator=True)
    async def zarzadzaj_configiem(self, ctx, klucz: str = None, operacja: str = None, *, wartosc: str = None):
        """Zaawansowane zarządzanie konfiguracją bota per serwer."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        
        # 1. Podgląd ogólny
        if not klucz:
            embed = discord.Embed(
                title="⚙️ Konfiguracja Systemu",
                description=f"Użyj: `{ctx.prefix}config [klucz] [wartość]`\n\n"
                            "**Klucze:** `prefix`, `tilt_limit`, `main_color`, `kanal_eventow`, `kanal_sezonu`, `kanal_podsumowan_elo`\n"
                            "**Klucze wizualne:** `level_emojis`, `level_default`\n\n"
                            f"*Zdania (_texts) edytuj bezpośrednio w config.py!*",
                color=get_cfg(guild_id, "main_color", 0x2b2d31)
            )
            
            pola_tekstowe = ["prefix", "tilt_limit", "main_color"]
            for p in pola_tekstowe:
                v = ustawienia.get(p, f"*Domyślny (`{getattr(config, p.upper(), '?')}`)*")
                embed.add_field(name=p.replace("_", " ").title(), value=str(v), inline=True)

            embed.add_field(name="Kanał Eventów", value=f"<#{ustawienia.get('kanal_eventow')}>" if ustawienia.get('kanal_eventow') else "Brak", inline=True)
            embed.add_field(name="Kanał Sezonu", value=f"<#{ustawienia.get('kanal_sezonu')}>" if ustawienia.get('kanal_sezonu') else "Brak", inline=True)
            embed.add_field(name="Kanał ELO (Tydzień)", value=f"<#{ustawienia.get('kanal_podsumowan_elo')}>" if ustawienia.get('kanal_podsumowan_elo') else "Brak", inline=True)
            
            await ctx.send(embed=embed)
            return

        # 2. Blokada modyfikacji tekstów (_texts)
        if klucz and klucz.endswith("_texts"):
            await ctx.send(f"⚠️ Zdania `{klucz}` można zmieniać tylko bezpośrednio w pliku `config.py`.")
            return

        # 3. Standardowa zmiana (Klucz -> Wartość)
        if operacja and not wartosc:
            wartosc = operacja
            operacja = None

        if not wartosc:
            if klucz in ["kanal_eventow", "kanal_sezonu", "kanal_podsumowan_elo"]:
                nowa_wartosc = ctx.channel.id
            else:
                await ctx.send(f"❌ Musisz podać wartość dla `{klucz}`.")
                return
        else:
            if wartosc.startswith("<") and wartosc.endswith(">"):
                for char in ["<", ">", "#", "@", "!"]:
                    wartosc = wartosc.replace(char, "")
            
            if klucz == "main_color" and wartosc.startswith("#"):
                nowa_wartosc = int(wartosc.replace("#", ""), 16)
            elif wartosc.isdigit():
                nowa_wartosc = int(wartosc)
            else:
                nowa_wartosc = wartosc

        stara = ustawienia.get(klucz, "Domyślna")
        ustawienia[klucz] = nowa_wartosc
        zapisz_ustawienia(guild_id, ustawienia)
        await ctx.send(f"✅ Zmieniono `{klucz}`: `{stara}` ➔ `{nowa_wartosc}`")

    @commands.command(name="elo_setup")
    @commands.has_permissions(administrator=True)
    async def elo_setup(self, ctx):
        """Automatycznie tworzy kanał statystyk ze średnim ELO ekipy."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        ekipa = wczytaj_ekipe(guild_id)
        
        if not ekipa:
            return await ctx.send("❌ Twoja ekipa jest pusta!")

        msg = await ctx.send("⏳ Obliczam średnie ELO i przygotowuję kanał...")
        total_elo, count = 0, 0
        for p_id in ekipa.values():
            gracz = await get_player_stats(p_id)
            if gracz and gracz != "error" and gracz.get("elo"):
                total_elo += int(gracz["elo"])
                count += 1
        
        avg = round(total_elo / count, 1) if count > 0 else 0
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
        }
        
        try:
            new_channel = await ctx.guild.create_voice_channel(name=f"Średnie ELO: {avg}", overwrites=overwrites)
            ustawienia["kanal_elo"] = new_channel.id
            ustawienia["ostatnie_srednie_elo"] = avg
            zapisz_ustawienia(guild_id, ustawienia)
            await msg.edit(content=f"✅ Stworzono kanał: {new_channel.mention}")
        except Exception as e:
            await msg.edit(content=f"❌ Błąd: {e}")

    @tasks.loop(minutes=0.5)
    async def check_matches(self):
        await self.bot.wait_until_ready()
        mecze_baza = wczytaj_ostatnie_mecze()
        tilt_baza = wczytaj_tilt()
        all_guilds_players = get_all_guilds_players()
        if not all_guilds_players: return

        import asyncio
        async def check_player_match(p_id):
            current_match_id = await get_latest_match_id(p_id)
            if not current_match_id: return None
            zapis_bazy = mecze_baza.get(p_id)
            saved_match_id = zapis_bazy if isinstance(zapis_bazy, str) else zapis_bazy.get("match_id") if isinstance(zapis_bazy, dict) else None
            if current_match_id == saved_match_id:
                if isinstance(zapis_bazy, dict) and zapis_bazy.get("retry_count", 0) > 0: pass
                else: return None
            gracz = await get_player_stats(p_id, lifetime=False)
            mecz = await get_last_match_stats(p_id)
            return {"gracz": gracz, "mecz": mecz}

        tasks = [check_player_match(p_id) for p_id in all_guilds_players.keys()]
        results = await asyncio.gather(*tasks)
        zmieniono_baze, zmieniono_tilt = False, False
        guilds_to_update = set()

        for res in results:
            if not res or not res["mecz"]: continue
            gracz, mecz = res["gracz"], res["mecz"]
            p_id = gracz["player_id"]
            aktualny_match_id = mecz["match_id"]
            zapis_bazy = mecze_baza.get(p_id)
            zapisany_match_id = zapis_bazy if isinstance(zapis_bazy, str) else zapis_bazy.get("match_id") if isinstance(zapis_bazy, dict) else None
            
            obecne_elo = int(gracz.get('elo', 0)) if str(gracz.get('elo', '')).isdigit() else 0
            obecny_level = int(gracz.get('poziom', 0)) if str(gracz.get('poziom', '')).isdigit() else 0

            if zapisany_match_id != aktualny_match_id:
                if p_id in mecze_baza:
                    stare_elo = zapis_bazy.get("elo") if isinstance(zapis_bazy, dict) else None
                    stary_level = zapis_bazy.get("poziom") if isinstance(zapis_bazy, dict) else None

                    if stare_elo is not None and obecne_elo == stare_elo:
                        retry_count = zapis_bazy.get("retry_count", 0) if isinstance(zapis_bazy, dict) else 0
                        if retry_count < 3:
                            mecze_baza[p_id] = {"match_id": zapisany_match_id, "elo": stare_elo, "poziom": stary_level, "retry_count": retry_count + 1}
                            zmieniono_baze = True
                            continue

                    win = mecz['win']
                    stary_streak = tilt_baza.get(p_id, 0)
                    nowy_streak = (max(0, stary_streak) + 1) if win else (min(0, stary_streak) - 1)
                    tilt_baza[p_id] = nowy_streak
                    zmieniono_tilt = True
                    
                    guilds_to_notify = all_guilds_players.get(p_id, [])
                    for g_id, d_id in guilds_to_notify:
                        guilds_to_update.add(g_id)
                        guild = self.bot.get_guild(g_id)
                        if not guild: continue
                        ust = wczytaj_ustawienia(g_id)
                        kanal_id = ust.get("kanal_eventow")
                        if not kanal_id: continue
                        kanal = self.bot.get_channel(int(kanal_id))
                        if not kanal: continue

                        tilt_limit = ust.get("tilt_limit", 3)
                        elo_tekst = f"**{obecne_elo}**"
                        if stare_elo and obecne_elo > 0 and stare_elo > 0:
                            diff = obecne_elo - stare_elo
                            elo_tekst += f" *({'+' if diff > 0 else ''}{diff} ELO)*"

                        hltv = float(mecz.get('hltv', 0))
                        if hltv >= 1.30: ocena = "BESTIA"
                        elif hltv >= 1.10: ocena = "Bardzo dobrze"
                        elif hltv >= 0.90: ocena = "Solidnie"
                        elif hltv >= 0.70: ocena = "Słabo"
                        else: ocena = "BOT"

                        heading_roast = None
                        if stary_level and obecny_level != stary_level and stary_level > 0:
                            if obecny_level > stary_level: heading_roast = random.choice(get_cfg(g_id, 'awans_texts', config.AWANS_TEXTS))
                            else: heading_roast = random.choice(get_cfg(g_id, 'spadek_texts', config.SPADEK_TEXTS))
                        else:
                            pula = []
                            if hltv >= 1.30: pula.extend(get_cfg(g_id, 'hltv_beast_texts', config.HLTV_BEAST_TEXTS))
                            elif hltv < 0.70: pula.extend(get_cfg(g_id, 'hltv_bot_texts', config.HLTV_BOT_TEXTS))
                            if tilt_limit and str(tilt_limit).lower() != "off" and abs(nowy_streak) >= int(tilt_limit):
                                if nowy_streak < 0: pula.extend(get_cfg(g_id, 'lose_streak_texts', config.LOSE_STREAK_TEXTS))
                                else: pula.extend(get_cfg(g_id, 'win_streak_texts', config.WIN_STREAK_TEXTS))
                            if pula: heading_roast = random.choice(pula)

                        details = []
                        if stary_level and obecny_level != stary_level and stary_level > 0:
                            details.append(f"{'wbija' if obecny_level > stary_level else 'spada na'} **{obecny_level} LEVEL**")
                        if tilt_limit and str(tilt_limit).lower() != "off" and abs(nowy_streak) >= int(tilt_limit):
                            details.append(f"{'wygrywa' if win else 'przegrywa'} **{abs(nowy_streak)}** mecz z rzędu")
                        
                        alert_msg = f"**{heading_roast}**\n<@{d_id}> {' i '.join(details or [f'kończy z HLTV **{hltv:.2f}**'])}!" if heading_roast else None
                        emotki = get_cfg(g_id, "level_emojis", config.LEVEL_EMOJIS)
                        lvl_e = emotki.get(str(obecny_level), get_cfg(g_id, "level_default", config.LEVEL_DEFAULT))

                        embed = discord.Embed(
                            title=f"{'WYGRANA' if win else 'PRZEGRANA'}: Mecz na {mecz['mapa']} ({mecz['wynik']})",
                            description=f"{lvl_e} **{gracz['nick']}** | **{ocena}** (HLTV: **{hltv:.2f}**)\nBieżące punkty: {elo_tekst}",
                            color=0x00FF00 if win else 0xFF0000
                        )
                        mk = []
                        if mecz.get('triple_kills', 0) > 0: mk.append(f"3k: **{mecz['triple_kills']}**")
                        if mecz.get('quadro_kills', 0) > 0: mk.append(f"4k: **{mecz['quadro_kills']}**")
                        if mecz.get('penta_kills', 0) > 0: mk.append(f"**ACE**")
                        
                        embed.add_field(name="Rezultaty Strzeleckie", value=f"K/D/A: **{int(mecz['kille'])}/{int(mecz['dedy'])}/{int(mecz['asysty'])}**\nK/D Ratio: **{mecz['kd']}**\nEntry: **{int(mecz.get('entry_wins',0))}** ({int(mecz.get('entry_success',0))}%)\nADR: **{mecz['adr']}**{f'\nMulti: {", ".join(mk)}' if mk else ''}", inline=True)
                        extra = f"\nSnajper: **{mecz['sniper_kills']}** killi" if mecz.get('sniper_kills', 0) >= 5 else (f"\nFlash: **{int(mecz.get('flash_success',0))}%**" if int(mecz.get('flash_success',0)) > 60 else "")
                        embed.add_field(name="Utility i Zgranie", value=f"Headshoty: **{int(mecz['hs_procent'])}%**\nClutche: **{int(mecz.get('clutch_1v1',0)+mecz.get('clutch_1v2',0))}**\nUtility Dmg: **{int(mecz.get('ud', 0))}**\nMVPs: **{int(mecz['mvp'])}**{extra}", inline=True)
                        embed.set_thumbnail(url=gracz['avatar_url'])
                        try:
                            await kanal.send(embed=embed)
                            if alert_msg: await kanal.send(content=alert_msg)
                        except: pass

                mecze_baza[p_id] = {"match_id": aktualny_match_id, "elo": obecne_elo, "poziom": obecny_level}
                
                # ZAPIS DO HISTORII (DLA WYKRESÓW)
                try:
                    zapisz_historie_meczu(aktualny_match_id, p_id, mecz, obecne_elo, win)
                except Exception as e:
                    print(f"Błąd zapisu historii meczu: {e}")
                
                zmieniono_baze = True
                
        if zmieniono_baze:
            zapisz_ostatnie_mecze(mecze_baza)
            season_cog = self.bot.get_cog("SeasonUICog")
            if season_cog:
                for g_id in guilds_to_update: await season_cog.update_live_leaderboard(g_id)
        if zmieniono_tilt: zapisz_tilt(tilt_baza)

    @tasks.loop(hours=1.0)
    async def update_team_elo_channel(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        aktualny_tydzien = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]}"
        for guild in self.bot.guilds:
            try:
                guild_id = guild.id
                ust = wczytaj_ustawienia(guild_id)
                k_id = ust.get("kanal_elo")
                if not k_id or not str(k_id).isdigit(): continue
                k = self.bot.get_channel(int(k_id)) or await self.bot.fetch_channel(int(k_id))
                if not k: continue
                ekipa = wczytaj_ekipe(guild_id)
                if not ekipa: continue
                tasks = [get_player_stats(p_id, lifetime=False) for p_id in ekipa.values()]
                results = await asyncio.gather(*tasks)
                total, count = 0, 0
                for g in results:
                    if g and g != "error" and g.get("elo"):
                        total += int(g["elo"]); count += 1
                if count == 0: continue
                curr_avg = round(total / count, 1)
                last_avg = ust.get("ostatnie_srednie_elo", curr_avg)
                z_tydzien = ust.get("ostatni_tydzien_resetu", "")
                if z_tydzien and aktualny_tydzien != z_tydzien:
                    diff = round(curr_avg - last_avg, 1)
                    k_p_id = ust.get("kanal_podsumowan_elo")
                    if k_p_id:
                        k_p = self.bot.get_channel(int(k_p_id))
                        if k_p:
                            e = discord.Embed(title="📅 Tygodniowe Podsumowanie Średniego ELO", description=f"Zmiana: **{'+' if diff > 0 else ''}{diff}**!\nAktualna średnia: **{curr_avg}**.", color=get_cfg(guild_id, "main_color", 0x2b2d31))
                            await k_p.send(embed=e)
                    last_avg = curr_avg
                    ust["ostatnie_srednie_elo"] = curr_avg
                    ust["ostatni_tydzien_resetu"] = aktualny_tydzien
                    zapisz_ustawienia(guild_id, ust)
                elif not z_tydzien:
                    ust["ostatni_tydzien_resetu"] = aktualny_tydzien
                    zapisz_ustawienia(guild_id, ust)
                diff = round(curr_avg - last_avg, 1)
                new_name = f"Średnie ELO: {curr_avg}{f' ({"+" if diff > 0 else ""}{diff})' if diff != 0 else ''}"
                if k.name != new_name: await k.edit(name=new_name)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                continue

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
