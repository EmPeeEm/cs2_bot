# CS2 Faceit Tracker Bot 🚀

Zaawansowany bot Discordowy do automatycznego śledzenia statystyk graczy Counter-Strike 2 z platformy Faceit. Bot oferuje systemy rankingowe, powiadomienia o meczach na żywo oraz unikalne funkcje społecznościowe (roasty, Tilt-Meter).

## 🌟 Kluczowe Funkcje

*   **Automatyczny Tracker**: Monitoruje mecze Twojej ekipy 24/7. Po każdym meczu wysyła szczegółowy embed z HLTV, K/D, ADR oraz statystykami utility.
*   **System Sezonowy**: Prowadzenie rankingów sezonowych z automatycznym odświeżaniem tabeli wyników na dedykowanym kanale.
*   **Licznik ELO na Żywo**: Dynamicznie aktualizuje nazwę kanału głosowego, pokazując średnie ELO całej ekipy.
*   **Tilt-Meter**: Śledzi serie zwycięstw i porażek. Przy długich "loss-streakach" bot wysyła zabawne roasty.
*   **Multi-Guild Support**: Możliwość działania na wielu serwerach Discorda jednocześnie z niezależną konfiguracją (różne prefixy, kanały, ekipy).
*   **Pełna Konfiguracja**: Zarządzanie ustawieniami bezpośrednio z poziomu Discorda za pomocą komendy `config`.

## 🛠 Instalacja Lokalna

### Wymagania
*   Python 3.10 lub nowszy
*   Klucz API Faceit (Data API)
*   Token Bota Discord (Discord Developer Portal)

### Kroki instalacji
1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/EmPeeEm/cs2_bot.git
    cd cs2_bot
    ```

2.  **Stwórz środowisko wirtualne i aktywuj je:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate  # Windows
    ```

3.  **Zainstaluj wymagane biblioteki:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj plik `.env`:**
    Stwórz plik `.env` w głównym katalogu i uzupełnij go:
    ```env
    DISCORD_TOKEN=twoj_token_bota
    FACEIT_API_KEY=twoj_klucz_faceit
    ```

5.  **Zainicjalizuj bazę danych:**
    ```bash
    python3 -c "from utils.db_sqlite import init_db; init_db()"
    ```

## 🚀 Uruchamianie

### Dewelopersko:
```bash
python3 main.py
```

### Produkcyjnie (używając PM2):
```bash
pm2 start main.py --name "cs2-bot" --interpreter ./venv/bin/python3
```

## ⌨️ Komendy Bota

Bot reaguje na ustawiony prefix serwerowy (domyślnie `!`) oraz na wzmiankę (ping `@Bot`).

### 👤 Komendy Gracza (Dostępne dla każdego)

| Komenda | Aliasy | Składnia / Użycie | Opis |
| :--- | :--- | :--- | :--- |
| `!polacz` | `link`, `ln` | `!polacz <nick_faceit>` | Łączy konto Discord z profilem Faceit i dołącza do ekipy serwera. |
| `!odlacz` | `unlink`, `un` | `!odlacz` | Usuwa powiązanie konta Faceit z kontem Discord. |
| `!stats` | `statystyki`, `s`, `fs` | `!stats [nick / @gracz]` | Paszport statystyk gracza: ELO, poziom, K/D, ADR, HS%, Win Rate, streak. |
| `!elo` | `e`, `fe` | `!elo [nick / @gracz]` | Szybki podgląd poziomu, ELO oraz paska postępu do awansu/spadku. |
| `!last` | `mecz`, `l`, `fl` | `!last [nick / @gracz]` | Szczegółowa karta ostatniego meczu: HLTV 2.0, ADR, kille, UD, +/- ELO. |
| `!recent` | `ostatnie`, `r`, `fr` | `!recent [ilość] [nick/@gracz]` | Średnie statystyki z ostatnich gier z bazy danych (domyślnie 20, max 100). |
| `!wykres` | `chart`, `graph` | `!wykres [ilość] [nick/@gracz]` | Wykres liniowy trajektorii punktów ELO na osi ostatnich meczów (2-100). |
| `!history` | `hist`, `historia` | `!history [nick / @gracz]` | Lista 5 ostatnich spotkań z wynikami, statystykami i linkami do Faceit. |
| `!maps` | `mapy`, `m` | `!maps [nick / @gracz]` | Skuteczność na poszczególnych mapach 5v5 (liczba meczów, WR%, K/D). |
| `!compare` | `porownaj`, `c`, `1v1`, `arena` | `!compare [ilość] <gracz1> <gracz2>` | Arena 1v1 — porównanie formy dwóch graczy ze wskazaniem lidera statystyk. |
| `!top` | `leaderboard`, `ranking` | `!top` | Tabela liderów zarejestrowanych członków ekipy serwera posortowana wg ELO. |
| `!streaks` | `passa`, `st` | `!streaks` | Zestawienie aktualnych serii zwycięstw / porażek (win/loss streak) ekipy. |
| `!pomoc` | `komendy`, `help` | `!pomoc [komenda / admin / user]` | Interaktywne menu pomocy z przyciskami i dokumentacją. |

---

### 🛠️ Komendy Administratora (Wymagają uprawnień Admina)

| Komenda | Aliasy | Składnia / Użycie | Opis |
| :--- | :--- | :--- | :--- |
| `!config` | `ustawienia`, `settings`, `cfg` | `!config [klucz] [wartość]` | Panel zarządzania bota per serwer (prefix, kanały powiadomień, kolory). |
| `!tilt_config` | — | `!tilt_config` | Interaktywne menu progu alertów i roastów Tilt-Meter. |
| `!elo_setup` | — | `!elo_setup` | Tworzy automatyczny kanał głosowy pokazujący średnie ELO ekipy na żywo. |
| `!sezon` | — | `!sezon` | Panel zarządzania sezonami (Start nowego sezonu, Zakończenie z nagrodą MVP). |
| `!sezony` | `sezon_lista`, `seasons` | `!sezony` | Lista zarejestrowanych sezonów z ich ID, statusem i zdobywcami MVP. |
| `!sezon_reload`| `sr` | `!sezon_reload` | Wymusza natychmiastowe odświeżenie embeda z tabelą sezonu. |
| `!sezon_repost`| `sezon_resend`, `srepost` | `!sezon_repost` | Przenosi tabelę sezonu na sam dół dedykowanego kanału. |
| `!sezon_set_mvp` | `sezon_ustaw_mvp`, `set_season_mvp` | `!sezon_set_mvp <ID> <@gracz> [progres]` | Ręczne przypisanie/korekta MVP dla archiwalnego sezonu (aktualizuje Halę Sław). |
| `!live_setup` | `ls`, `na_zywo_setup` | `!live_setup [#kanał]` | Konfiguruje kanał monitorowania meczów na żywo w czasie rzeczywistym. |
| `!live_reload` | `lr` | `!live_reload` | Wymusza natychmiastowe odświeżenie dashboardu meczów live. |
| `!live_repost` | — | `!live_repost` | Przenosi dashboard meczów live na sam dół kanału. |
| `!rekordy_setup` | `records_setup` | `!rekordy_setup` | Tworzy kanał `🏆・hala-sław` z dedykowanymi kartami rekordów serwera. |
| `!rekordy_reload`| `rr` | `!rekordy_reload` | Wymusza odświeżenie i przeliczenie wszystkich kart rekordów. |

## 📂 Struktura Projektu

*   `cogs/` – Moduły bota (CS, Tracker, UI Sezonowe).
*   `utils/` – Narzędzia pomocnicze (Faceit API, Baza SQLite).
*   `data/` – Katalog na bazę danych `cs2_stats.db`.
*   `config.py` – Globalne ustawienia tekstowe i wizualne.
