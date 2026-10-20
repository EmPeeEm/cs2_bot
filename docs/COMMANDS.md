# Podręcznik Komend

Spis komend bota ze składnią, parametrami, aliasami oraz wymaganymi uprawnieniami.

---

## 1. Informacje ogólne

* **Obsługa wywołań**: Komendy działają hybrydowo:
  1. Przez ukośnik Discorda (Slash Commands, np. `/stats nickname:s1mple`).
  2. Przez prefiks tekstowy (domyślnie `!`, np. `!stats s1mple`).
  3. Przez oznaczenie bota (np. `@CSBot stats`).
* **Uprawnienia**: Komendy administracyjne wymagają uprawnienia **Administrator** na serwerze i są ukrywane przed zwykłymi użytkownikami w menu slash.

---

## 2. Komendy gracza

### `polacz`
Łączy konto Discord z profilem Faceit i dodaje gracza do listy śledzonych na serwerze.
* **Składnia**: `!polacz <nick_faceit>` lub `/polacz nickname:<nick_faceit>`
* **Aliasy**: `link`, `ln`
* **Działanie**: Pobiera dane z Faceit i przypisuje rolę poziomu (Level 1–10), jeśli system ról jest włączony na serwerze.

### `odlacz`
Usuwa powiązanie konta Discord z profilem Faceit i wyłącza gracza ze śledzenia na serwerze.
* **Składnia**: `!odlacz` lub `/odlacz`
* **Aliasy**: `unlink`, `un`

### `stats`
Wyświetla kartę statystyk gracza: ELO, poziom Faceit, K/D, ADR, procent trafień w głowę oraz wskaźnik wygranych.
* **Składnia**: `!stats [nick_lub_@gracz]` lub `/stats [nickname]`
* **Aliasy**: `statystyki`, `s`, `fs`
* **Uwaga**: Wywołanie bez parametru sprawdza profil powiązany z autorem wiadomości.

### `elo`
Pokazuje liczbę punktów ELO, poziom Faceit oraz pasek postępu ze wskazaniem punktów brakujących do awansu lub spadku.
* **Składnia**: `!elo [nick_lub_@gracz]` lub `/elo [nickname]`
* **Aliasy**: `e`, `fe`

### `last`
Szczegółowe podsumowanie ostatniego rozegranego meczu: wynik, mapa, K/D/A, rating HLTV 2.0, ADR, obrażenia od granatów oraz zmiana ELO.
* **Składnia**: `!last [nick_lub_@gracz]` lub `/last [nickname]`
* **Aliasy**: `mecz`, `l`, `fl`

### `recent`
Średnie wskaźniki (K/D, ADR, Win Rate, HLTV) obliczane z ostatnich spotkań zapisanych w bazie danych.
* **Składnia**: `!recent [ilość] [nick_lub_@gracz]` lub `/recent [amount] [nickname]`
* **Aliasy**: `ostatnie`, `r`, `fr`
* **Zakres**: Od 1 do 100 meczów (domyślnie 20).

### `wykres`
Generuje wykres liniowy przedstawiający zmiany punktów ELO w ostatnich meczach.
* **Składnia**: `!wykres [ilość] [nick_lub_@gracz]` lub `/wykres [amount] [nickname]`
* **Aliasy**: `chart`, `graph`
* **Zakres**: Od 2 do 100 meczów (domyślnie 20).

### `history`
Lista 5 ostatnich spotkań z wynikami, kluczowymi statystykami i linkami do meczów w serwisie Faceit.
* **Składnia**: `!history [nick_lub_@gracz]` lub `/history [nickname]`
* **Aliasy**: `hist`, `historia`

### `maps`
Zestawienie skuteczności na poszczególnych mapach w trybie 5v5 (liczba spotkań, procent wygranych, bilans K/D).
* **Składnia**: `!maps [nick_lub_@gracz]` lub `/maps [nickname]`
* **Aliasy**: `mapy`, `m`

### `compare`
Bezpośrednie porównanie statystyk dwóch graczy z ostatnich spotkań.
* **Składnia**: `!compare <gracz1> <gracz2> [ilość]` lub `/compare <gracz1> <gracz2> [amount]`
* **Aliasy**: `porownaj`, `c`, `1v1`, `arena`
* **Domyślnie**: 20 meczów.

### `top`
Ranking zarejestrowanych członków ekipy serwera posortowany według punktów ELO.
* **Składnia**: `!top` lub `/top`
* **Aliasy**: `leaderboard`, `ranking`

### `streaks`
Zestawienie aktualnych serii zwycięstw lub porażek dla zarejestrowanych graczy na serwerze.
* **Składnia**: `!streaks` lub `/streaks`
* **Aliasy**: `passa`, `st`

### `pomoc`
Menu pomocy z opisem komend i przyciskami nawigacyjnymi.
* **Składnia**: `!pomoc [nazwa_komendy]` lub `/pomoc [command]`
* **Aliasy**: `komendy`, `help`

---

## 3. Komendy administratora

### `sync`
Synchronizuje zarejestrowane komendy aplikacji z Discord API.
* **Składnia**:
  * `!sync` — rejestracja natychmiastowa dla bieżącego serwera.
  * `!sync global` — rejestracja globalna w Discordzie (czas oczekiwania do 1h).
  * `!sync clear` — usunięcie komend aplikacji z bieżącego serwera.

### `config`
Odczyt lub zmiana konfiguracji bota dla danego serwera.
* **Składnia**: `!config [klucz] [wartość]` lub `/config [key] [value]`
* **Aliasy**: `ustawienia`, `settings`, `cfg`
* **Przykłady**:
  * `!config` — wyświetla bieżącą konfigurację serwera.
  * `!config prefix ?` — ustawia prefiks tekstu na `?`.
  * `!config main_channel #mecze` — definiuje kanał dla raportów z meczów.
  * `!config main_color #FF5500` — definiuje kolor embedów.

### `faceit_roles`
Konfiguracja ról Faceit Level 1–10.
* **Składnia**:
  * `!faceit_roles setup` lub `/faceit_roles setup` — tworzy 10 ról `Faceit Level 1-10` z kolorami Faceit oraz flagą wyświetlania oddzielnie (`hoist=True`).
  * `!faceit_roles sync` lub `/faceit_roles sync` — sprawdza rangi połączonych graczy i aktualizuje im role.
* **Aliasy**: `!roles_setup`, `!roles_sync`.

### `elo_setup`
Tworzy kanał głosowy z automatycznie odświeżaną nazwą zawierającą średnie ELO ekipy serwera.
* **Składnia**: `!elo_setup` lub `/elo_setup`

### `tilt_config`
Otwiera menu konfiguracji progów alertów Tilt-Meter przy seriach przegranych.
* **Składnia**: `!tilt_config` lub `/tilt_config`

### `live_setup`, `live_reload`, `live_repost`
Obsługa kanału z dashboardem meczów na żywo.
* `!live_setup [#kanał]` / `/live_setup [channel]` — konfiguracja kanału.
* `!live_reload` / `/live_reload` — wymuszenie odświeżenia dashboardu.
* `!live_repost` / `/live_repost` — przeniesienie dashboardu na dół kanału.

### `rekordy_setup`, `rekordy_reload`
Obsługa kanału Hali Sław z serwerowymi rekordami meczowymi.
* `!rekordy_setup` / `/rekordy_setup` — konfiguracja kanału `🏆・hala-sław`.
* `!rekordy_reload` / `/rekordy_reload` — przeliczenie rekordów z bazy.

### `sezon`, `sezony`, `sezon_reload`, `sezon_repost`, `sezon_set_mvp`
Zarządzanie sezonami rankingowymi.
* `!sezon` / `/sezon` — panel zarządzania (rozpoczęcie i zakończenie sezonu).
* `!sezony` / `/sezony` — lista archiwalnych sezonów z podsumowaniem i wyłonionym MVP.
* `!sezon_reload` / `/sezon_reload` — odświeżenie embeda z tabelą aktywnego sezonu.
* `!sezon_repost` / `/sezon_repost` — ponowne wysłanie tabeli na dół kanału.
* `!sezon_set_mvp <ID> <@gracz> [progres]` — ręczna korekta MVP dla zakończonego sezonu.
