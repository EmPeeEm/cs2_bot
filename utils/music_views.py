# utils/music_views.py
import discord
from discord.ext import commands
import wavelink
from utils.music_helpers import create_now_playing_embed, format_duration
from config import MAIN_COLOR

class VolumeModal(discord.ui.Modal, title="🔊 Ustawienie Głośności"):
    volume_input = discord.ui.TextInput(
        label="Poziom głośności (1 - 100%)",
        placeholder="Wpisz liczbę od 1 do 100 (np. 70)",
        min_length=1,
        max_length=3,
        required=True
    )

    def __init__(self, player: wavelink.Player):
        super().__init__()
        self.player = player

    async def on_submit(self, interaction: discord.Interaction):
        val = self.volume_input.value.strip()
        if not val.isdigit():
            return await interaction.response.send_message("❌ Podaj prawidłową liczbę całkowitą!", ephemeral=True)
        
        vol = int(val)
        if not (1 <= vol <= 100):
            return await interaction.response.send_message("❌ Głośność musi mieścić się w przedziale 1 - 100%!", ephemeral=True)
            
        await self.player.set_volume(vol)
        await interaction.response.send_message(f"🔊 Ustawiono głośność na **{vol}%**.", ephemeral=True)

class MusicControlView(discord.ui.View):
    def __init__(self, player: wavelink.Player, cog):
        super().__init__(timeout=None) # Persistent view
        self.player = player
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Sprawdzamy czy użytkownik jest na tym samym kanale głosowym co bot
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Musisz być na kanale głosowym, aby sterować muzyką!", ephemeral=True)
            return False
            
        if self.player.channel and interaction.user.voice.channel.id != self.player.channel.id:
            await interaction.response.send_message("❌ Musisz być na tym samym kanale głosowym co bot!", ephemeral=True)
            return False
            
        return True

    @discord.ui.button(label="Play/Pause", emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.current:
            return await interaction.response.send_message("❌ Nic aktualnie nie jest odtwarzane.", ephemeral=True)
        
        await self.player.pause(not self.player.paused)
        status_str = "wstrzymany ⏸️" if self.player.paused else "wznowiony ▶️"
        await interaction.response.send_message(f"Odtwarzacz został {status_str}.", ephemeral=True)
        
        # Aktualizacja embeda
        await self.cog.update_controller_message(self.player)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.current:
            return await interaction.response.send_message("❌ Brak utworu do pominięcia.", ephemeral=True)
        
        track_title = self.player.current.title
        await self.player.skip(force=True)
        await interaction.response.send_message(f"⏭️ Pominięto: **{track_title}**", ephemeral=False)

    @discord.ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.queue or len(self.player.queue) < 2:
            return await interaction.response.send_message("❌ W kolejce musi być przynajmniej 2 utwory, aby ją przetasować!", ephemeral=True)
        
        self.player.queue.shuffle()
        await interaction.response.send_message("🔀 Przetasowano kolejkę utworów!", ephemeral=True)

    @discord.ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.secondary, row=0)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Przełączanie wavelink queue mode: NORMAL -> LOOP -> LOOP_ALL -> NORMAL
        mode = self.player.queue.mode
        if mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            mode_str = "🔂 Pojedynczy utwór"
        elif mode == wavelink.QueueMode.loop:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            mode_str = "🔁 Cała kolejka"
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            mode_str = "❌ Wyłączona"
            
        await interaction.response.send_message(f"Tryb pętli zmieniony na: **{mode_str}**", ephemeral=True)
        await self.cog.update_controller_message(self.player)

    @discord.ui.button(label="Kolejka", emoji="📜", style=discord.ButtonStyle.secondary, row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.current and len(self.player.queue) == 0:
            return await interaction.response.send_message("📭 Kolejka jest pusta!", ephemeral=True)
        
        embed = discord.Embed(title="📜 Aktualna Kolejka Utworów", color=MAIN_COLOR)
        if self.player.current:
            dur = format_duration(self.player.current.length)
            embed.add_field(name="▶️ Teraz gra", value=f"**[{self.player.current.title}]({self.player.current.uri})** `[{dur}]`", inline=False)
        
        if len(self.player.queue) > 0:
            tracks_list = []
            for idx, tr in enumerate(list(self.player.queue)[:10], start=1):
                tr_dur = format_duration(tr.length)
                tracks_list.append(f"`{idx}.` [{tr.title}]({tr.uri}) `[{tr_dur}]`")
            
            queue_str = "\n".join(tracks_list)
            if len(self.player.queue) > 10:
                queue_str += f"\n*...oraz {len(self.player.queue) - 10} więcej utworów w kolejce.*"
            embed.add_field(name="📋 Następne w kolejce", value=queue_str, inline=False)
        else:
            embed.add_field(name="📋 Następne w kolejce", value="*Brak kolejnych utworów.*", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Głośność", emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def volume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VolumeModal(self.player))

    @discord.ui.button(label="Stop", emoji="🛑", style=discord.ButtonStyle.danger, row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.clear()
        await self.player.disconnect()
        await interaction.response.send_message("🛑 Zatrzymano odtwarzacz i wyczyszczono kolejkę.", ephemeral=False)
