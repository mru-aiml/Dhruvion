# DHRUVION Phase 3 - Scientific Validation Report

Generated 2026-11-14T19:46:18+00:00 from `metadata/validation_rasters.json`, `metadata/validation_pds_tables.json`, `metadata/validated_dataset_catalog.json` and `metadata/validation_summary.csv`. Per-product column dictionaries are in `metadata/column_dictionaries/`.

## 1. Result

Dataset status counts: {'NOT AVAILABLE': 12, 'VALIDATED WITH LIMITATIONS': 4}. **Approved for processing (12 files):**

- `raw/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.tif`
- `raw/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif`
- `raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.LBL`
- `raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.TAB`
- `raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.LBL`
- `raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.TAB`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.LBL`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.TXT`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.LBL`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.TXT`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.LBL`
- `raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.TXT`

**Rejected:** 

| File | Status | Reason |
|---|---|---|
| raw/rems/SOL00010/RME_398334213RMD00100000000_______PA.LBL | INCOMPLETE | Referenced file missing: Data file RME_398334213RMD00100000000_______PA.TAB not found near /home/claude/DHRUVION_DATA/raw/rems/SOL00010/RME_398334213R |

## 2. Terrain and CTX rasters

| File | Status | CRS | Size / type | Resolution | Bounds (planetocentric) | NoData | Units | AOI valid coverage | Gale centre | Valid px |
|---|---|---|---|---|---|---|---|---|---|---|
| raw/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif | VALIDATED WITH LIMITATIONS | Mars_2015_Ocentric_Equirectangular_clon_0 | 3794 x 3460, uint8 | 50.00 m (ground dx 50-50 m) | lon 136.200..139.400 E, lat -6.919..-4.000 | 0.0 | 8-bit DN (display imagery) (source documentation (download manifest)) | 87.8% | yes | 13127240/13127240 |
| raw/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.tif | VALIDATED WITH LIMITATIONS | Equirectangular Mars | 410 x 410, int16 | 463.09 m (ground dx 460-462 m) | lon 136.198..139.401 E, lat -7.000..-3.797 | -32768.0 | metre (source documentation (download manifest)) | 100.0% | yes | 168100/168100 |

**Alignment:** MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif vs Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.tif: **NEAR_EQUIVALENT_CRS_DIFFERENT_GRID** (max coordinate offset 12.1 m over the AOI). The MOLA file uses a sphere; the Murray Lab CTX file declares an ellipsoid (a = 3,396,190 m, b = 3,376,200 m) named "Ocentric". PROJ reports geodetic (planetographic) latitude for that ellipsoid, which near Gale differs from planetocentric latitude by about 0.05 deg (~3 km). All scripts now convert explicitly to **planetocentric** latitude (`planetocentric_lonlat` in `dhruvion_common.py`), and equivalence is tested numerically: the two CRSs place the same lon/lat within 12.1 m, which is under a quarter of a CTX pixel and 3% of a MOLA pixel. The grids differ (463 m versus 50 m), so the layers must be combined by coordinates, never by array index. A visual overlay of MOLA 1 km contours on the CTX image showed no visible misregistration.

**Limitations:** neither file stores its units. MOLA units (metres, elevation above the areoid) come from the USGS product page and CTX units (8-bit DN) from the Murray Lab product description; both are recorded in the manifest. The CTX copy covers 87.8% of the AOI sample grid: the tile ends at -4.0 and the user's crop ended at -6.92 planetocentric, because the first crop script version treated the AOI as planetographic (since fixed). It is also a 10x averaged display copy.

## 3. REMS (MODRDR)

| Label | Product | Status | Structure | Temporal coverage (LMST) | Sentinels | Quality fields | Reasons / limitations |
|---|---|---|---|---|---|---|---|
| raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.LBL | REMS MODRDR | VALIDATED WITH LIMITATIONS | 5520 rows x 40 cols; size check OK | 00009M12:30:37.759 .. 00009M23:05:57.172 | 22 columns contain -999 | WS_CONFIDENCE_LEVEL, BRIGHTNESS_TEMP_LONG_TERM_UNCERTAINTY, BRIGHTNESS_TEMP_SHORT_TERM_UNCERTAINTY... | REMS_SCIENCE_TABLE: 22 numeric column(s) contain values such as -999 that the label does not declare as missing - treat them as missing only where the SIS documents it |
| raw/rems/SOL00010/RME_398334213RMD00100000000_______PA.LBL | REMS MODRDR | INCOMPLETE | - rows x - cols; size check - | - .. - | 0 columns contain -999 | - | Referenced file missing: Data file RME_398334213RMD00100000000_______PA.TAB not found near /home/claude/DHRUVION_DATA/raw/rems/SOL00010/RME_398334213RMD00100000000_______PA.LBL |
| raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.LBL | REMS MODRDR | VALIDATED WITH LIMITATIONS | 12960 rows x 40 cols; size check OK | 00011M00:00:38.572 .. 00011M23:05:55.380 | 22 columns contain -999 | WS_CONFIDENCE_LEVEL, BRIGHTNESS_TEMP_LONG_TERM_UNCERTAINTY, BRIGHTNESS_TEMP_SHORT_TERM_UNCERTAINTY... | REMS_SCIENCE_TABLE: 22 numeric column(s) contain values such as -999 that the label does not declare as missing - treat them as missing only where the SIS documents it |

- **Columns and units.** These were read from `MODRDR6.FMT` (40 columns); all physical columns carry a UNIT: KELVIN, PASCAL, METERS/SECOND, DEGREE, %, W/m**2, ppm.
- **Missing and invalid values.** These are **-999**, per REMS RDR SIS section 3.2 (Issue 9): "Data may be set to -999 if their value is not known… stored as -999.00 or as -9.990E+02". The FMT does not declare this as a MISSING_CONSTANT, so the validator flags it and the processing applies it from the SIS, with the citation recorded in `scripts/config/rems_column_map.json`. No UNK or NULL tokens occur.
- **Confidence levels.** These are per-sensor strings of '1' (optimal), '0' (not optimal) and 'X' (unknown) (SIS section 3.1.6), for example `AMBIENT_TEMP_CONFIDENCE_LEVEL` and `PS_CONFIDENCE_LEVEL`.
- **Archive quirk.** The label DESCRIPTION for `HORIZONTAL_WIND_SPEED` repeats the wind-direction text; the column name and unit identify it as speed.
- **Sol 10** is INCOMPLETE because its .TAB file was not received.

## 4. RAD (calibrated RDR)

| Label | Product | Status | Structure | Temporal coverage | Units | QC | Reasons / limitations |
|---|---|---|---|---|---|---|---|
| raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.LBL | RAD RDR | VALIDATED WITH LIMITATIONS | 14 observations, 28 dose elements; label-vs-text 28/28 agree | sol [1]; UTC 2012-220 02:25:43 .. 2012-220 06:03:10 | microGray / Hour | QC values {'00000000': 14} (placeholder) | QC and ROVER_LAT/LON/ELEV are placeholders per RAD RDR SIS v3.2 sec. 4.2.1.2 - not used as quality flags or location; Only TOT_DOSE_B/E dose-rate elements are parsed; counters, histograms, LET arrays  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.LBL | RAD RDR | VALIDATED WITH LIMITATIONS | 20 observations, 40 dose elements; label-vs-text 40/40 agree | sol [2]; UTC 2012-221 02:47:54 .. 2012-221 08:12:32 | microGray / Hour | QC values {'00000000': 20} (placeholder) | QC and ROVER_LAT/LON/ELEV are placeholders per RAD RDR SIS v3.2 sec. 4.2.1.2 - not used as quality flags or location; Only TOT_DOSE_B/E dose-rate elements are parsed; counters, histograms, LET arrays  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.LBL | RAD RDR | VALIDATED WITH LIMITATIONS | 13 observations, 26 dose elements; label-vs-text 26/26 agree | sol [3]; UTC 2012-222 04:26:10 .. 2012-222 07:56:10 | microGray / Hour | QC values {'00000000': 13} (placeholder) | QC and ROVER_LAT/LON/ELEV are placeholders per RAD RDR SIS v3.2 sec. 4.2.1.2 - not used as quality flags or location; Only TOT_DOSE_B/E dose-rate elements are parsed; counters, histograms, LET arrays  |

- **Documented dose measurement.** For each observation `NN`, the labels define `OBSNN_TOT_DOSE_B_ELEMENT` and `OBSNN_TOT_DOSE_E_ELEMENT` with UNIT "microGray / Hour". RAD RDR SIS v3.2 section 4.2.1.6 confirms "the total dose for the B and E detectors… in microGray / hour". Detector B is a silicon detector; E is the BC-432 plastic scintillator (SIS section 3). Only these two elements are treated as dose rates.
- **Not parsed.** Counters, particle histograms, LET arrays and PHA tables are present in the files but are not dose rates and were not parsed.
- **Placeholder fields.** `QC` and `ROVER_LAT/LON/ELEV` are placeholders ("not yet implemented", SIS section 4.2.1.2): every QC value is `00000000` and every position is 0. They are carried through but never used as quality flags or as a location.

## 5. All catalogued datasets

| ID | Dataset | Status | Approved files / reason |
|---|---|---|---|
| C01 | Existing local DHRUVION MOLA elevation, slope and roughness GeoTIFFs | NOT AVAILABLE | Files not supplied to this environment; nothing to validate |
| C02 | MGS MOLA DEM global mosaic, 463 m/px (USGS Astrogeology) | VALIDATED WITH LIMITATIONS | raw/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.tif |
| C03 | MOLA Mission Experiment Gridded Data Records (MEGDR) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Skip unless C02 is una |
| C04 | HRSC and MOLA blended global DEM, 200 m/px, v2 (USGS) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Optional upgrade over  |
| C05 | Global CTX Mosaic of Mars (Caltech Murray Lab) - Gale tile(s) | VALIDATED WITH LIMITATIONS | raw/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif |
| C06 | NASA Mars Trek layer Gale_CTX_BlockAdj_dd | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Frontend alternative t |
| C07 | MRO CTX Experiment Data Records over Gale (via ODE) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Fallback only. ODE RES |
| C08 | USGS analysis-ready CTX DTMs (STAC catalogue) | NOT AVAILABLE | Download NOT_ATTEMPTED: Entry disabled: exact product URL not confirmed against the authoritative ar |
| C09 | HiRISE DTMs and orthoimages over Gale | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Only if rover-scale te |
| C10 | MSL Gale Merged Orthophoto Mosaic and Merged DEM (Calef & Parker, USGS) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): High value for rover-s |
| C11 | Curiosity REMS MODRDR (processed environmental tables) | VALIDATED WITH LIMITATIONS | raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.LBL, raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.TAB, raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.LBL, raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.TAB |
| C12 | Curiosity REMS ENVRDR (environmental RDR) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Use only if MODRDR lac |
| C13 | Curiosity REMS EDR (raw) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Skip. |
| C14 | Curiosity RAD calibrated RDR | VALIDATED WITH LIMITATIONS | raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.LBL, raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.TXT, raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.LBL, raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.TXT, raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.LBL, raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.TXT |
| C15 | Curiosity RAD EDR (raw binary) | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Skip - use C14. |
| C16 | THEMIS thermal data over Gale | NOT AVAILABLE | Not selected for download in this run (duplicate, deferred or no plan entry): Deferred. |

