# DHRUVION Phase 2 - Dataset Download / Acquisition Report

Generated 2026-11-14T19:46:18+00:00 from `metadata/download_manifest.json` (44 records).

## 1. Result

The build environment could not reach any authoritative archive (0 of 18 endpoints resolved; see Phase 1). The data were therefore acquired in two stages. First, the user found the exact authoritative URLs through web research. Second, the user downloaded the files manually, made Gale-sized copies of the two very large rasters with `crop_for_upload.py`, and uploaded `DHRUVION_UPLOAD.zip` (12.1 MB, 42 entries). Every received file was ingested by `scripts/02b_ingest_user_files.py` under an explicit spec (`scripts/config/ingest_spec_2026-11-14.json`): copied without overwriting, verified by SHA-256 after copying, and recorded with its source URL and evidence.

**36 files (41.65 MB) are now in `raw/`.** One duplicate was skipped. The datasets that remain unacquired are listed in section 5.

## 2. Files acquired

| Local path | Size | SHA-256 | Role | Source URL | Notes |
|---|---|---|---|---|---|
| raw/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.tif | 0.26 MB | 62d9595d0b431ddc... | data | https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif | AOI window (cols 40473-40882, rows 12006-12415) cut by the user with crop_for_upload.py; pixel values unchanged (shrink factor 1). |
| raw/terrain/Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI.provenance.json | 0.8 kB | f1d7542d41dfc1e8... | support | (crop record) | Crop provenance record |
| raw/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif | 9.23 MB | dbfe1ea652a328f2... | data | https://murray-lab.caltech.edu/CTX/V01/tiles/MurrayLab_GlobalCTXMosaic_V01_E136_N-08.zip | REDUCED RESOLUTION: 10x10 average (~50 m/px) of the 5 m/px tile over the AOI (lat -7.0 to -4.0; the tile ends at -4.0), made by crop_for_upload.py; NoData (0) ignored in averaging. Original-resolution tile is NOT in this package (kept on the user PC). |
| raw/ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.provenance.json | 0.8 kB | 506e5fe0b789fbd3... | support | (crop record) | Crop provenance record |
| raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.LBL | 3.0 kB | 1a635a9e2041cb2e... | label | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DATA/SOL_00001_00089/SOL00009/RME_398245439RMD00090000000_______PA.LBL |  |
| raw/rems/SOL00009/RME_398245439RMD00090000000_______PA.TAB | 2.05 MB | 2d7eee88333bdf61... | data | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DATA/SOL_00001_00089/SOL00009/RME_398245439RMD00090000000_______PA.TAB | Browser-added ".txt" suffix removed to restore the archive file name. |
| raw/rems/SOL00010/RME_398334213RMD00100000000_______PA.LBL | 3.0 kB | 3e05f99b1014f26c... | label | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DATA/SOL_00001_00089/SOL00010/RME_398334213RMD00100000000_______PA.LBL |  |
| raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.LBL | 3.0 kB | 5ebc6ea1edb535a7... | label | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DATA/SOL_00001_00089/SOL00011/RME_398422988RMD00110000000_______PA.LBL |  |
| raw/rems/SOL00011/RME_398422988RMD00110000000_______PA.TAB | 4.82 MB | 7fe1e90b08f42f2d... | data | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DATA/SOL_00001_00089/SOL00011/RME_398422988RMD00110000000_______PA.TAB |  |
| raw/rems/documentation/MODRDR6.FMT | 24.7 kB | 9609aa0d596bcbaf... | support | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/LABEL/MODRDR6.FMT | MODRDR column format file referenced by ^STRUCTURE |
| raw/rems/documentation/REMS_RDR_SIS.TXT | 0.33 MB | 31923356589c542b... | support | https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/DOCUMENT/REMS_RDR_SIS.TXT | REMS RDR Software Interface Specification |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.LBL | 0.13 MB | 6eb5e69243b26f84... | label | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.LBL |  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.TXT | 6.58 MB | 4d08d57a55b5c48a... | data | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_220_02_25_0001_V00.TXT |  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.LBL | 0.18 MB | 5637b21a0ee0d736... | label | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.LBL |  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.TXT | 9.99 MB | 4164af456db82a68... | data | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_221_02_47_0002_V00.TXT |  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.LBL | 0.12 MB | 5bba6128c6d7486a... | label | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.LBL |  |
| raw/rad/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.TXT | 6.55 MB | f9d238e33e98abdf... | data | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/RAD_RDR_2012_222_04_26_0003_V00.TXT |  |
| raw/rad/SOL_00000_00089/D_LETCNT.FMT | 1.6 kB | ac2cfcfae04353c4... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/D_LETCNT.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/D_LET_EVC.FMT | 1.6 kB | a6d0a32a73977b93... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/D_LET_EVC.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/D_LET_EVW.FMT | 1.6 kB | 57c162afcc55523a... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/D_LET_EVW.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_PP.FMT | 4.0 kB | 95e2aa655f39568c... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_PP.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_PPXC.FMT | 1.7 kB | 24dbc51a9efc5005... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_PPXC.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_PPXW.FMT | 1.7 kB | 28f2eeefb6006de3... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_PPXW.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_SP.FMT | 3.8 kB | a6d628bc956bb384... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_SP.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_SPXC.FMT | 1.7 kB | 78ea5efeb7116d4e... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_SPXC.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/HIST_SPXW.FMT | 1.7 kB | b35f2a29f393f788... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/HIST_SPXW.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_NDE.FMT | 4.0 kB | 0a319018ae98171b... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_NDE.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_NDE_XC.FMT | 1.7 kB | 591b8fe5b1e7c63e... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_NDE_XC.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_NDE_XW.FMT | 1.7 kB | ffc958ace3f325b7... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_NDE_XW.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_N_CNT.FMT | 1.6 kB | 06760971904c379d... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_N_CNT.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_N_EVC.FMT | 1.6 kB | 1d558296da1cc54d... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_N_EVC.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/H_N_EVW.FMT | 1.6 kB | d624d9f88c1ebf91... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/H_N_EVW.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/L1_CNTR.FMT | 11.1 kB | f91054abe15d27ef... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/L1_CNTR.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/L2_CNTR.FMT | 9.1 kB | c19a0f360cdce8b1... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/L2_CNTR.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/SOL_00000_00089/PHA_TAB.FMT | 7.1 kB | 5a1e8fdb16d84276... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00000_00089/PHA_TAB.FMT | Format file referenced by ^STRUCTURE in RAD labels (kept beside the data, as in the archive) |
| raw/rad/documentation/RAD_RDR_SIS.pdf | 1.31 MB | 3cfe8335d8c8d5c1... | support | https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DOCUMENT/RAD_RDR_SIS.PDF | RAD RDR SIS v3.2 (28 Aug 2013); received with lower-case ".pdf" extension |

## 3. Integrity and authenticity checks

- **MOLA.** The full source file the user downloaded is 2,125,771,142 bytes, exactly the size the USGS product page reports for `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif`. Its SHA-256 (`38a4eb0b...`) is recorded in the crop provenance file. The AOI window kept the source pixel values unchanged (shrink factor 1).
- **CTX.** The zip (1,774,557,393 bytes, SHA-256 `e7021d4e...`) opened and was read across the full AOI window without error, so it is a complete archive. Web research had indexed it as about 1.9 GB; that figure was not confirmed and does not affect integrity. The package holds a **10x10 averaged copy (~50 m/px)**; the 5 m original remains on the user's computer.
- **REMS.** Each .TAB size equals the label's FILE_RECORDS x RECORD_BYTES: 5520 x 372 = 2,053,440 B for sol 9, and 12960 x 372 = 4,821,120 B for sol 11. Both files are ASCII; neither is an HTML error page.
- **RAD.** All 94 dose-rate values read through the label byte offsets equal the values in the text sections ([DOSIMETRY_TOTAL_DOSE_B/E: NN]).
- **All files.** No HTML error pages were received. Each copy into `raw/` was verified by SHA-256.

## 4. Repairs and exclusions (all recorded in the manifest)

The browser had appended `.txt` to one REMS data file; the archive name `RME_398245439RMD00090000000_______PA.TAB` was restored, and its size check confirms the content is intact. A byte-identical duplicate label (`...PA.LBL.txt`, MD5 `eee38c94...`) was not ingested. The RAD SIS arrived as `RAD_RDR_SIS.pdf` (lower-case extension) and was kept as received.

## 5. Not acquired

The **REMS sol 10 data file** was not received; only its label is present, so sol 10 is INCOMPLETE. The **USGS Gale 1 m merged DEM** (3.6 GB) was not downloaded; it is optional, its footprint is 137.12-137.68 E, -5.10 to -4.13 and does not contain the Gale centre, and plan item `GALE_DEM_1M_OPTIONAL` is ready for it. CTX DTMs, HiRISE DTMs and the 25 cm orthophoto have no confirmed Gale product or were too large, and the remaining candidates were deferred as duplicates. Earlier automated attempts from the build environment:

| Record | Item | Status | Detail |
|---|---|---|---|
| DL0001 | MOLA_463M_GALE_SUBSET | FAILED | RasterioIOError: CURL error: Could not resolve host: planetarymaps.usgs.gov |
| DL0002 | CTX_MOSAIC_TILE | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0003 | CTX_OR_HIRISE_DTM | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0004 | REMS_RDR_SAMPLE | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0005 | REMS_DOCUMENTATION | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0006 | RAD_RDR_SAMPLE | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0007 | RAD_DOCUMENTATION | NOT_ATTEMPTED | Entry disabled: exact product URL not confirmed against the authoritative archive |
| DL0044 | REMS_RDR_SAMPLE | SKIPPED_DUPLICATE | Byte-identical duplicate (same MD5 eee38c94...) of RME_398245439RMD00090000000_______PA.LBL |

## 6. Reproducing the acquisition

`scripts/config/download_plan.json` now holds the exact URLs of every file acquired here, plus the optional Gale DEM. On a machine with internet access, `python scripts/02_download_datasets.py` reproduces the acquisition. As far as is known, none of these archives requires a login.
