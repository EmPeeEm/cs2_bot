# 🛡️ Raport z Pełnego Audytu Techniczno-Architektonicznego
**Projekt:** CS2 Faceit Tracker Discord Bot (`cs2_bot`)  
**Data audytu:** 11 października 2026  
**Status:** Zatwierdzony do implementacji  

---

## 1. Podsumowanie Zrozumienia (Understanding Summary)

* **Cel audytu:** Identyfikacja wąskich gardeł wydajnościowych, podatności na rate limity oraz modernizacja architektury bota do aktualnych standardów Discord API (Discord.py 2.x).
* **Kontekst i Odbiorcy:** Prywatna społeczność graczy CS2 (1–3 zaprzyjaźnione serwery, do ~50 aktywnych użytkowników).
* **Kluczowe Ograniczenia:**
  * Zachowanie prostoty wdrożenia – brak zewnętrznych demonów bazy danych (pozostanie przy SQLite).
  * 100% kompatybilności wstecznej dla użytkowników przyzwyczajonych do prefiksu `!`.
* **Wyraźne Cele Poza Zakresem (Non-goals):**
  * Migracja na PostgreSQL / Redis / Docker.
  * Sharding Gateway (wymagany dopiero przy >2500 serwerów).
  * Wdrażanie modułu odtwarzacza muzyki w ramach tego zadania.

---

## 2. Założenia i Ryzyka (Assumptions & Risks)

### Założenia:
1. Bot nadal uruchamiany jest lokalnie lub na VPS w środowisku Python 3.10+ (np. pod kontrolą PM2 / systemd).
2. Uprawnienie `intents.message_content` pozostaje aktywne, aby wspierać tradycyjny prefix `!` równolegle ze Slash Commands.
3. Wszystkie czasochłonne operacje (Faceit API, renderowanie Matplotlib, dyskowe I/O SQLite) muszą być asynchroniczne lub delegowane do puli wątków.

### Zidentyfikowane Ryzyka i Mitygacje:
* **Ryzyko:** Timeout interakcji Discorda (`10062 Unknown interaction`) przy zapytaniach Slash.  
  *Mitygacja:* Zastosowanie natychmiastowego `await ctx.defer()` w każdej komendzie hybrydowej.
* **Ryzyko:** Blokada HTTP 429 przy aktualizacjach nazw kanałów statystyk ELO.  
  *Mitygacja:* Globalny bufor historii edycji per kanał (`_safe_rename_channel`), respektujący limit max 2 edycji na 10 minut.
* **Ryzyko:** Wycieki pamięci RAM z procesu bota przez niezamknięte figury Matplotlib.  
  *Mitygacja:* Blok `try ... finally: plt.close(fig)` przy każdym wygenerowanym wykresie.
* **Ryzyko:** Zamrożenie pętli `asyncio` przez blokujące operacje I/O w SQLite.  
  *Mitygacja:* Aktywacja SQLite WAL oraz delegowanie zapytań przez `asyncio.to_thread`.

---

## 3. Dziennik Decyzji (Decision Log)

| Id | Kwestia | Wybrana Opcja | Odrzucone Alternatywy | Uzasadnienie |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-01** | Zakres audytu | Kompleksowy audyt techniczno-architektoniczny | Quick Wins, Audyt wyłącznie bezpieczeństwa | Potrzeba rozwiązania problemów u podstaw (blokowanie I/O, rate limity, brak slash commands). |
| **DEC-02** | Model komend | Hybrid Commands (`@commands.hybrid_command`) | Slash-Only, Prefix-Only | Bezbolesne wdrożenie: gracze mogą pisać `!` lub używać autouzupełniania `/`. |
| **DEC-03** | Silnik bazy danych | SQLite + WAL + delegacja do wątków | PostgreSQL, MongoDB | Idealne dopasowanie do skali 1-3 serwerów bez narzutu operacyjnego (YAGNI). |
| **DEC-04** | Obsługa odpowiedzi Slash | Globalny wzorzec `await ctx.defer()` | Odpowiedź synchroniczna | Operacje Faceit API i wykresy trwają 2-4s; Discord wymaga ACK w <3s. |
| **DEC-05** | Zarządzanie logami | Standardowy moduł `logging` z rotacją plików | Surowe `print()` | Możliwość diagnozowania awarii na VPS bez zaśmiecania konsoli. |

---

## 4. Szczegółowe Wyniki Audytu i Architektura Docelowa

### Moduł 1: Komendy i Gateway Discorda
1. **Migracja dekoratorów:** Zastąpienie `@commands.command(...)` w `cogs/cs.py`, `cogs/tracker.py`, `cogs/season_ui.py`, `cogs/records.py` przez `@commands.hybrid_command(...)`.
2. **Synchronizacja drzewa komend:** W `main.py` w metodzie `setup_hook()` dodanie `await self.tree.sync()`.
3. **Uprawnienia administracyjne:** Dodanie `@discord.app_commands.default_permissions(administrator=True)` do komend konfiguracji serwera, dzięki czemu Discord natywnie ukrywa je przed zwykłymi użytkownikami.

### Moduł 2: Baza Danych i Asynchroniczność
1. **Tryb WAL w SQLite:**
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   ```
   Wdrożenie w `init_db()` i `get_connection()` w `utils/db_sqlite.py`.
2. **Odblokowanie pętli zdarzeń:** Zapewnienie, że funkcje dostępowe z `utils/database.py` (np. `wczytaj_ekipe`, `wczytaj_ustawienia`, `pobierz_historie_elo`) wywoływane w kontekście komend nie blokują głównego wątku pętli zdarzeń.

### Moduł 3: Generowanie Wykresów (Matplotlib)
1. **Izolacja wątkowa:** Wywołanie funkcji generującej wykres w `cogs/cs.py`:
   ```python
   buf = await asyncio.to_thread(generuj_wykres_elo, nick, mecze)
   ```
2. **Czyszczenie pamięci:** W `utils/charts.py` jawne zwalnianie zasobów:
   ```python
   fig, ax = plt.subplots(figsize=(10, 5))
   try:
       # ... rysowanie ...
       buf = io.BytesIO()
       fig.savefig(buf, format="png", bbox_inches="tight")
       buf.seek(0)
       return buf
   finally:
       plt.close(fig)
   ```

### Moduł 4: Bezpieczeństwo i Rate Limity
1. **Unifikacja zmiany nazw kanałów:** Wyodrębnienie `safe_rename_channel` do wspólnego modułu pomocniczego i zabezpieczenie pętli `update_team_elo_channel` w `cogs/tracker.py` (Discord pozwala na max 2 edycje nazwy danego kanału na 10 minut).
2. **Faceit API Client:** Wprowadzenie dedykowanej obsługi statusu 429 i 5xx z `exponential backoff` oraz czytelnym komunikatem o błędzie dla użytkownika.

### Moduł 5: Centralne Logowanie
1. Zastąpienie surowych wywołań `print()` w całym projekcie zorganizowanym loggerem:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
       handlers=[
           logging.StreamHandler(),
           RotatingFileHandler("data/bot.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
       ]
   )
   ```

---

## 5. Plan Realizacji Krok po Kroku (Fazy Wdrożenia)

* **Faza 1: Baza Danych i Wydajność (Fundament)**
  - Konfiguracja trybu SQLite WAL w `db_sqlite.py`.
  - Refaktoryzacja renderowania wykresów w `charts.py` z gwarancją `plt.close()`.
  - Wydzielenie współdzielonej funkcji `safe_rename_channel`.
* **Faza 2: Standaryzacja Komend (Hybrid Commands & Defer)**
  - Dodanie `self.tree.sync()` w `main.py`.
  - Konwersja komend w `cogs/cs.py` na `@commands.hybrid_command` wraz z `await ctx.defer()`.
  - Zabezpieczenie komend administracyjnych w Discord UI (`default_permissions`).
* **Faza 3: Stabilność, Odporność API i Logowanie**
  - Obsługa błędów Faceit API (backoff, komunikaty).
  - Konfiguracja centralnego loggera z rotacją plików.
  - Weryfikacja działania bota i testy integracyjne.
