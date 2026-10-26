# Plan Integracji Modułu Muzycznego Vocard do CS2 Bota

Dokument ten opisuje szczegółowy plan architektoniczny i wdrożeniowy rozbudowy istniejącego bota **`cs2_bot`** o pełną funkcjonalność bota muzycznego z projektu **Vocard** (Lavalink v4, sterowanie przyciskami, kolejki, filtry dźwiękowe, wsparcie YouTube/Spotify).

W efekcie powstaje **jeden spójny bot Discord** działający na jednym tokenie, obsługujący zarówno statystyki CS2/Faceit, jak i muzykę w kanałach głosowych.

---

## 1. Architektura Połączonego Bota

```mermaid
graph TD
    subgraph Discord Gateway
        User([Użytkownik Discord])
    end

    subgraph CS2 Bot (Jeden Proces Python)
        Main[main.py - CSBot]
        
        subgraph Cogs CS2
            CS[cogs/cs.py]
            Faceit[cogs/tracker.py]
            Matches[cogs/live_matches.py]
            Season[cogs/season_ui.py]
        end
        
        subgraph Cogs Muzyczne (z Vocard)
            Music[cogs/music.py - /play, /skip, /queue]
            Effects[cogs/music_effects.py - bassboost, 8D]
            MusicEvents[cogs/music_events.py - NodePool, VoiceState]
        end
        
        subgraph Moduły pomocnicze
            Voicelink[utils/voicelink/ - Sterownik Lavalink v4]
            SQLite[(data/cs2_stats.db - CS2 SQLite)]
        end
    end

    subgraph Usługi Pomocnicze w Tle
        Lavalink[Lavalink v4 - Java 21 / Docker :2333]
        Mongo[(MongoDB - Ustawienia i Playlisty :27017)]
    end

    User <-->|Slash Commands & Buttons| Main
    Main --> CS2_COGS[Moduły CS2] --> SQLite
    Main --> MUSIC_COGS[Moduły Muzyczne] --> Voicelink
    Voicelink <-->|REST & WebSocket| Lavalink
    Voicelink <-->|motor async| Mongo
    Lavalink ==>|Strumień Opus UDP| Voice([Kanał Głosowy Discord])
```

---

## 2. Kluczowe Decyzje Architektoniczne

1. **Dlaczego jeden bot a nie dwa procesy?**
   - Jeden bot na serwerze oznacza jedną tożsamość bota na Discordzie, jeden token bota, brak konieczności zapraszania drugiego bota i wspólne zarządzanie procesem (jeden wpis w PM2 lub systemd).
2. **Zachowanie wydajności pętli zdarzeń (`asyncio`)**:
   - `cs2_bot` wykonuje okresowe zapytania o mecze Live i generuje wykresy `matplotlib` (generowane w wątkach).
   - Odtwarzanie muzyki **nie obciąża procesora Pythona**, ponieważ całe transkodowanie, pobieranie z YouTube/Spotify i streamowanie pakietów audio do Discorda wykonuje zewnętrzny proces **Lavalink v4**.
3. **Zarządzanie bazą danych**:
   - Statystyki CS2 i powiązania Faceit pozostają w SQLite (`data/cs2_stats.db`).
   - Playlisty użytkowników i zaawansowane ustawienia kontrolera Vocard obsługuje `motor` (lokalny kontener MongoDB lub darmowy klaster MongoDB Atlas).
4. **Discord Gateway Intents**:
   - `cs2_bot` posiada już `intents.message_content = True`, `intents.members = True` oraz domyślnie `intents.voice_states = True`.
   - Bot ma już wszystkie uprawnienia bramy wymagane do dołączania do kanałów głosowych i obsługi komend.

---

## 3. Plan Modyfikacji Krok po Kroku

### Krok 1: Rozszerzenie zależności (`requirements.txt`)
W `cs2_bot/requirements.txt` dopisujemy pakiety wymagane przez moduł muzyczny Vocard:
```text
# Istniejące:
discord.py
python-dotenv
aiohttp
matplotlib
curl_cffi

# Nowe (wymagane przez Voicelink/Vocard):
motor>=3.6.0
dnspython>=2.2.1
validators>=0.18.2
humanize>=4.0.0
beautifulsoup4>=4.11.1
psutil>=5.9.8
```

### Krok 2: Przeniesienie i integracja biblioteki `voicelink`
Przenosimy katalog `voicelink` z repozytorium Vocard do `cs2_bot/utils/voicelink`:
- `cs2_bot/utils/voicelink/pool.py` (Zarządzanie połączeniem z Lavalink v4)
- `cs2_bot/utils/voicelink/player.py` (Stan odtwarzacza na danym serwerze)
- `cs2_bot/utils/voicelink/queue.py` (Kolejka utworów, tryby powtarzania, autoplay)
- `cs2_bot/utils/voicelink/filters.py` (Korektor dźwięku, filtry audio)
- `cs2_bot/utils/voicelink/views/` (Interaktywne przyciski i menu wyboru)

### Krok 3: Dodanie nowych Cogów w `cs2_bot/cogs/`
W katalogu `cogs/` dodajemy:
1. **`music.py`**:
   - `/play <query>` – odtwarzanie z YouTube, Spotify, SoundCloud itp.
   - `/skip`, `/pause`, `/resume`, `/stop` – sterowanie playbackiem.
   - `/queue`, `/nowplaying` – podgląd kolejki i aktualnego utworu.
   - `/volume <1-100>`, `/shuffle`, `/seek <czas>`.
   - `/setup` – utworzenie dedykowanego kanału z interaktywnym kontrolerem (pin embed z przyciskami).
2. **`music_effects.py`**:
   - `/filter bassboost <low/med/high>`
   - `/filter nightcore`, `/filter 8d`, `/filter clear`
3. **`music_events.py`**:
   - Nasłuchiwanie `on_voice_state_update`: automatyczne opuszczanie kanału, gdy bot zostanie sam.
   - Inicjalizacja połączenia węzła `voicelink.NodePool.create_node()` w `cog_load()`.

### Krok 4: Rejestracja w `main.py`
W `cs2_bot/main.py`:
- Zapewniamy rejestrację trwałych widoków kontrolera muzycznego w `setup_hook`:
  ```python
  from utils.voicelink.views import ControllerView
  # self.add_view(ControllerView())
  ```
- Dzięki automatycznemu ładowaniu z `for filename in os.listdir('./cogs')`, nowe moduły załadują się same.
- Komenda `!sync` pozwoli natychmiast zarejestrować nowe komendy slash na serwerze Discord.

### Krok 5: Rozszerzenie `.env` i `config.py`
W `cs2_bot/.env`:
```env
# CS2 & Discord
DISCORD_TOKEN=twoj_token_bota
FACEIT_API_KEY=twoj_klucz_faceit

# Lavalink v4
LAVALINK_HOST=127.0.0.1
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass_secure_token

# MongoDB
MONGODB_URL=mongodb://127.0.0.1:27017
MONGODB_NAME=cs2_music_bot

# Spotify (LavaSrc)
SPOTIFY_CLIENT_ID=twoj_spotify_client_id
SPOTIFY_CLIENT_SECRET=twoj_spotify_client_secret
```

### Krok 6: Konfiguracja i uruchomienie Lavalink v4
W strukturze `cs2_bot/` dodajemy podkatalog `lavalink/`:
- `cs2_bot/lavalink/application.yml` (z wtyczkami `youtube-plugin` i `lavasrc-plugin`).
- Uruchomienie jako lekki kontener Dockera na maszynie produkcyjnej:
  ```bash
  docker run -d \
    --name cs2bot-lavalink \
    --restart unless-stopped \
    -p 127.0.0.1:2333:2333 \
    -v $(pwd)/lavalink/application.yml:/opt/Lavalink/application.yml:ro \
    -v $(pwd)/lavalink/plugins:/opt/Lavalink/plugins \
    ghcr.io/lavalink-devs/lavalink:4
  ```
  Oraz baza Mongo (jeśli nie używasz darmowego MongoDB Atlas):
  ```bash
  docker run -d \
    --name cs2bot-mongo \
    --restart unless-stopped \
    -p 127.0.0.1:27017:27017 \
    -v $(pwd)/data/mongo:/data/db \
    mongo:7.0
  ```

---

## 4. Harmonogram Wdrożenia

| Etap | Zadanie | Status |
| :--- | :--- | :---: |
| **Etap 1** | Przygotowanie `lavalink/application.yml` i uruchomienie Lavalink v4 z `youtube-plugin:1.18.2` | ✅ Ukończone |
| **Etap 2** | Przeniesienie i dostosowanie `voicelink` do struktury `cs2_bot/` | ✅ Ukończone |
| **Etap 3** | Implementacja `cogs/music*.py` (rozwiązane kolizje: `music_history`, `music_help`, `msettings`) | ✅ Ukończone |
| **Etap 4** | Rozszerzenie `requirements.txt` i instalacja zależności | ✅ Ukończone |
| **Etap 5** | Testy integracyjne: pomyślne zapytania REST Lavalink, wyszukiwanie utworów, brak ostrzeżeń | ✅ Ukończone |
| **Etap 6** | Aktualizacja dokumentacji w `DEPLOYMENT.md` i instrukcji uruchomienia | ✅ Ukończone |

