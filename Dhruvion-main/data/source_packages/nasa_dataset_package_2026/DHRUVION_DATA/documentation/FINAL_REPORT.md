# DHRUVION Final Report - Dataset Acquisition, Validation, Processing and Handover

> **Package status:** this package contains **real NASA/USGS data for Gale Crater**, together with validated derived products:
> - MOLA 463 m elevation for the Gale area, with slope, roughness and coverage layers derived from it;
> - a CTX mosaic image of the crater (a reduced 50 m/px copy);
> - Curiosity REMS environmental data for sols 9 and 11;
> - Curiosity RAD dose rates for sols 1–3.
>
> Twelve other catalogued datasets were not acquired and are marked NOT AVAILABLE. Nothing in this package is simulated.

## Totals

| Measure | Count | Detail |
|---|---|---|
| Candidate datasets catalogued | 16 | metadata/dataset_discovery_catalog.* |
| Archive endpoints reachable from build environment | 0 / 18 | domain allow-list; data acquired by the user instead |
| Files received from user | 37 | DHRUVION_UPLOAD.zip (12.1 MB) |
| Files ingested into raw/ | 36 | 41.7 MB; 1 byte-identical duplicate skipped |
| Files validated | 8 | 2 rasters + 6 PDS labels (with their data files) |
| Files approved for processing | 12 | MOLA, CTX, REMS sols 9 and 11 (label + table), RAD sols 1-3 (label + text) |
| Datasets processed | 4 | terrain, CTX, REMS, RAD |
| Processed output files | 29 | processed/ |
| Datasets VALIDATED WITH LIMITATIONS / NOT AVAILABLE | 4 / 12 | no dataset is fully VALIDATED: every one carries documented caveats |
| Automated tests | 26 passed / 26 | reports/test_results.txt |

## Skipped and incomplete

| Item | Status | Reason |
|---|---|---|
| raw/rems/SOL00010/RME_398334213RMD00100000000_______PA.LBL | INCOMPLETE | Referenced file missing: Data file RME_398334213RMD00100000000_______PA.TAB not found near /home/claude/DHRUVION_DATA/ra |

| ID | Dataset not acquired | Reason |
|---|---|---|
| C01 | Existing local DHRUVION MOLA elevation, slope and roughness GeoTIFFs | Files not supplied to this environment; nothing to validate |
| C03 | MOLA Mission Experiment Gridded Data Records (MEGDR) | Not selected for download in this run (duplicate, deferred or no plan entry): Skip unless C02 is unavailable ( |
| C04 | HRSC and MOLA blended global DEM, 200 m/px, v2 (USGS) | Not selected for download in this run (duplicate, deferred or no plan entry): Optional upgrade over C02: AOI w |
| C06 | NASA Mars Trek layer Gale_CTX_BlockAdj_dd | Not selected for download in this run (duplicate, deferred or no plan entry): Frontend alternative to C05; ins |
| C07 | MRO CTX Experiment Data Records over Gale (via ODE) | Not selected for download in this run (duplicate, deferred or no plan entry): Fallback only. ODE REST paramete |
| C08 | USGS analysis-ready CTX DTMs (STAC catalogue) | Download NOT_ATTEMPTED: Entry disabled: exact product URL not confirmed against the authoritative archive |
| C09 | HiRISE DTMs and orthoimages over Gale | Not selected for download in this run (duplicate, deferred or no plan entry): Only if rover-scale terrain is r |
| C10 | MSL Gale Merged Orthophoto Mosaic and Merged DEM (Calef & Parker, USGS) | Not selected for download in this run (duplicate, deferred or no plan entry): High value for rover-scale route |
| C12 | Curiosity REMS ENVRDR (environmental RDR) | Not selected for download in this run (duplicate, deferred or no plan entry): Use only if MODRDR lacks a neede |
| C13 | Curiosity REMS EDR (raw) | Not selected for download in this run (duplicate, deferred or no plan entry): Skip. |
| C15 | Curiosity RAD EDR (raw binary) | Not selected for download in this run (duplicate, deferred or no plan entry): Skip - use C14. |
| C16 | THEMIS thermal data over Gale | Not selected for download in this run (duplicate, deferred or no plan entry): Deferred. |

## Outputs generated

Phase 4 produced these outputs:
- **Terrain:** elevation, slope, roughness and coverage GeoTIFFs, four PNG overlays, overlay metadata and provenance.
- **CTX:** an AOI clip, a PNG overlay, overlay metadata and provenance.
- **REMS:** clean observations (18,480 rows), per-sol and per-session summaries, a missing-value report, trends and provenance.
- **RAD:** clean observations (94 rows, 47 observations x 2 detectors), per-sol summaries, trends and provenance.

The reports cover Phases 1–4 (Phase 1 with an addendum), and the metadata comprises the catalogs, manifests, validation results, column dictionaries and logs.

## Scripts

| Script | Lines |
|---|---|
| scripts/dhruvion_common.py | 327 |
| scripts/00_inventory_workspace.py | 124 |
| scripts/00_check_source_access.py | 107 |
| scripts/01_discover_ode_products.py | 169 |
| scripts/02_download_datasets.py | 330 |
| scripts/02b_ingest_user_files.py | 90 |
| scripts/03_validate_rasters.py | 320 |
| scripts/04_validate_pds_tables.py | 212 |
| scripts/pds3_table.py | 324 |
| scripts/rad_rdr.py | 178 |
| scripts/terrain_math.py | 267 |
| scripts/05_process_terrain.py | 264 |
| scripts/06_process_ctx.py | 174 |
| scripts/rover_tables.py | 346 |
| scripts/07_process_rems.py | 81 |
| scripts/08_process_rad.py | 166 |
| scripts/run_step4.py | 105 |
| scripts/09_build_catalogs.py | 222 |
| scripts/10_package_and_verify.py | 205 |
| scripts/crop_for_upload.py | 128 |
| scripts/run_pipeline.sh | 17 |
| scripts/tests/test_pipeline.py | 612 |

## Tests performed

The 26 automated tests cover terrain maths (analytic planes, distortion correction, NoData), the validators, the command-line processors, PDS3 parsing, REMS/RAD rules (documented sentinel, circular statistics, quality rules, detector separation), planetocentric conversion, the downloader over local HTTP, the catalog builder, and packaging safety. Three of them run against the real archive files: RAD label-versus-text agreement, REMS label structure, and the CTX CRS latitude. Further checks:
- **Data checks:** the REMS file sizes match their labels, the MOLA source size matches the USGS product page, and 94 of 94 RAD values agree between the label offsets and the text sections.
- **Visual check:** MOLA 1 km contours were overlaid on the CTX image.
- **Package checks:** a CRC test, a SHA-256 check of every member, and a test run from an extracted copy.

## Integrity checks

| Check | Result |
|---|---|
| All original files exist | Yes - 36 files in raw/, SHA-256 in download_manifest.json |
| All processed files exist and open | Yes - re-opened after writing; raster grids re-checked against inputs |
| Raster CRS, resolution and bounds documented | Yes - validation_rasters.json, provenance JSON, README |
| REMS/RAD columns and units documented | Yes - from labels; metadata/column_dictionaries/ |
| Missing values never converted to zero | Yes - -999 (REMS SIS 3.2), UNK, NULL and N/A all become NaN/null; tested |
| No fabricated measurements | Yes - every value comes from a received archive file |
| Every dataset has source provenance | Yes - URL, evidence level and SHA-256 per file |
| Every processed output has a documented method | Yes - GeoTIFF tags, provenance JSON, phase 4 report |
| Credentials / application code in package | None |

## Known limitations

1. **Small, reduced sample.** REMS covers 2 sols and RAD 3 sols, and the CTX copy is averaged to ~50 m. The higher-resolution Gale DEM (1 m) was not acquired.
2. **Assistant-prepared column maps.** The REMS and RAD maps were prepared by the assistant from the labels, FMT files and SIS; independent review is recommended.
3. **REMS wind is effectively unavailable** in these sols.
4. **RAD placeholders.** The RAD QC and rover-position fields are placeholders.
5. **Scale.** Terrain derivatives are at the 463 m baseline.
6. **CTX coverage gap.** The CTX copy stops at −6.92 in the south and −4.00 in the north.

## Not included in the package

The full source files are on the user's computer (D:\datanasa):
- MOLA global mosaic: 2,125,771,142 bytes, SHA-256 `38a4eb0b...`, too large.
- CTX tile zip: 1,774,557,393 bytes, SHA-256 `e7021d4e...`, too large.

The upload zip itself is not included; its contents are ingested, and its duplicate label is recorded in the manifest. The two planning documents are not datasets, and no application code is included. Exclusions are also listed in `metadata/EXCLUDED_FROM_PACKAGE.json`.
