# Wdrożenie i Utrzymanie

Instrukcja instalacji, konfiguracji środowiska i produkcyjnego uruchomienia bota na serwerze Linux lub macOS.

---

## 1. Wymagania

### Środowisko uruchomieniowe
* **System operacyjny**: Linux (Ubuntu 20.04+, Debian 11+) lub macOS
* **Python**: 3.10 lub nowszy
* **Pamięć RAM**: minimum 512 MB (zalecane 1 GB do generowania wykresów)

### Uprawnienia i klucze API
1. **Discord Developer Portal**:
   * Token aplikacji bota.
   * W sekcji **Bot -> Privileged Gateway Intents** należy włączyć:
     * **Message Content Intent** (obsługa tradycyjnego prefiksu tekstu)
     * **Server Members Intent** (obsługa ról i sprawdzanie użytkowników serwera)
2. **Faceit Developer Portal**:
   * Klucz **Server API Key** (Data API).

---

## 2. Instalacja

### Krok 1: Klonowanie repozytorium
```bash
git clone https://github.com/EmPeeEm/cs2_bot.git
cd cs2_bot
```

### Krok 2: Przygotowanie środowiska wirtualnego
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Zawartość `requirements.txt`:
* `discord.py` — biblioteka Discord Gateway i API
* `python-dotenv` — obsługa zmiennych środowiskowych
* `aiohttp` — asynchroniczne zapytania HTTP
* `matplotlib` — generowanie wykresów ELO
* `curl_cffi` — impersonacja przeglądarki dla Live API (omijanie blokad TLS)

### Krok 3: Konfiguracja zmiennych środowiskowych (`.env`)
Utwórz plik `.env` w katalogu `cs2_bot/`:
```env
DISCORD_TOKEN=twoj_token_bota
FACEIT_API_KEY=twoj_klucz_api_faceit
```

### Krok 4: Inicjalizacja bazy danych
```bash
python3 -c "from utils.db_sqlite import init_db; init_db()"
```
Polecenie tworzy katalog `data/`, plik `cs2_stats.db` oraz aktywuje tryb WAL.

---

## 3. Uprawnienia bota na Discordzie

Wymagane uprawnienia bota na serwerze:
* `Manage Roles` (Zarządzanie rolami)
* `Manage Channels` (Zarządzanie kanałami — potrzebne do aktualizacji kanału ELO i tworzenia kanałów rekordów)
* `Send Messages`, `Embed Links`, `Attach Files`
* `Use Application Commands` (Dostęp do Slash Commands)

### Hierarchia ról serwerowych
Rola bota na serwerze Discord musi znajdować się **powyżej** ról `Faceit Level 1` – `Faceit Level 10`. W przeciwnym razie Discord zablokuje próbę nadania lub odebrania roli błędem `discord.Forbidden (error code: 50013)`.

---

## 4. Rejestracja komend Slash (`!sync`)

Po pierwszym uruchomieniu bota:
1. Upewnij się, że bot ma status online na serwerze.
2. Jako administrator serwera wpisz:
   ```text
   !sync
   ```
3. Komendy aplikacji zostaną zarejestrowane dla bieżącej gildii i pojawią się w interfejsie pod znakiem `/`.

---

## 5. Uruchomienie produkcyjne

### Opcja A: PM2 (Process Manager)

1. Instalacja PM2 (wymaga Node.js / npm):
   ```bash
   npm install -g pm2
   ```
2. Start procesu:
   ```bash
   pm2 start main.py --name "cs2-bot" --interpreter ./venv/bin/python3
   ```
3. Konfiguracja autostartu po restarcie serwera:
   ```bash
   pm2 save
   pm2 startup
   ```
4. Podgląd logów i zarządzanie:
   ```bash
   pm2 logs cs2-bot
   pm2 restart cs2-bot
   ```

---

### Opcja B: Usługa systemd (Linux)

1. Utwórz plik `/etc/systemd/system/cs2-bot.service`:
   ```ini
   [Unit]
   Description=CS2 Faceit Tracker Discord Bot
   After=network.target

   [Service]
   Type=simple
   User=twoj_uzytkownik
   WorkingDirectory=/sciezka/do/cs2_bot
   ExecStart=/sciezka/do/cs2_bot/venv/bin/python3 main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
2. Przeładuj konfigurację i uruchom usługę:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cs2-bot
   sudo systemctl start cs2-bot
   ```
3. Monitorowanie:
   ```bash
   journalctl -u cs2-bot -f
   ```

---

## 6. Diagnostyka

### Logi aplikacji
Wszystkie zdarzenia i wyjątki są rejestrowane w pliku:
```bash
tail -f data/bot.log
```
Maksymalny rozmiar pliku to 5 MB. Starsze wpisy rotują do `bot.log.1`, `bot.log.2` i `bot.log.3`.

### Typowe problemy
* **`discord.Forbidden (Missing Permissions)` przy rolach**: Rola bota znajduje się w hierarchii niżej niż role poziomów Faceit. Podnieś rolę bota w ustawieniach serwera.
* **`HTTPException: 429` przy zmianie nazwy kanału**: Discord dopuszcza maksymalnie 2 edycje nazwy danego kanału na 10 minut. Zmiana zostanie wykonana po zwolnieniu blokady.
* **Brak komend `/` na serwerze**: Wykonaj komendę `!sync` na serwerze lub sprawdź uprawnienie `Use Application Commands`.
