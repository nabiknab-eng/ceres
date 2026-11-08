# Metodika CERES Střední Evropa

Atlas vychází z původních anomálií a referenčních polí CERES EBAF-TOA Ed4.2.1 a Berkeley Earth High-Resolution TAVG v síti 1° × 1°. Manifest obsahuje SHA-256 obou vstupů. Referenční období je 2001–2025. Mapy používají 307 klouzavých oken po 12 měsících, 25 ročních hodnot a pět pětiletí. Význam veličin a způsob časového průměrování jsou popsány přímo v atlasu.

## Prostorová interpolace

Hotové anomálie a referenční pole se bilineárně interpolují ze středů původních buněk na pravidelnou síť zeměpisných souřadnic s krokem 0,25° v obou směrech. Hodnota mezi čtyřmi zdrojovými středy je váženým průměrem podle jejich vzdálenosti ve směru šířky a délky. Na shodných souřadnicích se reprodukuje původní hodnota. Pokud chybí některá hodnota s nenulovou vahou, výsledek zůstává chybějící. Jemnější síť je odvozená z původních měření. [Definice bilineární interpolace ECMWF](https://codes.ecmwf.int/grib/format/grib2/ctables/4/15/)

NetCDF uchovává interpolované hodnoty a referenční pole v přesnosti float64. Pro každý pixel mapy se zvolí nejbližší bod nové sítě. Web i exportér používají stejné zobrazovací hodnoty float32, projekční tabulku, paletu a překryv hranic. Automatická škála vychází z maxima absolutní hodnoty všech zobrazených bodů přes celý zvolený časový režim.

## Výřez a hranice

Rámec pokrývá střední Evropu a okolí. V plochojevném zobrazení ETRS89 / LAEA Europe (EPSG:3035) má rozsah x = 3 860 000 až 5 460 000 m a y = 2 410 000 až přibližně 3 636 667 m. [Evropská agentura pro životní prostředí](https://sdi.eea.europa.eu/catalogue/water/api/records/a373b065-66d8-45ae-86af-6618cc6792cb)

Pobřeží i pevninské hranice států používají podklady Natural Earth v měřítku 1 : 50 mil. Hranice jsou bez názvů. Archivy a jejich kontrolní součty jsou v `geo` a `manifest.json`. [Natural Earth](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-boundary-lines-2/)

## Reprodukce

Se zdrojovým místním atlasem CERES (`manifest.json`, `render_spec.json` a `data/ceres_anomalies.nc`) a přiloženými archivy Natural Earth spusťte po instalaci závislostí z `requirements_build.txt`:

```sh
python3 build_central_europe.py --source-dir /cesta/k/ceres
```

Skript vytvoří regionální NetCDF, projekční tabulku, překryv hranic a datové bloky pro web. Zdroje dat jsou [NASA CERES](https://ceres.larc.nasa.gov/data/) a [Berkeley Earth](https://berkeleyearth.org/data/).
