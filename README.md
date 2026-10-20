# CS2 Faceit Tracker Bot

Bot Discord do monitorowania statystyk graczy Counter-Strike 2 z platformy Faceit. Śledzi mecze, aktualizuje rankingi serwerowe, nadaje role Discord za poziomy Faceit (1–10) i wysyła podsumowania spotkań.

Komendy działają w trybie hybrydowym: przez ukośnik (`/command`) oraz tradycyjny prefiks (domyślnie `!command`).

---

## Dokumentacja

Szczegółowa dokumentacja techniczna znajduje się w katalogu `docs/`:

* [Architektura Systemu](docs/ARCHITECTURE.md) — budowa modułowa (Cogs), obsługa zdarzeń, Faceit API i asynchroniczność.
* [Schemat Bazy Danych](docs/DATABASE.md) — tabele SQLite WAL, relacje, indeksy i model konfiguracji `get_cfg`.
* [Podręcznik Komend](docs/COMMANDS.md) — lista komend gracza i administratora, składnia, aliasy i uprawnienia.
* [Wdrożenie i Utrzymanie](docs/DEPLOYMENT.md) — instalacja, zmienne `.env`, systemd/PM2, uprawnienia ról i diagnostyka.

---

## Funkcje

* **Śledzenie meczów**: Pętla w tle sprawdza zakończone spotkania zarejestrowanych graczy i wysyła karty z ratingiem HLTV 2.0, K/D, ADR, zmianą ELO oraz statystykami granatów.
* **Komendy hybrydowe**: Obsługa Slash Commands (`/`) oraz tradycyjnych prefiksów tekstowych (`!`).
* **Role Faceit (Level 1–10)**: Automatyczne tworzenie ról z kolorystyką Faceit i ich aktualizacja po awansie lub spadku poziomu gracza.
* **Licznik ELO na żywo**: Aktualizacja nazwy wyznaczonego kanału głosowego ze średnim ELO ekipy, ograniczana buforem czasowym pod kątem limitów Discord API.
* **Sezony rankingowe**: Prowadzenie lokalnych sezonów ligowych, tabele wyników na dedykowanych kanałach i wyłanianie MVP.
* **Hala sław**: Rejestrowanie serwerowych rekordów meczowych (najwięcej killi, najwyższy ADR, multikille).
* **Wykresy formy**: Generowanie wykresów trajektorii ELO przez Matplotlib z izolacją w osobnym wątku.
* **Niezależna konfiguracja per serwer**: Osobne prefiksy, kanały i role dla każdej gildii w bazie SQLite.

---

## Szybki start

### Wymagania
* Python 3.10+
* Token bota Discord z uprawnieniami **Message Content Intent** oraz **Server Members Intent**
* Klucz API Faceit (Data API)

### 1. Pobranie repozytorium i instalacja zależności
```bash
git clone https://github.com/EmPeeEm/cs2_bot.git
cd cs2_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Zmienne środowiskowe (`.env`)
Utwórz plik `.env` w katalogu głównym projektu:
```env
DISCORD_TOKEN=twoj_token_bota
FACEIT_API_KEY=twoj_klucz_faceit
```

### 3. Inicjalizacja bazy i start
```bash
# Inicjalizacja schematu bazy danych
python3 -c "from utils.db_sqlite import init_db; init_db()"

# Uruchomienie bota
python3 main.py
```

### 4. Rejestracja komend Slash
Po dodaniu bota na serwer wykonaj jako administrator:
```text
!sync
```
Polecenie zarejestruje komendy aplikacji dla danego serwera.

---

## Przegląd komend

Szczegółowe opisy parametrów znajdują się w [Podręczniku Komend](docs/COMMANDS.md).

### Komendy gracza
| Komenda | Aliasy | Opis |
| :--- | :--- | :--- |
| `!polacz <nick>` | `link`, `ln` | Łączy konto Discord z profilem Faceit i dodaje gracza do bazy. |
| `!odlacz` | `unlink`, `un` | Usuwa powiązanie profilu Faceit z kontem Discord. |
| `!stats [nick/@gracz]` | `statystyki`, `s`, `fs` | Statystyki gracza: ELO, poziom, K/D, ADR, HS%, Win Rate. |
| `!elo [nick/@gracz]` | `e`, `fe` | Poziom Faceit, ELO i pasek postępu do zmiany rangi. |
| `!last [nick/@gracz]` | `mecz`, `l`, `fl` | Karta ostatniego meczu: HLTV 2.0, ADR, K/D/A, utility, zmiana ELO. |
| `!recent [ilość] [nick]`| `ostatnie`, `r`, `fr` | Średnie statystyki z ostatnich spotkań (domyślnie 20). |
| `!wykres [ilość] [nick]`| `chart`, `graph` | Wykres liniowy historii punktów ELO. |
| `!history [nick/@gracz]`| `hist`, `historia` | Lista 5 ostatnich meczów z linkami do podsumowań. |
| `!maps [nick/@gracz]` | `mapy`, `m` | Skuteczność na poszczególnych mapach 5v5 (mecze, WR%, K/D). |
| `!compare <g1> <g2> [n]` | `porownaj`, `c`, `1v1` | Porównanie statystyk dwóch graczy (1v1). |
| `!top` | `leaderboard`, `ranking`| Ranking zarejestrowanych graczy serwera według ELO. |
| `!streaks` | `passa`, `st` | Aktualne serie wygranych i przegranych. |
| `!pomoc [komenda]` | `komendy`, `help` | Menu pomocy z nawigacją przyciskami. |

---

### Komendy administratora
| Komenda | Aliasy | Opis |
| :--- | :--- | :--- |
| `!sync` | — | Synchronizacja komend Slash z serwerem (`!sync global` globalnie). |
| `!config [klucz] [wartość]`| `ustawienia`, `cfg` | Zmiana parametrów serwera (prefiks, kanały powiadomień, kolory). |
| `!faceit_roles setup` | `roles_setup` | Tworzy 10 ról `Faceit Level 1-10` z kolorami Faceit. |
| `!faceit_roles sync` | `roles_sync` | Synchronizuje role graczy na serwerze z ich rangami Faceit. |
| `!elo_setup` | — | Tworzy kanał głosowy pokazujący średnie ELO ekipy. |
| `!tilt_config` | — | Konfiguracja progu ostrzeżeń Tilt-Meter przy seriach porażek. |
| `!sezon` | — | Panel zarządzania sezonem ligowym (start/koniec, MVP). |
| `!sezony` | `seasons` | Archiwum zakończonych sezonów ze zwycięzcami. |
| `!sezon_reload` | `sr` | Odświeżenie embeda z tabelą aktywnego sezonu. |
| `!sezon_repost` | `srepost` | Ponowne wysłanie tabeli sezonu na spód kanału. |
| `!sezon_set_mvp <ID> <@u>` | `set_season_mvp` | Ręczne przypisanie MVP dla zakończonego sezonu. |
| `!live_setup [#kanał]` | `ls` | Konfiguracja kanału monitorowania meczów na żywo. |
| `!live_reload` / `!live_repost`| `lr` | Odświeżenie lub przeniesienie dashboardu meczów live. |
| `!rekordy_setup` | `records_setup` | Tworzy kanał `🏆・hala-sław` z tablicami rekordów. |
| `!rekordy_reload` | `rr` | Przelicza i odświeża tablice rekordów z bazy meczów. |

---

## Struktura katalogów

```text
cs2_bot/
├── cogs/                      # Moduły bota (rozszerzenia commands.Cog)
│   ├── cs.py                  # Statystyki gracza, wykresy, porównania
│   ├── live_matches.py        # Dashboard i mecze na żywo
│   ├── records.py             # Hala sław i rekordy serwerowe
│   ├── roles.py               # Role Faceit Level 1-10
│   ├── season_ui.py           # Sezony rankingowe i wyłanianie MVP
│   ├── tilt_ui.py             # Konfiguracja progów Tilt-Meter
│   └── tracker.py             # Pętla śledzenia zakończonych meczów
├── utils/                     # Moduły pomocnicze
│   ├── charts.py              # Generowanie wykresów w Matplotlib
│   ├── database.py            # Dostęp do bazy danych i konfiguracji (get_cfg)
│   ├── db_sqlite.py           # Inicjalizacja SQLite WAL i migracje
│   ├── faceit_api.py          # Klient Faceit Data API i Live API
│   └── helpers.py             # Ochrona przed limitami API (safe_rename_channel)
├── docs/                      # Dokumentacja techniczna
│   ├── ARCHITECTURE.md        # Architektura i przepływ zdarzeń
│   ├── DATABASE.md            # Schemat bazy danych SQLite
│   ├── COMMANDS.md            # Specyfikacja komend i uprawnień
│   ├── DEPLOYMENT.md          # Instalacja, PM2/systemd i diagnostyka
│   └── archive/               # Archiwum notatek audytowych
├── data/                      # Baza SQLite (cs2_stats.db) i pliki logów (bot.log)
├── tests/                     # Testy jednostkowe
├── config.py                  # Domyślne wartości konfiguracji
├── main.py                    # Punkt wejściowy bota
└── requirements.txt           # Zależności biblioteczne
```

---

## Testy

Uruchomienie testów jednostkowych:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
