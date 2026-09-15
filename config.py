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
    "W końcu awans. Teraz będziesz dostawał wpierdol od ludzi z nieco lepszym celownikiem, przygotuj maść na ból dupy.",
    "Ranga w górę, ale ego wystrzeliło w kosmos. Przypominam, że nadal nie potrafisz rzucić prostego smoke'a na Mirage'u.",
    "Cud nad Wisłą! Gaben osobiście musiał przestawić suwak twojego ELO, bo z gry tego nie widać.",
    "Awansik wjechał na pełnej. Czyżbyś w końcu znalazł lewy przycisk myszy?",
    "Wbiłeś wyższy poziom, gratki! Następny krok to włączenie dźwięku w słuchawkach.",
    "O kurwa, awans! Jeszcze z 5 lat takiego carry przez ziomków i może sam wygrasz rundę 1v1.",
    "Podobno ranga nie gra roli, ale w twoim przypadku to cud, że w ogóle poszła w prawo, a nie w lewo.",
    "Gratulacje awansu! Przeciwnicy musieli mieć po 3 promile i grać na touchpadach, żeby ci na to pozwolić.",
    "Widzę awans na koncie! Szkoda, że twój crosshair placement nadal celuje w krety pod ziemią.",
    "No no, szacunek rośnie na dzielnicy. Teraz tylko nie spadnij w następnym meczu jak zwykle.",
    "Awans wszedł gładko. Ciekawe ile modlitw poszło do serwerów Valve, żeby ten pocisk siadł.",
    "Brawo, ranga w górę! Twoi randomi pewnie do teraz biorą antydepresanty po tym co musieli wycarować.",
    "Szefie, awansik elegancki. Szkoda tylko, że połowa twoich fragów to były plecy i baitowanie całego teamu.",
    "No i klasa, awansik wbity! Aż dziwne, że antycheat nie zablokował ci tego wyniku z litości.",
    "Awans leci, wielkie brawa! Może czas odpiąć kółka boczne od roweru i zagrać coś samemu?",
    "Wyższy level odblokowany! Pamiętaj, żeby podziękować ziomalom z lobby na kolanach za ten darmowy transport.",
    "O proszę, awans! Czyżbyś w końcu przetarł monitor i zauważył, gdzie jest celownik?",
    "Ranga w górę! Statystyki mówią awans, ale killfeed wciąż płacze ze śmiechu.",
    "Gratki, poziom wyżej! Tylko nie zapomnij, że teraz przeciwnicy już potrafią klikać 'A' i 'D'.",
    "Awansik jak najbardziej zasłużony... przez czterech twoich kolegów z drużyny.",
    "Nareszcie! Koniec wstydu na serwerze, teraz zaczyna się wstyd na nieco wyższym poziomie.",
    "Gratulacje! Przebiłeś barierę żenady i awansowałeś szczebel wyżej. Oby tak dalej.",
    "Awans wbity! Ciekawe, ile klawiatur poległo u przeciwników, że dali ci to ugrać.",
    "Święto lasu, ranga poszła w górę! Otwierajcie szampana, zanim w kolejnym meczu odda z nawiązką.",
    "Awans! Donk już drży ze strachu przed twoim sprayem z Galila w sufit.",
    "Wbiłeś wyższy level, gg! Może teraz twoi rodzice w końcu będą z ciebie dumni.",
    "Ranga wjechała na salon. Tylko nie kozacz za bardzo na Discordzie, bo matchmaking szybko sprowadza na ziemię.",
    "Awansik zrobiony. Czas na tradycyjny zjazd o 3 rangi w dół w ciągu najbliższego weekendu!",
    "No i elegancko! Nowa ranga wygląda ładnie, teraz tylko dostosuj do niej swoje umiejętności.",
    "Gratulacje awansu! Wygląda na to, że nawet zepsuty zegar dwa razy na dobę pokazuje właściwy czas.",
    "Ranga w górę! Jeszcze chwila i przestaniemy się wstydzić grać z tobą 5v5.",
    "Awans! Wreszcie opuściłeś strefę całkowitego upośledzenia taktycznego.",
    "Wbity kolejny szczebel! Wygląda na to, że twoja taktyka 'biegnij i módl się' w końcu przyniosła skutek.",
    "Brawo za awans! Podobno po tym meczu wrogowie złożyli zbiorowy pozew o odszkodowanie moralne.",
    "Nowy level wpadł na profil! Niech żyje potęga baitowania kolegów zza ściany.",
    "Gratulacje, ranga w górę! Tylko pamiętaj: wyższy level to nie powód, żeby przestać kupować defuse kit.",
    "Awans wbity z buta! Zobaczymy jak długo wytrzyma twoja psychika na nowych progach.",
    "Obywatelu, awans został zaliczony. Prosimy o zachowanie spokoju i nie oddawanie ELO w pierwszym lepszym meczu.",
    "Ranga podskoczyła! Nawet boty na offline zaczynają cię szanować.",
    "Awansik piękny jak poezja. Tylko błagam, naucz się wreszcie rzucać flesze za siebie, a nie w oczy teamu.",
    "Nowa ranga wbita! Gratulacje, oficjalnie jesteś najlepszym graczem wśród najgorszych."
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
    "Ranga w dół, ego w dół. Może czas zaakceptować, że jesteś po prostu jebanym łakiem i przestać marnować prąd?",
    "Spadek zaliczony z gracją worka cementu rzuconego z czwartego piętra.",
    "Lecisz w dół szybciej niż polski złoty w kryzysie. Gdzie jest dno tej studni?",
    "Derank wjechał na pełnej. Twój gameplay przypominał dzisiaj pokaz slajdów w PowerPoincie.",
    "I cyk, ranga w dół. Jak się czujesz ze świadomością, że boty z Counter-Strike 1.6 miały lepszy movement?",
    "Zjazd do bazy. Matchmaking zweryfikował twoje marzenia o byciu prosem w ułamku sekundy.",
    "Derank! Nawet podkładka pod myszkę miała dzisiaj większy wkład w mecz niż ty.",
    "Gratulacje spadku! Valve powinno wprowadzić specjalną rangę pod poziomem 1 dedykowaną tylko tobie.",
    "Zleciałeś na ryj. Mam nadzieję, że chociaż pasy miałeś zapięte podczas tej katastrofy.",
    "Ranga poszła się jebać. Kup sobie maść na odparzenia, bo te baty musiały piec.",
    "Spadek w dół! Przestań winić tickrate i ping – po prostu twój celownik omijał modele jak zarazę.",
    "Wracasz tam, skąd przyszedłeś. W rynsztoku przynajmniej nikt nie ma wobec ciebie żadnych oczekiwań.",
    "Derank wszedł na miękko. Wyglądałeś jakbyś grał na kierownicy od traktora z wyłączonym force feedbackiem.",
    "Spadłeś z rowerka. Daj komuś innemu myszkę, kot biegający po klawiaturze narobiłby mniej szkód.",
    "Ranga w dół! Twoja obecność na serwerze to był czysty sabotaż i sponsoring wrogiej ekonomii.",
    "Piękny zjazd. Z taką formą to ty nawet w Tetrisie byś klocki do góry nogami poukładał.",
    "Derank! Przeciwnicy dziękują za darmowe punkty i proszą o więcej takich meczów z twoim udziałem.",
    "Spadek poziomu. Zmień rozdzielczość, crosshair, fotel i najlepiej grę, bo to nie ma sensu.",
    "Ranga runęła jak domek z kart. Szkoda prądu na twoje popisy.",
    "Witamy piętro niżej! Przynajmniej teraz będziesz mógł trafiać na ludzi, którzy też nie wiedzą co to monitor.",
    "Derank to jedyna sprawiedliwa kara za twój dzisiejszy festiwal whiffów.",
    "Zleciałeś z rangi. Czy ty celujesz wrogom w stopy z szacunku, czy po prostu nie dajesz rady podnieść myszki?",
    "Spadek! Jeśli twoim celem było zrujnowanie dnia czterem osobom z teamu, to gratuluję – sukces w 100%.",
    "Ranga spadła, a z nią resztki twojej godności. Idź spać, jutro też będziesz słaby.",
    "Derank! Twój spray z AK wyglądał jak rysunek przedszkolaka z padaczką.",
    "Zjazd w dół. Nawet kurczaki na Inferno miały lepszą przeżywalność niż ty w tym meczu.",
    "Spadłeś! Twój movement był tak drewniany, że leśnicy chcieli cię zaciągnąć do tartaku.",
    "Ranga w dół! Jak to jest być piątym kołem u wozu w każdym możliwym meczu?",
    "Derank zaliczony! Twoja celność sprawia, że pacyfiści czują z tobą głęboką więź duchową.",
    "Zleciałeś z ligi. Może zapisz się na korepetycje z obsługi myszki optycznej?",
    "Spadek na dno! Grawitacja twojej nieudolności wciągnęła cały team w czarną dziurę porażki.",
    "Ranga w dół. Widziałem tosty z większą dynamiką i zmysłem taktycznym niż twoje wejścia na BS.",
    "Derank! Za taki pokaz anty-skilla powinieneś dostać zakaz zbliżania się do Steama na 50 metrów.",
    "Zjazd o poziom! Może spróbuj grać z otwartymi oczami, podobno diametralnie poprawia to wyniki.",
    "Spadłeś jak liść na jesień. Smutny, bezwładny i bez żadnej kontroli nad sytuacją.",
    "Ranga leci w dół. Twoje K/D w tym meczu wyglądało jak stan konta studenta po imprezie.",
    "Derank! Matchmaking uznał, że zbrodnią byłoby trzymanie cię na tak wysokim poziomie.",
    "Zleciałeś na ziemię. Czas schować ego do kieszeni i przeprosić kolegów z teamu.",
    "Spadek! Gratulacje, pobiłeś rekord w prędkości tracenia ELO w jednym meczu.",
    "Ranga w dół. Gdyby głupota w CSie miała masę, to zagiąłbyś czasoprzestrzeń na serwerze.",
    "Derank z pompą. Zrób sobie herbatę, wyłącz komputer i przemyśl swoje życiowe wybory."
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
    "Nie zdejmuj nogi z gazu! Przeciwnicy wychodzą z serwera, jak tylko widzą twój nick w tabeli.",
    "Zielono jak na łące na wiosnę! Co mecz to ez win, typy nie wiedzą co się dzieje.",
    "Pociąg zwycięstw pędzi bez hamulców! Ktokolwiek stanie na torach, zostaje zmielony na pył.",
    "Win streak rośnie! Czyżbyś w końcu przestał pić piwo przed meczem i skupił się na grze?",
    "Maszyna nie do zatrzymania! Twoja passa wygranych zawstydza profesjonalne drużyny.",
    "Rozjeżdżasz ich jak walec drogowy! Przeciwnicy po meczu szukają psychologa na NFZ.",
    "Zielona fala zalewa profil! Masz taki ciąg na wygrane, że aż Valve sprawdza twoje IP.",
    "Kolejny win do kolekcji! Wyglądasz jakbyś grał z kodami na nieśmiertelność.",
    "Win streak jak marzenie! Twoja pewność siebie przebiła już sufit i leci na orbitę.",
    "Znowu wygrana! Przeciwnicy piszą 'report player', a ty po prostu wjechałeś na serwer z buta.",
    "Passa trwa w najlepsze! Kosisz ich jak rolnik zboże na dożynkach.",
    "Zielona ściana rośnie w siłę! Chyba zapomniałeś jak smakuje porażka.",
    "Co mecz to zwycięstwo! Twoje plecy są ze stali, a celownik z czystego złota.",
    "Dominacja totalna! Z taką passą to możesz w pojedynkę wygrać Majora.",
    "Kolejny skalp zdobyty! Przeciwnicy mogą ci tylko buty czyścić po takim występie.",
    "Win streak płonie! Jesteś tak rozgrzany, że straż pożarna powinna dyżurować pod twoim biurkiem.",
    "Znowu na zielono! Wygląda na to, że w końcu podłączyłeś myszkę do właściwego portu USB.",
    "Mecz za meczem do przodu! Wrogowie poddają się w myślach jeszcze przed końcem rozgrzewki.",
    "Wygrana goni wygraną! Masz taki gaz, że nikt na tym serwerze cię nie zatrzyma.",
    "Potężna seria zwycięstw! Oby tak dalej, póki algorytm matchmakingu nie dobierze ci pięciu prosów.",
    "Zielono, gładko i bez stresu! Twoja gra to czysta poezja niszczenia rywali.",
    "Win streak jak z podręcznika! Wyglądasz jak gigachad, który przyszedł odebrać swoje ELO.",
    "Nie do zdarcia! Rozstawiasz ich po kątach w każdym kolejnym meczu.",
    "Kolejny triumf! Twoi wrogowie płaczą w poduszkę, a ty zgarniasz darmowe punkty.",
    "Seria wygranych robi wrażenie! Jeszcze chwila i sam Gaben pogratuluje ci formy.",
    "Znowu zwycięstwo! Jesteś w takim transie, że nawet z zamkniętymi oczami byś to wygrał.",
    "Zielona passa nie ma końca! Miażdżysz przeciwników z precyzją chirurga.",
    "Kolejny łatwy mecz do portfolio! Wygląda na to, że znalazłeś sekretny cheat-code do tej gry.",
    "Win streak leci w kosmos! Wrogie drużyny rozpadają się na kawałki pod twoim naporem.",
    "Bezlitosny dla rywali! Z taką serią wygranych to ty ustalasz zasady na mapie.",
    "Znowu win! Przeciwnicy myśleli, że mają szanse, ale brutalnie sprowadziłeś ich na ziemię.",
    "Zielona ściana chwały! Twoja forma jest dziś po prostu nie do opisania.",
    "Kolejne zwycięstwo wbite do bazy! Twoje mecze to czysta egzekucja bez prawa do apelacji.",
    "Passa trwa! Jesteś jak czołg, który taranuje każdą przeszkodę na swojej drodze.",
    "Znowu ez win! Zaczynamy podejrzewać, że grasz przeciwko botom na najniższym poziomie trudności.",
    "Win streak puchnie w oczach! Oby ta passa trwała wiecznie, bo pięknie to wygląda.",
    "Niepokonany! Twoja obecność na serwerze gwarantuje wrogom szybki powrót do lobby.",
    "Kolejny mecz, kolejna wygrana! Jesteś w życiowej formie, wykorzystaj to na maksa.",
    "Zielony festiwal trwa! Przeciwnicy uciekają z serwera zanim runda na dobre się zacznie.",
    "Znowu do przodu! Twoja seria wygranych budzi postrach w całym matchmakingu.",
    "Win streak potwór! Nic i nikt nie jest w stanie wybić cię z tego morderczego rytmu."
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
    "Stiltowany, zniszczony, bez formy. Jesteś pośmiewiskiem matchmakingu. Wyjdź na dwór, dotknij trawy.",
    "Czerwona ściana wstydu! Twoja historia meczów wygląda jak raport z katastrofy budowlanej.",
    "Lose streak trwa! Czy ty masz jakiś zakład o to, kto szybciej odda całe swoje ELO?",
    "Znowu w pizdę! Może zamiast grać w CSa, spróbuj symulatora farmy? Tam nikt do ciebie nie strzela.",
    "Kolejna porażka z rzędu! Twój mental osiągnął temperaturę zera bezwzględnego.",
    "Lecisz po równi pochyłej! Nawet grawitacja nie działa tak szybko jak twoja seria przegranych.",
    "Czerwono wszędzie, gówno wszędzie! Zrób przysługę ludzkości i wciśnij Alt+F4.",
    "Znowu w plecy! Twoja passa porażek jest tak stabilna, że można na niej zegarki nastawiać.",
    "Kolejny mecz w błoto! Wyglądasz jak sponsor wrogich zwycięstw z dożywotnim karnetem.",
    "Lose streak rośnie w oczach! Czy ty w ogóle trafiasz w klawisze, czy kot ci śpi na klawiaturze?",
    "Dno i metr mułu! Z każdym kolejnym meczem udowadniasz, że nie ma granicy dla twojej nieudolności.",
    "Czerwona fala porażek! Twój profil na Faceicie powinien mieć ostrzeżenie o treściach drastycznych.",
    "Znowu przegrana! Może czas wymienić monitor na taki, który wyświetla też wrogich graczy?",
    "Porażka za porażką! Wygląda na to, że twoją jedyną strategią jest szybkie oddawanie pierwszej krwi.",
    "Lose streak jak z koszmaru! Twoi koledzy z drużyny płaczą w kącie po każdym wspólnym meczu.",
    "Kolejny wpierdol! Twój styl gry to idealny materiał instruktażowy pod tytułem 'czego NIE robić w CSie'.",
    "Czerwono aż oczy bolą! Zrób przerwę, napij się melisy i wyjdź na świeże powietrze, bo pękniesz.",
    "Znowu L na koncie! Jesteś jak magnes na przegrane rundy – cokolwiek zrobisz, i tak kończy się klapą.",
    "Seria porażek bije rekordy! Podobno Valve planuje wprowadzić dla ciebie specjalną kategorię w rankingu.",
    "Dno osiągnięte, a ty wciąż kopiesz! Wyglądasz na kompletnie bezradnego na każdej możliwej mapie.",
    "Kolejny mecz w plecy! Twoja celność przypomina rzucanie grochem o betonową ścianę.",
    "Lose streak z piekła rodem! Przeciwnicy nawet nie muszą się starać, sami oddajecie im te mecze.",
    "Czerwona ściana rozpaczy! Twój bilans wygląda jak wykres bankrutującej spółki na giełdzie.",
    "Znowu przegrana runda za rundą! Może czas zmienić hobby na szydełkowanie?",
    "Niekończące się porażki! Twój tilt osiągnął już poziom radioaktywny.",
    "Kolejna klęska! Jesteś największym dawcą punktów rankingowych na tym serwerze.",
    "Czerwono jak na światłach w centrum! Stoisz w miejscu i obrywasz z każdej strony.",
    "Znowu przegrana! Twoja gra to czysta abstrakcja, nikt nie rozumie co ty właściwie próbujesz zrobić.",
    "Lose streak bez litości! Twój celownik chyba ucieka przed modelami wrogów ze strachu.",
    "Kolejny mecz, kolejna katastrofa! Wygląda na to, że nawet boty z matchmakingu grałyby lepiej.",
    "Zjazd w otchłań! Z taką passą to ty zaraz wylądujesz na ujemnym ELO.",
    "Czerwona flaga wisi nad twoim profilem! Twoja gra to jawny sabotaż i brak jakiejkolwiek dyscypliny.",
    "Znowu porażka! Wyglądasz jakbyś grał z odwróconą myszką i wyłączonym monitorem.",
    "Lose streak nie bierze jeńców! Twój team ma ochotę złożyć wniosek o zakaz gry z tobą.",
    "Kolejny mecz przegrany do zera! Nawet w totka łatwiej wygrać niż z tobą w jednej drużynie.",
    "Czerwono aż strach patrzeć! Twój gameplay to najsmutniejszy dramat jaki dziś widziałem.",
    "Znowu w plecy! Może spróbuj grać rękami zamiast łokciami, podobno pomaga.",
    "Seria przegranych rośnie w siłę! Twój entuzjazm umarł, a forma leży w grobie obok.",
    "Kolejna lekcja pokory od wrogów! Szkoda tylko, że ty z tych lekcji nic nie wyciągasz.",
    "Czerwona ściana nie bierze urlopu! Zrób przysługę swoim punktom i zamknij tę grę na tydzień.",
    "Totalna kompromitacja w serii! Twój bilans krzyczy o natychmiastową przerwę od CSa."
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
    "Każdy twój strzał to była poezja niszczenia. Rozpierdoliłeś ten mecz w pojedynkę.",
    "Kosmiczny rating HLTV! Wyglądałeś jak profesjonalny gracz na serwerze dla początkujących.",
    "Absolutny rzeźnik na serwerze! Przeciwnicy chowali się po kątach, ale i tak ich znalazłeś.",
    "Potwór w killfeedzie! Twój nick pojawiał się częściej niż powiadomienia o podatkach.",
    "Zrobiłeś z nich miazgę! Twój występ zasługuje na pomnik przed siedzibą Valve.",
    "Carry na poziomie mistrzowskim! Twoje plecy powinny dostać order za odwagę i wytrzymałość.",
    "HLTV rating eksplodował! Donk i m0NESY mogą ci dzisiaj nosić myszkę w teczce.",
    "Czysty pogrom! Strzelałeś takie banie, że wrogowie sprawdzali czy serwer nie jest zhakowany.",
    "Potęga i dominacja! Wjechałeś w ten mecz jak czołg w budkę z kebabem.",
    "Występ życia! Pokazałeś im gdzie raki zimują i jak się gra w tę grę na poważnie.",
    "Zdemolowałeś ich psychikę! Po tym meczu połowa wrogiego teamu usunęła CSa z biblioteki Steam.",
    "Król serwera! Twój rating HLTV świeci tak jasno, że muszę założyć okulary przeciwsłoneczne.",
    "Nie brałeś jeńców! Każda runda to był twój prywatny pokaz siły i bezwzględności.",
    "Strzelecki geniusz! Twój celownik wchodził na głowy rywali z chirurgiczną precyzją.",
    "Czysta poezja fragowania! Rozstrzelałeś ich tak gładko, że aż miło było popatrzeć.",
    "Bezlitosny egzekutor! Wrogowie bali się nawet spojrzeć w twoją stronę przez celownik.",
    "Występ godny Majora! Wyciągnąłeś ten mecz za uszy i jeszcze skasowałeś przeciwników.",
    "Dominator totalny! Twoje cyfry w tym meczu wyglądają jak z gry na kodach.",
    "Prawdziwy gigachad! Plecy bolą od noszenia teamu, ale satysfakcja z rozbicia wrogów jest bezcenna.",
    "Rzeź na kółkach! Zrobiłeś sobie z wrogiego teamu darmowy poligon strzelecki.",
    "Potężny impact w każdej rundzie! Bez ciebie ten mecz byłby tylko smutną formalnością.",
    "Maszyna do eliminacji! Twój bilans wygląda jak lista obecności na cmentarzu wrogiej drużyny.",
    "Zdominowałeś całą mapę! Przeciwnicy czuli twój oddech na karku w każdym zakątku serwera.",
    "Forma wywalona w kosmos! Dzisiejszy występ to czysty majstersztyk sztuki strzeleckiej.",
    "Rozdałeś im takie lekcje, że powinni ci zapłacić za korepetycje z CSa.",
    "Prawdziwy snajper i rzeźnik w jednym! Każdy twój strzał to był gwarantowany frag.",
    "Statystyki z innej galaktyki! HLTV rating na poziomie bóstwa strzeleckiego.",
    "Po prostu zniszczyłeś ten serwer! Nikt nie miał prawa nawet zbliżyć się do twojego wyniku.",
    "Absolutny szef gry! Pokazałeś im jak wygląda przepaść między amatorem a profesjonalistą.",
    "Fragowałeś tak gęsto, że gra nie nadążała wyświetlać powiadomień o zabójstwach.",
    "Czysty talent i perfekcja! Zrobiłeś z nich marmoladę i zjadłeś na deser.",
    "Występ marzeń! Twój rating HLTV to najlepszy dowód na to, kto tu rządzi.",
    "Rozmontowałeś ich defensywę jak klocki Lego! Zero litości, sto procent czystego skilla.",
    "Potęga ognia nie do zatrzymania! Twój karabin nie przestawał strzelać i trafiać.",
    "Wjechałeś w nich bez znieczulenia! Rywale do teraz mają koszmary z twoim nickiem w roli głównej.",
    "Prawdziwy mistrz ceremonii! Dyktowałeś warunki od pierwszej do ostatniej rundy.",
    "Rozjechani do spodu! Twój występ to definicja słowa 'hard carry' w słowniku gracza.",
    "Błysk geniuszu na serwerze! Twoje staty krzyczą: MVP, szef, gigachad.",
    "Zostawiłeś po nich tylko zgliszcza! Co za niesamowity pokaz indywidualnej dominacji.",
    "Czyste złoto w tabeli! Twój rating HLTV zasłużył na wpis do księgi rekordów serwera.",
    "Nie do zatrzymania, nie do pokonania! Zagrałeś mecz, o którym wnuki będą pisać wiersze."
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
    "Największy dzban meczu. Otwierasz tabelę... od dołu. Mam nadzieję, że chociaż ci wstyd za ten pokaz nieudolności.",
    "Rating HLTV poniżej norm społecznych! Twoja gra to był jawny zamach na psychikę całego teamu.",
    "Zagrałeś jak totalny bot! Nawet kukły na strzelnicy stawiają większy opór niż ty dzisiaj.",
    "Twoje statystyki wyglądają jak błąd systemu. Jak można biegać 30 minut po mapie i nic nie trafić?",
    "Kompletne dno! Twój jedyny pożytek to było rzucanie broni kolegom przed śmiercią.",
    "Grałeś jakbyś pierwszy raz w życiu zobaczył komputer na wystawie sklepowej.",
    "Zero killi, zero asyst, zero pożytku. Twoje HLTV rating osiągnęło poziom rynsztoka.",
    "Chodzący darmowy frag! Wrogowie bili się między sobą o to, kto pierwszy cię skasuje.",
    "Kompromitacja roku! Twój movement przypominał tapczan ciągnięty po schodach.",
    "Zrobiłeś z siebie pośmiewisko. Nawet boty na rozgrzewce miały lepszy czas reakcji.",
    "Twój impact w meczu był ujemny. Bardziej pomagałeś wrogom niż własnemu teamowi.",
    "Staty wołają o pomstę do nieba! Zmień czułość myszy, albo po prostu wyjmij wtyczkę z gniazdka.",
    "Zagrałeś jak paralityk! Czy ty w ogóle wiesz, z której strony lufy wylatują pociski?",
    "Nawet stojąc na AFK w bazie zrobiłbyś mniejsze straty dla ekonomii drużyny.",
    "Wstyd i hańba! Twoje HLTV rating z tego meczu powinno być karane grzywną.",
    "Biegałeś jak kurczak bez głowy! Przeciwnicy nawet nie musieli celować, sam wbiegałeś pod lufę.",
    "Najgorszy występ w historii tego serwera! Twoje staty to czysta komedia pomyłek.",
    "Czy ty grałeś stopą na touchpadzie od laptopa z 2005 roku? Bo tak to dokładnie wyglądało.",
    "Totalny sabotażysta! Twoja gra to idealny dowód na to, że matchmaking dobiera ludzi losowo.",
    "Zagrałeś na poziomie deski do prasowania. Zero dynamiki, zero myślenia, zero trafień.",
    "Dno tabeli należało dziś w 100% do ciebie. Oby nikt nigdy nie musiał z tobą grać w teamie.",
    "Twój spray z karabinu poleciał w kosmos i zestrzelił satelitę pogodową zamiast wroga.",
    "Zrobiłeś z siebie worek treningowy dla rywali. Dziękujemy za zniszczenie tego meczu.",
    "Twój rating HLTV wygląda jak temperatura na biegunie północnym – grubo poniżej zera.",
    "Grałeś jak NPC z uszkodzonym skryptem. Ciągle w tej samej ścianie, ciągle martwy.",
    "Statystyki gorsze niż u bota na Easy. Jakim cudem ty w ogóle trafiłeś na ten serwer?",
    "Twoja celność to absolutna abstrakcja. Kulki omijały wrogów z kilometrowym marginesem.",
    "Chodząca katastrofa! Twoja obecność na serwerze to była czysta strata prądu.",
    "Występ poniżej wszelkiej krytyki! Powinieneś zapłacić odszkodowanie kolegom z drużyny.",
    "Brak rąk, brak wzroku, brak słuchu. Twój gameplay to definicja bezradności.",
    "Oddałeś więcej darmowych fragów niż Czerwony Krzyż posiłków potrzebującym.",
    "Dno absolutne! Zamiast fragować, zajmowałeś się głównie oglądaniem czarno-białego ekranu po śmierci.",
    "Twój rating HLTV to jawna kpina. Zgłoś się do okulisty, bo ewidentnie nie widzisz wrogów.",
    "Najgorszy gracz na mapie bez cienia wątpliwości. Zlituj się i nie klikaj więcej 'Szukaj meczu'.",
    "Grałeś jakbyś miał ręce z plasteliny i laga na łączu mózgowym.",
    "Nawet nie potrafiłeś rzucić granatu pod nogi wroga, rzucałeś go prosto we własny team.",
    "Żenada roku! Twój bilans w tym meczu to idealny materiał na mema.",
    "Zagrałeś tak tragicznie, że przeciwnicy zaczęli z litości pisać ci słowa wsparcia na czacie.",
    "Totalny ściek! Twój celownik trząsł się jak galareta na wietrze.",
    "Zero pożytku z twojej gry. Gdyby cię zastąpić klockiem drewna, wynik byłby dokładnie ten sam.",
    "Oficjalny bot serwera! Gratulacje, zapisałeś się w historii jako największe rozczarowanie meczu."
]

# --- MAPY ---
TOURNAMENT_MAPS = ["Mirage", "Inferno", "Dust2", "Nuke", "Ancient", "Anubis", "Vertigo", "Cache", "Overpass"]

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

RECORD_WINSTREAK_TEXTS = [
    "🔥 NIEPOWSTRZYMANY POTWÓR! {gracz} ustanawia NOWY REKORD SERWERA z passą aż {wynik} WYGRANYCH Z RZĘDU! Ktoś w ogóle jest w stanie go zatrzymać?",
    "🚀 Droga na sam szczyt! {gracz} pobija rekord winstreaku osiągając {wynik} zwycięstw z rzędu na Faceit! Maszyna do wygrywania!",
    "👑 Król serwera! {gracz} notuje rekordową serię {wynik} wygranych z rzędu. ELO samo wpada do kieszeni!"
]

RECORD_WINSTREAK_TIE_TEXTS = [
    "🤝 Ognista seria! {gracz} wyrównuje rekord serwera osiągając aż {wynik} wygranych z rzędu!",
    "🔥 Dołączenie do elity! {gracz} wyrównał rekord winstreaku z wynikiem {wynik} zwycięstw z rzędu!"
]

RECORD_LOSSSTREAK_TEXTS = [
    "❄️ CZARNA SERIA! {gracz} ustanawia NOWY ANTY-REKORD serwera z fatalną serią {wynik} PORAŻEK Z RZĘDU! Czy ktoś może odciąć mu internet dla jego dobra?",
    "📉 Płacz i zgrzytanie zębów! {gracz} bije rekord loss-streaku: {wynik} przegranych meczów pod rząd. ELO leci na samo dno rowu mariańskiego!",
    "💀 Klątwa czy brak skilla? {gracz} notuje rekordową serię {wynik} porażek z rzędu. Wyłącz ten komputer i idź na spacer!"
]

RECORD_LOSSSTREAK_TIE_TEXTS = [
    "🤝 Solidarność w tiltowaniu! {gracz} wyrównuje anty-rekord z serią {wynik} porażek z rzędu!",
    "❄️ Ktoś tu potrzebuje przerwy! {gracz} wyrównał najgorszy loss-streak na serwerze: {wynik} przegranych pod rząd."
]