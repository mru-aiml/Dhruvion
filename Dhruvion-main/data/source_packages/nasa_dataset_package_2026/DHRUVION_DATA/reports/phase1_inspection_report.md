# DHRUVION Phase 1 - Project Inspection and Dataset Discovery Report

Generated 2026-11-14T17:45:21+00:00 in the Claude build environment. Target: Gale Crater and Aeolis Mons (Mount Sharp), centre latitude -5.4 deg, longitude 137.8 deg E. Discovery area of interest (AOI): latitude -7.0 to -3.8, longitude 136.2 to 139.4 E (centre +/- 1.6 deg, enclosing the ~154 km crater with margin; configurable in every script with `--aoi`).

## 1. Summary

The working environment contains no Mars, NASA or USGS data of any kind, and the existing MOLA elevation, slope and roughness GeoTIFFs described in the DHRUVION planning documents were not supplied. None of the 18 authoritative endpoints (ODE, USGS Astrogeology, the PDS nodes, NMSU Atmospheres, Mars Trek, Murray Lab, HiRISE) could be reached: every one failed at DNS resolution because the build sandbox only permits an allow-list of domains. Sixteen candidate datasets were therefore catalogued from two kinds of evidence, the user's planning documents and the assistant's prior knowledge, and every field that could not be confirmed live is marked UNVERIFIED. No coverage, file size or product ID was confirmed against a live archive.

## 2. Working directory and folder structure

The working directory was `/home/claude`. Before this project it contained only hidden tool configuration and cache folders (`.cache`, `.config`, `.local`, `.npm`, `.npm-global`, `.npmrc`, `.wget-hsts`); there was no DHRUVION repository, frontend or backend code. The package structure created for this work is:

```
DHRUVION_DATA/
  raw/{terrain,ctx,rems,rad}/        original downloads (empty - see Phase 2)
  processed/{terrain,ctx,rems,rad}/  derived outputs (empty - see Phase 4)
  scripts/                           pipeline scripts, config/, tests/
  metadata/                          catalogs, manifests, logs, evidence
  reports/                           phase reports and test results
  documentation/                     README, TEAM_HANDOVER, FINAL_REPORT
```

## 3. Uploaded files

Two files were uploaded. Both are DHRUVION planning documents (advice text about which sources to use), not datasets.

| File | Size (bytes) | MD5 | Content |
|---|---|---|---|
| Dhruvion___NASA_Space_Apps_Challenge_2026.docx | 17,390,278 | ca4cb323081980f8aa788a3361fe6c69 | Planning text plus 11 embedded PNG illustrations taken from web pages (not scientific data) |
| Dhruvion___NASA_Space_Apps_Challenge_2026__1_.docx | 231,997 | e7bf5817f3cb9cfe16611618c0910ecf | Planning text (terrain/REMS/RAD workflow advice) |

The two files are not byte duplicates (different MD5) but their content overlaps heavily. Both note that the first two source links originally shared by the team were the same ODE link, so ODE counts as one source.

## 4. Existing datasets found

A full filesystem scan (all mounted volumes, matching .tif/.tiff/.img/.lbl/.cub/.jp2 and names containing MOLA, HiRISE, REMS, CTX, DTM or Gale) found no Mars data. The only matches were unrelated library test images (scikit-image) and software files. The reusable inventory script `scripts/00_inventory_workspace.py` reproduced this result (`metadata/workspace_inventory.json`): 0 files with Mars-product name tags in `/home/claude` or the uploads folder.

| Requested item | Found | Evidence |
|---|---|---|
| MOLA elevation GeoTIFF | No | Filesystem scan + inventory; not among uploads |
| Existing slope / roughness rasters | No | Referenced in planning documents only |
| CTX imagery | No | Scan |
| CTX-derived DTM | No | Scan |
| HiRISE data | No | Scan |
| REMS data | No | Scan |
| RAD data | No | Scan |

Action for the team: run `python scripts/00_inventory_workspace.py --scan <DHRUVION repo>` and `python scripts/03_validate_rasters.py --rasters <your MOLA/slope/roughness tifs>` on the machine that holds the existing files, or upload them.

## 5. Python environment and libraries

The interpreter is `/usr/bin/python3` (Python 3.12.3). There is no conda installation and no project virtual environment; the only virtual environment present (`/opt/pipx/shared`) belongs to the system's pipx tooling. rasterio, pyproj, pvl and pytest were missing at the start and were installed from PyPI, which is reachable. rasterio's bundled GDAL replaces the absent `osgeo` bindings. PROJ ships the IAU 2015 Mars definitions (IAU_2015:49900 geographic sphere R = 3 396 190 m; 49910-49912 equirectangular variants), which were verified.

| Library | Version |
|---|---|
| numpy | 2.5.4 |
| pandas | 3.0.6 |
| scipy | 1.18.1 |
| rasterio | 1.5.2 |
| pyproj | 3.8.0 |
| pvl | 1.3.2 |
| matplotlib | 3.11.2 |
| PIL | 13.0.0 |
| requests | 2.34.2 |
| geopandas | not installed |
| shapely | not installed |
| xarray | not installed |
| rioxarray | not installed |
| pds4_tools | not installed |
| planetaryimage | not installed |
| astropy | not installed |
| skimage | 0.26.0 |
| pytest | 9.2.0 |
| gdal_via_rasterio | 3.12.2 |
| proj | 9.8.1 |

## 6. Disk space and resources

Free space on the working volume: about 10.5 GB (root filesystem 252 GB, 8.0 GB used, capped quota). Memory 3.9 GiB, 1 CPU. This is ample for the recommended Gale subsets (a MOLA AOI window is estimated at ~0.3 MB) but not for whole global mosaics (MOLA ~2 GB, HRSC-MOLA blend ~11 GB, both UNVERIFIED sizes). The processing code works in row blocks so large DTMs do not need to fit in memory.

## 7. Authoritative source research - reachability evidence

`scripts/00_check_source_access.py` probed every source. The control check (`metadata/network_control_check.txt`) shows PyPI and GitHub return HTTP 200/301, so the failure is a domain allow-list in the build sandbox, not a general outage or a problem with the archives. An organization owner can extend the sandbox network settings; otherwise run the scripts on a machine with normal internet access.

| Endpoint | Host | DNS | HTTP | URL evidence | Error |
|---|---|---|---|---|---|
| ODE_PORTAL | ode.rsl.wustl.edu | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| ODE_REST | oderest.rsl.wustl.edu | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| USGS_ASTRO_DATA | www.usgs.gov | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| USGS_ARD | www.usgs.gov | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| USGS_STAC | stac.astrogeology.usgs.gov | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| USGS_MOLA_463M | planetarymaps.usgs.gov | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| USGS_HRSC_MOLA_200M | planetarymaps.usgs.gov | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| PDS_GEO_MOLA | pds-geosciences.wustl.edu | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| MURRAY_LAB_CTX | murray-lab.caltech.edu | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| MARS_TREK | trek.nasa.gov | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| HIRISE_DTM | www.uahirise.org | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| PDS_IMG | pds-imaging.jpl.nasa.gov | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| NMSU_REMS_PAGE | pdsatmospheres.nmsu.edu | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| NMSU_REMS_PAGE_ALT | atmos.nmsu.edu | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| PDS_DSVIEW_RAD_RDR | pds.nasa.gov | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| PDS_DSVIEW_RAD_EDR | pds.nasa.gov | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |
| PDS_GEO_MSL_RAD | pds-geosciences.wustl.edu | NO | - | prior_knowledge_unverified | DNS resolution failed: [Errno -2] Name or service not known |
| AN_MSL | an.rsl.wustl.edu | NO | - | user_document | DNS resolution failed: [Errno -2] Name or service not known |

An alternative authoritative route was investigated: GitHub (reachable) was searched for repositories of the NASA-PDS (110 repos) and DOI-USGS (156 repos) organizations and for REMS, RAD and Gale DTM data. These organizations publish software (validators, ISIS3, information models), not Gale datasets, and the data searches returned 0 repositories. Third-party copies were not used because they are not authoritative and could not be checksum-verified against the source.

## 8. Candidate products

Full details (coverage, units, CRS, limitations, duplicates) are in `metadata/dataset_discovery_catalog.json` and `.csv`. Evidence levels: USER_DOCUMENT = stated in the user's planning documents; PRIOR_KNOWLEDGE_UNVERIFIED = recalled by the assistant and not confirmed live. Where a product ID could not be stated with confidence, it is left as UNKNOWN rather than guessed.

| ID | Dataset | Product ID | Format | Resolution | Units | Level | Size | Evidence |
|---|---|---|---|---|---|---|---|---|
| C01 | Existing local DHRUVION MOLA elevation, slope and roughness GeoTIFFs | UNKNOWN - files not provided | GeoTIFF (per user document) | UNKNOWN | UNKNOWN - must be confirmed | Derived | UNKNOWN | USER_DOCUMENT + LOCAL_INSPECTION (not found) |
| C02 | MGS MOLA DEM global mosaic, 463 m/px (USGS Astrogeology) | Mars_MGS_MOLA_DEM_mosaic_global_463m | GeoTIFF, signed 16-bit integer (UNVERIFIED) | ~463 m/px (128 px/deg at equator) (UNVERIFIED) | metres, elevation relative to the MOLA areoid (UNVERIFIED) | Derived gridded product (interpolated from MOLA altimetry) | ~2.1 GB full file (estimate = 46080 x 23040 px x 2 bytes; dimensions UNVERIFIED). Gale AOI window ~410 x 410 px ~0.3 MB (computed estimate). | PRIOR_KNOWLEDGE_UNVERIFIED |
| C03 | MOLA Mission Experiment Gridded Data Records (MEGDR) | 128 px/deg topography tile covering Gale - tile name UNVERIFIED | PDS3 raw image (.IMG) + label (.LBL) (UNVERIFIED) | Up to 128 px/deg (~463 m) (UNVERIFIED) | metres (topography relative to areoid) (UNVERIFIED) | PDS Level 3 gridded | UNKNOWN | PRIOR_KNOWLEDGE_UNVERIFIED |
| C04 | HRSC and MOLA blended global DEM, 200 m/px, v2 (USGS) | Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2 | GeoTIFF (UNVERIFIED) | 200 m/px (UNVERIFIED) | metres relative to areoid (UNVERIFIED) | Derived (blended) | ~11 GB full file (UNVERIFIED) | PRIOR_KNOWLEDGE_UNVERIFIED |
| C05 | Global CTX Mosaic of Mars (Caltech Murray Lab) - Gale tile(s) | Tile(s) covering 136.2-139.4 E, 7.0-3.8 S - names UNVERIFIED | Georeferenced 8-bit raster tiles in ZIP archives (UNVERIFIED) | ~5 m/px (UNVERIFIED) | 8-bit DN (not radiometrically calibrated) (UNVERIFIED) | Derived mosaic (not a PDS archive product) | UNKNOWN | PRIOR_KNOWLEDGE_UNVERIFIED |
| C06 | NASA Mars Trek layer Gale_CTX_BlockAdj_dd | Gale_CTX_BlockAdj_dd | WMTS map tiles (service, not a single file) | UNKNOWN | Display imagery | Block-adjusted mosaic (per layer name; method UNVERIFIED) | N/A (tiled service) | USER_DOCUMENT |
| C07 | MRO CTX Experiment Data Records over Gale (via ODE) | To be listed by 01_discover_ode_products.py (MRO:CTX:EDR over AOI) | PDS3 .IMG with attached label (UNVERIFIED) | ~6 m/px, ~30 km swath (UNVERIFIED) | Raw DN (EDR) | EDR (raw) | Per product, reported by ODE | USER_DOCUMENT (portal) + PRIOR_KNOWLEDGE_UNVERIFIED (IDs) |
| C08 | USGS analysis-ready CTX DTMs (STAC catalogue) | UNKNOWN - query STAC for AOI intersection | Cloud-optimised GeoTIFF (UNVERIFIED) | UNKNOWN (CTX DTMs are typically tens of m/px) (UNVERIFIED) | metres (UNVERIFIED) | Derived (stereo photogrammetry) | UNKNOWN | USER_DOCUMENT + PRIOR_KNOWLEDGE_UNVERIFIED |
| C09 | HiRISE DTMs and orthoimages over Gale | UNKNOWN - specific DTEEC IDs not verifiable offline | PDS IMG DTM + JP2 orthoimages (UNVERIFIED) | ~1 m/px DTM, 0.25-0.5 m/px ortho (UNVERIFIED) | metres (UNVERIFIED) | Derived (stereo photogrammetry) | Typically hundreds of MB to GB per product (UNVERIFIED) | PRIOR_KNOWLEDGE_UNVERIFIED |
| C10 | MSL Gale Merged Orthophoto Mosaic and Merged DEM (Calef & Parker, USGS) | UNKNOWN exact file names | GeoTIFF (UNVERIFIED) | ~0.25 m ortho, ~1 m DEM (UNVERIFIED) | metres (DEM) (UNVERIFIED) | Derived merged mosaic | Multi-GB (UNVERIFIED) | PRIOR_KNOWLEDGE_UNVERIFIED |
| C11 | Curiosity REMS MODRDR (processed environmental tables) | Per-sol products - IDs UNVERIFIED | PDS3 ASCII tables + labels (structure to be read from labels) | ~1 Hz within observation sessions (per user document) | As declared in each PDS label (not assumed) | Reduced Data Record (processed) | UNKNOWN | USER_DOCUMENT |
| C12 | Curiosity REMS ENVRDR (environmental RDR) | UNVERIFIED | PDS3 ASCII tables + labels | As C11 | From labels | Reduced Data Record | UNKNOWN | USER_DOCUMENT |
| C13 | Curiosity REMS EDR (raw) | - | Raw instrument data | N/A | Raw | EDR (raw) | UNKNOWN | USER_DOCUMENT |
| C14 | Curiosity RAD calibrated RDR | Per-sol products - IDs UNVERIFIED | ASCII text tables + PDS3 labels + format files (per user document) | UNKNOWN cadence | As declared in labels/format files (not assumed) | Calibrated RDR (PDS level 3 per ID) | UNKNOWN | USER_DOCUMENT |
| C15 | Curiosity RAD EDR (raw binary) | - | Binary + PDS label | N/A | Raw | EDR (raw) | UNKNOWN | USER_DOCUMENT |
| C16 | THEMIS thermal data over Gale | - | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | USER_DOCUMENT |

## 9. Duplicates and overlaps (avoid unnecessary downloads)

C02 (USGS MOLA mosaic) and C03 (PDS MEGDR) carry the same MOLA measurements, so only one is needed, and neither is needed if the existing local files (C01) validate. C04 (HRSC-MOLA blend) contains MOLA and is an optional upgrade, not an addition. C05, C06 and C07 are three routes to the same CTX images; choose one (C05 for analysis, C06 if the frontend streams tiles). C08, C09 and C10 overlap in the rover operations area. C11, C12 and C13 are the same REMS observations at different processing levels; C14 and C15 are the same RAD observations at calibrated and raw levels.

## 10. Recommendation - download order

| Order | Candidate | Action | Why |
|---|---|---|---|
| 1 | C01, else C02 | Validate existing local MOLA files; if missing/invalid, fetch only the Gale AOI window of the USGS 463 m mosaic (plan item MOLA_463M_GALE_SUBSET) | Terrain is the core of route planning; tiny download |
| 2 | C05 | One Murray Lab CTX tile covering Gale (confirm tile name) | Georeferenced regional imagery without ISIS3 |
| 3 | C08 (or C10) | One CTX DTM intersecting Gale from USGS STAC; C10 merged HiRISE DEM if rover-scale terrain is needed | Higher-resolution terrain |
| 4 | C11 | A few sols of REMS MODRDR + labels + SIS/FMT | Environmental dashboard |
| 5 | C14 | A few sols of RAD RDR + labels + FMT + SIS | Radiation chart |
| 6 | C09 | HiRISE only if required | Small footprints, large files |


## 11. Addendum - after user web research and manual downloads (2026-11-14)

The sections above record the state of Step 1 inside the build environment. Afterwards the user ran web searches (ChatGPT and Gemini) with a structured prompt and downloaded the recommended files manually. That evidence corrected four assumptions in this report, all now fixed in the scripts and in `metadata/dataset_discovery_catalog.*`:
- The MSL RAD calibrated RDR is archived at the **PDS Planetary Plasma Interactions (PPI) Node** (`https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/`), not the Geosciences Node.
- The ODE REST interface uses `query=products` (plural) and `loc=b` for bounding-box intersection (ODE REST manual v2.1.6).
- The HRSC-MOLA blend lives under `mosaic/Mars/HRSC_MOLA_Blend/`.
- Murray Lab tiles are named from their lower-left corner; the tile containing the Gale centre is `E136_N-08`.

Candidates C02, C05, C11 and C14 are now verified on received files. The candidates marked USER_RESEARCH are documented from the research results without download, and anything still marked UNVERIFIED rests on the assistant's prior knowledge.
