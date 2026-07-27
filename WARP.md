# WARP.md

Project context and conventions for AI agents working in this repository.

## Buoy stations and locations

The buoy CLI supports two moored ocean-observing stations (see `StationName` in `buoys/__init__.py`). Their physical deployment locations are:

- **Blynken → Islesboro.** The `blynken` station is the Islesboro buoy. To plot "Islesboro" data, use the `blynken` station.
- **Wynken → near Hurricane Island** (coordinates `44.0420272, -68.891064`, recorded in `weather-alloy/locations.csv`).

Station names are the only identifiers the CLI accepts (`wynken` / `blynken`); place names like "Islesboro" are not recognized as CLI arguments.

## Plotting buoy data

Plot a single data stream (writes a PNG to `buoys/figures/tail/<station>/<series>.png`):

```bash
pixi run penbay buoys plot tail <station> <table> <series>
```

- `<station>`: `wynken` | `blynken`
- `<table>`: `diagnostic` | `sonde`
- `<series>`: e.g. `sea_water_temperature`, `sea_water_salinity`, `dissolved_oxygen`, `sea_water_chlorophyll_rfu`, `barometric_pressure`, `water_pressure`

Example — most recent sea water temperature at Islesboro (Blynken):

```bash
pixi run penbay buoys plot tail blynken sonde sea_water_temperature
```

Useful options: `--days N` (window, default 30), `--test rollup|gross_range|spike|climatology|flat_line|rate_of_change` (QARTOD flag to overlay), `--qartod qartod.yaml`.

Local raw data lives in `buoys/data/` as Campbell logger `.dat` files named `<Station>_<Table>_<TimeRecovered>.dat`.
