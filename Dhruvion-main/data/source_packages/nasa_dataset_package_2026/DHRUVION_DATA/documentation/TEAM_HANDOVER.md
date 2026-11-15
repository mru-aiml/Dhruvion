# DHRUVION Team Handover - Using the NASA Dataset Package

> **Package status:** this package contains **real NASA/USGS data for Gale Crater**, together with validated derived products:
> - MOLA 463 m elevation for the Gale area, with slope, roughness and coverage layers derived from it;
> - a CTX mosaic image of the crater (a reduced 50 m/px copy);
> - Curiosity REMS environmental data for sols 9 and 11;
> - Curiosity RAD dose rates for sols 1–3.
>
> Twelve other catalogued datasets were not acquired and are marked NOT AVAILABLE. Nothing in this package is simulated.

No application code was changed. This note covers which files to load, how to place them on the map and what you must not do with them.

## 1. Mars map layers

| Layer | File | Leaflet bounds [[S, W], [N, E]] (planetocentric deg) |
|---|---|---|
| Base imagery (CTX) | processed/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__GaleAOI.png | [[-6.9187, 136.1999], [-4.0, 139.4]] |
| Elevation overlay | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_elevation.png | [[-7.0002, 136.1982], [-3.797, 139.4014]] |
| Slope overlay | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_slope.png | [[-7.0002, 136.1982], [-3.797, 139.4014]] |
| Roughness overlay | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_roughness.png | [[-7.0002, 136.1982], [-3.797, 139.4014]] |
| Data-coverage overlay | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_coverage.png | [[-7.0002, 136.1982], [-3.797, 139.4014]] |

Always read the bounds and legend from the `*_overlay_metadata.json` next to each PNG rather than hard-coding them. The metadata gives `display_vmin`/`display_vmax`, the colour map and the units for each layer:
- elevation: −4,422 to 377 m;
- slope: 0–22°;
- roughness: 9–392 m.

These ranges are display stretches only; values outside them are clipped in the image, not in the data.

The images use an equirectangular (plate carrée) grid, so use a lat/lon map CRS such as `L.CRS.EPSG4326` with Mars tiles in the same projection. Do not place them on Leaflet's default Web Mercator map without reprojecting.

The CTX image covers −6.92 to −4.00 latitude. The tile ends at −4.0, so the crater's northern rim beyond that line has no imagery: leave that strip blank.

## 2. Elevation, slope and roughness (for the route planner)

| Layer | File | Units | Method |
|---|---|---|---|
| Elevation | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_elevation_m.tif | metres above the MOLA areoid | source values, NoData -> NaN |
| Slope | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_slope_deg.tif | degrees | Horn (1981), geodesic pixel spacing |
| Roughness | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_roughness_tri_riley_m.tif | metres | TRI, Riley et al. (1999) |
| Coverage | processed/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI_coverage_mask.tif | class | 0 no data, 1 usable, 2 elevation only |

All four rasters share one grid: 410 x 410 cells, CRS `Equirectangular Mars` (sphere R = 3,396,190 m), cell 463.09 m. Ground spacing is dx 459.6–462.1 m and dy 463.1 m (see `*_terrain_provenance.json`); use it as the step distance between cells. Cell `[row, col]` refers to the same place in every layer, and you should read the transform from the file rather than hard-coding it. The 1,636 border cells have class 2, meaning slope and roughness are undefined there. There are no NoData cells inside the AOI.

**Do not:**
- treat NaN or class ≠ 1 cells as zero cost — they are **unknown and impassable**;
- interpolate across them;
- route outside the raster bounds.

At 463 m per cell this supports regional route planning, not rover-scale obstacle avoidance.

## 3. REMS environmental charts

| File | Use |
|---|---|
| processed/rems/rems_sol_summary.csv / .json | One row per sol x measurement x filter. Columns: sol, measurement, column, quantity, detector, unit, filter, n_rows, n_valid, n_missing, mean, min, max, median, std, n_excluded_by_quality, circular_mean_deg, resultant_length, note |
| processed/rems/rems_session_summary.csv / .json | Same statistics per observation session (gap > 60 s); good for intra-sol charts |
| processed/rems/rems_observations_clean.csv / .json | ~1 Hz points, label column names (AMBIENT_TEMP, PRESSURE, ...), with sol, session_id, LMST, LTST and confidence strings |
| processed/rems/rems_missing_values_report.csv | Per column: valid values and -999 (documented sentinel) counts |
| processed/rems/rems_trends.json | Not computed: fewer than 5 sols |

Measurement keys:
- `air_temperature` (AMBIENT_TEMP, K)
- `ground_temperature` (BRIGHTNESS_TEMP, K)
- `pressure` (Pa)
- `relative_humidity` (%)
- `uv_a` … `uv_e` and `uv_abc` (W/m²)
- `horizontal_wind_speed` (m/s)
- `wind_direction`, summarised with **circular** statistics (`circular_mean_deg`); never average angles arithmetically.

How to chart them:
- Default to the rows with `filter == "all_valid_values"`. The `...: no_zeros` and `...: all_ones` rows are quality-filtered versions to offer as a toggle.
- Use LMST for Mars local time; `TIMESTAMP` (seconds since noon 1 Jan 2000) is for ordering.
- If you show °C, convert from kelvin (°C = K − 273.15) and label the value as converted.
- Wind is effectively unavailable on these sols (7 and 25 valid samples). Show "insufficient data", not a value.

## 4. RAD radiation charts

| File | Use |
|---|---|
| processed/rad/rad_sol_summary.csv / .json | Per sol x detector: n_observations, mean, min, max, median, std (microGray / Hour); unweighted mean of observation dose rates |
| processed/rad/rad_observations_clean.csv / .json | One row per observation per detector. Columns: source_product, obs_index, sol, lmst_start, utc_start, measurement, detector, quantity, value, unit, label_object, label_vs_text_crosscheck, qc_placeholder, edr_filename |
| processed/rad/rad_trends.json | Not computed: fewer than 5 sols |

Draw **one series per detector**: `dose_rate_B` is detector B (silicon) and `dose_rate_E` is detector E (plastic scintillator). Never add, average or merge the two. The unit is µGy/h exactly as labelled; if you display µGy/day, multiply by 24 and say so. `qc_placeholder` is not a quality flag (RAD RDR SIS v3.2 §4.2.1.2), so don't filter on it. Caption the charts "Historical Curiosity RAD dose rate at the rover location, sols 1–3 (August 2012)".

## 5. Coverage restrictions

The terrain covers the AOI only; requests outside it should return an out-of-coverage response. CTX covers −6.92 to −4.00 latitude. REMS (sols 9 and 11) and RAD (sols 1–3) are measurements at the rover's position in 2012. They describe one point and do not apply to other map locations or to a planned route.

## 6. Suggested API behaviour (guidance only)

| Endpoint | Serve |
|---|---|
| /api/terrain/elevation, /slope, /roughness | sample the processed GeoTIFFs; return null + reason for NaN or out-of-coverage |
| /api/terrain/coverage | the coverage mask and its legend |
| /api/environment/rems | the summary JSON files with units, filter and n_valid |
| /api/environment/radiation | rad_sol_summary.json and rad_observations_clean.json, per detector |
| every response | classification (OBSERVED / DERIVED / SIMULATED), source and a link to FINAL_DATASET_CATALOG.json |

## 7. Scientific limitations

- **MOLA:** cells are about 463 m, and many low-latitude cells are interpolated between orbit tracks.
- **CTX:** values are DN, not reflectance; this copy is averaged to ~50 m; mosaic seams are visible.
- **REMS:** the column map was prepared from the FMT and SIS by the assistant, so ask a team member to review it. The confidence-code rules follow SIS §3.1.6.
- **RAD:** per-sol means are unweighted; QC and rover position are placeholders.

All REMS and RAD data are historical, local and few in number (2 and 3 sols).
