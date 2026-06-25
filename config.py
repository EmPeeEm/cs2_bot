# config.py
# Ten plik zawiera DOMYŚLNE wartości parametrów bota. 
# Aby zmienić te wartości na stałe, użyj komendy Discordowej: .config [klucz] [wartość]
# np. .config main_color #ff5500

PREFIX = "!"
MAIN_COLOR = 0xFF5500 
ERROR_CHANNEL_ID = 1492847111274762320

# Wizualne
LEVEL_EMOJIS = {
    "1": "<:level01:1492863871738970192>",
    "2": "<:level02:1492863914352840775>",
    "3": "<:level03:1492863952735174826>",
    "4": "<:level04:1492863987224940546>",
    "5": "<:level05:1492864020007485643>",
    "6": "<:level06:1492864045932613775>",
    "7": "<:level07:1492864083752386671>",
    "8": "<:level08:1492864116438601840>",
    "9": "<:level09:1492864154308968468>",
    "10": "<:level10:1492864194532348036>"
}
LEVEL_DEFAULT = "⚪"

# --- TEKSTY (ZIOMALSKI STYL / ROASTY) ---

AWANS_TEXTS = [
    "No w końcu, ile można było gnić w tym elo hell. Gratulacje, może teraz zaczniesz trafiać na ludzi z włączonym monitorem.",
    "Awansik wpadł? Gg, powoli przestajesz grać jak totalny NPC. Jesteś o mały krok od wyjścia z gówna.",
    "Oho, mamy tu tryharda. Nie przyzwyczajaj się do tej rangi, zaraz matchmaking zweryfikuje twój skill i wracasz do budy.",
    "Ktoś tu chyba wynajął ruska do boostowania konta. Gratulacje, oby tak dalej, póki ci bana za to nie wlepią.",
    "Nowa ranga? Śmieszne, grałeś jak warzywo, a i tak cię wyciągnęli. Podziękuj teamowi za darmowy wózek.",
    "Wyskoczyłeś z silvera jak filip z konopi. Zobaczymy, jak długo utrzymasz się na powierzchni zanim znowu zatoniesz z ujemnym K/D.",
    "Dobry awans! Szkoda tylko, że twój movement dalej przypomina pijanego dziadka na weselu.",
    "Patrzcie na tego koxa, nowa ranga w profilu. A aim dalej na poziomie drewno 3.",
    "No proszę, ranga w górę! Chociaż jeden raz nie stiltowałeś całego teamu swoją odklejką.",
    "W końcu awans. Teraz będziesz dostawał wpierdol od ludzi z nieco lepszym celownikiem, przygotuj maść na ból dupy."
]

SPADEK_TEXTS = [
    "XDDDD wracaj do piaskownicy. Ten poziom ewidentnie przerósł twoje dwie szare komórki.",
    "Stabilnie w dół. Jak tam powietrze w mule? Oddychasz w ogóle, czy już całkowicie poszedłeś na dno?",
    "Oho, wita nas król deranków. Twój plan 'road to silver' to jedyne, co ci w tej grze wychodzi.",
    "Patrzeć na twoją grę to jak patrzeć na wypadek drogowy. Odinstaluj csa, idź grać w bierki pod wodą.",
    "Derank to i tak łagodny wyrok. Za to co odwalałeś, powinni ci sformatować dysk i odciąć router.",
    "Grasz jakbyś miał ping 500 w mózgu. Witamy z powrotem w rynsztoku, tam gdzie twoje miejsce.",
    "Ładnie zjechałeś. Twoje plecy muszą być w opłakanym stanie, skoro nawet team na wózku cię nie uratował od upadku.",
    "Spadek? Nic dziwnego, z takim refleksem to ty byś w szachach ze statycznym botem przegrał.",
    "Powrót do starych śmieci. Może na tej randze znajdziesz w końcu kogoś, kto też napierdala w klawiaturę czołem.",
    "Ranga w dół, ego w dół. Może czas zaakceptować, że jesteś po prostu jebanym łakiem i przestać marnować prąd?"
]

WIN_STREAK_TEXTS = [
    "Odpalony jak piecyk w zimę. Co ty masz w tych plikach, że nagle tak siada? Jedziesz z kurwami!",
    "Win streak leci, zaraz na Overwatchu wylądujesz. Ale póki co, dojisz ich jak rasowy smurf.",
    "Bierz ich wszystkich! Tryb Boga włączony, wjeżdżasz w nich jak dzik w żołędzie.",
    "Ogień z dupy, co mecz to zielono! Przeciwnicy już płaczą na czacie, że masz wallhacka.",
    "Wygrywasz tyle, że zaraz ci algorytm wywali błąd. Kontynuuj to zniszczenie!",
    "Co mecz to gładki stomp. Wyglądasz, jakbyś wczoraj dostał klawiaturę mechaniczną i w końcu nauczył się klikać.",
    "Zielona ściana w historii meczów. Czuć pociąg, który nie bierze jeńców, rozjeżdżasz ich jak walec!",
    "Jesteś tak nagrzany, że pewnie myszka ci się topi w łapie. Kolejne ez winy wpadają na konto.",
    "Z taką passą to ty zaraz do Faceit Pro League wbijesz. Miażdżysz tych noobów bez grama litości.",
    "Nie zdejmuj nogi z gazu! Przeciwnicy wychodzą z serwera, jak tylko widzą twój nick w tabeli."
]

LOSE_STREAK_TEXTS = [
    "Czerwona ściana płaczu. Zmień myszkę, podkładkę, a najlepiej zajmij się hodowlą jedwabników, bo to już boli patrzeć.",
    "Serio, kupię to konto za paczkę czipsów. I tak grasz jak byś operował stopami na touchpadzie.",
    "Lose streak jak stąd do Sosnowca. Lecisz na ryj z taką prędkością, że zaraz przebijesz dno tabeli.",
    "Ty w ogóle patrzysz w ten monitor, czy rzucasz kostką i losujesz przyciski? Zlituj się i wyłącz to.",
    "Przegrywasz z taką regularnością, że to podchodzi pod masochizm. Lubisz być dymany na serwerze na każdym kroku?",
    "Z każdym meczem udowadniasz, że można zagrać jeszcze gorzej. To nie pech, to jest po prostu absolutny brak skilla.",
    "Czerwono jak w burdelu. Zrób sobie przerwę, bo twój mental leży i kwiczy w rogu.",
    "Kolejny wpierdol do kolekcji. Team cię nienawidzi, wrogowie z ciebie leją. Odinstaluj, zrób wszystkim przysługę.",
    "Z takimi wynikami to powinieneś płacić odszkodowanie ludziom, których losuje z tobą w drużynie.",
    "Stiltowany, zniszczony, bez formy. Jesteś pośmiewiskiem matchmakingu. Wyjdź na dwór, dotknij trawy."
]

HLTV_BEAST_TEXTS = [
    "Prawdziwy rzeźnik. Ktoś tu dzisiaj opierdolił wiadro przedtreningówki przed wejściem na serwer.",
    "To była rzeź niewiniątek, zmiażdżyłeś ich psychikę. Musieli odinstalować grę po tym, jak zrobiliście z nich miazgę.",
    "Gigachad na serwerze. Carry roku, plecy pewnie do wymiany po targaniu tych bezużytecznych paralityków z teamu.",
    "Staty wyjebane w kosmos, s1mple dzwoni po porady. Rozstawiłeś ich po kątach jak małe dzieci.",
    "Strzelałeś takie łby, że pewnie do teraz sprawdzają profil, szukając twoich banów na VACu. Czysta dominacja!",
    "Król killfeeda! Zrobiłeś sobie z nich strzelnicę. Typy bali się w ogóle wychylać ze spawna.",
    "Jesteś maszyną do robienia fragów, terminator to przy tobie złom. Wykręciłeś takie cyfry, że HLTV eksplodowało.",
    "Twój celownik to był dziś pierdolony magnes na głowy. Zlałeś ich tak, że nie będą mogli usiąść przez tydzień.",
    "Zjadłeś ich na śniadanie i nawet nie popiłeś. Co za potężny występ, absolutny szef na mapie.",
    "Każdy twój strzał to była poezja niszczenia. Rozpierdoliłeś ten mecz w pojedynkę."
]

HLTV_BOT_TEXTS = [
    "Grałeś nogami czy monitor miałeś wyłączony? Bo te staty krzyczą, że jesteś kompletnym warzywem.",
    "Gdybyśmy grali 4 na 5, z botem Gabenem, to mielibyśmy większe szanse. Przeszkadzałeś jak kamień w bucie.",
    "Twoje K/D to jebany żart. Na mapie byłeś tylko chodzącym darmowym fragiem i sponsorem ich ekonomii.",
    "Jesteś tak słaby, że bot na najniższym poziomie inteligencji wykręciłby lepsze staty. Kompromitacja w chuj.",
    "Ilość twoich killi można policzyć na palcach rąk drwala po wypadku. Jesteś beznadziejny.",
    "Robiłeś za tarczę strzelniczą, czy po prostu masz laga mózgu? Twój impact na grę wynosił równe zero.",
    "Strzelasz ślepakami, movement jak w wózku inwalidzkim bez kółek. Zagrałeś jak totalny ściek.",
    "Powinni wymyślić nową odznakę w CSie dla takich łaków. 'Główny dostarczyciel fragów dla wroga'.",
    "Ty chyba grałeś z padem od Pegasusa. Nie da się być tak tragicznym celowo, ty masz to wpisane w DNA.",
    "Największy dzban meczu. Otwierasz tabelę... od dołu. Mam nadzieję, że chociaż ci wstyd za ten pokaz nieudolności."
]

# --- MAPY ---
TOURNAMENT_MAPS = ["Mirage", "Inferno", "Dust2", "Nuke", "Ancient", "Anubis", "Overpass"]

# --- TEKSTY DLA REKORDÓW ---
RECORD_KILLS_TEXTS = [
    "Co za rzeźnik! {gracz} właśnie ustanowił NOWY REKORD SERWERA, zdobywając aż {wynik} killi na mapie {mapa}! Czy ktoś go w końcu zatrzyma?",
    "Ałć, to musiało boleć. {gracz} wjechał w nich jak walec i zdobył {wynik} killi na {mapa}, pobijając rekord serwera! Szykujcie dla niego tron.",
    "Patrzcie i płaczcie, {gracz} właśnie pobił rekord z {wynik} fragami na {mapa}. Chyba przedtreningówka weszła za mocno!"
]

RECORD_HLTV_TEXTS = [
    "Kosmiczny występ! {gracz} wykręcił rekordowe HLTV rating na poziomie {wynik} na mapie {mapa}! HLTV już pisze o nim artykuł.",
    "Tryb Boga aktywowany. Rekordowe rating HLTV {wynik} na {mapa} ląduje na koncie gracza {gracz}. Czysta poezja niszczenia!",
    "Czy to człowiek, czy to maszyna? {gracz} ustanawia nowy rekord z HLTV {wynik} na {mapa}. Przeciwnicy do teraz płaczą w kącie."
]

RECORD_UD_TEXTS = [
    "Grenadier roku! {gracz} zadał rekordowe {wynik} Utility Damage na mapie {mapa}. Granaty latały gęsto!",
    "Prawdziwy terrorysta z granatami. {gracz} ustanawia rekord serwera z {wynik} Utility Damage na {mapa}. Piekło na ziemi!",
    "Nikt tak nie rzuca heków jak on. {gracz} sieje spustoszenie z rekordem {wynik} Utility Damage na {mapa}!"
]

RECORD_LOW_KILLS_TEXTS = [
    "🚨 ALARM BOTOWANIA! 🚨 {gracz} zagrał mecz życia i pobił rekord najmniejszej liczby killi w pełnym meczu: zaledwie {wynik} na mapie {mapa} ({wynik_meczu})! Zabrać mu komputer, bo jeszcze kogoś nim skrzywdzi!",
    "Czy to pacyfista? {gracz} ustanawia rekord rynsztoka z {wynik} fragami na {mapa} ({wynik_meczu}). Przeciwnicy nawet nie musieli unikać jego strzałów, bo i tak strzelał w niebo.",
    "Co za spektakularny pokaz bezradności. {gracz} zamyka tabelę z rekordowo niskim wynikiem {wynik} killi na {mapa} ({wynik_meczu}). Nawet bot z Gabenem gra lepiej!"
]

RECORD_LOW_HLTV_TEXTS = [
    "🚨 REKORD BOTOWANIA POBITY! 🚨 {gracz} osiągnął historyczne dno z HLTV rating na poziomie {wynik} na mapie {mapa} ({wynik_meczu})! To nie jest gra nogami, to jest brak rąk.",
    "Jak można być tak bezużytecznym? {gracz} ustanawia absolutny rekord najniższego HLTV: {wynik} na {mapa} ({wynik_meczu}). Nawet stojąc w miejscu, miałby większy impact.",
    "Historyczny moment! {gracz} pobija rekord najniższego HLTV na tym serwerze: {wynik} na {mapa} ({wynik_meczu}). Gratulacje, zasłużyłeś na miano oficjalnego bota serwera."
]

RECORD_DEATHS_TEXTS = [
    "Główny sponsor wroga! {gracz} pobił rekord zgonów, umierając aż {wynik} razy na mapie {mapa}! Twoje plecy muszą być czerwone od tego ciągłego padania na glebę.",
    "Co mecz to darmowy frag dla przeciwników. {gracz} ustanawia rekord zgonów z wynikiem {wynik} na {mapa}. Może zainwestujesz w kamizelkę kuloodporną?",
    "Czy ty masz włączony auto-run na spawn wroga? {gracz} pobił rekord, umierając {wynik} razy na {mapa}. Wyglądało to jak celowy sabotaż!"
]

# --- TEKSTY DLA REMISÓW / WYRÓWNAŃ REKORDÓW ---
RECORD_KILLS_TIE_TEXTS = [
    "🤝 Mamy remis na szczycie! {gracz} wyrównuje rekord killi, zdobywając {wynik} na mapie {mapa}! {gracz} dołącza do elity.",
    "Oho, {gracz} poczuł krew i zdobył {wynik} killi na {mapa}, wyrównując rekord serwera! Robi się ciasno na podium."
]

RECORD_HLTV_TIE_TEXTS = [
    "🤝 Co za stabilizacja formy! {gracz} wyrównuje rekord najwyższego ratingu HLTV: {wynik} na {mapa}! Klasa sama w sobie.",
    "Kolejny tryhard na serwerze! {gracz} wykręcił {wynik} HLTV na {mapa}, wyrównując dotychczasowy rekord!"
]

RECORD_UD_TIE_TEXTS = [
    "🤝 Kolejny miotacz ognia! {gracz} wyrównuje rekord Utility Damage: {wynik} UD na mapie {mapa}!",
    "Granaty latają z tą samą precyzją. {gracz} wyrównał rekord {wynik} Utility Damage na {mapa}!"
]

RECORD_LOW_KILLS_TIE_TEXTS = [
    "🤝 Witamy w klubie pacyfistów! {gracz} wyrównuje anty-rekord najmniejszej liczby killi w pełnym meczu: zaledwie {wynik} na {mapa} ({wynik_meczu}). Grasz tak samo słabo jak poprzednik!",
    "Bratnia dusza dla bota! {gracz} wyrównał najgorszy wynik killi ({wynik}) na {mapa} ({wynik_meczu}). Idealnie uzupełniacie ten rynsztok."
]

RECORD_LOW_HLTV_TIE_TEXTS = [
    "🚨 REMIS W RYNSZTOKU! 🚨 {gracz} wyrównuje anty-rekord najniższego HLTV rating: {wynik} na mapie {mapa} ({wynik_meczu}). Poziom żenady osiągnął stan równowagi.",
    "Boty się mnożą! {gracz} wyrównał rekord najniższego HLTV ({wynik}) na {mapa} ({wynik_meczu}). Obaj powinniście grać w bierki pod wodą."
]

RECORD_DEATHS_TIE_TEXTS = [
    "🤝 Solidarność w ginięciu! {gracz} wyrównuje rekord zgonów, padając aż {wynik} razy na mapie {mapa}. Wasz darmowy catering dla wroga działa bez zarzutu!",
    "Kolejny chętny do bycia mięsem armatnim. {gracz} umiera {wynik} razy na {mapa}, wyrównując dotychczasowy rekord zgonów!"
]