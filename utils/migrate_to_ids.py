import json
import os
import re
import urllib.request
import urllib.error

# Manual .env reading to avoid dependencies
def load_env_manual():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

def is_uuid(val):
    """Sprawdza czy ciąg znaków jest w formacie UUID (player_id)"""
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str(val).lower()))

def get_player_id(nickname, faceit_key):
    url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {faceit_key}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                dane = json.loads(response.read().decode())
                return dane.get("player_id")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"❌ Nie znaleziono gracza: {nickname} (404)")
        else:
            print(f"⚠️ Błąd HTTP {e.code} dla {nickname}")
    except Exception as e:
        print(f"⚠️ Błąd dla {nickname}: {e}")
    return None

def run_migration():
    load_env_manual()
    faceit_key = os.getenv('FACEIT_API_KEY')
    if not faceit_key:
        print("❌ Brak klucza FACEIT_API_KEY w pliku .env!")
        return

    plik_ekipy = "data/ekipa.json"
    if not os.path.exists(plik_ekipy):
        print(f"❌ Nie znaleziono pliku {plik_ekipy}")
        return

    with open(plik_ekipy, "r", encoding="utf-8") as f:
        try:
            dane = json.load(f)
        except Exception as e:
            print(f"❌ Błąd odczytu JSON: {e}")
            return
        ekipa = dane.get("gracze", {})

    nowa_ekipa = {}
    print(f"🚀 Rozpoczynam migrację {len(ekipa)} wpisów...")

    for discord_id, identifier in ekipa.items():
        if is_uuid(identifier):
            print(f"✅ [{discord_id}] To już jest ID ({identifier}). Pomijam.")
            nowa_ekipa[discord_id] = identifier
        else:
            print(f"🔍 [{discord_id}] Nick: {identifier} -> Pobieram ID...")
            pid = get_player_id(identifier, faceit_key)
            if pid:
                print(f"   ✨ Znaleziono: {pid}")
                nowa_ekipa[discord_id] = pid
            else:
                print(f"   ⚠️ Pozostawiam nick: {identifier} (wymaga ręcznej poprawy)")
                nowa_ekipa[discord_id] = identifier

    with open(plik_ekipy, "w", encoding="utf-8") as f:
        json.dump({"gracze": nowa_ekipa}, f, indent=4)
    
    print("\n✅ Migracja zakończona sukcesem!")
    print("Jeśli niektórzy gracze nadal mają nicki zamiast ID, muszą użyć komendy !polacz ponownie.")

if __name__ == "__main__":
    run_migration()
