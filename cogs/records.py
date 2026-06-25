# cogs/records.py
import discord
from discord.ext import commands
import sqlite3
import random
import datetime
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

class RecordsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_category_embed(self, guild_id, category):
        cat_info = CATEGORIES[category]
        val = get_extreme_value(guild_id, category)
        
        # Kolor na podstawie czy rekord jest pozytywny czy negatywny
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
            value_str = f"🏆 Wynik: **{formatted_val}** {cat_info['unit']}\n\n"
            
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
        # Fallback na wypadek gdyby stara pojedyncza wiadomość była wciąż używana
        embed = discord.Embed(
            title="🏆 REKORDY SERWERA: HALA SŁAW I WSTYDU",
            description="Tutaj zobaczysz rekordy wszech czasów graczy naszej ekipy.\n*Wszystkie statystyki pobierane automatycznie z bazy danych.*",
            color=get_cfg(guild_id, "main_color", 0xFF5500)
        )
        
        good_fields = []
        bad_fields = []
        
        for category, cat_info in CATEGORIES.items():
            val = get_extreme_value(guild_id, category)
            if val is None:
                value_str = "*Brak rekordów*"
            else:
                holders = get_record_holders(guild_id, category, val)
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
            
        embed.set_footer(text="Rekordy aktualizują się automatycznie po każdym meczu.")
        return embed

    async def update_records_board(self, guild_id):
        ustawienia = wczytaj_ustawienia(guild_id)
        chan_id = ustawienia.get("kanal_rekordow")
        msg_ids = ustawienia.get("rekordy_msg_ids")
        msg_id_old = ustawienia.get("rekordy_msg_id")
        
        if not chan_id:
            return
            
        channel = self.bot.get_channel(int(chan_id))
        if not channel:
            return
            
        if isinstance(msg_ids, dict):
            for category, msg_id in msg_ids.items():
                try:
                    embed = self.generate_category_embed(guild_id, category)
                    msg = await channel.fetch_message(int(msg_id))
                    await msg.edit(embed=embed)
                except Exception as e:
                    print(f"Błąd podczas edycji tablicy rekordów dla kategorii {category}: {e}")
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

    def extract_new_value(self, category, stats):
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
        
        for category, cat_info in CATEGORIES.items():
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
                # Sprawdzamy, czy ten gracz nie jest już współposiadaczem tego rekordu
                # (np. przy re-parsowaniu meczu)
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
