#!/usr/bin/env bash
# DHRUVION dataset pipeline - full run on a machine WITH internet access.
# Manual gates (by design): confirm product URLs in config/download_plan.json,
# and confirm REMS/RAD column maps against the SIS before Step 4 rover processing.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pytest -q tests                      # 0. software self-test
python3 00_inventory_workspace.py --scan ..     # 1. inventory
python3 00_check_source_access.py               # 1. source reachability evidence
python3 01_discover_ode_products.py --query MRO:CTX:EDR --query MRO:HIRISE:DTM || true
python3 02_download_datasets.py --record-disabled || true   # 2. download (failures logged)
python3 03_validate_rasters.py                  # 3. raster validation
python3 04_validate_pds_tables.py               # 3. REMS/RAD validation
python3 09_build_catalogs.py                    # 3. validated catalog
python3 run_step4.py                            # 4. process approved inputs only
python3 09_build_catalogs.py                    # 5. final catalog incl. derived products
python3 10_package_and_verify.py                # 5. ZIP + verification
