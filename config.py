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