# cogs/cs.py

import discord
from discord.ext import commands
import typing
from utils.faceit_api import get_player_stats
import config
from utils.database import wczytaj_ekipe, zapisz_ekipe, wczytaj_sezon, zapisz_sezon, get_cfg

class CSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="stats", aliases=["statystyki", "s", "fs"])
    async def sprawdz_elo(self, ctx, *args):
        nickname = self.parse_nick(ctx, args)
        if not await self.check_nick(ctx, nickname, args[0] if args else None):
            return

        # Wysyłamy status ładowania
        msg = await ctx.send(f"Przeszukuję serwery Faceit dla gracza **{nickname}**...")
        
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
            color=get_cfg("main_color", 0x2b2d31)
        )
        embed.set_thumbnail(url=dane['avatar_url'])
        # Wyciągamy level gracza jako tekst (np. "8")
        poziom = str(dane['poziom'])
        
        # Szukamy emotki w configu.
        emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg("level_default", config.LEVEL_DEFAULT))

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

    @commands.command(name="last", aliases=["mecz", "l", "fl"])
    async def ostatni_mecz(self, ctx, *args):
        nickname = self.parse_nick(ctx, args)
        if not await self.check_nick(ctx, nickname, args[0] if args else None):
            return

        msg = await ctx.send(f"Pobieram dane o ostatnim meczu gracza **{nickname}**...")
        
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
        emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg("level_default", config.LEVEL_DEFAULT))

        embed = discord.Embed(
            title=f"Ostatni mecz: {gracz['nick']} — {wynik_tekst}",
            description=f"Mapa: **{mecz['mapa']}** | Wynik: **{mecz['wynik']}**\nObecna ranga: {emotka_levelu} **{gracz['elo']} ELO**",
            color=kolor
        )
        
        embed.add_field(name="Wyniki Strzeleckie", 
                        value=f"K/D/A: **{int(mecz['kille'])}/{int(mecz['dedy'])}/{int(mecz['asysty'])}**\n"
                              f"K/D Ratio: **{mecz['kd']}** (KPR: **{mecz['kr']}**)\n"
                              f"Headshoty: **{mecz['hs_procent']}%**\n"
                              f"ADR: **{mecz['adr']}**", inline=True)
                              
        embed.add_field(name="Taktyka & Zagrywki", 
                        value=f"Est. HLTV: **{mecz['hltv']}**\n"
                              f"Utility: **{int(mecz['ud'])}** Dmg (Śr. **{mecz['udpr']}**)\n"
                              f"Oślepieni wrogowie: **{int(mecz['ef'])}**\n"
                              f"Entry Kills: **{int(mecz['entry_wins'])}**\n"
                              f"Wyg. Clutche (1vX): **{int(mecz['clutch_1v1']+mecz['clutch_1v2'])}**", inline=True)
                              
        embed.add_field(name="🎖️ MVP Spotkania", 
                        value=f"Gwiazdki: **{int(mecz['mvp'])}**\n", inline=False)
        
        embed.set_thumbnail(url=gracz['avatar_url'])

        await msg.edit(content=None, embed=embed)

    @commands.command(name="top", aliases=["leaderboard", "ranking"])
    async def tablica_wynikow(self, ctx):
        # Ta komenda musi sprawdzić kilka osób, więc zajmie botowi sekundę lub dwie
        msg = await ctx.send("Zbieram dane z serwerów Faceit... (to potrwa chwilę)")
        
        # (NOWY KOD)
        ekipa = wczytaj_ekipe()
        
        sezon = wczytaj_sezon()
        sezon_aktywny = "nazwa" in sezon
        
        if not ekipa:
            await msg.edit(content=f"Ekipa jest pusta! Dodaj kogoś używając `{ctx.prefix}polacz [nick]`.")
            return

        wyniki = []
        for discord_id, nick in ekipa.items():
            dane = await get_player_stats(nick)
            
            # Sprawdzamy czy pobrało dane poprawnie i czy gracz ma jakieś ELO
            if dane and dane != "error":
                dane["discord_id"] = discord_id
                wyniki.append(dane)

        # Sortowanie graczy po ELO od najwyższego do najniższego
        # (Zabezpieczenie na wypadek gdyby ktoś miał status 'Brak' ELO)
        wyniki.sort(key=lambda x: int(x['elo']) if str(x['elo']).isdigit() else 0, reverse=True)

        # Tworzymy ładną ramkę
        embed = discord.Embed(
            title=f"Ranking Ekipy - {sezon['nazwa'] if sezon_aktywny else 'FACEIT'}",
            color=get_cfg("main_color", 0x2b2d31)
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
            emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
            emotka_levelu = emotki.get(poziom, get_cfg("level_default", config.LEVEL_DEFAULT))
            
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

    @commands.command(name="streaks", aliases=["passa", "st"])
    async def zestawienie_passy(self, ctx):
        """Wyświetla aktualne serie zwycięstw/porażek dla całej ekipy."""
        from utils.database import wczytaj_tilt
        msg = await ctx.send("Sprawdzam, kto dzisiaj carruje, a kto sabotuje... 🔍")
        
        ekipa = wczytaj_ekipe()
        tilt_baza = wczytaj_tilt()
        
        if not ekipa:
            await msg.edit(content="Ekipa jest pusta!")
            return

        wyniki = []
        # Pobieramy ID graczy, żeby dopasować ich do tilt.json
        for discord_id, nick in ekipa.items():
            dane = await get_player_stats(nick)
            if dane and dane != "error":
                pid = dane['player_id']
                streak = tilt_baza.get(pid, 0)
                wyniki.append({
                    "nick": nick,
                    "discord_id": discord_id,
                    "streak": streak
                })

        # Sortujemy: najpierw największe winstreaki, na dole największe loostreaki
        wyniki.sort(key=lambda x: x["streak"], reverse=True)

        embed = discord.Embed(
            title="🔥 Termometr Ekipy — Serie Gier",
            description="Zestawienie aktualnych serii zwycięstw i porażek w bieżącej sesji.",
            color=get_cfg("main_color", 0x2b2d31)
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

    @commands.command(name="polacz", aliases=["link", "ln"])
    async def polacz_konto(self, ctx, *args):
        if not args:
            await ctx.send(f"Podaj nick Faceit! Użycie: `{ctx.prefix}polacz [nick]` lub `{ctx.prefix}polacz @Ktoś [nick]`.")
            return

        discord_id = str(ctx.author.id)
        faceit_nick = None
        
        # Sprawdzanie czy kogoś oznaczono
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
            discord_id = str(target.id)
            # Szukamy nicku Faceit, ignorując stringi będące wzmiankami <@id>
            for arg in args:
                if not arg.startswith("<@"):
                    faceit_nick = arg
        else:
            faceit_nick = args[0]
            
        if not faceit_nick:
            await ctx.send("Zabrakło nazwy gracza z Faceit!")
            return

        ekipa = wczytaj_ekipe()
        
        if discord_id in ekipa and not ctx.message.mentions:
            await ctx.send(f"Masz już połączone konto: **{ekipa[discord_id]}**. Użyj `{ctx.prefix}un` by je odłączyć.")
            return

        msg = await ctx.send(f"Łączę profil <@{discord_id}> z kontem Faceit: **{faceit_nick}**...")

        from utils.faceit_api import get_player_stats
        test = await get_player_stats(faceit_nick)
        if not test or test == "error":
            await msg.edit(content=f"Taki gracz nie istnieje na Faceit: **{faceit_nick}**.")
            return

        ekipa[discord_id] = faceit_nick
        zapisz_ekipe(ekipa)
        
        # WPISANIE DO TRWAJĄCEGO SEZONU (Zabezpiecza przed omijaniem late-joinerów)
        sezon = wczytaj_sezon()
        if "nazwa" in sezon and str(test.get('elo', 'Brak')).isdigit():
            player_id = str(test['player_id'])
            if "start_elo" not in sezon:
                sezon["start_elo"] = {}
                
            if player_id not in sezon["start_elo"]:
                sezon["start_elo"][player_id] = int(test['elo'])
                zapisz_sezon(sezon)
                
        await msg.edit(content=f"<@{discord_id}> pomyślnie powiązano z kontem **{faceit_nick}** na Faceit.")

    @commands.command(name="odlacz", aliases=["unlink", "un"])
    async def odlacz_konto(self, ctx, *args):
        ekipa = wczytaj_ekipe()
        
        discord_id = str(ctx.author.id)
        if ctx.message.mentions:
            discord_id = str(ctx.message.mentions[0].id)
            
        if discord_id in ekipa:
            usuniony = ekipa.pop(discord_id)
            zapisz_ekipe(ekipa)
            await ctx.send(f"Odlączono powiązanie z kontem Faceit: **{usuniony}** z profilu <@{discord_id}>.")
        else:
            await ctx.send(f"Ten profil nie ma obecnie podpiętego konta Faceit.")

    @commands.command(name="recent", aliases=["ostatnie", "r", "fr"])
    async def komenda_stats(self, ctx, *args):
        limit = 20
        
        # Logika wyciągania limitu i nicku z args
        parsed_args = []
        for arg in args:
            if arg.isdigit():
                limit = int(arg)
            else:
                parsed_args.append(arg)
        
        nickname = self.parse_nick(ctx, parsed_args)
        
        if not await self.check_nick(ctx, nickname, parsed_args[0] if parsed_args else None):
            return
                
        # Zabezpieczenie przed nadużyciami limitu
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 10
            
        msg = await ctx.send(f"Pobieram historię **{limit}** ostatnich meczów gracza **{nickname}** na Faceit. Może to potrwać kilka sekund...")
        
        gracz = await get_player_stats(nickname)
        if not gracz or gracz == "error":
            await msg.edit(content=f"Nie znalazłem gracza `{nickname}`.")
            return

        from utils.faceit_api import get_multiple_matches_stats
        mecze = await get_multiple_matches_stats(gracz['player_id'], limit)
        
        if not mecze:
            await msg.edit(content=f"Gracz `{nickname}` nie rozegrał jeszcze żadnego meczu CS2.")
            return
            
        wygrane = sum(1 for m in mecze if m['win'])
        wr = int((wygrane / len(mecze)) * 100)
        
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
        emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg("level_default", config.LEVEL_DEFAULT))

        embed = discord.Embed(
            title=f"Seria Ostatnich {len(mecze)} Spotkań - {gracz['nick']}",
            description=f"Skuteczność: **{wr}%** ({wygrane}W - {len(mecze)-wygrane}L)\n"
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

    def parse_nick(self, ctx, args, default_to_author=True):
        """Pomocnik parsujący wzmianki (pingi) lub czyste nicki na nick Faceit."""
        from utils.database import wczytaj_ekipe
        ekipa = wczytaj_ekipe()
        
        # Jeśli nic nie podano, bierzemy autora
        if not args:
            if default_to_author:
                return ekipa.get(str(ctx.author.id))
            return None

        # Pierwszy argument to zazwyczaj to, co nas interesuje
        arg = str(args[0]) if isinstance(args, (tuple, list)) else str(args)

        # Sprawdzanie czy to wzmianka (ping): <@ID> lub <@!ID>
        if arg.startswith("<@") and ">" in arg:
            user_id = arg.replace("<@", "").replace("!", "").replace(">", "")
            # Jeśli osoba ma konto - bierzemy nick. Jeśli nie - zwracamy specjalny obiekt lub None
            return ekipa.get(user_id)
        
        # W przeciwnym razie traktujemy jako czysty nick Faceit
        return arg

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

    @commands.command(name="elo", aliases=["e", "fe"])
    async def komenda_szybkie_elo(self, ctx, *args):
        faceit_nick = self.parse_nick(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, args[0] if args else None):
            return
            
        from utils.faceit_api import get_player_stats
        msg = await ctx.send(f"Sprawdzam aktualne punkty: **{faceit_nick}**...")
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
            kolor = 0xFFA500 if do_spadku < 15 else get_cfg("main_color", 0x2b2d31)
            
        poziom = str(dane['poziom'])
        emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
        emotka_levelu = emotki.get(poziom, get_cfg("level_default", config.LEVEL_DEFAULT))
        
        embed = discord.Embed(
            title=f"Błyskawiczne ELO: {dane['nick']}",
            description=f"Aktualny stan: {emotka_levelu} **{obecne_elo}**\n\n{opis}",
            color=kolor
        )
        embed.set_thumbnail(url=dane['avatar_url'])
        await msg.edit(content=None, embed=embed)

    @commands.command(name="history", aliases=["hist", "historia"])
    async def komenda_historia(self, ctx, *args):
        faceit_nick = self.parse_nick(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, args[0] if args else None):
            return
            
        from utils.faceit_api import get_multiple_matches_stats, get_player_stats
        msg = await ctx.send(f"Pobieram historię gier: **{faceit_nick}**...")
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
            color=get_cfg("main_color", 0x2b2d31)
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
        
    @commands.command(name="maps", aliases=["mapy", "m"])
    async def komenda_mapy(self, ctx, *args):
        faceit_nick = self.parse_nick(ctx, args)
        if not await self.check_nick(ctx, faceit_nick, args[0] if args else None):
            return
            
        from utils.faceit_api import get_map_segments, get_player_stats
        msg = await ctx.send(f"Sprawdzam statystyki map dla gracza **{faceit_nick}**...")
        gracz = await get_player_stats(faceit_nick)
        if not gracz or gracz == "error":
            await msg.edit(content=f"Brak danych o graczu wpisanym: {faceit_nick}")
            return
            
        katalog_map = await get_map_segments(gracz['player_id'])
        if not katalog_map:
            await msg.edit(content=f"Ten gracz nie grał na mapach 5v5.")
            return
            
        mapy_5v5 = []
        for segment in katalog_map:
            if segment.get("mode") == "5v5" and segment.get("type") == "Map":
                nazwa = segment.get("label", "Nieznana")
                stats = segment.get("stats", {})
                mecze_liczba = int(stats.get("Matches", 0))
                win_rate = int(stats.get("Win Rate %", 0))
                if mecze_liczba > 0:
                    mapy_5v5.append({
                        "nazwa": nazwa, "mecze": mecze_liczba, "wr": win_rate, 
                        "kd": float(stats.get("Average K/D Ratio", 1))
                    })
                    
        mapy_5v5.sort(key=lambda x: (x["wr"], x["kd"]), reverse=True)
        if not mapy_5v5:
            await msg.edit(content="Brak danych 5v5 dla tego profilu.")
            return
            
        top_3 = mapy_5v5[:3]
        bottom_3 = mapy_5v5[-3:]
        bottom_3.reverse()
        
        embed = discord.Embed(
            title="Atlas Terenów (Mapy 5v5)",
            description=f"Wizualizacja skuteczności map dla gracza: **{gracz['nick']}**",
            color=get_cfg("main_color", 0x2b2d31)
        )
        
        for i, m in enumerate(top_3):
            embed.add_field(
                name=f"🟢 {m['nazwa']} (Domena)",
                value=f"W/R: **{m['wr']}%** z {m['mecze']} Gier\nK/D: **{m['kd']}**",
                inline=True
            )
            
        embed.add_field(name="\u200b", value="\u200b", inline=False) # Przerwa
        
        for i, m in enumerate(reversed(bottom_3)):
            embed.add_field(
                name=f"🔴 {m['nazwa']} (Weto)",
                value=f"W/R: **{m['wr']}%** z {m['mecze']} Gier\nK/D: **{m['kd']}**",
                inline=True
            )
        
        embed.set_thumbnail(url=gracz['avatar_url'])
        await msg.edit(content=None, embed=embed)
        
    @commands.command(name="compare", aliases=["porownaj", "c", "1v1", "arena"])
    async def komenda_compare(self, ctx, *args):
        limit = 10
        targets = []
        
        # Logika parsująca args
        for arg in args:
            if arg.isdigit():
                limit = int(arg)
            else:
                targets.append(arg)
                
        if len(targets) < 2:
            await ctx.send(f"❌ Musisz podać dwóch graczy! Użycie: `{ctx.prefix}compare [ilość] [Gracz1] [Gracz2]`")
            return
            
        # Zabezpieczenie limitu
        limit = min(max(1, limit), 50)
            
        from utils.faceit_api import get_player_stats, get_multiple_matches_stats
        nick1 = self.parse_nick(ctx, [targets[0]], default_to_author=False)
        nick2 = self.parse_nick(ctx, [targets[1]], default_to_author=False)
        
        if not nick1: nick1 = targets[0]
        if not nick2: nick2 = targets[1]
        
        msg = await ctx.send(f"⚔️ Otwieranie areny... Przygotowuję statystyki z ostatnich **{limit}** meczów dla **{nick1}** i **{nick2}**.")
        
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
        emotki = get_cfg("level_emojis", config.LEVEL_EMOJIS)
        def get_lvl_emoji(lvl):
            return emotki.get(str(lvl), get_cfg("level_default", config.LEVEL_DEFAULT))

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
            color=get_cfg("main_color", 0x2b2d31)
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


    @commands.command(name="pomoc", aliases=["komendy", "help"])
    async def komenda_pomoc(self, ctx, command_name: str = None):
        """Dynamiczny system pomocy z obsługą szczegółów."""
        if not command_name:
            # GŁÓWNY WIDOK POMOCY
            embed = discord.Embed(
                title="🎮 CS2 Faceit Bot — Instrukcja Obsługi",
                description=(f"Bot pozwala na monitorowanie postępów i statystyk Faceit.\n"
                             f"Użyj `{ctx.prefix}pomoc [nazwa]` aby zobaczyć szczegóły komendy.\n\n"
                             f"Większość komend obsługuje **ping gracza** (np. `{ctx.prefix}stats @Gracz`)."),
                color=get_cfg("main_color", 0x2b2d31)
            )
            
            embed.add_field(
                name="👤 PROFIL I POWIĄZANIA", 
                value=f"🔹 `{ctx.prefix}polacz`, `{ctx.prefix}odlacz`, `{ctx.prefix}stats`, `{ctx.prefix}elo`", 
                inline=False
            )
            
            embed.add_field(
                name="📊 ANALIZA MECZÓW", 
                value=f"🔹 `{ctx.prefix}last`, `{ctx.prefix}recent`, `{ctx.prefix}history`, `{ctx.prefix}maps`", 
                inline=False
            )
            
            embed.add_field(
                name="🏆 EKIPA I RYWALIZACJA", 
                value=f"🔹 `{ctx.prefix}top`, `{ctx.prefix}streaks`, `{ctx.prefix}compare`", 
                inline=False
            )
            
            if ctx.author.guild_permissions.administrator:
                embed.add_field(
                    name="🛠️ ADMINISTRACJA", 
                    value=f"🔸 `{ctx.prefix}config`, `{ctx.prefix}sezon`, `{ctx.prefix}tilt_config` ", 
                    inline=False
                )
            
            embed.set_footer(text=f"Prefix bota: {ctx.prefix} | Wszystkie ustawienia pod {ctx.prefix}config")
            await ctx.send(embed=embed)
            return

        # SZCZEGÓŁOWY WIDOK KOMENDY
        target_command = self.bot.get_command(command_name)
        
        if not target_command:
            await ctx.send(f"❌ Nie znalazłem komendy o nazwie `{command_name}`. Wpisz `{ctx.prefix}pomoc` aby zobaczyć listę.")
            return

        # Mapowanie szczegółowych opisów (jeśli nie chcemy polegać na docstringach)
        descriptions = {
            "polacz": "Łączy Twój profil Discord z kontem Faceit. Pozwala to na używanie komend bez wpisywania nicku.",
            "stats": "Wyświetla kompletny paszport statystyk gracza: ELO, poziom, K/D, ADR oraz winstreaki.",
            "last": "Szczegółowa analiza ostatniego meczu. Pokazuje kille, HLTV rating oraz wpływ na punkty ELO.",
            "recent": "Analiza formy z ostatniej serii gier (domyślnie 20). Pokazuje średnie statystyki strzeleckie.",
            "compare": "Arena 1v1. Porównuje formę dwóch graczy ze wskazaniem lidera w każdej kategorii.",
            "history": "Wyświetla listę 5 ostatnich spotkań wraz z wynikiem i Twoimi statystykami.",
            "maps": "Twoja skuteczność na poszczególnych mapach 5v5. Pokazuje WR i K/D.",
            "elo": "Szybki podgląd ELO i informacji ile punktów brakuje do awansu na kolejny poziom.",
            "config": "Panel zarządzania bota. Pozwala zmieniać prefix, kolory i kanały powiadomień.",
            "sezon": "System rankingowy wewnątrz serwera. Pozwala zarządzać startem i końcem sezonu.",
            "tilt_config": "Ustawienia alertów dla serii wygranych/porażek (tzw. Tilt-Meter)."
        }

        # Parametry użycia
        usage_map = {
            "polacz": "[nick_faceit]",
            "stats": "[nick/ping]",
            "last": "[nick/ping]",
            "recent": "[ilość] [nick/ping]",
            "compare": "[ilość] [nick1/ping1] [nick2/ping2]",
            "history": "[nick/ping]",
            "maps": "[nick/ping]",
            "elo": "[nick/ping]",
            "config": "[klucz] [wartość]",
            "sezon": "[operacja]",
            "tilt_config": "[limit/off]"
        }

        name = target_command.name
        desc = descriptions.get(name, target_command.help or "Brak szczegółowego opisu.")
        usage = usage_map.get(name, "")
        aliases = ", ".join([f"`{a}`" for a in target_command.aliases]) if target_command.aliases else "Brak"

        embed = discord.Embed(
            title=f"📖 Komenda: {ctx.prefix}{name}",
            description=desc,
            color=get_cfg("main_color", 0x2b2d31)
        )
        
        embed.add_field(name="💡 Użycie", value=f"`{ctx.prefix}{name} {usage}`", inline=False)
        embed.add_field(name="🔗 Aliasy (skróty)", value=aliases, inline=False)
        
        if name == "recent":
             embed.add_field(name="ℹ️ Info", value="Domyślnie analizuje 20 meczów. Możesz podać własną liczbę (max 50).", inline=False)
        elif name == "compare":
             embed.add_field(name="ℹ️ Info", value="Możesz spingować dwóch graczy lub wpisać ich nicki ręcznie.", inline=False)

        embed.set_footer(text=f"Więcej pomocy pod {ctx.prefix}pomoc")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CSCommands(bot))