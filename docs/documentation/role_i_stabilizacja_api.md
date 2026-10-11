# 🎖️ Specyfikacja Architektoniczna: Automatyczny System Ról Faceit i Stabilizacja Live API
**Projekt:** CS2 Faceit Tracker Discord Bot (`cs2_bot`)  
**Data projektu:** 11 października 2026  
**Status:** Zatwierdzony do implementacji  

---

## 1. Podsumowanie Zrozumienia (Understanding Summary)

* **Cel projektu:** Wdrożenie automatycznego przypisywania i aktualizacji ról na Discordzie dla poziomów Faceit 1–10 oraz eliminacja błędów Cloudflare 403 i zaśmiecania konsoli przez Live API.
* **Zakres:**
  * Nowy moduł `cogs/roles.py` zarządzający tworzeniem i synchronizacją ról na serwerze.
  * Zdarzeniowa aktualizacja roli członka serwera przy wykryciu awansu/spadku poziomu w trackerze meczów.
  * Natychmiastowe nadawanie roli przy rejestracji konta (`/polacz`).
  * Instalacja `curl_cffi` w wirtualnym środowisku bota i wyciszenie spamu logów z czystym fallbackiem na oficjalne Faceit Data API.
* **Cele poza zakresem (Non-goals):**
  * Brak pobierania i parsowania plików `.dem` (brak publicznego dostępu w Data API).
  * Brak ręcznego mapowania ID ról – pełna automatyzacja tworzenia ról Level 1–10.

---

## 2. Założenia i Ryzyka (Assumptions & Risks)

### Założenia:
1. Bot posiada uprawnienie `Manage Roles` (Zarządzanie rolami) na serwerze Discord.
2. Rola bota na serwerze Discord jest ustawiona wyżej w hierarchii ról niż role `Faceit Level 1` – `Faceit Level 10`.
3. Gracz może posiadać w danej chwili tylko jedną rolę poziomu Faceit (poprzednia jest zdejmowana przy zmianie).

### Ryzyka i Mitygacje:
* **Ryzyko:** `discord.Forbidden` gdy rola bota jest poniżej ról Faceit w hierarchii ról Discorda.  
  *Mitygacja:* Wychwytywanie wyjątku, logowanie jasnego ostrzeżenia i wysłanie czytelnego komunikatu w podsumowaniu komendy `/faceit_roles setup`.
* **Ryzyko:** Przekroczenie limitów Discord API (Rate Limit na edycję członków).  
  *Mitygacja:* Aktualizacja ról wyłącznie w momencie rzeczywistej zmiany poziomu (`obecny_level != stary_level`), a w komendzie `/faceit_roles sync` wprowadzenie opóźnienia 0.5s między użytkownikami.

---

## 3. Dziennik Decyzji (Decision Log)

| Id | Kwestia | Wybrana Opcja | Odrzucone Alternatywy | Uzasadnienie |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-06** | Architektura systemu ról | Dedykowany Cog `cogs/roles.py` | Kod w `tracker.py` | Zachowanie Single Responsibility Principle; modułowość. |
| **DEC-07** | Tworzenie ról | Pełny automat `/faceit_roles setup` | Ręczne konfigurowanie ID ról | Zero konfiguracji dla admina: 1 komenda tworzy 10 ról z paletą Faceit. |
| **DEC-08** | Moment aktualizacji roli | Zdarzeniowo (tylko przy zmianie poziomu i przy `/polacz`) | Ciągłe odpytywanie w pętli | Ochrona przed rate limitami Discord API. |
| **DEC-09** | Obsługa Live API 403 | Instalacja `curl_cffi` + `logger.debug` | Wyłączenie monitoringu live | Przywrócenie działania impersonacji przeglądarki i czysty fallback na Data API. |

---

## 4. Architektura Docelowa

### Moduł 1: `cogs/roles.py` (Nowy Cog)
1. **Paleta Kolorów Faceit:**
   ```python
   FACEIT_LEVEL_COLORS = {
       1: discord.Color.from_rgb(238, 238, 238), # Level 1 (Biały / Jasny szary #EEEEEE)
       2: discord.Color.from_rgb(70, 230, 38),   # Level 2 (Zielony Faceit #46E626)
       3: discord.Color.from_rgb(70, 230, 38),   # Level 3 (Zielony Faceit #46E626)
       4: discord.Color.from_rgb(255, 199, 0),   # Level 4 (Żółty Faceit #FFC700)
       5: discord.Color.from_rgb(255, 199, 0),   # Level 5 (Żółty Faceit #FFC700)
       6: discord.Color.from_rgb(255, 199, 0),   # Level 6 (Żółty Faceit #FFC700)
       7: discord.Color.from_rgb(255, 199, 0),   # Level 7 (Żółty Faceit #FFC700)
       8: discord.Color.from_rgb(255, 99, 9),    # Level 8 (Pomarańczowy Faceit #FF6309)
       9: discord.Color.from_rgb(255, 99, 9),    # Level 9 (Pomarańczowy Faceit #FF6309)
       10: discord.Color.from_rgb(254, 31, 67)   # Level 10 (Czerwony Faceit #FE1F43)
   }
   ```
2. **Komendy Hybrydowe:**
   - `/faceit_roles setup` – tworzy/mapuje 10 ról `Faceit Level 1-10` z włączoną opcją wyświetlania oddzielnie (`hoist=True`) i zapisuje ich ID w bazie.
   - `/faceit_roles sync` – synchronizuje role wszystkim połączonym członkom serwera.
3. **Metoda publiczna:**
   - `async def update_member_faceit_role(self, guild: discord.Guild, member: discord.Member, new_level: int) -> bool`

### Moduł 2: Integracja z `cogs/tracker.py` i `cogs/cs.py`
1. W trackerze meczów w pętli `check_matches`:
   ```python
   if stary_level and obecny_level != stary_level and stary_level > 0:
       roles_cog = self.bot.get_cog("FaceitRolesCog")
       if roles_cog:
           member = guild.get_member(int(d_id)) or await guild.fetch_member(int(d_id))
           if member:
               await roles_cog.update_member_faceit_role(guild, member, obecny_level)
   ```
2. W komendzie `/polacz` w `cogs/cs.py`:
   - Po powiązaniu konta natychmiastowe nadanie roli odpowiedniej do aktualnego poziomu gracza.

### Moduł 3: Stabilizacja Live API w `utils/faceit_api.py`
1. Instalacja `curl_cffi` w środowisku venv bota.
2. Zastąpienie `print(f"⚠️ [LIVE API] groupByState status 403...")` cichym logowaniem na poziomie `logger.debug`.
3. Płynne przechodzenie do oficjalnego Faceit Data API bez zalewania konsoli bota.
