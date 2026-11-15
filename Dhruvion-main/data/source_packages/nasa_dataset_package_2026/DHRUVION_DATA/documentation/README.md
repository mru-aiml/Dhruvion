# DHRUVION NASA Dataset Package

Dataset package for **DHRUVION**, the Mars Mission Intelligence Platform for Gale Crater and Aeolis Mons (Mount Sharp). Target centre: latitude -5.4 deg, longitude 137.8 deg E. Analysis area (AOI): latitude -7.0 to -3.8, longitude 136.2 to 139.4 E (planetocentric, east-positive).

> **Package status:** this package contains **real NASA/USGS data for Gale Crater**, together with validated derived products:
> - MOLA 463 m elevation for the Gale area, with slope, roughness and coverage layers derived from it;
> - a CTX mosaic image of the crater (a reduced 50 m/px copy);
> - Curiosity REMS environmental data for sols 9 and 11;
> - Curiosity RAD dose rates for sols 1–3.
>
> Twelve other catalogued datasets were not acquired and are marked NOT AVAILABLE. Nothing in this package is simulated.

## Purpose

The terrain layers (MOLA elevation, slope, roughness and coverage) drive the map and the route planner. The CTX image is the regional base layer. The Curiosity REMS (environment) and RAD (radiation) summaries feed historical charts. REMS and RAD are single-location rover measurements: they are not maps, live conditions or forecasts, and must not drive route costs.

## Folder structure

```
DHRUVION_DATA/
  raw/terrain/   MOLA 463 m Gale AOI window (values unchanged) + crop provenance
  raw/ctx/       Murray Lab CTX tile E136_N-08, 10x averaged (~50 m) Gale copy + crop provenance
  raw/rems/      SOL00009, SOL00010 (label only), SOL00011 MODRDR .TAB/.LBL; documentation/ (SIS, MODRDR6.FMT)
  raw/rad/       SOL_00000_00089/ RDR .TXT/.LBL for sols 1-3 + 18 .FMT files; documentation/ (SIS PDF)
  processed/terrain/  elevation_m, slope_deg, roughness_tri_riley_m, coverage_mask GeoTIFFs + PNG overlays + JSON
  processed/ctx/      AOI clip GeoTIFF + PNG overlay + JSON
  processed/rems/     clean observations, per-sol and per-session summaries, missing-value report, trends
  processed/rad/      clean observations (per observation, per detector), per-sol summaries, trends
  scripts/       pipeline 00-10, 02b ingestion, readers, config/, tests/ (26 tests)
  metadata/      catalogs, manifests, validation results, column dictionaries, logs, evidence
  reports/       phase 1-4 reports, test results
  documentation/ README.md (this file), TEAM_HANDOVER.md, FINAL_REPORT.md
```

Key metadata: `metadata/FINAL_DATASET_CATALOG.json` (every dataset: source, files, coverage, units, level, OBSERVED/DERIVED, status, limitations), `download_manifest.*` (source URL, SHA-256 and notes for every file), `validated_dataset_catalog.json` and `validation_summary.csv`, `column_dictionaries/` (label-derived column definitions), `PACKAGE_MANIFEST.json` (SHA-256 of every packaged file).

## Formats, units and coordinate systems

| Product | Format | Units | NoData |
|---|---|---|---|
| MOLA elevation (raw window) | GeoTIFF Int16, 410 x 410 | metres above the MOLA areoid (USGS product page) | -32768 |
| Elevation (processed) | GeoTIFF float32 | metres | NaN |
| Slope | GeoTIFF float32 | degrees (Horn 1981) | NaN |
| Roughness | GeoTIFF float32 | metres (TRI, Riley et al. 1999) | NaN |
| Coverage mask | GeoTIFF uint8 | 0 no data / 1 all valid / 2 elevation only | none |
| CTX image | GeoTIFF uint8, 3794 x 3460, ~50 m/px | 8-bit DN (not reflectance) | 0 |
| PNG overlays | RGBA PNG | display colours (stretch in *_overlay_metadata.json) | alpha = 0 |
| REMS tables | CSV + JSON | label units: KELVIN, PASCAL, METERS/SECOND, DEGREE, %, W/m**2 | empty (CSV) / null (JSON) |
| RAD tables | CSV + JSON | microGray / Hour (label unit) | empty / null |

**Coordinate reference systems.** MOLA uses equirectangular projection on the Mars sphere (R = 3,396,190 m). The CTX file uses equirectangular projection on the Mars 2015 ellipsoid with planetocentric latitude. All latitudes in this package (bounds, overlays, AOI) are **planetocentric**, and longitudes are east-positive in the -180..180 range. The two CRSs agree to within 12.1 m over the AOI, but their grids differ, so combine the layers by coordinates, not by pixel index.

## Processing instructions

```bash
pip install -r requirements.txt            # Python >= 3.10
cd scripts
python -m pytest -q tests                  # expect 26 passed
python 03_validate_rasters.py && python 04_validate_pds_tables.py && python 09_build_catalogs.py
python run_step4.py && python 09_build_catalogs.py
python 10_package_and_verify.py --overwrite
```

To fetch more data on a machine with internet access, run `python 02_download_datasets.py`; the exact URLs are in `config/download_plan.json`. Files downloaded by hand are added with `02b_ingest_user_files.py` and a spec like `config/ingest_spec_2026-11-14.json`, and `crop_for_upload.py` shrinks very large rasters before sharing. `run_pipeline.sh` runs the full chain.

## Provenance vocabulary

OBSERVED: acquired by a mission instrument (including clipped or reformatted copies). DERIVED: calculated from validated observed data (slope, roughness, statistics, the 10x averaged CTX copy). SIMULATED: generated by application demo logic (none in this package). UNAVAILABLE: not obtained.
