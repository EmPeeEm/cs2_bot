# cogs/roles.py
import discord
from discord.ext import commands
import logging
import asyncio
import typing

from utils.database import (
    wczytaj_ekipe, wczytaj_ustawienia, zapisz_ustawienia, get_cfg
)
from utils.faceit_api import get_player_stats

logger = logging.getLogger("FaceitRoles")

FACEIT_LEVEL_COLORS = {
    1: discord.Color.from_rgb(238, 238, 238),  # Level 1 (Biały / Jasny szary #EEEEEE)
    2: discord.Color.from_rgb(70, 230, 38),    # Level 2 (Zielony Faceit #46E626)
    3: discord.Color.from_rgb(70, 230, 38),    # Level 3 (Zielony Faceit #46E626)
    4: discord.Color.from_rgb(255, 199, 0),    # Level 4 (Żółty Faceit #FFC700)
    5: discord.Color.from_rgb(255, 199, 0),    # Level 5 (Żółty Faceit #FFC700)
    6: discord.Color.from_rgb(255, 199, 0),    # Level 6 (Żółty Faceit #FFC700)
    7: discord.Color.from_rgb(255, 199, 0),    # Level 7 (Żółty Faceit #FFC700)
    8: discord.Color.from_rgb(255, 99, 9),     # Level 8 (Pomarańczowy Faceit #FF6309)
    9: discord.Color.from_rgb(255, 99, 9),     # Level 9 (Pomarańczowy Faceit #FF6309)
    10: discord.Color.from_rgb(254, 31, 67)    # Level 10 (Czerwony Faceit #FE1F43)
}

class FaceitRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_faceit_roles_map(self, guild: discord.Guild) -> typing.Dict[int, discord.Role]:
        """Zwraca mapowanie poziomu Faceit (1-10) na obiekty discord.Role danej gildii."""
        ustawienia = wczytaj_ustawienia(guild.id)
        saved_roles = ustawienia.get("faceit_roles", {})
        roles_map: typing.Dict[int, discord.Role] = {}

        for lvl in range(1, 11):
            role = None
            role_id = saved_roles.get(str(lvl)) or saved_roles.get(lvl)
            if role_id:
                try:
                    role = guild.get_role(int(role_id))
                except (ValueError, TypeError):
                    role = None

            # Fallback po nazwie jeśli rola nie została znaleziona po ID
            if not role:
                expected_name = f"Faceit Level {lvl}".lower()
                for r in guild.roles:
                    if r.name.lower() == expected_name:
                        role = r
                        break

            if role:
                roles_map[lvl] = role

        return roles_map

    async def update_member_faceit_role(self, guild: discord.Guild, member: discord.Member, new_level: typing.Union[int, str]) -> bool:
        """
        Nadaje graczowi rolę odpowiadającą jego poziomowi Faceit i usuwa pozostałe role poziomów.
        Zwraca True jeśli rola została zmieniona, False jeśli nie wymagała zmian lub wystąpił błąd.
        """
        try:
            new_level = int(new_level)
        except (ValueError, TypeError):
            return False

        if not (1 <= new_level <= 10):
            return False

        roles_map = self.get_faceit_roles_map(guild)
        target_role = roles_map.get(new_level)

        if not target_role:
            logger.warning(f"Rola dla Faceit Level {new_level} nie istnieje na serwerze {guild.name} ({guild.id}). Uruchom /faceit_roles_setup.")
            return False

        all_level_roles = set(roles_map.values())
        current_level_roles = [r for r in member.roles if r in all_level_roles]

        # Jeśli gracz ma już właściwą rolę i żadnej innej rangi Faceit - nic nie robimy
        if target_role in member.roles and len(current_level_roles) == 1:
            return False

        roles_to_remove = [r for r in current_level_roles if r.id != target_role.id]
        
        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Aktualizacja poziomu Faceit (usunięcie starej rangi)")
            if target_role not in member.roles:
                await member.add_roles(target_role, reason=f"Aktualizacja poziomu Faceit (awans/spadek na Level {new_level})")
            
            logger.info(f"✅ Zaktualizowano rolę dla {member.display_name} w '{guild.name}' -> {target_role.name}")
            return True
        except discord.Forbidden:
            logger.warning(
                f"⚠️ Brak uprawnień do nadania roli {target_role.name} dla {member.display_name} "
                f"na serwerze '{guild.name}'. Sprawdź czy rola bota jest wyżej w hierarchii serwera!"
            )
            return False
        except Exception as e:
            logger.error(f"❌ Błąd podczas aktualizacji roli dla {member.display_name}: {e}")
            return False

    async def remove_all_faceit_roles(self, guild: discord.Guild, member: discord.Member) -> bool:
        """Usuwa wszystkie role Faceit Level 1-10 z członka (np. po komendzie /odlacz)."""
        roles_map = self.get_faceit_roles_map(guild)
        all_level_roles = set(roles_map.values())
        roles_to_remove = [r for r in member.roles if r in all_level_roles]

        if not roles_to_remove:
            return False

        try:
            await member.remove_roles(*roles_to_remove, reason="Odłączenie profilu Faceit")
            logger.info(f"Usunięto role Faceit z {member.display_name} po odłączeniu konta.")
            return True
        except discord.Forbidden:
            logger.warning(f"Brak uprawnień do usunięcia ról z {member.display_name}.")
            return False
        except Exception as e:
            logger.error(f"Błąd usuwania ról z {member.display_name}: {e}")
            return False

    async def execute_setup(self, ctx):
        """Wewnętrzna logika konfiguracji ról Faceit Level 1-10."""
        await ctx.defer()
        guild = ctx.guild

        if not guild.me.guild_permissions.manage_roles:
            await ctx.send("❌ Bot nie posiada uprawnienia **Zarządzanie rolami** (`Manage Roles`) na tym serwerze!")
            return

        ustawienia = wczytaj_ustawienia(guild.id)
        saved_roles = ustawienia.get("faceit_roles", {})
        if not isinstance(saved_roles, dict):
            saved_roles = {}

        created_count = 0
        mapped_count = 0
        role_summary = []

        for lvl in range(1, 11):
            role_name = f"Faceit Level {lvl}"
            role = None

            # 1. Sprawdzenie po zapisanym ID
            role_id = saved_roles.get(str(lvl)) or saved_roles.get(lvl)
            if role_id:
                try:
                    role = guild.get_role(int(role_id))
                except (ValueError, TypeError):
                    role = None

            # 2. Sprawdzenie po nazwie
            if not role:
                for r in guild.roles:
                    if r.name.lower() == role_name.lower():
                        role = r
                        break

            # 3. Tworzenie nowej roli jeśli brak
            if not role:
                try:
                    role = await guild.create_role(
                        name=role_name,
                        color=FACEIT_LEVEL_COLORS[lvl],
                        hoist=True,
                        reason="Konfiguracja ról Faceit",
                        mentionable=False
                    )
                    created_count += 1
                except discord.Forbidden:
                    await ctx.send("❌ Brak uprawnień do utworzenia roli. Upewnij się, że bot ma uprawnienie `Manage Roles`.")
                    return
                except Exception as e:
                    await ctx.send(f"❌ Wystąpił błąd podczas tworzenia roli `{role_name}`: {e}")
                    return
            else:
                mapped_count += 1
                # Aktualizacja koloru i opcji hoist (wyświetlanie na liście oddzielnie)
                if role < guild.me.top_role:
                    edits = {}
                    if role.color != FACEIT_LEVEL_COLORS[lvl]:
                        edits["color"] = FACEIT_LEVEL_COLORS[lvl]
                    if not role.hoist:
                        edits["hoist"] = True
                    if edits:
                        try:
                            await role.edit(**edits, reason="Aktualizacja ustawień ról Faceit (kolor / wyświetlanie oddzielnie)")
                        except Exception:
                            pass

            saved_roles[str(lvl)] = role.id
            role_summary.append(f"• **Level {lvl}:** <@&{role.id}>")

        ustawienia["faceit_roles"] = saved_roles
        zapisz_ustawienia(guild.id, ustawienia)

        # Sprawdzenie hierarchii ról bota
        bot_top_role = guild.me.top_role
        roles_higher_than_bot = [
            guild.get_role(int(saved_roles[str(lvl)]))
            for lvl in range(1, 11)
            if guild.get_role(int(saved_roles[str(lvl)])) and guild.get_role(int(saved_roles[str(lvl)])) >= bot_top_role
        ]

        hierarchy_warning = ""
        if roles_higher_than_bot:
            role_names = ", ".join(r.name for r in roles_higher_than_bot)
            hierarchy_warning = (
                f"\n\n⚠️ **UWAGA - HIERARCHIA RÓL:**\n"
                f"Rola bota (**{bot_top_role.name}**) znajduje się poniżej niektórych ról Faceit ({role_names})!\n"
                f"Przejdź do: *Ustawienia Serwera -> Role* i **przesuń rolę bota wyżej** niż role `Faceit Level 1-10`, "
                f"aby bot mógł bez problemu nadawać rangi graczom."
            )

        embed = discord.Embed(
            title="🎖️ Konfiguracja Ról Faceit Zakończona",
            description=(
                f"Pomyślnie skonfigurowano 10 ról poziomów Faceit na serwerze!\n"
                f"• Utworzono nowych: **{created_count}**\n"
                f"• Przypięto istniejących: **{mapped_count}**\n\n"
                f"**Skonfigurowane role:**\n" + "\n".join(role_summary) +
                hierarchy_warning
            ),
            color=get_cfg(guild.id, "main_color", 0x2b2d31)
        )
        embed.set_footer(text=f"Użyj {ctx.prefix}faceit_roles sync aby nadać role wszystkim obecnym graczom!")
        await ctx.send(embed=embed)

    async def execute_sync(self, ctx):
        """Wewnętrzna logika synchronizacji ról Faceit."""
        await ctx.defer()
        guild = ctx.guild
        ekipa = wczytaj_ekipe(guild.id)

        if not ekipa:
            await ctx.send(f"❌ Ekipa jest pusta! Połącz konta graczy używając `{ctx.prefix}polacz [nick]`.")
            return

        roles_map = self.get_faceit_roles_map(guild)
        if len(roles_map) < 10:
            await ctx.send(
                f"⚠️ Na serwerze nie znaleziono pełnego zestawu ról Faceit 1-10 (znaleziono {len(roles_map)}/10).\n"
                f"Uruchom najpierw `{ctx.prefix}faceit_roles setup`, aby automatycznie utworzyć role!"
            )
            return

        status_msg = await ctx.send(f"⏳ Rozpoczynam synchronizację ról dla {len(ekipa)} graczy...")

        zaktualizowano = 0
        bez_zmian = 0
        bledy = 0

        for discord_id, player_id in ekipa.items():
            member = guild.get_member(int(discord_id))
            if not member:
                try:
                    member = await guild.fetch_member(int(discord_id))
                except Exception:
                    member = None

            if not member:
                bledy += 1
                continue

            try:
                stats = await get_player_stats(player_id)
                if not stats or stats == "error":
                    bledy += 1
                    continue

                level = stats.get("poziom")
                if level:
                    changed = await self.update_member_faceit_role(guild, member, level)
                    if changed:
                        zaktualizowano += 1
                    else:
                        bez_zmian += 1
                else:
                    bledy += 1
            except Exception as e:
                logger.error(f"Błąd synchronizacji dla {discord_id}: {e}")
                bledy += 1

            # Opóźnienie 0.5s chroniące przed limitami Discord API
            await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="🔄 Wynik Synchronizacji Ról Faceit",
            description=(
                f"Zakończono synchronizację poziomów Faceit na serwerze:\n\n"
                f"• Nadano / zaktualizowano role: **{zaktualizowano}**\n"
                f"• Role były już aktualne: **{bez_zmian}**\n"
                f"• Błędy / brak użytkownika na serwerze: **{bledy}**"
            ),
            color=get_cfg(guild.id, "main_color", 0x2b2d31)
        )
        await status_msg.edit(content=None, embed=embed)

    # --- Grupa komend hybrydowych (/faceit_roles setup, /faceit_roles sync) ---
    @commands.hybrid_group(
        name="faceit_roles",
        aliases=["roles"],
        description="Zarządzanie automatycznym systemem ról Faceit Level 1-10"
    )
    @commands.has_permissions(administrator=True)
    @discord.app_commands.default_permissions(administrator=True)
    async def faceit_roles(self, ctx):
        """Zarządzanie rolami Faceit."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"ℹ️ Użycie: `{ctx.prefix}faceit_roles setup` lub `{ctx.prefix}faceit_roles sync`")

    @faceit_roles.command(
        name="setup",
        description="Automatycznie tworzy i konfiguruje role Faceit Level 1-10 z paletą kolorów"
    )
    @commands.has_permissions(administrator=True)
    @discord.app_commands.default_permissions(administrator=True)
    async def sub_faceit_roles_setup(self, ctx):
        await self.execute_setup(ctx)

    @faceit_roles.command(
        name="sync",
        description="Synchronizuje role Faceit dla wszystkich graczy połączonych na serwerze"
    )
    @commands.has_permissions(administrator=True)
    @discord.app_commands.default_permissions(administrator=True)
    async def sub_faceit_roles_sync(self, ctx):
        await self.execute_sync(ctx)

    # --- Płaskie komendy jako alternatywy (np. !faceit_roles_setup, !roles_setup) ---
    @commands.hybrid_command(
        name="faceit_roles_setup",
        aliases=["roles_setup", "faceit_setup_roles"],
        description="Tworzy i konfiguruje role Faceit Level 1-10 z paletą kolorów"
    )
    @commands.has_permissions(administrator=True)
    @discord.app_commands.default_permissions(administrator=True)
    async def flat_faceit_roles_setup(self, ctx):
        await self.execute_setup(ctx)

    @commands.hybrid_command(
        name="faceit_roles_sync",
        aliases=["roles_sync", "sync_roles"],
        description="Synchronizuje role Faceit dla wszystkich graczy z ekipy"
    )
    @commands.has_permissions(administrator=True)
    @discord.app_commands.default_permissions(administrator=True)
    async def flat_faceit_roles_sync(self, ctx):
        await self.execute_sync(ctx)

async def setup(bot):
    await bot.add_cog(FaceitRolesCog(bot))
