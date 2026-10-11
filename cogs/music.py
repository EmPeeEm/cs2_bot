# cogs/music.py
import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
import re

from config import (
    MAIN_COLOR, 
    MUSIC_DEFAULT_VOLUME, 
    MUSIC_INACTIVITY_TIMEOUT, 
    MUSIC_EMPTY_CHANNEL_TIMEOUT,
    LAVALINK_URI,
    LAVALINK_PASSWORD
)
from utils.music_helpers import create_now_playing_embed, format_duration, resolve_youtube_title, resolve_spotify_title
from utils.music_views import MusicControlView

class Music(commands.Cog):
    """Zaawansowany moduł bota muzycznego zintegrowany z Lavalink i Wavelink."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.controller_messages = {} # guild_id -> discord.Message
        self.active_filters = {} # guild_id -> filter_name

    async def cog_load(self):
        """Łączenie z węzłem Lavalink podczas ładowania Coga."""
        nodes = [
            wavelink.Node(
                uri=LAVALINK_URI,
                password=LAVALINK_PASSWORD,
                inactive_player_timeout=MUSIC_INACTIVITY_TIMEOUT
            )
        ]
        # Inicjalizacja puli połączeń Wavelink
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            print("🔊 [Music Cog] Inicjalizacja puli Lavalink...")
        except Exception as e:
            print(f"⚠️ [Music Cog] Błąd łączenia z Lavalink: {e}")

    # --- LISTENERZY WAVELINK ---

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        node = payload.node
        print(f"✅ [Lavalink] Połączono pomyślnie z węzłem: {node.identifier} ({node.uri})")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player or not player.guild:
            return

        track = payload.track
        guild_id = player.guild.id
        
        # Pobieramy aktywny filtr
        filter_name = self.active_filters.get(guild_id, "Brak")
        
        # Mapowanie trybu pętli
        mode_name = "off"
        if player.queue.mode == wavelink.QueueMode.loop:
            mode_name = "track"
        elif player.queue.mode == wavelink.QueueMode.loop_all:
            mode_name = "queue"

        embed = create_now_playing_embed(
            track=track,
            position_ms=0,
            is_paused=player.paused,
            volume=player.volume,
            loop_mode=mode_name,
            filter_name=filter_name
        )

        view = MusicControlView(player, self)

        # Usuwamy poprzednią wiadomość kontrolera, jeśli istnieje
        old_msg = self.controller_messages.get(guild_id)
        if old_msg:
            try:
                await old_msg.delete()
            except Exception:
                pass

        # Jeśli player ma powiązany kanał tekstowy, wysyłamy nowy panel
        text_channel = getattr(player, 'home', None)
        if text_channel:
            try:
                new_msg = await text_channel.send(embed=embed, view=view)
                self.controller_messages[guild_id] = new_msg
            except Exception as e:
                print(f"⚠️ [Music Cog] Nie udało się wysłać kontrolera: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player or not player.guild:
            return

        # Jeśli kolejka ma kolejne utwory, upewniamy się, że kolejny wystartuje
        if len(player.queue) > 0 and not player.playing:
            try:
                await player.play(player.queue.get())
                return
            except Exception as e:
                print(f"⚠️ [Music Cog] Błąd startu kolejnego utworu: {e}")

        # Jeśli kolejka jest pusta i tryb pętli nie jest aktywny
        if len(player.queue) == 0 and not player.current:
            guild_id = player.guild.id
            old_msg = self.controller_messages.get(guild_id)
            if old_msg:
                try:
                    await old_msg.delete()
                except Exception:
                    pass
                self.controller_messages.pop(guild_id, None)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        player: wavelink.Player = payload.player
        track = payload.track
        print(f"⚠️ [Music Cog] Błąd odtwarzania utworu '{track.title}': {payload.exception}")
        home = getattr(player, 'home', None)
        if home:
            await home.send(f"⚠️ Nie udało się odtworzyć **{track.title}** (ograniczenia platformy). Przechodzę do następnego utworu...")
        if len(player.queue) > 0:
            await player.play(player.queue.get())

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        """Automatyczne odłączenie po określonym czasie braku aktywności."""
        if player.channel:
            home = getattr(player, 'home', None)
            if home:
                embed = discord.Embed(
                    title="💤 Automatyczne Rozłączenie",
                    description="Odtwarzacz był bezczynny przez zbyt długi czas i opuścił kanał głosowy.",
                    color=MAIN_COLOR
                )
                await home.send(embed=embed)
        await player.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Wykrywanie pustego kanału głosowego i opuszczanie go."""
        if member.bot:
            return

        guild = member.guild
        player = guild.voice_client

        if not isinstance(player, wavelink.Player):
            return

        if player.channel:
            # Liczymy członków (bez botów)
            real_members = [m for m in player.channel.members if not m.bot]
            if len(real_members) == 0:
                # Wszyscy wyszli - czekamy krótko i sprawdzamy ponownie
                await asyncio.sleep(MUSIC_EMPTY_CHANNEL_TIMEOUT)
                if player.channel and len([m for m in player.channel.members if not m.bot]) == 0:
                    home = getattr(player, 'home', None)
                    if home:
                        await home.send(embed=discord.Embed(
                            title="🚪 Kanał opustoszał",
                            description="Wszyscy użytkownicy opuścili kanał głosowy. Odtwarzacz został zatrzymany.",
                            color=MAIN_COLOR
                        ))
                    self.active_filters.pop(guild.id, None)
                    await player.disconnect()

    async def update_controller_message(self, player: wavelink.Player):
        """Pomocnik do odświeżania treści wiadomości kontrolera."""
        if not player or not player.guild or not player.current:
            return

        guild_id = player.guild.id
        msg = self.controller_messages.get(guild_id)
        if not msg:
            return

        filter_name = self.active_filters.get(guild_id, "Brak")
        mode_name = "off"
        if player.queue.mode == wavelink.QueueMode.loop:
            mode_name = "track"
        elif player.queue.mode == wavelink.QueueMode.loop_all:
            mode_name = "queue"

        embed = create_now_playing_embed(
            track=player.current,
            position_ms=player.position,
            is_paused=player.paused,
            volume=player.volume,
            loop_mode=mode_name,
            filter_name=filter_name
        )
        try:
            await msg.edit(embed=embed)
        except Exception:
            pass

    # --- AUTOCOMPLETE DLA KOMENDY PLAY ---

    async def play_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Dynamiczne autouzupełnianie wyszukiwania w YouTube / Spotify."""
        if not current.strip():
            return []

        # Jeśli to bezpośredni link URL, nie szukamy autocomplete
        if current.startswith("http://") or current.startswith("https://"):
            return [app_commands.Choice(name=f"🔗 Odtwórz URL: {current[:80]}", value=current)]

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(current, source=wavelink.TrackSource.SoundCloud)
            if not tracks:
                tracks = await wavelink.Playable.search(current, source=wavelink.TrackSource.YouTubeMusic)
            if not tracks:
                return []

            choices = []
            for track in tracks[:7]:
                title = f"{track.title} - {track.author}"
                if len(title) > 95:
                    title = title[:92] + "..."
                dur = format_duration(track.length)
                choice_label = f"{title} [{dur}]"
                choices.append(app_commands.Choice(name=choice_label, value=track.uri or track.title))
            return choices
        except Exception:
            return []

    # --- KOMENDY HYBRYDOWE / SLASH ---

    @commands.hybrid_command(name="play", aliases=["p"], description="Odtwarza utwór lub dodaje go do kolejki.")
    @app_commands.describe(query="Tytuł utworu, fraza wyszukiwania lub link (SoundCloud, Spotify, YouTube)")
    @app_commands.autocomplete(query=play_autocomplete)
    async def play(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Musisz dołączyć do kanału głosowego!", ephemeral=True)

        # Połączenie lub pobranie istniejącego odtwarzacza
        player: wavelink.Player = ctx.voice_client
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                player.autoplay = wavelink.AutoPlayMode.partial
                await player.set_volume(MUSIC_DEFAULT_VOLUME)
            except Exception as e:
                return await ctx.send(f"❌ Nie udało się dołączyć do kanału głosowego: `{e}`", ephemeral=True)
        else:
            player.autoplay = wavelink.AutoPlayMode.partial

        if player.channel.id != ctx.author.voice.channel.id:
            return await ctx.send("❌ Bot gra już na innym kanale głosowym!", ephemeral=True)

        # Zapisujemy kanał tekstowy jako domowy dla kontrolera
        player.home = ctx.channel

        # Wyszukiwanie utworów: YouTube (oEmbed), Spotify (oEmbed), linki bezpośrednie lub SoundCloud
        is_yt = "youtube.com" in query or "youtu.be" in query
        is_spotify = "spotify.com" in query
        tracks = None
        try:
            if is_yt:
                yt_title = await resolve_youtube_title(query)
                search_term = yt_title if yt_title else query
                try:
                    tracks = await wavelink.Playable.search(search_term, source=wavelink.TrackSource.SoundCloud)
                except Exception:
                    pass
                if not tracks:
                    tracks = await wavelink.Playable.search(search_term)
            elif is_spotify:
                sp_title = await resolve_spotify_title(query)
                search_term = sp_title if sp_title else query
                try:
                    tracks = await wavelink.Playable.search(search_term, source=wavelink.TrackSource.SoundCloud)
                except Exception:
                    pass
                if not tracks:
                    tracks = await wavelink.Playable.search(query)
            elif query.startswith("http://") or query.startswith("https://"):
                tracks = await wavelink.Playable.search(query)
            else:
                try:
                    tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
                except Exception:
                    pass
                if not tracks:
                    tracks = await wavelink.Playable.search(query)
        except Exception as e:
            return await ctx.send(f"❌ Błąd wyszukiwania utworu: `{e}`", ephemeral=True)

        if not tracks:
            return await ctx.send("❌ Nie znaleziono żadnych utworów dla podanego zapytania.", ephemeral=True)

        # Obsługa Playlisty
        if isinstance(tracks, wavelink.Playlist):
            added_count = await player.queue.put_wait(tracks)
            for t in tracks:
                t.requester = ctx.author

            embed = discord.Embed(
                title="📑 Załadowano Playlistę",
                description=f"Dodano **{added_count}** utworów z playlisty **{tracks.name}**.",
                color=MAIN_COLOR
            )
            await ctx.send(embed=embed)
        else:
            # Pojedynczy utwór
            track: wavelink.Playable = tracks[0]
            track.requester = ctx.author
            await player.queue.put_wait(track)

            if player.playing:
                dur = format_duration(track.length)
                embed = discord.Embed(
                    title="➕ Dodano do kolejki",
                    description=f"**[{track.title}]({track.uri})** `[{dur}]`\nPozycja w kolejce: `#{len(player.queue)}`",
                    color=MAIN_COLOR
                )
                embed.set_footer(text=f"Zamówił: {ctx.author.display_name}")
                await ctx.send(embed=embed)

        # Jeśli nic nie gra, startujemy odtwarzacz
        if not player.playing:
            await player.play(player.queue.get(), volume=MUSIC_DEFAULT_VOLUME)

    @commands.hybrid_command(name="pause", description="Wstrzymuje odtwarzanie bieżącego utworu.")
    async def pause(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send("❌ Nic aktualnie nie jest odtwarzane.", ephemeral=True)

        await player.pause(True)
        await ctx.send("⏸️ Wstrzymano odtwarzanie.")
        await self.update_controller_message(player)

    @commands.hybrid_command(name="resume", description="Wznawia wstrzymane odtwarzanie.")
    async def resume(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ Brak utworu do wznowienia.", ephemeral=True)

        await player.pause(False)
        await ctx.send("▶️ Wznowiono odtwarzanie.")
        await self.update_controller_message(player)

    @commands.hybrid_command(name="skip", aliases=["next", "sk"], description="Pomija aktualnie odtwarzany utwór.")
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ Nic aktualnie nie jest odtwarzane.", ephemeral=True)

        track_title = player.current.title
        await player.skip(force=True)
        await ctx.send(f"⏭️ Pominięto: **{track_title}**")

    @commands.hybrid_command(name="stop", description="Zatrzymuje muzykę, czyści kolejkę i opuszcza kanał.")
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Bot nie jest połączony z żadnym kanałem.", ephemeral=True)

        player.queue.clear()
        self.active_filters.pop(ctx.guild.id, None)
        await player.disconnect()
        await ctx.send("🛑 Zatrzymano odtwarzacz, wyczyszczono kolejkę i rozłączono bota.")

    @commands.hybrid_command(name="queue", aliases=["q"], description="Pokazuje aktualną kolejkę utworów.")
    async def queue(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or (not player.current and len(player.queue) == 0):
            return await ctx.send("📭 Kolejka jest pusta!", ephemeral=True)

        embed = discord.Embed(title="📜 Aktualna Kolejka Utworów", color=MAIN_COLOR)
        if player.current:
            dur = format_duration(player.current.length)
            embed.add_field(name="▶️ Teraz gra", value=f"**[{player.current.title}]({player.current.uri})** `[{dur}]`", inline=False)

        if len(player.queue) > 0:
            tracks_list = []
            for idx, tr in enumerate(list(player.queue)[:12], start=1):
                tr_dur = format_duration(tr.length)
                tracks_list.append(f"`{idx}.` [{tr.title}]({tr.uri}) `[{tr_dur}]`")

            queue_str = "\n".join(tracks_list)
            if len(player.queue) > 12:
                queue_str += f"\n*...oraz {len(player.queue) - 12} więcej utworów.*"
            embed.add_field(name=f"📋 W kolejce ({len(player.queue)})", value=queue_str, inline=False)
        else:
            embed.add_field(name="📋 W kolejce", value="*Brak kolejnych utworów.*", inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="nowplaying", aliases=["np"], description="Wyświetla panel aktualnie granego utworu.")
    async def nowplaying(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ Nic aktualnie nie jest odtwarzane.", ephemeral=True)

        filter_name = self.active_filters.get(ctx.guild.id, "Brak")
        mode_name = "off"
        if player.queue.mode == wavelink.QueueMode.loop:
            mode_name = "track"
        elif player.queue.mode == wavelink.QueueMode.loop_all:
            mode_name = "queue"

        embed = create_now_playing_embed(
            track=player.current,
            position_ms=player.position,
            is_paused=player.paused,
            volume=player.volume,
            loop_mode=mode_name,
            filter_name=filter_name
        )
        view = MusicControlView(player, self)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="volume", aliases=["vol"], description="Ustawia głośność odtwarzacza (1 - 100%).")
    @app_commands.describe(level="Poziom głośności od 1 do 100")
    async def volume(self, ctx: commands.Context, level: int):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Bot nie odtwarza muzyki.", ephemeral=True)

        if not (1 <= level <= 100):
            return await ctx.send("❌ Głośność musi mieścić się w przedziale 1 - 100%!", ephemeral=True)

        await player.set_volume(level)
        await ctx.send(f"🔊 Ustawiono głośność na **{level}%**.")
        await self.update_controller_message(player)

    @commands.hybrid_command(name="loop", description="Zmienia tryb zapętlania (off, track, queue).")
    @app_commands.describe(mode="Tryb zapętlania")
    @app_commands.choices(mode=[
        app_commands.Choice(name="❌ Wyłączona", value="off"),
        app_commands.Choice(name="🔂 Pojedynczy utwór", value="track"),
        app_commands.Choice(name="🔁 Cała kolejka", value="queue")
    ])
    async def loop(self, ctx: commands.Context, mode: str):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Bot nie odtwarza muzyki.", ephemeral=True)

        if mode == "track":
            player.queue.mode = wavelink.QueueMode.loop
            msg = "🔂 Włączono zapętlanie **bieżącego utworu**."
        elif mode == "queue":
            player.queue.mode = wavelink.QueueMode.loop_all
            msg = "🔁 Włączono zapętlanie **całej kolejki**."
        else:
            player.queue.mode = wavelink.QueueMode.normal
            msg = "❌ Wyłączono zapętlanie."

        await ctx.send(msg)
        await self.update_controller_message(player)

    @commands.hybrid_command(name="shuffle", description="Miesza kolejność utworów w kolejce.")
    async def shuffle(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or len(player.queue) < 2:
            return await ctx.send("❌ Za mało utworów w kolejce, aby przetasować!", ephemeral=True)

        player.queue.shuffle()
        await ctx.send("🔀 Przetasowano kolejkę utworów!")

    @commands.hybrid_command(name="clear", description="Czyści wszystkie utwory z kolejki.")
    async def clear(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or len(player.queue) == 0:
            return await ctx.send("❌ Kolejka jest już pusta!", ephemeral=True)

        player.queue.clear()
        await ctx.send("🧹 Wyczyszczono całą kolejkę utworów.")

    @commands.hybrid_command(name="seek", description="Przewija utwór do wskazanego momentu (np. 1:30 lub 90).")
    @app_commands.describe(position="Pozycja w sekundach lub formacie MM:SS (np. 1:45)")
    async def seek(self, ctx: commands.Context, position: str):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ Nic aktualnie nie jest odtwarzane.", ephemeral=True)

        # Parsowanie formatu MM:SS lub SS
        pos_seconds = 0
        if ":" in position:
            parts = position.split(":")
            try:
                if len(parts) == 2:
                    pos_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    pos_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                return await ctx.send("❌ Niepoprawny format czasu. Użyj formatu `MM:SS` (np. `1:30`).", ephemeral=True)
        else:
            if not position.isdigit():
                return await ctx.send("❌ Podaj liczbę sekund lub format `MM:SS`.", ephemeral=True)
            pos_seconds = int(position)

        pos_ms = pos_seconds * 1000
        if pos_ms > player.current.length:
            return await ctx.send("❌ Pozycja przekracza długość utworu!", ephemeral=True)

        await player.seek(pos_ms)
        await ctx.send(f"⏩ Przewinięto do `{format_duration(pos_ms)}`.")
        await self.update_controller_message(player)

    @commands.hybrid_command(name="filter", description="Nakłada filtr audio na odtwarzaną muzykę.")
    @app_commands.describe(preset="Wybierz filtr dźwiękowy")
    @app_commands.choices(preset=[
        app_commands.Choice(name="Brak / Reset", value="reset"),
        app_commands.Choice(name="🔊 Bassboost", value="bassboost"),
        app_commands.Choice(name="⚡ Nightcore", value="nightcore"),
        app_commands.Choice(name="🎧 8D Audio (Spatial)", value="8d"),
        app_commands.Choice(name="🐢 Slowed", value="slowed")
    ])
    async def filter(self, ctx: commands.Context, preset: str):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ Bot nie odtwarza muzyki.", ephemeral=True)

        filters = wavelink.Filters()

        if preset == "bassboost":
            # Wzmocnienie niskich częstotliwości (Equalizer)
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.3},
                {"band": 1, "gain": 0.25},
                {"band": 2, "gain": 0.2},
                {"band": 3, "gain": 0.1}
            ])
            self.active_filters[ctx.guild.id] = "🔊 Bassboost"
            msg = "🔊 Zastosowano filtr: **Bassboost**."

        elif preset == "nightcore":
            # Przyspieszenie + podwyższenie pitchu
            filters.timescale.set(speed=1.2, pitch=1.2, rate=1.0)
            self.active_filters[ctx.guild.id] = "⚡ Nightcore"
            msg = "⚡ Zastosowano filtr: **Nightcore**."

        elif preset == "8d":
            # Efekt rotacji przestrzennej
            filters.rotation.set(rotation_hz=0.2)
            self.active_filters[ctx.guild.id] = "🎧 8D Audio"
            msg = "🎧 Zastosowano filtr: **8D Audio**."

        elif preset == "slowed":
            filters.timescale.set(speed=0.85, pitch=0.85, rate=1.0)
            self.active_filters[ctx.guild.id] = "🐢 Slowed"
            msg = "🐢 Zastosowano filtr: **Slowed**."

        else:
            self.active_filters[ctx.guild.id] = "Brak"
            msg = "🔄 Zresetowano filtry audio."

        await player.set_filters(filters)
        await ctx.send(msg)
        await self.update_controller_message(player)

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
