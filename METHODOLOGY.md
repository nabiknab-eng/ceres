# Metodika CERES

## Vstupy a souřadnice

Použity jsou stejné měsíční soubory jako v zachované verzi ASR: NASA `CERES_EBAF-TOA_Edition4.2.1_200003-202608.nc` a Berkeley Earth `Global_TAVG_Gridded_1deg.nc` (High-Resolution TAVG). Vstupní soubory, jejich verze a SHA-256 zaznamenává manifest i NetCDF. Pobřeží pochází z Natural Earth 1 : 50 mil. Nejsou použity generované geografické podklady, hranice států ani geografická síť.

Měsíce jsou explicitně spojeny podle dvojice rok–měsíc. Společná řada 03/2000–08/2026 má 318 měsíců a žádné globální mezery. Žádné jiné měsíce se nedoplňují. Všechny veličiny jsou v jedné skutečné síti 180 × 360 buněk, se středy −89,5…89,5° a −179,5…179,5°. Délky se normalizují do [−180°,180°) a následně seřadí; šířky se řadí od jihu k severu. Pole se přeuspořádají podle týchž indexů. Fill hodnoty a hodnoty mimo deklarované valid_min/valid_max se převedou na NaN.

## Dostupné veličiny

| Klíč | Výpočet ze zdroje | Jednotka anomálie |
| --- | --- | --- |
| asr | solar_mon − toa_sw_all_mon | W/m² |
| olr | toa_lw_all_mon | W/m² |
| net | toa_net_all_mon | W/m² |
| albedo | 100 × poměr časově integrovaného toa_sw_all_mon a solar_mon | procentní body |
| cloud | cldarea_total_daynight_mon, původně percent | procentní body |
| temperature | temperature, stejný Berkeley Earth produkt jako ASR | °C |

NET je kladný směrem do soustavy, OLR kladný směrem ven. Regionální mapa NET není mapou globálního EEI; EEI označuje jeho plošně vážený globální průměr. Znaménka se při barvení neobracejí. Výklad barev se řídí samotnou vybranou veličinou.

NET se přebírá přímo z `toa_net_all_mon`. Samostatně uložené toky mají omezené číselné rozlišení: v tomto konkrétním vstupním souboru se jejich měsíční součet ASR − OLR od uloženého NET liší nejvýše přibližně o 0,1501 W/m². Identita je fyzikální definicí; číselná kontrola respektuje tuto přesnost zdroje. Původní NET se nepřepisuje rozdílem jiných zaokrouhlených polí. Přesná maxima rozdílů pro měsíce i výsledné anomálie obsahuje `validation_media.json`.

## Průměrování a reference

Pro toky, oblačnost a teplotu je průměr úplného okna Σ(x_m d_m)/Σd_m, kde d_m je skutečný počet dní v měsíci gregoriánského kalendáře. Chybí-li kterákoliv z 12 měsíčních hodnot v buňce, je výsledkem NaN. Za každý rok 2001–2025 se vypočítá úplný kalendářní průměr. Reference je aritmetickým průměrem těchto 25 ročních hodnot se stejnou vahou roků; tato definice přesně zachovává původní projekt. U ASR a teploty se načte původní referenční pole a nezávislým přepočtem se kontroluje jeho shoda. Reference se nikdy neodvozuje z vybraného exportního intervalu.

Albedo období je poměr odražené a příchozí sluneční energie: 100 Σ(SW↑_m d_m)/Σ(Fin_m d_m), vyjádřený v procentech. Průměr měsíčních albed vážený jen dny by stejný poměr energií obecně nereprodukoval. Při polární noci jsou měsíční sluneční toky nulové, ale měsíční albedo není definováno; žádné nulové albedo se nedoplňuje. Poměr za celé roční okno je definován pouze při kladném součtu příchozí energie a úplných vstupních tocích. Reference albeda je průměr 25 takto vypočtených ročních poměrů. Jeho anomálie i anomálie oblačnosti jsou v procentních bodech.

307 klouzavých oken tvoří vždy 12 po sobě jdoucích společných měsíců. Datum snímku je přesný časový střed jeho polootevřených hranic [začátek prvního měsíce, začátek měsíce následujícího po posledním). První snímek: 03/2000–02/2001, 30.08.2000 12:00 UTC. Poslední: 09/2025–08/2026, 02.03.2026 12:00 UTC. Lednová–prosincová okna se kontrolují proti všem 25 kalendářním mapám. Pětiletí jsou průměry pěti ročních anomálií. Jakýkoliv chybějící rok nebo reference propaguje NaN.

## Projekce a barvy

Skutečná Mollweideova plochojevná projekce s centrálním poledníkem 0°. Společná inverzní projekční tabulka určuje zdrojovou 1° buňku pro každý střed pixelu rastru 600 × 300. Polohy mimo elipsu jsou bílé. Převod délky na obou stranách ±180° a limitní polohy pólů se ověřují; polární šířka středu nejvyššího pixelu je dána rozlišením rastru a není zaměňována s přesným pólem. Data se prostorově neinterpolují. Pobřeží i obrys elipsy jsou sdílené neprůhledné černé pixely.

Paleta: deset modrých stupňů, bílá pro přesnou nulu, deset červených stupňů. Každý nenulový interval má jednu desetinu zvolené meze; hodnoty mimo meze přebírají nejkrajnější barvu. NaN má zvláštní šedou barvu. Legenda má pouze záporný konec, nulu a kladný konec. Automatická škála je stálá pro celý aktuální časový režim; nepřepočítává se každý snímek. Nikdy se nemění výpočetní data.

## Synchronizace, export a přesnost

Vizualizace načítá pouze vybrané veličiny po nejvýše 12 snímcích. Tři pole se zobrazí atomicky až po načtení stejného indexu ze všech vybraných bloků. Starší asynchronní požadavek nemůže přepsat novější volbu. Cache drží nejvýše 12 bloků. Shodná veličina ve dvou panelech sdílí načtená data, nikoliv nastavení škály.

HTML i Python používají stejné little-endian float32 vizualizační hodnoty, paletu, projekční tabulku a pobřeží. Plné NetCDF výsledky jsou float64. Zobrazení nemění číselné výsledky. Exportní JSON uchovává všechny tři veličiny, konkrétní meze, indexy intervalu a FPS. Exportní skript kontroluje jejich rozsahy, referenci a SHA-256 bloků. Každému vybranému měsíci odpovídá právě jeden vstupní snímek MP4. Video má H.264/yuv420p a 1920 × 1080; jde o ztrátovou kompresi. Přilehlý manifest snímků obsahuje časy a kontrolní součty předkompresních map.

## Zdroje definic

- [NASA CERES: produkty a rozlišení EBAF-TOA / kombinovaný EBAF](https://ceres.larc.nasa.gov/data/)
- [NASA CERES EBAF Ed4.2 / Ed4.2.1 Data Quality Summary, V8, 10. 9. 2026](https://ceres.larc.nasa.gov/documents/DQ_summaries/CERES_EBAF_Ed4.2_DQS.pdf)
- Původní nezměněná metodika Berkeley Earth, pobřeží a vstupních měsíčních souborů ([web ASR](https://nabiknab-eng.github.io/ceres-asr-temperature-atlas/)): `asr/original/METHODOLOGY.md` a `asr/original/provenance.json`.

Povrchové toky v souboru EBAF-TOA nejsou. Bezoblačná pole clr_c se vztahují k bezoblačným částem buněk; současná definice SW/LW CRE v EBAF používá clr_t pro celou buňku. Proto tyto tři veličiny bez dalších dat nejsou nabízeny. Dokument ani mapy neinterpretují příčiny změn.
