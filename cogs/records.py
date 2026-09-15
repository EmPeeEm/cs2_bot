# cogs/records.py
import discord
from discord.ext import commands
import sqlite3
import random
import datetime
import json
from utils.database import wczytaj_ustawienia, zapisz_ustawienia, get_cfg, DB_PATH
import config

CATEGORIES = {
    "max_kills": {
        "title": "👑 Najwięcej killi (Mecz)",
        "col": "kills",
        "func": "MAX",
        "unit": "killi",
        "is_bad": False,
        "texts_key": "RECORD_KILLS_TEXTS",
        "tie_texts_key": "RECORD_KILLS_TIE_TEXTS",
        "extra_where": ""
    },
    "max_hltv": {
        "title": "⭐ Najwyższe HLTV (Mecz)",
        "col": "hltv",
        "func": "MAX",
        "unit": "HLTV",
        "is_bad": False,
        "texts_key": "RECORD_HLTV_TEXTS",
        "tie_texts_key": "RECORD_HLTV_TIE_TEXTS",
        "extra_where": ""
    },
    "max_ud": {
        "title": "💣 Najwyższe Utility Damage",
        "col": "ud",
        "func": "MAX",
        "unit": "UD",
        "is_bad": False,
        "texts_key": "RECORD_UD_TEXTS",
        "tie_texts_key": "RECORD_UD_TIE_TEXTS",
        "extra_where": ""
    },
    "max_winstreak": {
        "title": "🔥 Najdłuższa seria zwycięstw (Winstreak)",
        "unit": "wygranych z rzędu",
        "is_bad": False,
        "texts_key": "RECORD_WINSTREAK_TEXTS",
        "tie_texts_key": "RECORD_WINSTREAK_TIE_TEXTS",
        "is_custom": True
    },
    "min_kills": {
        "title": "🐌 Najmniej killi (Pełen mecz)",
        "col": "kills",
        "func": "MIN",
        "unit": "killi",
        "is_bad": True,
        "texts_key": "RECORD_LOW_KILLS_TEXTS",
        "tie_texts_key": "RECORD_LOW_KILLS_TIE_TEXTS",
        "extra_where": "AND m.rounds >= 13"
    },
    "min_hltv": {
        "title": "🤖 Najniższe HLTV (Mecz)",
        "col": "hltv",
        "func": "MIN",
        "unit": "HLTV",
        "is_bad": True,
        "texts_key": "RECORD_LOW_HLTV_TEXTS",
        "tie_texts_key": "RECORD_LOW_HLTV_TIE_TEXTS",
        "extra_where": ""
    },
    "max_deaths": {
        "title": "💀 Najwięcej zgonów (Mecz)",
        "col": "deaths",
        "func": "MAX",
        "unit": "zgonów",
        "is_bad": True,
        "texts_key": "RECORD_DEATHS_TEXTS",
        "tie_texts_key": "RECORD_DEATHS_TIE_TEXTS",
        "extra_where": ""
    },
    "max_lossstreak": {
        "title": "❄️ Najdłuższa seria porażek (Loss-streak)",
        "unit": "porażek z rzędu",
        "is_bad": True,
        "texts_key": "RECORD_LOSSSTREAK_TEXTS",
        "tie_texts_key": "RECORD_LOSSSTREAK_TIE_TEXTS",
        "is_custom": True
    },
    "season_mvps": {
        "title": "✨ MVP Zakończonych Sezonów",
        "unit": "",
        "is_bad": False,
        "is_custom": True,
        "is_season": True
    }
}

def format_date(timestamp):
    if not timestamp:
        return "Brak daty"
    try:
        ts = float(timestamp)
        if ts > 1000000000000:
            ts = ts / 1000.0
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(timestamp)[:10]

def get_extreme_value(guild_id, category):
    cat = CATEGORIES[category]
    if cat.get("is_custom"):
        return None
    col = cat["col"]
    func = cat["func"]
    extra_where = cat["extra_where"]
    
    query = f"""
        SELECT {func}(mh.{col}) 
        FROM match_history mh
        JOIN guild_players gp ON mh.player_id = gp.player_id
        JOIN matches m ON mh.match_id = m.match_id
        WHERE gp.guild_id = ? {extra_where}
    """
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(guild_id),))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else None
    except Exception as e:
        print(f"Error getting extreme value for {category}: {e}")
        return None

def get_extreme_value_excluding(guild_id, category, current_match_id):
    cat = CATEGORIES[category]
    if cat.get("is_custom"):
        return None
    col = cat["col"]
    func = cat["func"]
    extra_where = cat["extra_where"]
    
    query = f"""
        SELECT {func}(mh.{col}) 
        FROM match_history mh
        JOIN guild_players gp ON mh.player_id = gp.player_id
        JOIN matches m ON mh.match_id = m.match_id
        WHERE gp.guild_id = ? AND mh.match_id != ? {extra_where}
    """
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(guild_id), str(current_match_id)))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else None
    except Exception as e:
        print(f"Error getting extreme value excluding match {current_match_id}: {e}")
        return None

def get_record_holders(guild_id, category, value):
    if value is None:
        return []
    cat = CATEGORIES[category]
    if cat.get("is_custom"):
        return []
    col = cat["col"]
    extra_where = cat["extra_where"]
    
    query = f"""
        SELECT gp.nickname, gp.discord_id, m.map_name, m.score, m.match_date, mh.match_id
        FROM match_history mh
        JOIN matches m ON mh.match_id = m.match_id
        JOIN guild_players gp ON mh.player_id = gp.player_id
        WHERE gp.guild_id = ? AND mh.{col} = ? {extra_where}
        ORDER BY m.match_date ASC
    """
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(guild_id), value))
            rows = cursor.fetchall()
            return [
                {
                    "nickname": row[0],
                    "discord_id": row[1],
                    "map_name": row[2],
                    "score": row[3],
                    "match_date": row[4],
                    "match_id": row[5]
                }
                for row in rows
            ]
    except Exception as e:
        print(f"Error getting record holders: {e}")
        return []

def get_streak_records(guild_id, exclude_match_id=None):
    """
    Oblicza rekordowe serie zwycięstw i porażek dla graczy danej gildii.
    """
    query = """
        SELECT gp.player_id, gp.discord_id, gp.nickname, mh.win, m.match_date, m.map_name, m.score, mh.match_id
        FROM match_history mh
        JOIN matches m ON mh.match_id = m.match_id
        JOIN guild_players gp ON mh.player_id = gp.player_id
        WHERE gp.guild_id = ?
        ORDER BY gp.player_id, m.match_date ASC
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(guild_id),))
            rows = cursor.fetchall()
            
        player_streaks = {}
        current_pid = None
        cur_w = 0
        cur_l = 0
        
        for r in rows:
            p_id, d_id, nick, win, m_date, map_name, score, m_id = r
            if exclude_match_id and str(m_id) == str(exclude_match_id):
                continue
                
            if p_id != current_pid:
                current_pid = p_id
                cur_w = 0
                cur_l = 0
                if p_id not in player_streaks:
                    player_streaks[p_id] = {
                        "discord_id": d_id,
                        "nickname": nick,
                        "max_w": 0,
                        "w_info": None,
                        "max_l": 0,
                        "l_info": None
                    }
                    
            if win == 1:
                cur_w += 1
                cur_l = 0
                if cur_w > player_streaks[p_id]["max_w"]:
                    player_streaks[p_id]["max_w"] = cur_w
                    player_streaks[p_id]["w_info"] = {
                        "discord_id": d_id,
                        "nickname": nick,
                        "map_name": map_name,
                        "score": score,
                        "match_date": m_date,
                        "match_id": m_id
                    }
            else:
                cur_l += 1
                cur_w = 0
                if cur_l > player_streaks[p_id]["max_l"]:
                    player_streaks[p_id]["max_l"] = cur_l
                    player_streaks[p_id]["l_info"] = {
                        "discord_id": d_id,
                        "nickname": nick,
                        "map_name": map_name,
                        "score": score,
                        "match_date": m_date,
                        "match_id": m_id
                    }
                    
        global_max_w = 0
        w_holders = []
        global_max_l = 0
        l_holders = []
        
        for p_id, p_data in player_streaks.items():
            if p_data["max_w"] > global_max_w:
                global_max_w = p_data["max_w"]
                w_holders = [p_data["w_info"]] if p_data["w_info"] else []
            elif p_data["max_w"] == global_max_w and global_max_w > 0:
                if p_data["w_info"]:
                    w_holders.append(p_data["w_info"])
                    
            if p_data["max_l"] > global_max_l:
                global_max_l = p_data["max_l"]
                l_holders = [p_data["l_info"]] if p_data["l_info"] else []
            elif p_data["max_l"] == global_max_l and global_max_l > 0:
                if p_data["l_info"]:
                    l_holders.append(p_data["l_info"])
                    
        return {
            "max_winstreak": (global_max_w if global_max_w > 0 else None, w_holders),
            "max_lossstreak": (global_max_l if global_max_l > 0 else None, l_holders)
        }
    except Exception as e:
        print(f"Error calculating streak records: {e}")
        return {
            "max_winstreak": (None, []),
            "max_lossstreak": (None, [])
        }

def get_season_mvps(guild_id):
    """
    Pobiera listę wszystkich zakończonych sezonów wraz z ich MVP.
    Format: [nr sezonu]. [nazwa sezonu] - [mvp sezonu]
    """
    query = """
        SELECT id, name, archive_data
        FROM seasons
        WHERE guild_id = ? AND is_active = 0
        ORDER BY id ASC
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(guild_id),))
            rows = cursor.fetchall()
            
        seasons_list = []
        for i, (s_id, s_name, archive_json) in enumerate(rows, 1):
            if archive_json:
                try:
                    archive = json.loads(archive_json)
                    if isinstance(archive, list) and len(archive) > 0:
                        mvp = archive[0]
                        seasons_list.append({
                            "nr": i,
                            "nazwa": s_name,
                            "discord_id": mvp.get("discord_id"),
                            "nick": mvp.get("nick"),
                            "progres": mvp.get("progres", 0),
                            "obecne": mvp.get("obecne", 0)
                        })
                except Exception as e:
                    print(f"Error parsing season archive {s_id}: {e}")
        return seasons_list
    except Exception as e:
        print(f"Error getting season mvps: {e}")
        return []

class RecordsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_category_embed(self, guild_id, category):
        cat_info = CATEGORIES[category]
        
        # Specjalna karta MVP Sezonów
        if category == "season_mvps":
            embed = discord.Embed(
                title="✨ MVP ZAKOŃCZONYCH SEZONÓW",
                color=0xFFD700
            )
            seasons = get_season_mvps(guild_id)
            if not seasons:
                embed.description = "*Brak zakończonych sezonów. Tytuł MVP zostanie wpisany po zakończeniu pierwszego sezonu!*"
            else:
                lines = []
                for s in seasons:
                    nr = s["nr"]
                    nazwa = s["nazwa"]
                    d_id = s.get("discord_id")
                    progres = s.get("progres", 0)
                    znak = "+" if progres > 0 else ""
                    if d_id:
                        lines.append(f"**{nr}.** **{nazwa}** — <@{d_id}> *({znak}{progres} ELO)*")
                    else:
                        lines.append(f"**{nr}.** **{nazwa}** — **{s.get('nick', 'Gracz')}** *({znak}{progres} ELO)*")
                embed.description = "\n".join(lines)
            return embed

        # Karty serii (winstreak / lossstreak)
        if category in ["max_winstreak", "max_lossstreak"]:
            streak_data = get_streak_records(guild_id)
            val, holders = streak_data[category]
            color = 0x00FF00 if not cat_info["is_bad"] else 0xFF0000
            embed = discord.Embed(
                title=cat_info["title"],
                color=color
            )
            if val is None:
                value_str = "*Brak rekordów*"
            else:
                formatted_val = str(val)
                ikona = "🏆" if not cat_info["is_bad"] else "💀"
                value_str = f"{ikona} Wynik: **{formatted_val}** {cat_info['unit']}\n\n"
                if holders:
                    holder_lines = []
                    for h in holders:
                        date_str = format_date(h["match_date"])
                        holder_lines.append(
                            f"• <@{h['discord_id']}> — *{h['map_name']} ({h['score']}), {date_str}*"
                        )
                    value_str += "\n".join(holder_lines)
                else:
                    value_str += "*Brak posiadaczy*"
            embed.description = value_str
            return embed

        # Standardowe kategorie meczowe
        val = get_extreme_value(guild_id, category)
        color = 0x00FF00 if not cat_info["is_bad"] else 0xFF0000
        embed = discord.Embed(
            title=cat_info["title"],
            color=color
        )
        
        if val is None:
            value_str = "*Brak rekordów*"
        else:
            holders = get_record_holders(guild_id, category, val)
            formatted_val = f"{val:.2f}" if isinstance(val, float) else str(val)
            ikona = "🏆" if not cat_info["is_bad"] else "💀"
            value_str = f"{ikona} Wynik: **{formatted_val}** {cat_info['unit']}\n\n"
            
            if holders:
                holder_lines = []
                for h in holders:
                    date_str = format_date(h["match_date"])
                    holder_lines.append(
                        f"• <@{h['discord_id']}> — *{h['map_name']} ({h['score']}), {date_str}*"
                    )
                value_str += "\n".join(holder_lines)
            else:
                value_str += "*Brak posiadaczy*"
                
        embed.description = value_str
        return embed

    async def generate_records_embed(self, guild_id):
        # Fallback na wypadek gdyby pojedyncza wiadomość była wciąż używana
        embed = discord.Embed(
            title="🏆 REKORDY SERWERA: HALA SŁAW I WSTYDU",
            description="Tutaj zobaczysz rekordy wszech czasów graczy naszej ekipy.\n*Wszystkie statystyki pobierane automatycznie z bazy danych.*",
            color=get_cfg(guild_id, "main_color", 0xFF5500)
        )
        
        good_fields = []
        bad_fields = []
        
        streak_data = get_streak_records(guild_id)
        
        for category, cat_info in CATEGORIES.items():
            if category == "season_mvps":
                continue
            elif category in ["max_winstreak", "max_lossstreak"]:
                val, holders = streak_data[category]
            else:
                val = get_extreme_value(guild_id, category)
                holders = get_record_holders(guild_id, category, val) if val is not None else []
                
            if val is None:
                value_str = "*Brak rekordów*"
            else:
                formatted_val = f"{val:.2f}" if isinstance(val, float) else str(val)
                value_str = f"**{formatted_val}** {cat_info['unit']}\n"
                if holders:
                    holder_lines = []
                    for h in holders:
                        date_str = format_date(h["match_date"])
                        holder_lines.append(
                            f"• <@{h['discord_id']}> — *{h['map_name']} ({h['score']}), {date_str}*"
                        )
                    value_str += "\n".join(holder_lines)
            
            if cat_info["is_bad"]:
                bad_fields.append((cat_info["title"], value_str))
            else:
                good_fields.append((cat_info["title"], value_str))
                
        embed.add_field(name="🟢 HALA SŁAW", value="\u200b", inline=False)
        for title, val_str in good_fields:
            embed.add_field(name=title, value=val_str, inline=False)
            
        embed.add_field(name="🔴 HALA WSTYDU", value="\u200b", inline=False)
        for title, val_str in bad_fields:
            embed.add_field(name=title, value=val_str, inline=False)
            
        # MVP Sezonów na dole
        seasons = get_season_mvps(guild_id)
        if seasons:
            mvp_lines = []
            for s in seasons:
                d_id = s.get("discord_id")
                progres = s.get("progres", 0)
                znak = "+" if progres > 0 else ""
                mvp_lines.append(f"**{s['nr']}.** **{s['nazwa']}** — <@{d_id}> *({znak}{progres} ELO)*")
            embed.add_field(name="✨ MVP ZAKOŃCZONYCH SEZONÓW", value="\n".join(mvp_lines), inline=False)
            
        embed.set_footer(text="Rekordy aktualizują się automatycznie po każdym meczu.")
        return embed

    async def update_records_board(self, guild_id):
        ustawienia = wczytaj_ustawienia(guild_id)
        chan_id = ustawienia.get("kanal_rekordow")
        msg_ids = ustawienia.get("rekordy_msg_ids", {})
        msg_id_old = ustawienia.get("rekordy_msg_id")
        
        if not chan_id:
            return
            
        channel = self.bot.get_channel(int(chan_id))
        if not channel:
            return
            
        if isinstance(msg_ids, dict):
            updated_ids = dict(msg_ids)
            for category in CATEGORIES.keys():
                embed = self.generate_category_embed(guild_id, category)
                msg_id = msg_ids.get(category)
                if msg_id:
                    try:
                        msg = await channel.fetch_message(int(msg_id))
                        await msg.edit(embed=embed)
                        continue
                    except (discord.NotFound, discord.HTTPException):
                        pass
                
                # Jeśli danej karty jeszcze nie ma na kanale (nowa kategoria), wyślij ją
                try:
                    new_msg = await channel.send(embed=embed)
                    updated_ids[category] = new_msg.id
                except Exception as e:
                    print(f"Błąd wysyłania nowej karty dla kategorii {category}: {e}")
                    
            if updated_ids != msg_ids:
                ustawienia["rekordy_msg_ids"] = updated_ids
                zapisz_ustawienia(guild_id, ustawienia)
        elif msg_id_old:
            try:
                embed = await self.generate_records_embed(guild_id)
                msg = await channel.fetch_message(int(msg_id_old))
                await msg.edit(embed=embed)
            except Exception as e:
                print(f"Błąd podczas edycji starej tablicy rekordów: {e}")

    @commands.command(name="rekordy_setup", aliases=["records_setup"])
    @commands.has_permissions(administrator=True)
    async def records_setup(self, ctx):
        """Konfiguruje dedykowany kanał z tablicą rekordów (każda kategoria w osobnej wiadomości)."""
        guild_id = ctx.guild.id
        ustawienia = wczytaj_ustawienia(guild_id)
        
        msg = await ctx.send("⏳ Tworzenie kanału rekordów i generowanie wiadomości...")
        
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)
        }
        
        try:
            # Tworzymy nowy kanał
            new_channel = await ctx.guild.create_text_channel(name="🏆-hala-sław", overwrites=overwrites)
            
            # Nagłówek główny
            header_embed = discord.Embed(
                title="🏆 TABLICA REKORDÓW WSZECH CZASÓW",
                description="Statystyki są pobierane automatycznie po każdym meczu z bazy danych Faceit.\nKażdy rekord poniżej ma swoją dedykowaną kartę.",
                color=get_cfg(guild_id, "main_color", 0xFF5500)
            )
            await new_channel.send(embed=header_embed)
            
            # Wysyłamy oddzielną wiadomość dla każdego rekordu i zbieramy ich ID
            msg_ids = {}
            for category in CATEGORIES.keys():
                embed = self.generate_category_embed(guild_id, category)
                board_msg = await new_channel.send(embed=embed)
                msg_ids[category] = board_msg.id
                
            ustawienia["kanal_rekordow"] = new_channel.id
            ustawienia["rekordy_msg_ids"] = msg_ids
            # Czyścimy stary pojedynczy klucz
            if "rekordy_msg_id" in ustawienia:
                del ustawienia["rekordy_msg_id"]
            zapisz_ustawienia(guild_id, ustawienia)
            
            await msg.edit(content=f"✅ Stworzono kanał {new_channel.mention} z dedykowanymi wiadomościami dla każdego rekordu!")
        except Exception as e:
            await msg.edit(content=f"❌ Błąd podczas konfiguracji: {e}")

    @commands.command(name="rekordy_reload", aliases=["rr"])
    @commands.has_permissions(administrator=True)
    async def records_reload(self, ctx):
        """Wymusza aktualizację tablicy rekordów na kanale."""
        guild_id = ctx.guild.id
        msg = await ctx.send("⏳ Aktualizowanie tablicy rekordów...")
        await self.update_records_board(guild_id)
        await msg.edit(content="✅ Tablica rekordów została zaktualizowana!")

    def extract_new_value(self, category, stats, win=None, player_id=None, guild_id=None):
        if category == "max_kills" or category == "min_kills":
            return int(stats.get('kille', 0))
        elif category == "max_hltv" or category == "min_hltv":
            return float(stats.get('hltv', 0.0))
        elif category == "max_ud":
            return float(stats.get('ud', 0.0))
        elif category == "max_deaths":
            return int(stats.get('dedy', 0))
        return None

    async def check_and_announce(self, guild_id, discord_id, player_id, match_id, stats, win):
        # Sprawdzamy czy dany mecz kwalifikuje się do rekordów
        rounds = int(stats.get('rounds', 0))
        
        any_change = False
        announcements = []
        
        # 1. Sprawdzenie standardowych kategorii
        for category, cat_info in CATEGORIES.items():
            if cat_info.get("is_custom"):
                continue
                
            # Ograniczenie dla min_kills
            if category == "min_kills" and rounds < 13:
                continue
                
            new_val = self.extract_new_value(category, stats)
            if new_val is None:
                continue
                
            prev_val = get_extreme_value_excluding(guild_id, category, match_id)
            
            is_broken = False
            is_tied = False
            
            if prev_val is None:
                # Brak dotychczasowego rekordu (pierwszy mecz w bazie)
                is_broken = True
            else:
                if cat_info["func"] == "MAX":
                    if new_val > prev_val:
                        is_broken = True
                    elif new_val == prev_val:
                        is_tied = True
                else:  # MIN
                    if new_val < prev_val:
                        is_broken = True
                    elif new_val == prev_val:
                        is_tied = True
                        
            if is_broken or is_tied:
                existing_holders = get_record_holders(guild_id, category, new_val)
                player_already_holder = any(h["discord_id"] == str(discord_id) and h["match_id"] == str(match_id) for h in existing_holders)
                
                if player_already_holder:
                    continue
                    
                any_change = True
                gracz_mention = f"<@{discord_id}>"
                formatted_val = f"{new_val:.2f}" if isinstance(new_val, float) else str(new_val)
                mapa = stats.get('mapa', 'Nieznana')
                wynik_meczu = stats.get('wynik', '0-0')
                
                if is_broken:
                    texts_key = cat_info["texts_key"]
                    pula = get_cfg(guild_id, texts_key.lower(), getattr(config, texts_key))
                    if pula:
                        msg_template = random.choice(pula)
                        msg_text = msg_template.format(
                            gracz=gracz_mention,
                            wynik=formatted_val,
                            mapa=mapa,
                            wynik_meczu=wynik_meczu
                        )
                        announcements.append(msg_text)
                    else:
                        announcements.append(
                            f"🏆 **NOWY REKORD!** {gracz_mention} pobił rekord w kategorii **{cat_info['title']}** osiągając wynik **{formatted_val}** na mapie **{mapa}** ({wynik_meczu})!"
                        )
                elif is_tied:
                    tie_texts_key = cat_info["tie_texts_key"]
                    pula = get_cfg(guild_id, tie_texts_key.lower(), getattr(config, tie_texts_key))
                    if pula:
                        msg_template = random.choice(pula)
                        msg_text = msg_template.format(
                            gracz=gracz_mention,
                            wynik=formatted_val,
                            mapa=mapa,
                            wynik_meczu=wynik_meczu
                        )
                        announcements.append(msg_text)
                    else:
                        announcements.append(
                            f"🤝 **WYRÓWNANIE REKORDU!** {gracz_mention} wyrównał rekord w kategorii **{cat_info['title']}** osiągając wynik **{formatted_val}** na mapie **{mapa}** ({wynik_meczu})!"
                        )

        # 2. Sprawdzenie rekordów serii (Winstreak / Loss-streak)
        streak_data_prev = get_streak_records(guild_id, exclude_match_id=match_id)
        streak_data_now = get_streak_records(guild_id)
        
        target_cat = "max_winstreak" if win else "max_lossstreak"
        cat_info = CATEGORIES[target_cat]
        prev_streak_val, _ = streak_data_prev[target_cat]
        now_streak_val, now_holders = streak_data_now[target_cat]
        
        # Sprawdzamy, czy ten gracz jest posiadaczem obecnego rekordu i czy pobił/wyrównał wynik
        is_holder_now = any(str(h.get("match_id")) == str(match_id) and str(h.get("discord_id")) == str(discord_id) for h in now_holders)
        
        if is_holder_now and now_streak_val and now_streak_val >= 2:
            is_broken = False
            is_tied = False
            
            if prev_streak_val is None:
                is_broken = True
            elif now_streak_val > prev_streak_val:
                is_broken = True
            elif now_streak_val == prev_streak_val:
                # Sprawdzamy czy to wyrównanie rekordu
                is_tied = True
                
            if is_broken or is_tied:
                any_change = True
                gracz_mention = f"<@{discord_id}>"
                mapa = stats.get('mapa', 'Nieznana')
                wynik_meczu = stats.get('wynik', '0-0')
                formatted_val = str(now_streak_val)
                
                if is_broken:
                    texts_key = cat_info["texts_key"]
                    pula = get_cfg(guild_id, texts_key.lower(), getattr(config, texts_key))
                    if pula:
                        msg_template = random.choice(pula)
                        msg_text = msg_template.format(
                            gracz=gracz_mention,
                            wynik=formatted_val,
                            mapa=mapa,
                            wynik_meczu=wynik_meczu
                        )
                        announcements.append(msg_text)
                    else:
                        announcements.append(
                            f"🏆 **NOWY REKORD SERII!** {gracz_mention} pobił rekord w kategorii **{cat_info['title']}** osiągając aż **{formatted_val}** meczów z rzędu!"
                        )
                elif is_tied:
                    tie_texts_key = cat_info["tie_texts_key"]
                    pula = get_cfg(guild_id, tie_texts_key.lower(), getattr(config, tie_texts_key))
                    if pula:
                        msg_template = random.choice(pula)
                        msg_text = msg_template.format(
                            gracz=gracz_mention,
                            wynik=formatted_val,
                            mapa=mapa,
                            wynik_meczu=wynik_meczu
                        )
                        announcements.append(msg_text)
                    else:
                        announcements.append(
                            f"🤝 **WYRÓWNANIE REKORDU SERII!** {gracz_mention} wyrównał rekord w kategorii **{cat_info['title']}** z wynikiem **{formatted_val}** meczów z rzędu!"
                        )

        if any_change:
            # 1. Zaktualizuj tablicę na kanale rekordów
            await self.update_records_board(guild_id)
            
            # 2. Wyślij powiadomienia na kanale eventów meczowych
            ust = wczytaj_ustawienia(guild_id)
            chan_id = ust.get("kanal_eventow")
            if chan_id:
                channel = self.bot.get_channel(int(chan_id))
                if channel:
                    for ann in announcements:
                        try:
                            await channel.send(content=ann)
                        except Exception as e:
                            print(f"Nie udało się wysłać powiadomienia o rekordzie: {e}")

async def setup(bot):
    await bot.add_cog(RecordsCog(bot))
