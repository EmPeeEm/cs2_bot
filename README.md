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
    git clone [url-twojego-repozytorium]
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

## ⌨️ Komendy

*   `!config` – Zaawansowane zarządzanie ustawieniami serwera.
*   `!elo` – Szybki podgląd statystyk graczy z ekipy.
*   `!top` – Wyświetla tabelę liderów obecnego sezonu.
*   `!elo_setup` – Tworzy kanał głosowy ze średnim ELO ekipy.
*   `!sezon [start/koniec]` – Zarządzanie sezonami rankingowymi.
*   `!help` – Pełna lista dostępnych komend.

*Bot reaguje również na wzmiankę (ping) jako prefix.*

## 📂 Struktura Projektu

*   `cogs/` – Moduły bota (CS, Tracker, UI Sezonowe).
*   `utils/` – Narzędzia pomocnicze (Faceit API, Baza SQLite).
*   `data/` – Katalog na bazę danych `cs2_stats.db`.
*   `config.py` – Globalne ustawienia tekstowe i wizualne.
