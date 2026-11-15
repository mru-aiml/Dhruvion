# DHRUVION Phase 4 - Processing Report

Generated 2026-11-14T19:46:18+00:00. Inputs: only the Step 3-approved files. Orchestrator: `scripts/run_step4.py`; log: `metadata/step4_run_log.json` (4 processed, 12 skipped, 0 failed). Raw files were never modified; all outputs are in `processed/`.

## 1. Run log

| Dataset | Action | Script | Reason |
|---|---|---|---|
| C01 | SKIPPED |  | Step 3 status NOT AVAILABLE: Files not supplied to this environment; nothing to validate |
| C03 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C04 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C06 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C07 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C08 | SKIPPED |  | Step 3 status NOT AVAILABLE: Download NOT_ATTEMPTED: Entry disabled: exact product URL not |
| C09 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C10 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C12 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C13 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C15 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C16 | SKIPPED |  | Step 3 status NOT AVAILABLE: Not selected for download in this run (duplicate, deferred or |
| C02 | PROCESSED | 05_process_terrain.py |  |
| C05 | PROCESSED | 06_process_ctx.py |  |
| rems | PROCESSED | 07_process_rems.py |  |
| rad | PROCESSED | 08_process_rad.py |  |

## 2. Terrain (MOLA 463 m, Gale AOI) - `05_process_terrain.py`

The input is 410 x 410 px, Int16, NoData -32768 (no NoData pixels in the AOI), with elevation units in metres. True ground spacing (geodesic, Mars sphere) is dx 459.6-462.1 m and dy 463.1 m; degrees were never used as metres.

**Methods.**
- **Slope:** Horn (1981).
- **Roughness:** Terrain Ruggedness Index (Riley et al. 1999), the square root of the sum of squared elevation differences to the 8 neighbours, in metres.
- **NoData and edges:** both produce NaN.
- **Coverage mask:** 0 = no data, 1 = all valid, 2 = elevation only. The 1,636 class-2 pixels are the one-pixel raster border.

| Layer | Valid px | Min | Max | Mean | Median | p99 |
|---|---|---|---|---|---|---|
| elevation_m | 168100 | -4607.00 | 1347.00 | -1850.27 | -1958.00 | 545.00 |
| slope_deg | 166464 | 0.00 | 38.29 | 5.44 | 4.08 | 21.58 |
| roughness_m | 166464 | 0.00 | 889.83 | 114.03 | 86.23 | 454.36 |

**Plausibility.** The elevation range of -4,607 m (crater floor) to +1,347 m (upper Aeolis Mons) relative to the areoid is consistent with Gale. The slope and roughness maxima sit on the crater rim and the flanks of the mound, as the visual check confirmed. Slope and roughness describe relief at the ~463 m pixel baseline; they understate local, rover-scale slopes and are not rover-scale hazard maps.

## 3. CTX imagery - `06_process_ctx.py`

The script clipped the approved copy to the AOI, leaving pixel values unchanged at 3794 x 3460 px and ~50 m/px. NoData 0 became transparent in the PNG, and 8-bit DN were used as stored with no stretch. Overlay bounds (planetocentric): `[[-6.9187, 136.1999], [-4.0, 139.4]]`. Alignment with the MOLA DEM: **NEAR_EQUIVALENT_CRS_DIFFERENT_GRID**, with a maximum coordinate offset of 12.078 m.

## 4. REMS - `07_process_rems.py`

The confirmed column map `scripts/config/rems_column_map.json` was built from the FMT descriptions and SIS sections 3.1.6 and 3.2; independent review by a team member is recommended.
- **Sol:** taken from `LMST`, format `SSSSSM...`.
- **Sessions:** a new session starts after a gap of more than 60 s in `TIMESTAMP` (REMS samples at ~1 Hz). Sessions found: {9: 12, 11: 25}.
- **Missing values:** -999 is excluded and counted in `rems_missing_values_report.csv`.
- **Wind direction:** summarised with circular statistics.
- **Quality filters:** each is reported beside the unfiltered values, never instead of them. `no_zeros` means no factor was reported non-optimal ('X', unknown, is allowed); `all_ones` means every factor was optimal.

| Sol | Measurement | Unit | Valid / rows | Mean (min .. max) | Valid with no_zeros | Valid with all_ones |
|---|---|---|---|---|---|---|
| 9 | air_temperature | KELVIN | 5280/5520 | 239.56 (206.90 .. 266.97) | 3384 | 0 |
| 9 | ground_temperature | KELVIN | 4620/5520 | 250.28 (185.89 .. 290.79) | 3880 | 3880 |
| 9 | pressure | PASCAL | 5220/5520 | 711.33 (690.64 .. 754.97) | 4680 | 4680 |
| 9 | horizontal_wind_speed | METERS/SECOND | 7/5520 | 8.39 (7.18 .. 10.07) | 0 | 0 |
| 9 | wind_direction | DEGREE | 9/5520 | circ. mean 58 deg | 0 | 0 |
| 9 | relative_humidity | % | 5111/5520 | 2.27 (0.00 .. 11.47) | 0 | 0 |
| 9 | uv_a | W/m**2 | 4200/5520 | 0.35 (0.00 .. 0.98) | 0 | 0 |
| 9 | uv_b | W/m**2 | 4200/5520 | 0.08 (0.00 .. 0.22) | 0 | 0 |
| 9 | uv_c | W/m**2 | 4200/5520 | 0.22 (0.00 .. 0.64) | 0 | 0 |
| 9 | uv_abc | W/m**2 | 4200/5520 | 1.09 (0.00 .. 2.83) | 0 | 0 |
| 9 | uv_d | W/m**2 | 4200/5520 | 0.07 (0.00 .. 0.23) | 0 | 0 |
| 9 | uv_e | W/m**2 | 4200/5520 | 0.31 (0.00 .. 0.96) | 0 | 0 |
| 11 | air_temperature | KELVIN | 12360/12960 | 234.81 (196.54 .. 273.26) | 6782 | 0 |
| 11 | ground_temperature | KELVIN | 10620/12960 | 245.77 (162.11 .. 281.86) | 8215 | 8215 |
| 11 | pressure | PASCAL | 12360/12960 | 724.06 (692.67 .. 779.53) | 12360 | 12360 |
| 11 | horizontal_wind_speed | METERS/SECOND | 25/12960 | 6.53 (4.31 .. 9.56) | 0 | 0 |
| 11 | wind_direction | DEGREE | 33/12960 | circ. mean 79 deg | 0 | 0 |
| 11 | relative_humidity | % | 12235/12960 | 5.02 (0.00 .. 31.41) | 0 | 0 |
| 11 | uv_a | W/m**2 | 8700/12960 | 0.81 (0.00 .. 9.20) | 0 | 0 |
| 11 | uv_b | W/m**2 | 8700/12960 | 0.31 (0.00 .. 3.79) | 0 | 0 |
| 11 | uv_c | W/m**2 | 8700/12960 | 0.25 (0.00 .. 2.13) | 0 | 0 |
| 11 | uv_abc | W/m**2 | 8700/12960 | 1.81 (0.00 .. 19.21) | 0 | 0 |
| 11 | uv_d | W/m**2 | 8700/12960 | 0.15 (0.00 .. 1.69) | 0 | 0 |
| 11 | uv_e | W/m**2 | 8700/12960 | 0.62 (0.00 .. 6.72) | 0 | 0 |

**Gaps and limitations.** Wind data are almost entirely missing: only 7 and 25 valid samples on these sols. Sol 10 is absent. All values are historical measurements at the rover's location, not a map, and are uncorrected for the rover's own thermal environment beyond what MODRDR already applies.

## 5. RAD - `08_process_rad.py`, `rad_rdr.py`

The confirmed map `scripts/config/rad_column_map.json` was built from the labels and SIS v3.2 section 4.2.1.6. The output is in long format, one row per observation per detector, so the detectors are never combined. Per-sol statistics are the **unweighted** mean, min, max, median and standard deviation of the observation dose rates; observation durations were not used. With only 3 sols, no trend was computed (the minimum is 5).

| Sol | Measurement | Detector | Unit | Observations | Mean | Min .. max | Std |
|---|---|---|---|---|---|---|---|
| 1 | dose_rate_B | B (silicon detector) | microGray / Hour | 14 | 8.925 | 7.253 .. 9.867 | 0.584 |
| 1 | dose_rate_E | E (BC-432 plastic scintillator) | microGray / Hour | 14 | 8.584 | 7.058 .. 8.936 | 0.459 |
| 2 | dose_rate_B | B (silicon detector) | microGray / Hour | 20 | 9.275 | 8.471 .. 10.518 | 0.556 |
| 2 | dose_rate_E | E (BC-432 plastic scintillator) | microGray / Hour | 20 | 8.520 | 7.840 .. 8.719 | 0.181 |
| 3 | dose_rate_B | B (silicon detector) | microGray / Hour | 13 | 8.829 | 8.315 .. 9.237 | 0.256 |
| 3 | dose_rate_E | E (BC-432 plastic scintillator) | microGray / Hour | 13 | 8.320 | 7.714 .. 8.641 | 0.241 |

## 6. Output files

| File | Size |
|---|---|
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_coverage.png | 1.3 kB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_coverage_mask.tif | 3.4 kB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_elevation.png | 0.14 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_elevation_m.tif | 0.21 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_overlay_metadata.json | 1.8 kB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_roughness.png | 0.30 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_roughness_tri_riley_m.tif | 0.54 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_slope.png | 0.34 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_slope_deg.tif | 0.54 MB |
| processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_terrain_provenance.json | 3.9 kB |
| processed/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__GaleAOI.png | 10.47 MB |
| processed/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__GaleAOI_clip.tif | 10.73 MB |
| processed/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__GaleAOI_overlay_metadata.json | 1.0 kB |
| processed/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__ctx_provenance.json | 1.8 kB |
| processed/rems/rems_missing_values_report.csv | 2.6 kB |
| processed/rems/rems_observations_clean.csv | 4.95 MB |
| processed/rems/rems_observations_clean.json | 23.22 MB |
| processed/rems/rems_processing_provenance.json | 2.7 kB |
| processed/rems/rems_session_summary.csv | 0.23 MB |
| processed/rems/rems_session_summary.json | 0.59 MB |
| processed/rems/rems_sol_summary.csv | 10.6 kB |
| processed/rems/rems_sol_summary.json | 29.1 kB |
| processed/rems/rems_trends.json | 4.0 kB |
| processed/rad/rad_observations_clean.csv | 23.5 kB |
| processed/rad/rad_observations_clean.json | 54.3 kB |
| processed/rad/rad_processing_provenance.json | 1.6 kB |
| processed/rad/rad_sol_summary.csv | 1.5 kB |
| processed/rad/rad_sol_summary.json | 3.1 kB |
| processed/rad/rad_trends.json | 0.5 kB |

## 7. Defects found on real archive data and fixed in this phase

1. **Undeclared REMS sentinel.** REMS writes -999 for missing values without declaring it in the FMT. Before this fix, -999 would have been averaged into temperatures. The pipeline now detects such values and applies them only where the SIS documents it.
2. **Planetographic latitude.** Ellipsoidal CRSs reported planetographic latitude, which shifted the CTX overlay bounds by about 0.05 deg. All coordinate conversions are now explicitly planetocentric, and CRS equivalence is tested numerically.
3. **RAD file structure.** RAD files are sectioned stream text with ELEMENT objects, not tables. A dedicated, label-driven reader now cross-checks every value against the text sections.

Each fix has tests; the suite now has 26 tests, all passing (`reports/test_results.txt`).
