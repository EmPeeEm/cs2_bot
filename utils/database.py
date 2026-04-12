# utils/database.py

import json
import os

# Utworzenie folderu na dane
os.makedirs("data", exist_ok=True)

# Ścieżka do naszego pliku z danymi (stworzy się sam!)
PLIK_BORY = "data/ekipa.json"
PLIK_USTAWIEN = "data/ustawienia.json"
PLIK_MECZE = "data/mecze.json"
PLIK_SEZONU = "data/sezon.json"
PLIK_TILTU = "data/tilt.json"

def wczytaj_ekipe():
    """Zwraca słownik powiązań np. {"12345678": "s1mple"}. Zwraca puste {} jeśli jest to stary format."""
    if not os.path.exists(PLIK_BORY):
        return {}
    
    with open(PLIK_BORY, "r", encoding="utf-8") as f:
        try:
            dane = json.load(f)
            gracze = dane.get("gracze", {})
            if isinstance(gracze, list):
                # Stara lista - uznajemy za czystą by zaczeli od nowa.
                return {}
            return gracze
        except Exception:
            return {}

def zapisz_ekipe(slownik_graczy):
    """Zapisuje zaktualizowany słownik do pliku JSON."""
    with open(PLIK_BORY, "w", encoding="utf-8") as f:
        json.dump({"gracze": slownik_graczy}, f, indent=4)

def wczytaj_ustawienia():
    if not os.path.exists(PLIK_USTAWIEN):
        return {}
    with open(PLIK_USTAWIEN, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def zapisz_ustawienia(dane):
    with open(PLIK_USTAWIEN, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4)

def wczytaj_ostatnie_mecze():
    if not os.path.exists(PLIK_MECZE):
        return {}
    with open(PLIK_MECZE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def zapisz_ostatnie_mecze(dane):
    with open(PLIK_MECZE, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4)

def wczytaj_sezon():
    if not os.path.exists(PLIK_SEZONU):
        return {}
    with open(PLIK_SEZONU, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def zapisz_sezon(dane):
    with open(PLIK_SEZONU, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4)

def wczytaj_tilt():
    if not os.path.exists(PLIK_TILTU):
        return {}
    with open(PLIK_TILTU, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def zapisz_tilt(dane):
    with open(PLIK_TILTU, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4)