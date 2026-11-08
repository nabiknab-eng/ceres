# Metodika CERES Evropa

Regionální atlas přebírá hotové anomálie, referenční pole a časové hranice z místního atlasu CERES. Datové zdroje jsou CERES EBAF-TOA Ed4.2.1 a Berkeley Earth High-Resolution TAVG v síti 1° × 1°. `manifest.json` uchovává SHA-256 obou původních vstupů.

Společná data pokrývají 03/2000–08/2026. K dispozici je 307 úplných klouzavých oken po 12 měsících s krokem jeden měsíc, 25 ročních hodnot a pět pětiletí. Průměry toků, teploty a oblačnosti v rámci roku váží měsíce skutečným počtem dní. Albedo je poměr odražené a příchozí sluneční energie za celé okno. Referenci každé buňky tvoří průměr jejích 25 ročních hodnot za 2001–2025. Chybějící hodnoty zůstávají NaN. Definice a jednotky jednotlivých veličin jsou také přímo v atlasu.

## Výřez a hranice

Mapy používají plochojevné zobrazení ETRS89 / LAEA Europe (EPSG:3035). Rámec má v tomto systému souřadnice x = 850 000 až 7 650 000 m a y = 1 350 000 až 6 563 333⅓ m. Zahrnuje mimo jiné kontinentální Evropu, Island, Azory, Špicberky a Kypr a přilehlé oblasti. [Evropská agentura pro životní prostředí](https://sdi.eea.europa.eu/catalogue/water/api/records/a373b065-66d8-45ae-86af-6618cc6792cb)

Pobřeží je z Natural Earth 1 : 50 mil. (4.1.0), pevninské hranice států ze sady Admin 0 Boundary Lines Land (5.1.0). Používá se výchozí klasifikace Natural Earth. Sporné, neurčité a kontrolní linie mají světlejší barvu. V mapách nejsou názvy států. Zdrojové archivy a jejich kontrolní součty jsou v `geo` a `manifest.json`. [Natural Earth](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-boundary-lines-2/)

Střed každého pixelu rastru 600 × 460 se inverzní projekcí přiřadí k původní buňce 1°. Hodnoty se prostorově neinterpolují. NetCDF uchovává obdélníkový výřez v původní síti zeměpisných souřadnic ve float64. Na mapě se využívá 5 920 buněk. Prohlížeč i exportér používají stejné hodnoty float32, projekční tabulku, paletu a překryv hranic a pobřeží. Automatická škála vychází z maxima absolutní hodnoty v těchto viditelných buňkách přes všechny snímky zvoleného časového režimu.

## Reprodukce

Se zdrojovým místním atlasem CERES (`manifest.json`, `render_spec.json` a `data/ceres_anomalies.nc`) a přiloženými archivy Natural Earth spusťte po instalaci závislostí z `requirements_build.txt`:

```sh
python3 build_europe.py --source-dir /cesta/k/ceres
```

Skript vytvoří regionální NetCDF, projekční tabulku, překryv hranic a bloky pro offline prohlížeč. Zdroje dat [NASA CERES](https://ceres.larc.nasa.gov/data/) a [Berkeley Earth](https://berkeleyearth.org/data/). Licence přiložených fontů a macOS FFmpeg jsou ve složkách `fonts` a `bin`.
