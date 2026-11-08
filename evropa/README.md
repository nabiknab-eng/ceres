# CERES Evropa

Otevřete `index.html` v aktuálním Safari, Chrome nebo Firefoxu. Pro prohlížení bez internetu rozbalte celý repozitář a zachovejte společnou strukturu složek.

- První dvě mapy mají nezávislý výběr ASR, OLR, NET / EEI, planetárního albeda a oblačnosti. Třetí mapa zobrazuje povrchovou teplotu.
- K dispozici je 307 klouzavých 12měsíčních oken, 25 kalendářních roků a pět pětiletí. Všechny tři mapy zobrazují stejné období.
- Každý panel má vlastní ruční a automatickou škálu. Automatická škála vychází z hodnot zobrazených v evropském výřezu v celém vybraném časovém režimu.
- Hranice států a pobřeží jsou vykreslené bez názvů. Evropský výřez zahrnuje i přilehlý Atlantik, Středomoří a okolní území.

## Export MP4

Pro vlastní video nastavte v atlasu veličiny, škály, interval a rychlost. Tlačítko **Export MP4 — stáhnout nastavení** uloží `ceres-evropa-export.json`. Na Macu otevřete `Export_MP4.command`, přetáhněte stažený JSON do terminálu a stiskněte Enter. Výstup se uloží do `exports`.

Pro samostatný export nainstalujte Python závislosti z `requirements_export.txt` a systémový FFmpeg s podporou H.264. Příkaz spusťte z této složky:

```sh
python3 export_mp4.py --settings /cesta/k/ceres-evropa-export.json
```

Výsledkem je H.264 ve Full HD se třemi synchronizovanými mapami. Soubor `.frames.json` uvádí čas a kontrolní součty map každého snímku.

Podrobnosti o výřezu, zdrojích a reprodukci jsou v [metodice](METHODOLOGY.md).

Plná výpočetní data NetCDF a hotové MP4 jsou v původním místním balíčku. Pro zobrazení map v prohlížeči stačí soubory v repozitáři.
