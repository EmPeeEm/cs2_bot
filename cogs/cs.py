# cogs/cs.py

import discord
from discord.ext import commands
import typing
from utils.faceit_api import get_player_stats, is_uuid, get_player_id
import config
from utils.database import (
    wczytaj_ekipe, zapisz_ekipe, wczytaj_sezon, zapisz_sezon, 
    get_cfg, pobierz_historie_elo, pobierz_mecze_z_bazy
)
from utils.charts import generuj_wykres_elo

class HelpView(discord.ui.View):
    def __init__(self, bot_cog, ctx, current_page="main"):
        super().__init__(timeout=180)
        self.bot_cog = bot_cog
        self.ctx = ctx
        self.current_page = current_page
        self._update_buttons()

    def _update_buttons(self):
        self.clear_items()
        
        btn_main = discord.ui.Button(
            label="Menu Główne",
            emoji="🏠",
            style=discord.ButtonStyle.primary if self.current_page == "main" else discord.ButtonStyle.secondary,
            custom_id="help_main",
            disabled=(self.current_page == "main")
        )
        btn_user = discord.ui.Button(
            label="Komendy Gracza",
            emoji="👤",
            style=discord.ButtonStyle.primary if self.current_page == "user" else discord.ButtonStyle.secondary,
            custom_id="help_user",
            disabled=(self.current_page == "user")
        )
        btn_admin = discord.ui.Button(
            label="Komendy Admina",
            emoji="🛠️",
            style=discord.ButtonStyle.danger if self.current_page == "admin" else discord.ButtonStyle.secondary,
            custom_id="help_admin",
            disabled=(self.current_page == "admin")
        )
        
        btn_main.callback = self.on_main_click
        btn_user.callback = self.on_user_click
        btn_admin.callback = self.on_admin_click
        
        self.add_item(btn_main)
        self.add_item(btn_user)
        self.add_item(btn_admin)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Tylko osoba, która wywołała komendę pomocy, może korzystać z tych przycisków.", ephemeral=True)
            return False
        return True

    async def on_main_click(self, interaction: discord.Interaction):
        self.current_page = "main"
        self._update_buttons()
        embed = self.bot_cog.get_main_help_embed(self.ctx)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_user_click(self, interaction: discord.Interaction):
        self.current_page = "user"
        self._update_buttons()
        embed = self.bot_cog.get_user_help_embed(self.ctx)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_admin_click(self, interaction: discord.Interaction):
        self.current_page = "admin"
        self._update_buttons()
        embed = self.bot_cog.get_admin_help_embed(self.ctx)
        await interaction.response.edit_message(embed=embed, view=self)


class CSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="stats", aliases=["statystyki", "s", "fs"], description="Paszport statystyk gracza Faceit")
    async def sprawdz_elo(self, ctx, gracz: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        args = (gracz,) if gracz else ()
        nickname, display_name = self.parse_identifier(ctx, args)
        if not await self.check_nick(ctx, nickname, gracz):
            return

        msg = await ctx.send(f"Przeszukuję serwery Faceit dla **{display_name}**...")
        
        # Pobieramy dane używając naszego pliku z utils
        dane = await get_player_stats(nickname)
        
        if dane is None:
            await msg.edit(content=f"Nie znalazłem gracza `{nickname}` na Faceit.")
            return
        elif dane == "error":
            await msg.edit(content="Błąd łączenia z Faceit. Spróbuj ponownie później.")
            return

        # Budujemy profesjonalną ramkę (Embed)
        embed = discord.Embed(
            title=f"Statystyki FACEIT - {dane['nick']}",
            url=dane['url_profilu'],
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        embed.set_thumbnail(url=dane['avatar_url'])
        # Wyciągamy level gracza jako tekst (np. "8")
        poziom = str(dane['poziom'])
        
        # Szukamy emotki w configu.
        emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))

        embed.description = f"{emotka_levelu} **{dane['elo']} ELO**  |  Rozegrane Mecze: **{dane['lifetime_matches']}**"
        
        embed.add_field(name="Ratingi i Pomiary", 
                        value=f"K/D Ratio: **{dane['lifetime_kd']}**\n"
                              f"ADR (Śr. Obr.): **{dane['lifetime_adr']}**\n"
                              f"Headshoty (HS%): **{dane['lifetime_hs']}%**", inline=True)

        embed.add_field(name="Skuteczność Ogólna", 
                        value=f"Win Rate: **{dane['lifetime_winrate']}%**\n"
                              f"Wygrane Mecze: **{dane['lifetime_wins']}**\n"
                              f"Obecny Winstreak: **{dane['lifetime_winstreak']}**", inline=True)
                              
        embed.add_field(name="Zgranie i Playmaking", 
                        value=f"Wygrane Clutche (1vX): **{dane['lifetime_clutches']}**\n"
                              f"Otwierające zab. (Entry): **{dane['lifetime_entry']}**", inline=False)
                              

        # Edytujemy wiadomość ładowania, podmieniając ją na ładnego embeda
        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(name="last", aliases=["mecz", "l", "fl"], description="Szczegółowa karta ostatniego meczu")
    async def ostatni_mecz(self, ctx, gracz: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        args = (gracz,) if gracz else ()
        nickname, display_name = self.parse_identifier(ctx, args)
        if not await self.check_nick(ctx, nickname, gracz):
            return

        msg = await ctx.send(f"Pobieram dane o ostatnim meczu dla **{display_name}**...")
        
        # Najpierw musimy pobrać player_id
        gracz = await get_player_stats(nickname)
        if not gracz:
            await msg.edit(content=f"Nie znalazłem gracza `{nickname}`.")
            return

        # Teraz pobieramy staty meczu
        from utils.faceit_api import get_last_match_stats # Import wewnątrz, żeby uniknąć problemów
        mecz = await get_last_match_stats(gracz['player_id'])
        
        if not mecz:
            await msg.edit(content=f"Nie znalazłem ostatniego meczu CS2 dla gracza `{nickname}`.")
            return

        # Kolor w zależności od win/loss
        kolor = 0x00FF00 if mecz['win'] else 0xFF0000
        wynik_tekst = "WYGRANA" if mecz['win'] else "PRZEGRANA"
        
        poziom = str(gracz['poziom'])
        emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))

        embed = discord.Embed(
            title=f"Ostatni mecz: {gracz['nick']} — {wynik_tekst}",
            description=f"Mapa: **{mecz['mapa']}** | Wynik: **{mecz['wynik']}**\nObecna ranga: {emotka_levelu} **{gracz['elo']} ELO**",
            color=kolor
        )
        
        # Grupowanie statystyk strzeleckich
        mk = []
        if mecz.get('triple_kills', 0) > 0: mk.append(f"3k: **{mecz['triple_kills']}**")
        if mecz.get('quadro_kills', 0) > 0: mk.append(f"4k: **{mecz['quadro_kills']}**")
        if mecz.get('penta_kills', 0) > 0: mk.append(f"**ACE**")
        mk_text = f"\nMulti: {', '.join(mk)}" if mk else ""

        entry_rate = int(mecz.get('entry_success', 0))
        entry_text = f"Entry Wins: **{int(mecz.get('entry_wins', 0))}** (Skuteczność: **{entry_rate}%**)"

        embed.add_field(
            name="Rezultaty Strzeleckie", 
            value=f"K/D/A: **{int(mecz['kille'])} / {int(mecz['dedy'])} / {int(mecz['asysty'])}**\n"
                  f"K/D Ratio: **{mecz['kd']}**\n"
                  f"{entry_text}\n"
                  f"ADR: **{mecz['adr']}**"
                  f"{mk_text}", 
            inline=True
        )
        
        # Grupowanie utility
        suma_clutches = int(mecz.get('clutch_1v1', 0) + mecz.get('clutch_1v2', 0))
        flash_rate = int(mecz.get('flash_success', 0))
        
        extra_stats = ""
        if mecz.get('sniper_kills', 0) >= 5:
            extra_stats = f"\nSnajper: **{mecz['sniper_kills']}** killi"
        elif flash_rate > 60:
            extra_stats = f"\nFlash Success: **{flash_rate}%**"

        embed.add_field(
            name="Utility i Zgranie", 
            value=f"Headshoty: **{int(mecz['hs_procent'])}%**\n"
                  f"Wygrane Clutche: **{suma_clutches}**\n"
                  f"Utility Dmg: **{int(mecz.get('ud', 0))}**\n"
                  f"MVPs: **{int(mecz['mvp'])}**"
                  f"{extra_stats}", 
            inline=True
        )
        
        embed.set_thumbnail(url=gracz['avatar_url'])

        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(name="top", aliases=["leaderboard", "ranking"], description="Tabela liderów ekipy serwera posortowana wg ELO")
    async def tablica_wynikow(self, ctx):
        await ctx.defer()
        guild_id = ctx.guild.id
        # Ta komenda musi sprawdzić kilka osób, więc zajmie botowi sekundę lub dwie
        msg = await ctx.send("Zbieram dane z serwerów Faceit... (to potrwa chwilę)")
        
        # (NOWY KOD)
        ekipa = wczytaj_ekipe(guild_id)
        
        sezon = wczytaj_sezon(guild_id)
        sezon_aktywny = "nazwa" in sezon
        
        if not ekipa:
            await msg.edit(content=f"Ekipa jest pusta! Dodaj kogoś używając `{ctx.prefix}polacz [nick]`.")
            return

        import asyncio
        tasks = []
        for discord_id, p_id in ekipa.items():
            tasks.append(get_player_stats(p_id, lifetime=False))
        
        results = await asyncio.gather(*tasks)
        
        wyniki = []
        ekipa_items = list(ekipa.items())
        for i, dane in enumerate(results):
            # Sprawdzamy czy pobrało dane poprawnie i czy gracz ma jakieś ELO
            if dane and dane != "error":
                dane["discord_id"] = ekipa_items[i][0]
                wyniki.append(dane)

        # Sortowanie graczy po ELO od najwyższego do najniższego
        # (Zabezpieczenie na wypadek gdyby ktoś miał status 'Brak' ELO)
        wyniki.sort(key=lambda x: int(x['elo']) if str(x['elo']).isdigit() else 0, reverse=True)

        # Tworzymy ładną ramkę
        embed = discord.Embed(
            title=f"Ranking Ekipy - {sezon['nazwa'] if sezon_aktywny else 'FACEIT'}",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )

        opis = ""
        # Przechodzimy przez posortowaną listę, dodając numerki (1, 2, 3...)
        for i, gracz in enumerate(wyniki, 1):
            # Fajny detal: medale dla top 3
            if i == 1:
                pozycja = "🥇"
            elif i == 2:
                pozycja = "🥈"
            elif i == 3:
                pozycja = "🥉"
            else:
                pozycja = f"**{i}.**"

            poziom = str(gracz['poziom'])
            emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
            emotka_levelu = emotki.get(poziom, get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
            
            # Wrzucamy emotkę poziomu przed napisem ELO
            # Pinguje subtelnie bez wzmianki glownej (tylko wyswietla w Embedzie imie jako @DiscordUser)
            opis += f"{pozycja} <@{gracz['discord_id']}> {emotka_levelu} — ELO: **{gracz['elo']}**"
            
            # (NOWY KOD) Sprawdzamy statystyki bieżącego sezonu:
            if sezon_aktywny and gracz['player_id'] in sezon.get('start_elo', {}):
                obecne = int(gracz['elo']) if str(gracz['elo']).isdigit() else 0
                start_elo = sezon['start_elo'][gracz['player_id']]
                diff = obecne - start_elo
                if diff > 0:
                    opis += f" *(+{diff} )*\n"
                elif diff < 0:
                    opis += f" *({diff} )*\n"
                else:
                    opis += " *(Bez zmian)*\n"
            else:
                opis += "\n"

        embed.description = opis if opis else "Brak danych do wyświetlenia."

        # Edytujemy naszą wiadomość o ładowaniu na gotową tablicę
        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(name="streaks", aliases=["passa", "st"], description="Zestawienie aktualnych serii zwycięstw / porażek ekipy")
    async def zestawienie_passy(self, ctx):
        """Wyświetla aktualne serie zwycięstw/porażek dla całej ekipy."""
        await ctx.defer()
        from utils.database import wczytaj_tilt
        guild_id = ctx.guild.id
        msg = await ctx.send("Sprawdzam, kto dzisiaj carruje, a kto sabotuje... 🔍")
        
        ekipa = wczytaj_ekipe(guild_id)
        tilt_baza = wczytaj_tilt()
        
        if not ekipa:
            await msg.edit(content="Ekipa jest pusta!")
            return

        import asyncio
        tasks = []
        ekipa_ids = list(ekipa.keys())
        for p_id in ekipa.values():
            tasks.append(get_player_stats(p_id, lifetime=False))
            
        results = await asyncio.gather(*tasks)

        wyniki = []
        for i, dane in enumerate(results):
            if dane and dane != "error":
                pid = dane['player_id']
                streak = tilt_baza.get(pid, 0)
                wyniki.append({
                    "nick": dane['nick'],
                    "discord_id": ekipa_ids[i],
                    "streak": streak
                })

        # Sortujemy: najpierw największe winstreaki, na dole największe loostreaki
        wyniki.sort(key=lambda x: x["streak"], reverse=True)

        embed = discord.Embed(
            title="🔥 Termometr Ekipy — Serie Gier",
            description="Zestawienie aktualnych serii zwycięstw i porażek w bieżącej sesji.",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )

        opis = ""
        for r in wyniki:
            if r['streak'] > 0:
                ikonka = "🔥" * min(r['streak'], 3) # Max 3 ogniki
                stan = f"**{r['streak']} Win(s)**"
            elif r['streak'] < 0:
                ikonka = "❄️" * min(abs(r['streak']), 3)
                stan = f"**{abs(r['streak'])} Loss(es)**"
            else:
                ikonka = "⚪"
                stan = "Brak serii"
            
            opis += f"{ikonka} <@{r['discord_id']}> — {stan}\n"

        embed.description = opis if opis else "Wszyscy na czysto!"
        embed.set_footer(text="Passa liczona od ostatniego wykrycia przez bota.")
        
        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(name="polacz", aliases=["link", "ln"], description="Połącz konto Discord z profilem Faceit")
    async def polacz_konto(self, ctx, nick: str, gracz: typing.Optional[discord.Member] = None):
        guild_id = ctx.guild.id
        discord_id = str(ctx.author.id)
        faceit_nick = nick

        # Sprawdzanie czy kogoś oznaczono lub przekazano w parametrze
        if gracz:
            discord_id = str(gracz.id)
        elif ctx.message and ctx.message.mentions:
            target = ctx.message.mentions[0]
            discord_id = str(target.id)
            if nick.startswith("<@"):
                parts = ctx.message.content.split()
                for p in parts[1:]:
                    if not p.startswith("<@"):
                        faceit_nick = p
                        break
        elif nick.startswith("<@"):
            user_id = nick.replace("<@", "").replace("!", "").replace(">", "")
            if user_id.isdigit():
                discord_id = user_id
                if ctx.message:
                    parts = ctx.message.content.split()
                    for p in parts[1:]:
                        if not p.startswith("<@"):
                            faceit_nick = p
                            break

        if not faceit_nick or faceit_nick.startswith("<@"):
            await ctx.send("Zabrakło nazwy gracza z Faceit! Użycie: `/polacz nick: [TwójNick]`.")
            return

        ekipa = wczytaj_ekipe(guild_id)
        
        has_target = bool(gracz or (ctx.message and ctx.message.mentions))
        if discord_id in ekipa and not has_target:
            await ctx.send(f"Masz już połączone konto. Użycie dla innego użytkownika: `{ctx.prefix}polacz [nick] @Ktoś`.")
            return

        msg = await ctx.send(f"Łączę profil <@{discord_id}> z kontem Faceit: **{faceit_nick}**...")

        from utils.faceit_api import get_player_stats
        test = await get_player_stats(faceit_nick)
        if not test or test == "error":
            await msg.edit(content=f"Taki gracz nie istnieje na Faceit: **{faceit_nick}**.")
            return

        player_id = test['player_id']
        ekipa[discord_id] = player_id
        zapisz_ekipe(guild_id, ekipa)
        
        # WPISANIE DO TRWAJĄCEGO SEZONU (Zabezpiecza przed omijaniem late-joinerów)
        sezon = wczytaj_sezon(guild_id)
        if "nazwa" in sezon and str(test.get('elo', 'Brak')).isdigit():
            player_id = str(test['player_id'])
            if "start_elo" not in sezon:
                sezon["start_elo"] = {}
                
            if player_id not in sezon["start_elo"]:
                sezon["start_elo"][player_id] = int(test['elo'])
                zapisz_sezon(guild_id, sezon)
                
        await msg.edit(content=f"<@{discord_id}> pomyślnie powiązano z kontem **{faceit_nick}** na Faceit.")

    @commands.hybrid_command(name="odlacz", aliases=["unlink", "un"], description="Odłącz konto Faceit od profilu Discord")
    async def odlacz_konto(self, ctx, gracz: typing.Optional[discord.Member] = None):
        guild_id = ctx.guild.id
        ekipa = wczytaj_ekipe(guild_id)
        
        discord_id = str(ctx.author.id)
        if gracz:
            discord_id = str(gracz.id)
        elif ctx.message and ctx.message.mentions:
            discord_id = str(ctx.message.mentions[0].id)
            
        if discord_id in ekipa:
            usuniety = ekipa.pop(discord_id)
            zapisz_ekipe(guild_id, ekipa)
            await ctx.send(f"Odłączono powiązanie z profilu <@{discord_id}>.")
        else:
            await ctx.send(f"Ten profil nie ma obecnie podpiętego konta Faceit.")

    @commands.hybrid_command(name="recent", aliases=["ostatnie", "r", "fr"], description="Średnie statystyki z ostatnich gier z bazy danych")
    async def komenda_stats(self, ctx, argument1: typing.Optional[str] = None, argument2: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        limit = 20
        
        raw_args = [a for a in [argument1, argument2] if a is not None]
        parsed_args = []
        for arg in raw_args:
            if arg.isdigit():
                limit = int(arg)
            else:
                parsed_args.append(arg)
        
        nickname, display_name = self.parse_identifier(ctx, parsed_args)
        
        if not await self.check_nick(ctx, nickname, parsed_args[0] if parsed_args else None):
            return
                
        # Zabezpieczenie przed nadużyciami limitu
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 10
            
        msg = await ctx.send(f"Pobieram historię **{limit}** ostatnich meczów dla **{display_name}**. Może to potrwać kilka sekund...")
        
        gracz = await get_player_stats(nickname)
        if not gracz or gracz == "error":
            await msg.edit(content=f"Nie znalazłem gracza `{nickname}`.")
            return

        # Pobieramy mecze z bazy danych
        import asyncio
        mecze = await asyncio.to_thread(pobierz_mecze_z_bazy, gracz['player_id'], limit)
        
        if not mecze:
            await msg.edit(content=f"⚠️ Brak zarejestrowanych meczów gracza `{nickname}` w bazie danych bota.")
            return
            
        wygrane = sum(1 for m in mecze if m['win'])
        wr = int((wygrane / len(mecze)) * 100)
        
        # Bilans ELO na przestrzeni tych meczów
        elo_diff = sum(m.get('elo_gain', 0) for m in mecze)
        if elo_diff > 0:
            elo_diff_text = f"+{elo_diff} ELO"
        elif elo_diff < 0:
            elo_diff_text = f"{elo_diff} ELO"
        else:
            elo_diff_text = "Bez zmian"
        
        avg_kills = sum(m['kille'] for m in mecze) / len(mecze)
        avg_kd = sum(m['kd'] for m in mecze) / len(mecze)
        avg_kr = sum(m['kr'] for m in mecze) / len(mecze)
        avg_hs = sum(m['hs_procent'] for m in mecze) / len(mecze)
        suma_mvp = int(sum(m['mvp'] for m in mecze))
        
        avg_adr = sum(m['adr'] for m in mecze) / len(mecze)
        avg_ud = sum(m['ud'] for m in mecze) / len(mecze)
        avg_ef = sum(m['ef'] for m in mecze) / len(mecze)
        sum_entry = int(sum(m['entry_wins'] for m in mecze))
        sum_clutches = int(sum(m['clutch_1v1'] + m['clutch_1v2'] for m in mecze))
        avg_hltv = sum(m['hltv'] for m in mecze) / len(mecze)

        kolor = 0x00FF00 if wr >= 50 else 0xFF0000

        poziom = str(gracz['poziom'])
        emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))

        embed = discord.Embed(
            title=f"Seria Ostatnich {len(mecze)} Spotkań - {gracz['nick']}",
            description=f"Skuteczność: **{wr}%** ({wygrane}W - {len(mecze)-wygrane}L)\n"
                        f"Bilans ELO: **{elo_diff_text}**\n"
                        f"Est. HLTV: **{avg_hltv:.2f}**\n\n"
                        f"Obecna Ranga: {emotka_levelu} **{gracz['elo']} ELO**",
            color=kolor
        )
        
        embed.set_thumbnail(url=gracz['avatar_url'])
        
        embed.add_field(name="Strzeleckie Pomiary", 
                        value=f"Kille (śr): **{avg_kills:.1f}**\n"
                              f"K/D Ratio: **{avg_kd:.2f}**\n"
                              f"KPR: **{avg_kr:.2f}**\n"
                              f"Headshoty: **{avg_hs:.0f}%**\n"
                              f"ADR (śr): **{avg_adr:.1f}**", inline=True)

        embed.add_field(name="Taktyka & Zagrywki", 
                        value=f"Wszystkie First Kills: **{sum_entry}**\n"
                              f"Wygrane Clutche (1vX): **{sum_clutches}**\n"
                              f"Oślepieni wrogowie (śr): **{avg_ef:.1f}**\n"
                              f"Utility Dmg (śr): **{avg_ud:.1f}**\n"
                              f"Zdobyte MVPs: **{suma_mvp}**", inline=True)
        
        await msg.edit(content=None, embed=embed)

    def parse_identifier(self, ctx, args, default_to_author=True):
        """Pomocnik parsujący wzmianki (pingi) lub czyste nicki na nick Faceit."""
        from utils.database import wczytaj_ekipe
        ekipa = wczytaj_ekipe(ctx.guild.id)
        
        # Jeśli nic nie podano, bierzemy autora
        if not args:
            if default_to_author:
                p_id = ekipa.get(str(ctx.author.id))
                return p_id, (ctx.author.display_name if p_id else None)
            return None, None

        # Pierwszy argument to zazwyczaj to, co nas interesuje
        arg = str(args[0]) if isinstance(args, (tuple, list)) else str(args)

        # Sprawdzanie czy to wzmianka (ping): <@ID> lub <@!ID>
        if arg.startswith("<@") and ">" in arg:
            user_id = arg.replace("<@", "").replace("!", "").replace(">", "")
            p_id = ekipa.get(user_id)
            
            # Pobieramy nazwę z Discorda do wyświetlenia
            display_name = "wybranego gracza"
            member = ctx.guild.get_member(int(user_id))
            if member:
                display_name = member.display_name
            
            return p_id, display_name
        
        # W przeciwnym razie traktujemy jako czysty nick Faceit
        return arg, arg

    async def check_nick(self, ctx, nickname, original_arg=None):
        """Weryfikuje czy nick jest poprawny i wysyła jasny komunikat o błędzie pingu."""
        if nickname:
            return True
            
        # Jeśli nickname jest None, sprawdzamy czy próbowano pingować
        if original_arg and str(original_arg).startswith("<@"):
            await ctx.send(f"❌ Ta osoba ({original_arg}) nie ma jeszcze połączonego konta Faceit.")
        else:
            await ctx.send(f"Podaj nick gracza albo połącz najpierw konto wpisując `{ctx.prefix}polacz [TwójNick]`.")
        return False

    @commands.hybrid_command(name="elo", aliases=["e", "fe"], description="Szybki podgląd poziomu, ELO oraz paska postępu")
    async def komenda_szybkie_elo(self, ctx, gracz: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        args = (gracz,) if gracz else ()
        faceit_nick, display_name = self.parse_identifier(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, gracz):
            return
            
        from utils.faceit_api import get_player_stats
        msg = await ctx.send(f"Sprawdzam aktualne punkty: **{display_name}**...")
        dane = await get_player_stats(faceit_nick)
        
        if not dane or dane == "error":
            await msg.edit(content=f"Nie znalazłem gracza: **{faceit_nick}**.")
            return

        obecne_elo = int(dane['elo']) if str(dane['elo']).isdigit() else 0
        poziomy = [
            (1, 0, 500), (2, 501, 750), (3, 751, 900), (4, 901, 1050),
            (5, 1051, 1200), (6, 1201, 1350), (7, 1351, 1530),
            (8, 1531, 1750), (9, 1751, 1999), (10, 2000, 99999)
        ]
        
        do_awansu = 0
        do_spadku = 0
        for lvl, min_elo, max_elo in poziomy:
            if min_elo <= obecne_elo <= max_elo:
                do_awansu = max_elo - obecne_elo + 1
                do_spadku = obecne_elo - min_elo
                break
                
        if obecne_elo >= 2000:
            opis = f"Awansowałeś na szczyt! Brak kolejnych poziomów."
            kolor = 0xFFD700
        else:
            opis = f"🟢 **{do_awansu} ELO** brakuje do wyższego poziomu.\n🔴 **{do_spadku} ELO** zapasu przed spadkiem."
            kolor = 0xFFA500 if do_spadku < 15 else get_cfg(guild_id, "main_color", 0x2b2d31)
            
        poziom = str(dane['poziom'])
        emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))
        
        embed = discord.Embed(
            title=f"Błyskawiczne ELO: {dane['nick']}",
            description=f"Aktualny stan: {emotka_levelu} **{obecne_elo}**\n\n{opis}",
            color=kolor
        )
        embed.set_thumbnail(url=dane['avatar_url'])
        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(name="history", aliases=["hist", "historia"], description="Lista 5 ostatnich spotkań z wynikami i statystykami")
    async def komenda_historia(self, ctx, gracz: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        args = (gracz,) if gracz else ()
        faceit_nick, display_name = self.parse_identifier(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, gracz):
            return
            
        from utils.faceit_api import get_multiple_matches_stats, get_player_stats
        msg = await ctx.send(f"Pobieram historię gier: **{display_name}**...")
        gracz = await get_player_stats(faceit_nick)
        if not gracz or gracz == "error":
            await msg.edit(content=f"Brak danych o faceit: {faceit_nick}")
            return
            
        mecze = await get_multiple_matches_stats(gracz['player_id'], 5)
        if not mecze:
            await msg.edit(content=f"{faceit_nick} nie zagrał żadnych meczów.")
            return
            
        embed = discord.Embed(
            title=f"Dziennik Spotkań", 
            description=f"Profil operacyjny: **{gracz['nick']}**\n"
                        f"Raport z {len(mecze)} ostatnich gier", 
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        for i, mecz in enumerate(mecze, 1):
            rezultat = "🟩 Wygrana" if mecz['win'] else "🟥 Porażka"
            
            opis = (f"**W/L:** {rezultat} ({mecz['score']})\n"
                    f"**Rating HLTV:** {mecz['hltv']:.2f}\n"
                    f"**K/D Ratio:** {mecz['kd']} | **ADR:** {mecz['adr']}")
            
            embed.add_field(
                name=f"#{i} — {mecz['mapa']}", 
                value=opis,
                inline=True
            )
        embed.set_thumbnail(url=gracz['avatar_url'])
        await msg.edit(content=None, embed=embed)
        
    @commands.hybrid_command(name="maps", aliases=["mapy", "m"], description="Skuteczność na poszczególnych mapach 5v5")
    async def komenda_mapy(self, ctx, gracz: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        args = (gracz,) if gracz else ()
        faceit_nick, display_name = self.parse_identifier(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, gracz):
            return
            
        from utils.faceit_api import get_map_segments, get_player_stats
        msg = await ctx.send(f"Sprawdzam statystyki map dla **{display_name}**...")
        gracz = await get_player_stats(faceit_nick)
        if not gracz or gracz == "error":
            await msg.edit(content=f"Brak danych o graczu wpisanym: {faceit_nick}")
            return
            
        katalog_map = await get_map_segments(gracz['player_id'])
        if not katalog_map:
            await msg.edit(content=f"Ten gracz nie grał na mapach 5v5.")
            return
            
        mapy_pool = []
        for segment in katalog_map:
            if segment.get("mode") == "5v5" and segment.get("type") == "Map":
                nazwa = segment.get("label", "Nieznana")
                if nazwa in config.TOURNAMENT_MAPS:
                    stats = segment.get("stats", {})
                    mecze_liczba = int(stats.get("Matches", 0))
                    win_rate = int(stats.get("Win Rate %", 0))
                    kd = float(stats.get("Average K/D Ratio", 0))
                    kr = float(stats.get("Average K/R Ratio", 0))
                    hs = stats.get("Average Headshots %", "0")
                    mvp = stats.get("Average MVPs", "0")
                    k3 = stats.get("Triple Kills", "0")
                    k4 = stats.get("Quadro Kills", "0")
                    
                    mapy_pool.append({
                        "nazwa": nazwa, "mecze": mecze_liczba, "wr": win_rate, 
                        "kd": kd, "kr": kr, "hs": hs, "mvp": mvp,
                        "k3": k3, "k4": k4
                    })
        
        # Uzupełniamy o mapy z puli, w które gracz nie grał
        znalezione_nazwy = [m["nazwa"] for m in mapy_pool]
        for m_name in config.TOURNAMENT_MAPS:
            if m_name not in znalezione_nazwy:
                mapy_pool.append({
                    "nazwa": m_name, "mecze": 0, "wr": 0, "kd": 0.0, "kr": 0.0, 
                    "hs": "0", "mvp": "0", "k3": "0", "k4": "0"
                })
        
        # Sortowanie od najlepszej do najsłabszej
        mapy_pool.sort(key=lambda x: (x["wr"], x["kd"]), reverse=True)
            
        embed = discord.Embed(
            title="Analityka Map Turniejowych (Dashboard)",
            description=f"Szczegółowa wydajność operacyjna dla: **{gracz['nick']}**",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        
        for m in mapy_pool:
            if m['mecze'] == 0:
                emoji = "⚪"
                value_text = "*Brak zarejestrowanych operacji*"
            else:
                if m['wr'] >= 55: emoji = "🟢"
                elif m['wr'] >= 45: emoji = "🟡"
                else: emoji = "🔴"
                
                value_text = (
                    f"**W/R:** {m['wr']}% ({m['mecze']} gier)\n"
                    f"**K/D:** {m['kd']} | **K/R:** {m['kr']}\n"
                    f"**HS:** {m['hs']}% | **MVP:** {m['mvp']}\n"
                    f"**Impact:** {m['k3']}x3K | {m['k4']}x4K"
                )
                
            embed.add_field(
                name=f"{emoji} {m['nazwa']}",
                value=value_text,
                inline=True
            )
        
        embed.set_thumbnail(url=gracz['avatar_url'])
        embed.set_footer(text="Legenda: 🟢 Pro | 🟡 Solidnie | 🔴 Słabo | K/R: Kills per Round")
        await msg.edit(content=None, embed=embed)
        
    @commands.hybrid_command(name="compare", aliases=["porownaj", "c", "1v1", "arena"], description="Arena 1v1 — porównanie formy dwóch graczy")
    async def komenda_compare(self, ctx, argument1: str, argument2: str, argument3: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        limit = 10
        raw_args = [argument1, argument2]
        if argument3 is not None:
            raw_args.append(argument3)
            
        targets = []
        for arg in raw_args:
            if arg.isdigit():
                limit = int(arg)
            else:
                targets.append(arg)
                
        if len(targets) < 2:
            await ctx.send(f"❌ Musisz podać dwóch graczy! Użycie: `{ctx.prefix}compare [ilość] [Gracz1] [Gracz2]`")
            return
            
        # Zabezpieczenie limitu
        limit = min(max(1, limit), 100)
            
        from utils.faceit_api import get_player_stats, get_multiple_matches_stats
        nick1, d_name1 = self.parse_identifier(ctx, [targets[0]], default_to_author=False)
        nick2, d_name2 = self.parse_identifier(ctx, [targets[1]], default_to_author=False)
        
        if not nick1: nick1 = targets[0]; d_name1 = targets[0]
        if not nick2: nick2 = targets[1]; d_name2 = targets[1]
        
        msg = await ctx.send(f"⚔️ Otwieranie areny... Przygotowuję statystyki dla **{d_name1}** i **{d_name2}**.")
        
        g1 = await get_player_stats(nick1)
        g2 = await get_player_stats(nick2)
        
        if not g1 or g1 == "error" or not g2 or g2 == "error":
            await msg.edit(content="❌ Błąd. Nie znaleziono profili na Faceit. Sprawdź pisownię.")
            return

        # Pobieranie historii dla obu
        m1 = await get_multiple_matches_stats(g1['player_id'], limit)
        m2 = await get_multiple_matches_stats(g2['player_id'], limit)

        if not m1 or not m2:
            await msg.edit(content="❌ Jeden z graczy nie rozegrał wystarczającej liczby meczów w CS2.")
            return

        # Obliczenia
        def calc_avg(mecze, klucz):
            return sum(m[klucz] for m in mecze) / len(mecze)

        s1 = {
            "wr": (sum(1 for m in m1 if m['win']) / len(m1)) * 100,
            "hltv": calc_avg(m1, "hltv"),
            "kd": calc_avg(m1, "kd"),
            "adr": calc_avg(m1, "adr"),
            "hs": calc_avg(m1, "hs_procent"),
            "kpr": calc_avg(m1, "kr")
        }
        s2 = {
            "wr": (sum(1 for m in m2 if m['win']) / len(m2)) * 100,
            "hltv": calc_avg(m2, "hltv"),
            "kd": calc_avg(m2, "kd"),
            "adr": calc_avg(m2, "adr"),
            "hs": calc_avg(m2, "hs_procent"),
            "kpr": calc_avg(m2, "kr")
        }

        # Pobranie emotek poziomów
        import config
        emotki = get_cfg(guild_id, "level_emojis", config.LEVEL_EMOJIS)
        def get_lvl_emoji(lvl):
            return emotki.get(str(lvl), get_cfg(guild_id, "level_default", config.LEVEL_DEFAULT))

        emoji1 = get_lvl_emoji(g1['poziom'])
        emoji2 = get_lvl_emoji(g2['poziom'])

        # Formatowanie kolumn
        def get_vals(v1, v2, suffix="", dec=2):
            fmt = f"{{:.{dec}f}}"
            val1 = fmt.format(v1) + suffix
            val2 = fmt.format(v2) + suffix
            
            if v1 > v2:
                return f"**{val1}** ─ {val2}"
            elif v2 > v1:
                return f"{val1} ─ **{val2}**"
            else:
                return f"{val1} ─ {val2}"

        embed = discord.Embed(
            title=f"⚔️ ARENA: {g1['nick']} vs {g2['nick']}",
            description=f"Bezpośrednie starcie na podstawie ostatnich **{len(m1)}** meczów.",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        
        # Sekcja ELO
        embed.add_field(
            name="📈 Ranking ELO",
            value=f"{emoji1} **{g1['elo']}** ─ {emoji2} **{g2['elo']}**\n*Różnica: {abs(int(g1['elo']) - int(g2['elo']))} pkt*",
            inline=False
        )

        # Sekcja Statystyk
        stats_list = [
            f"📊 **Rating HLTV**: {get_vals(s1['hltv'], s2['hltv'])}",
            f"🏆 **Win Rate**: {get_vals(s1['wr'], s2['wr'], '%', 0)}",
            f"🔫 **K/D Ratio**: {get_vals(s1['kd'], s2['kd'])}",
            f"💥 **Średni ADR**: {get_vals(s1['adr'], s2['adr'], '', 1)}",
            f"🎯 **Kille/Rundę**: {get_vals(s1['kpr'], s2['kpr'])}",
            f"🤯 **Headshoty**: {get_vals(s1['hs'], s2['hs'], '%', 0)}"
        ]
        
        embed.add_field(
            name="🔥 Forma (Ostatnie gry)",
            value="\n".join(stats_list),
            inline=False
        )
        
        embed.set_footer(text=f"Arena wygenerowana dla {ctx.author.display_name} | Powodzenia!")
        await msg.edit(content=None, embed=embed)


    def get_main_help_embed(self, ctx):
        guild_id = ctx.guild.id
        color = get_cfg(guild_id, "main_color", 0x2b2d31)
        is_admin = ctx.author.guild_permissions.administrator if hasattr(ctx.author, "guild_permissions") else False
        
        embed = discord.Embed(
            title="🎮 CS2 Faceit Bot — Centrum Pomocy",
            description=(
                f"Bot automatycznie śledzi mecze, statystyki oraz formę graczy Faceit.\n"
                f"Prefix na tym serwerze: `{ctx.prefix}` (lub wzmianka bota @Bot)\n\n"
                f"📌 **Szybka nawigacja:** Kliknij przyciski poniżej lub wpisz:\n"
                f"• `{ctx.prefix}pomoc user` — szczegółowy spis komend gracza\n"
                f"• `{ctx.prefix}pomoc admin` — spis narzędzi administracyjnych\n"
                f"• `{ctx.prefix}pomoc [nazwa_komendy]` — pełny opis konkretnej komendy"
            ),
            color=color
        )
        
        embed.add_field(
            name="👤 PROFIL I KONTO",
            value=(
                f"`{ctx.prefix}polacz` • Powiązanie profilu Faceit z kontem Discord\n"
                f"`{ctx.prefix}odlacz` • Odłączenie konta z ekipy serwera\n"
                f"`{ctx.prefix}stats` • Pełny paszport statystyk gracza (K/D, ADR, ELO)\n"
                f"`{ctx.prefix}elo` • Szybki podgląd punktów ELO i paska do awansu"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 ANALIZA MECZÓW I FORMA",
            value=(
                f"`{ctx.prefix}last` • Raport z ostatniego meczu (+/- ELO, HLTV 2.0)\n"
                f"`{ctx.prefix}recent` • Średnie statystyki z ostatnich gier (2-100)\n"
                f"`{ctx.prefix}wykres` • Wykres liniowy trajektorii punktów ELO\n"
                f"`{ctx.prefix}history` • Ostatnie 5 meczów z wynikami i linkami\n"
                f"`{ctx.prefix}maps` • Skuteczność i Win Rate na poszczególnych mapach\n"
                f"`{ctx.prefix}compare` • Arena 1v1 — bezpośrednie porównanie graczy"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 RANKINGI I SPOŁECZNOŚĆ",
            value=(
                f"`{ctx.prefix}top` • Tabela liderów ekipy serwera wg ELO\n"
                f"`{ctx.prefix}streaks` • Zestawienie aktualnych serii (win/loss streak)"
            ),
            inline=False
        )
        
        if is_admin:
            embed.add_field(
                name="🛠️ ADMINISTRACJA SERWEREM (Widoczne dla Admina)",
                value=(
                    f"`{ctx.prefix}config` • Panel konfiguracji bota (prefix, kanały, kolory)\n"
                    f"`{ctx.prefix}sezon` • Zarządzanie sezonami rankingowymi i nagrodami MVP\n"
                    f"`{ctx.prefix}live_setup` • Konfiguracja dedykowanego kanału meczów live\n"
                    f"`{ctx.prefix}rekordy_setup` • Inicjalizacja kanału Hali Sław z rekordami\n"
                    f"`{ctx.prefix}elo_setup` • Utworzenie kanału głosowego ze średnim ELO\n"
                    f"`{ctx.prefix}tilt_config` • Ustawienia czułości alertów Tilt-Meter"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Więcej informacji: {ctx.prefix}pomoc <nazwa_komendy> | Użyj przycisków poniżej")
        return embed

    def get_user_help_embed(self, ctx):
        guild_id = ctx.guild.id
        color = get_cfg(guild_id, "main_color", 0x2b2d31)
        
        embed = discord.Embed(
            title="👤 Komendy Gracza — Pełny Spis",
            description="Większość komend akceptuje nick Faceit lub oznaczenie gracza (`@Gracz`). Jeśli połączyłeś konto (`!polacz`), możesz wpisywać komendy bez argumentów!",
            color=color
        )
        
        embed.add_field(
            name="🔗 Zarządzanie Kontem",
            value=(
                f"• `{ctx.prefix}polacz <nick_faceit>` — Łączy Discorda z kontem Faceit.\n"
                f"• `{ctx.prefix}odlacz` — Usuwa powiązanie konta z profilem Discord."
            ),
            inline=False
        )
        
        embed.add_field(
            name="📈 Statystyki & Forma",
            value=(
                f"• `{ctx.prefix}stats [nick/ping]` — Pełny profil gracza (ELO, KD, ADR, HS%, WR).\n"
                f"• `{ctx.prefix}elo [nick/ping]` — Aktualne punkty ELO, poziom i brakujące punkty do awansu/spadku.\n"
                f"• `{ctx.prefix}last [nick/ping]` — Szczegółowa karta ostatniego meczu (HLTV 2.0, kille, UD, +/- ELO).\n"
                f"• `{ctx.prefix}recent [ilość] [nick/ping]` — Podsumowanie formy z ostatnich gier (domyślnie 20, max 100).\n"
                f"• `{ctx.prefix}wykres [ilość] [nick/ping]` — Wykres liniowy punktów ELO z ostatnich gier (2-100).\n"
                f"• `{ctx.prefix}history [nick/ping]` — Szybka lista 5 ostatnich meczów wraz z linkami.\n"
                f"• `{ctx.prefix}maps [nick/ping]` — Analiza skuteczności (Win Rate, mecze) na mapach turniejowych."
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Rywalizacja & Ekipa",
            value=(
                f"• `{ctx.prefix}compare [ilość] <gracz1> <gracz2>` — Pojedynek 1v1 dwóch graczy na bazie ostatnich gier.\n"
                f"• `{ctx.prefix}top` — Ranking serwerowy ekipy posortowany według ELO.\n"
                f"• `{ctx.prefix}streaks` — Tablica pass zwycięstw i porażek członków ekipy."
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Szczegóły komendy: {ctx.prefix}pomoc [nazwa]")
        return embed

    def get_admin_help_embed(self, ctx):
        guild_id = ctx.guild.id
        color = get_cfg(guild_id, "main_color", 0x2b2d31)
        
        embed = discord.Embed(
            title="🛠️ Komendy Administratora — Zarządzanie Botem",
            description="Poniższe komendy wymagają uprawnień **Administratora** na serwerze Discord.",
            color=color
        )
        
        embed.add_field(
            name="⚙️ Konfiguracja & Alerty",
            value=(
                f"• `{ctx.prefix}config` — Panel główny lub edycja `{ctx.prefix}config [klucz] [wartość]` (np. `prefix`, `kanal_eventow`, `main_color`).\n"
                f"• `{ctx.prefix}tilt_config` — Menu wyboru progu alertów Tilt-Meter (serie porażek/zwycięstw).\n"
                f"• `{ctx.prefix}elo_setup` — Tworzy automatyczny kanał głosowy ze średnim ELO ekipy."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 System Sezonowy",
            value=(
                f"• `{ctx.prefix}sezon` — Interaktywny panel sezonu (Start, Koniec z MVP, Podgląd tabeli).\n"
                f"• `{ctx.prefix}sezony` — Lista wszystkich sezonów z ID i archiwalnymi zwycięzcami MVP.\n"
                f"• `{ctx.prefix}sezon_reload` — Wymusza natychmiastowe odświeżenie tabeli sezonu na kanale.\n"
                f"• `{ctx.prefix}sezon_repost` — Usuwa starą wiadomość z tabelą i wysyła nową na dół kanału.\n"
                f"• `{ctx.prefix}sezon_set_mvp <ID/nazwa> <@gracz> [progres]` — Ręczne przypisanie MVP do sezonu."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔴 Mecze Na Żywo (Live Tracker)",
            value=(
                f"• `{ctx.prefix}live_setup [#kanał]` — Konfiguracja kanału ze śledzeniem meczów na żywo w czasie rzeczywistym.\n"
                f"• `{ctx.prefix}live_reload` — Natychmiastowe odświeżenie dashboardu meczów live.\n"
                f"• `{ctx.prefix}live_repost` — Przeniesienie dashboardu live na sam dół kanału."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎖️ Hala Sław & Rekordy",
            value=(
                f"• `{ctx.prefix}rekordy_setup` — Tworzy kanał `🏆・hala-sław` z dedykowanymi kartami rekordów.\n"
                f"• `{ctx.prefix}rekordy_reload` — Wymusza ponowne przeliczenie i odświeżenie kart rekordów."
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Szczegóły wybranej komendy: {ctx.prefix}pomoc [nazwa]")
        return embed

    @commands.hybrid_command(name="pomoc", aliases=["komendy", "help"], description="Interaktywne menu pomocy z dokumentacją komend")
    async def komenda_pomoc(self, ctx, komenda: typing.Optional[str] = None):
        """Dynamiczny i kompletny system pomocy z podziałem na role."""
        command_name = komenda
        guild_id = ctx.guild.id
        
        # 1. Sprawdzenie widoków kategorii
        if not command_name:
            embed = self.get_main_help_embed(ctx)
            view = HelpView(self, ctx, current_page="main")
            await ctx.send(embed=embed, view=view)
            return

        cmd_lower = command_name.lower().strip()
        
        if cmd_lower in ["admin", "adm", "administrator", "zarzadzanie", "a"]:
            embed = self.get_admin_help_embed(ctx)
            view = HelpView(self, ctx, current_page="admin")
            await ctx.send(embed=embed, view=view)
            return

        if cmd_lower in ["user", "gracz", "gracze", "uzytkownik", "u"]:
            embed = self.get_user_help_embed(ctx)
            view = HelpView(self, ctx, current_page="user")
            await ctx.send(embed=embed, view=view)
            return

        # 2. SZCZEGÓŁOWY WIDOK DOWOLNEJ KOMENDY
        target_command = self.bot.get_command(cmd_lower)
        
        if not target_command:
            await ctx.send(
                f"❌ Nie znaleziono komendy ani sekcji o nazwie `{command_name}`.\n"
                f"Wpisz `{ctx.prefix}pomoc`, aby zobaczyć pełną listę dostępnych opcji."
            )
            return

        # Baza opisów, użycia i przykładów
        meta_komend = {
            "polacz": {
                "desc": "Łączy profil Discord z kontem Faceit. Dodaje gracza do monitorowanej ekipy serwera oraz pozwala używać komend bez każdorazowego podawania nicku.",
                "usage": "<nick_faceit>",
                "admin": False,
                "examples": [f"{ctx.prefix}polacz s1mple", f"{ctx.prefix}polacz NiKo"],
                "note": "Każdy użytkownik może powiązać jedno konto Faceit."
            },
            "odlacz": {
                "desc": "Usuwa powiązanie Twojego konta Discord z profilem Faceit na tym serwerze.",
                "usage": "",
                "admin": False,
                "examples": [f"{ctx.prefix}odlacz"],
                "note": "Po odłączeniu bot przestanie uwzględniać Twoje mecze w powiadomieniach i rankingu."
            },
            "stats": {
                "desc": "Wyświetla kompletny paszport statystyk gracza: aktualne ELO, poziom (z emoji), winrate ogólny, bilans K/D, średnie ADR, aktualną passę (streak), liczbę meczów oraz wskaźnik formy.",
                "usage": "[nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}stats", f"{ctx.prefix}stats @Gracz", f"{ctx.prefix}stats m0NESY"],
                "note": "Wpisane bez argumentów wyświetla statystyki powiązanego konta autora."
            },
            "elo": {
                "desc": "Szybki podgląd poziomu Faceit, aktualnej liczby punktów ELO oraz paska postępu z informacją ile punktów brakuje do awansu na wyższy poziom lub spadku.",
                "usage": "[nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}elo", f"{ctx.prefix}elo @Gracz", f"{ctx.prefix}elo donk"],
                "note": "Obsługuje zarówno ping gracza, jak i bezpośredni nick Faceit."
            },
            "last": {
                "desc": "Szczegółowa analiza ostatniego meczu: wynik, mapa, kille/dedy/asysty, HLTV Rating 2.0, ADR, HS%, Utility Damage oraz bezpośrednią zmianę ELO (+/-).",
                "usage": "[nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}last", f"{ctx.prefix}last @Gracz", f"{ctx.prefix}last ropz"],
                "note": "Zawiera również bezpośredni odnośnik do meczu na platformie Faceit."
            },
            "recent": {
                "desc": "Analiza formy ze wskazanej serii ostatnich meczów pobranych z bazy danych bota (domyślnie 20). Wylicza średnie K/D, zabójstwa/mecz, HS%, ADR oraz sumaryczny bilans ELO.",
                "usage": "[ilość (2-100)] [nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}recent", f"{ctx.prefix}recent 10", f"{ctx.prefix}recent 30 @Gracz"],
                "note": "Możesz podać liczbę meczów w zakresie od 2 do 100."
            },
            "wykres": {
                "desc": "Generuje przejrzysty wykres liniowy punktów ELO na przestrzeni ostatnich spotkań, obrazujący aktualną tendencję i formę gracza.",
                "usage": "[ilość (2-100)] [nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}wykres", f"{ctx.prefix}wykres 15", f"{ctx.prefix}wykres @Gracz 50"],
                "note": "Argumenty (ilość i nick/ping) można podawać w dowolnej kolejności."
            },
            "history": {
                "desc": "Wyświetla listę 5 ostatnich spotkań gracza wraz z datą, mapą, wynikiem spotkania, statystykami K-D, K/D oraz różnicą punktów ELO.",
                "usage": "[nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}history", f"{ctx.prefix}history @Gracz"],
                "note": "Idealne do szybkiego sprawdzenia bilansu ostatnich gier."
            },
            "maps": {
                "desc": "Zestawienie skuteczności na poszczególnych mapach turniejowych 5v5. Pokazuje liczbę meczów, Win Rate % oraz średnie K/D.",
                "usage": "[nick / @gracz]",
                "admin": False,
                "examples": [f"{ctx.prefix}maps", f"{ctx.prefix}maps @Gracz"],
                "note": "Pozwala ocenić najsilniejsze i najsłabsze mapy w puli."
            },
            "compare": {
                "desc": "Arena 1v1. Bezpośrednie porównanie formy dwóch graczy na bazie ostatnich meczów ze wskazaniem lidera w każdej kategorii statystyk.",
                "usage": "[ilość] <gracz1> <gracz2>",
                "admin": False,
                "examples": [f"{ctx.prefix}compare @Gracz1 @Gracz2", f"{ctx.prefix}compare 15 Nick1 Nick2"],
                "note": "Graczy można podawać jako wzmianki (@ping) lub bezpośrednie nicki Faceit."
            },
            "top": {
                "desc": "Wyświetla tabelę liderów zarejestrowanych członków ekipy serwera, posortowaną według aktualnego poziomu i punktów ELO.",
                "usage": "",
                "admin": False,
                "examples": [f"{ctx.prefix}top"],
                "note": "Uwzględnia wszystkich graczy powiązanych komendą !polacz."
            },
            "streaks": {
                "desc": "Zestawienie aktualnych serii zwycięstw lub porażek z rzędu dla wszystkich zarejestrowanych graczy z ekipy serwera.",
                "usage": "",
                "admin": False,
                "examples": [f"{ctx.prefix}streaks"],
                "note": "Pokazuje kto jest na fali (Win Streak), a kto w strefie tiltu (Loss Streak)."
            },
            "pomoc": {
                "desc": "Centrum pomocy i interaktywna dokumentacja bota. Pozwala przeglądać komendy gracza, narzędzia administratora lub szczegóły wybranej komendy.",
                "usage": "[komenda / admin / user]",
                "admin": False,
                "examples": [f"{ctx.prefix}pomoc", f"{ctx.prefix}pomoc admin", f"{ctx.prefix}pomoc stats"],
                "note": "Działa również pod aliasami !help oraz !komendy."
            },
            "config": {
                "desc": "Panel zarządzania konfiguracją bota per serwer. Umożliwia zmianę prefixu, kanałów powiadomień, głównego koloru embedów oraz progów alertów.",
                "usage": "[klucz] [wartość]",
                "admin": True,
                "examples": [
                    f"{ctx.prefix}config",
                    f"{ctx.prefix}config prefix ?",
                    f"{ctx.prefix}config kanal_eventow #powiadomienia",
                    f"{ctx.prefix}config main_color #FF5500"
                ],
                "note": "Klucze kanałów: kanal_eventow, kanal_sezonu, kanal_podsumowan_elo, kanal_live."
            },
            "tilt_config": {
                "desc": "Otwiera interaktywne menu wyboru czułości alertów Tilt-Meter (liczba porażek/zwycięstw z rzędu, po której bot wysyła powiadomienie/roast).",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}tilt_config"],
                "note": "Można wybrać próg 3, 4, 5 gier lub całkowicie wyłączyć powiadomienia."
            },
            "elo_setup": {
                "desc": "Automatycznie tworzy i konfiguruje kanał głosowy, którego nazwa wyświetla uśrednione punkty ELO całej zarejestrowanej ekipy serwera na żywo.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}elo_setup"],
                "note": "Wymaga uprawnień do zarządzania kanałami."
            },
            "sezon": {
                "desc": "Główny panel zarządzania systemem sezonów rankingowych serwera. Pozwala rozpocząć nowy sezon, wyświetlić tabelę lub zamknąć sezon z nagrodą MVP.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}sezon"],
                "note": "Zakończenie sezonu automatycznie archiwizuje wyniki i aktualizuje Halę Sław."
            },
            "sezony": {
                "desc": "Wyświetla listę wszystkich zarejestrowanych sezonów w bazie danych z podziałem na status (aktywny / zakończony) oraz przypisanych zwycięzców MVP.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}sezony"],
                "note": "Zawiera numery ID sezonów potrzebne do komendy !sezon_set_mvp."
            },
            "sezon_reload": {
                "desc": "Ręcznie wymusza natychmiastowe przeliczenie i zaktualizowanie aktywnej wiadomości z tabelą sezonu na dedykowanym kanale.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}sezon_reload"],
                "note": "Przydatne, gdy bot nie zaktualizował tabeli automatycznie."
            },
            "sezon_repost": {
                "desc": "Usuwa poprzednią wiadomość z rankingiem sezonowym i wysyła nową na sam dół dedykowanego kanału.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}sezon_repost"],
                "note": "Przydatne w przypadku zapełnienia kanału innymi wiadomościami."
            },
            "sezon_set_mvp": {
                "desc": "Ręcznie przypisuje lub koryguje zdobywcę tytułu MVP dla wskazanego archiwalnego sezonu (automatycznie aktualizuje Halę Sław).",
                "usage": "<ID_sezonu/nazwa> <@gracz> [progres_elo]",
                "admin": True,
                "examples": [f"{ctx.prefix}sezon_set_mvp 1 @Gracz 280", f"{ctx.prefix}sezon_set_mvp Sezon_1 @Gracz 150"],
                "note": "ID sezonu można sprawdzić komendą !sezony."
            },
            "live_setup": {
                "desc": "Inicjalizuje i konfiguruje dedykowany kanał monitorowania meczów na żywo. Bot wyświetla na nim dashboard z aktualnym stanem rund i statystykami graczy.",
                "usage": "[#kanał]",
                "admin": True,
                "examples": [f"{ctx.prefix}live_setup", f"{ctx.prefix}live_setup #mecze-live"],
                "note": "Wpisane bez kanału używa bieżącego kanału tekstowego."
            },
            "live_reload": {
                "desc": "Natychmiastowo wymusza odświeżenie dashboardu meczów na żywo na skonfigurowanym kanale live.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}live_reload"],
                "note": "Wymaga wcześniejszego skonfigurowania kanału komendą !live_setup."
            },
            "live_repost": {
                "desc": "Usuwa dotychczasowe wiadomości panelu live i generuje świeży dashboard na samym dole kanału.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}live_repost"],
                "note": "Zalecane przy problemach z widocznością wiadomości dashboardu."
            },
            "rekordy_setup": {
                "desc": "Tworzy dedykowany kanał Hali Sław (🏆・hala-sław) z osobnymi, estetycznymi kartami dla każdego rekordu serwera (Kills, HLTV, UD, Deaths, MVP).",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}rekordy_setup"],
                "note": "Karty rekordów są aktualizowane automatycznie po zakończeniu każdego meczu."
            },
            "rekordy_reload": {
                "desc": "Wymusza natychmiastowe przeliczenie bazy i zaktualizowanie wszystkich kart rekordów na kanale Hali Sław.",
                "usage": "",
                "admin": True,
                "examples": [f"{ctx.prefix}rekordy_reload"],
                "note": "Synchronizuje rekordy ze stanem bazy danych."
            }
        }

        name = target_command.name
        info = meta_komend.get(name, {
            "desc": target_command.help or "Brak szczegółowego opisu.",
            "usage": "",
            "admin": False,
            "examples": [],
            "note": None
        })

        aliases = ", ".join([f"`{a}`" for a in target_command.aliases]) if target_command.aliases else "Brak"
        uprawnienia = "🛡️ Administrator" if info.get("admin") else "👥 Gracz (Wszyscy)"
        
        embed = discord.Embed(
            title=f"📖 Komenda: {ctx.prefix}{name}",
            description=info["desc"],
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        
        embed.add_field(name="💡 Składnia", value=f"`{ctx.prefix}{name} {info.get('usage', '')}`".strip(), inline=False)
        embed.add_field(name="🔒 Uprawnienia", value=uprawnienia, inline=True)
        embed.add_field(name="🔗 Aliasy (skróty)", value=aliases, inline=True)
        
        if info.get("examples"):
            przykłady_txt = "\n".join([f"• `{ex}`" for ex in info["examples"]])
            embed.add_field(name="🧪 Przykłady użycia", value=przykłady_txt, inline=False)
            
        if info.get("note"):
            embed.add_field(name="ℹ️ Dodatkowe informacje", value=info["note"], inline=False)

        embed.set_footer(text=f"Więcej pomocy: {ctx.prefix}pomoc | {ctx.prefix}pomoc admin | {ctx.prefix}pomoc user")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="wykres", aliases=["chart", "graph"], description="Wykres liniowy trajektorii punktów ELO")
    async def komenda_wykres(self, ctx, argument1: typing.Optional[str] = None, argument2: typing.Optional[str] = None):
        await ctx.defer()
        guild_id = ctx.guild.id
        limit = 20
        raw_args = [a for a in [argument1, argument2] if a is not None]
        parsed_args = []
        for arg in raw_args:
            if arg.isdigit():
                limit = int(arg)
            else:
                parsed_args.append(arg)
                
        limit = min(max(2, limit), 100)
        
        faceit_nick, display_name = self.parse_identifier(ctx, parsed_args)
        if not await self.check_nick(ctx, faceit_nick, parsed_args[0] if parsed_args else None):
            return
            
        msg = await ctx.send(f"Generuję wykres ELO z ostatnich **{limit}** gier dla **{display_name}**... 📊")
        
        # 1. Pobieramy player_id (jeśli to nie jest już UUID)
        p_id = await get_player_id(faceit_nick)
        if not p_id:
            await msg.edit(content=f"Nie znalazłem gracza: **{faceit_nick}**.")
            return
 
        # 2. Pobieramy historię z bazy asynchronicznie
        import asyncio
        historia = await asyncio.to_thread(pobierz_historie_elo, p_id, limit=limit)
        
        if not historia or len(historia) < 2:
            await msg.edit(content=f"⚠️ Za mało danych w bazie, aby wygenerować wykres dla **{display_name}**. Muszę zarejestrować co najmniej 2 mecze (aktualnie w bazie: {len(historia) if historia else 0}).")
            return
 
        # 3. Generujemy wykres asynchronicznie
        plik = await asyncio.to_thread(generuj_wykres_elo, display_name, historia)
        
        if not plik:
            await msg.edit(content="❌ Błąd podczas generowania wykresu.")
            return
 
        embed = discord.Embed(
            title=f"Wykres ELO - {display_name}",
            color=get_cfg(guild_id, "main_color", 0x2b2d31)
        )
        embed.set_image(url="attachment://wykres_elo.png")
        embed.set_footer(text="Dane zbierane od momentu aktywacji monitoringu.")
        
        await msg.edit(content=None, embed=embed, attachments=[plik])

async def setup(bot):
    await bot.add_cog(CSCommands(bot))