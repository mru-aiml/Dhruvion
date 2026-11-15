"""Integration tests for the supplied NASA DHRUVION_DATA package.

These tests assert the contract the frontend relies on: every scientific
response carries units, coverage, provenance and availability, class 2 cells
never gain slope/roughness, CTX is partial and labelled as DN, and REMS/RAD
are historical point measurements.
"""

from __future__ import annotations

import os

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.terrain_service import get_terrain_service

client = TestClient(app)
REGION = "gale_crater"


def _class_two_coordinate():
    """Find a real coverage-class-2 cell and return its lon/lat."""
    terrain = get_terrain_service()
    coverage = terrain._require("coverage")
    row, col = np.argwhere(coverage.data == 2)[0]
    elevation = terrain._require("elevation")
    x, y = elevation.transform * (col + 0.5, row + 0.5)
    lon, lat = terrain._from_raster_crs(elevation, x, y)
    return float(lon), float(lat)


# ----------------------------------------------------------------- datasets
def test_dataset_catalog_lists_real_package_files():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    body = response.json()
    assert body["statistics"]["package_installed"] is True
    assert body["statistics"]["available"] > 0

    by_id = {item["dataset_id"]: item for item in body["datasets"]}
    assert by_id["terrain_elevation"]["provenance"] == "observed"
    assert by_id["terrain_elevation"]["status"] == "available"
    assert by_id["terrain_slope"]["provenance"] == "derived"
    assert by_id["terrain_roughness"]["provenance"] == "derived"
    assert by_id["terrain_coverage"]["status"] == "available"
    assert by_id["ctx_mosaic"]["status"] == "available"
    assert by_id["rems_environment"]["status"] == "available"
    assert by_id["rad_dosimetry"]["status"] == "available"

    for dataset in body["datasets"]:
        if dataset["status"] != "available" or dataset["dataset_type"] == "tiles":
            continue
        assert dataset["file_path"], dataset["dataset_id"]
        # Paths are package-relative, never developer-machine absolutes.
        assert not os.path.isabs(dataset["file_path"]), dataset["file_path"]


def test_dataset_catalog_filters_and_detail():
    response = client.get("/api/datasets", params={"dataset_type": "derived"})
    assert response.status_code == 200
    items = response.json()["datasets"]
    assert items
    assert all(item["dataset_type"] == "derived" for item in items)

    detail = client.get("/api/datasets/terrain_slope")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["dataset_id"] == "terrain_slope"
    assert payload["provenance"] == "derived"
    assert payload["coverage"]["resolution_m"] > 0


# ------------------------------------------------------------------ terrain
def test_terrain_point_and_layer_endpoints_carry_metadata():
    point = client.get("/api/terrain", params={"region_id": REGION, "x": 137.4, "y": -5.4})
    assert point.status_code == 200
    body = point.json()
    assert body["availability"] in {"available", "partial"}
    assert body["values"]["elevation_m"] is not None
    assert "observed" in body["provenance"]
    assert body["units"]["elevation_m"] == "m"
    assert body["coverage"]["class"] in (1, 2)
    assert body["source"]["provider"]
    assert body["limitations"]

    for layer in ("elevation", "slope", "roughness"):
        response = client.get(f"/api/terrain/{layer}", params={"region_id": REGION, "x": 137.4, "y": -5.4})
        assert response.status_code == 200, layer
        payload = response.json()
        assert payload["layer"] == layer
        assert payload["unit"]
        assert payload["coverage"]["class"] in (1, 2)

    coverage = client.get("/api/terrain/coverage", params={"region_id": REGION, "x": 137.4, "y": -5.4})
    assert coverage.status_code == 200
    assert coverage.json()["layer"] == "coverage"
    assert coverage.json()["value"] in (0, 1, 2)


def test_coverage_summary_and_class_two_has_no_derivatives():
    summary = client.get("/api/terrain/coverage/summary", params={"region_id": REGION})
    assert summary.status_code == 200
    body = summary.json()
    assert body["counts"]["1"] > 0
    assert body["counts"]["2"] > 0
    assert body["classes"]["2"]
    assert body["resolution_m"] > 400

    lon, lat = _class_two_coordinate()
    elevation = client.get(
        "/api/terrain/elevation", params={"region_id": REGION, "x": lon, "y": lat}
    ).json()
    assert elevation["coverage"]["class"] == 2
    assert elevation["value"] is not None

    for layer in ("slope", "roughness"):
        response = client.get(
            f"/api/terrain/{layer}", params={"region_id": REGION, "x": lon, "y": lat}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["value"] is None, f"{layer} must stay undefined for class 2"
        assert payload["availability"] == "unavailable"
        assert any("not replaced with a zero" in warning for warning in payload["warnings"])


def test_outside_coverage_is_unavailable_not_zero():
    response = client.get("/api/terrain", params={"region_id": REGION, "x": 0, "y": 0})
    assert response.status_code == 200
    payload = response.json()
    assert payload["availability"] == "unavailable"
    assert payload["values"] == {"elevation_m": None, "slope_deg": None, "roughness": None}
    assert payload["provenance"] == []


def test_terrain_profile_samples_real_elevation():
    response = client.get(
        "/api/terrain/profile",
        params={
            "region_id": REGION,
            "start_x": 137.2,
            "start_y": -4.5,
            "end_x": 137.3,
            "end_y": -4.55,
            "samples": 12,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["samples"] == 12
    assert payload["distance_m"] > 0
    assert len(payload["points"]) == 12
    assert any(point["values"]["elevation_m"] is not None for point in payload["points"])


# ------------------------------------------------------------------ imagery
def test_ctx_imagery_is_partial_and_labelled_dn():
    response = client.get("/api/imagery")
    assert response.status_code == 200
    body = response.json()
    ctx = body["ctx"]
    assert ctx["available"] is True
    assert ctx["partial_coverage"] is True
    assert "DN" in ctx["units"]
    assert "reflectance" in ctx["units"]
    assert ctx["bounds"]["bounds_latlon"]["south"] == -6.918712153475242
    assert ctx["bounds"]["bounds_latlon"]["north"] == -4.0000380966075735
    assert ctx["overlay_url"].startswith("/static/dhruvion/")
    assert ctx["alignment_with_dem"]["result"] == "NEAR_EQUIVALENT_CRS_DIFFERENT_GRID"
    assert any("Web Mercator" in item for item in ctx["limitations"])

    layers = client.get("/api/imagery/layers")
    assert layers.status_code == 200
    assert "items" in layers.json()


# --------------------------------------------------------------------- REMS
def test_rems_is_historical_point_data_with_circular_wind():
    response = client.get("/api/environment/rems")
    assert response.status_code == 200
    body = response.json()
    assert body["instrument"] == "REMS"
    assert body["availability"] == "available"
    assert body["observation_type"] == "historical_point_measurement"
    assert body["sols"] == [9, 11]
    assert body["default_filter"] == "all_valid_values"
    assert body["coverage"]["live"] is False
    assert body["coverage"]["forecast"] is False
    assert body["coverage"]["spatially_distributed"] is False
    assert body["units"]["air_temperature"] == "KELVIN"
    assert body["measurements"]["9"]["air_temperature"]["mean"] is not None
    assert body["measurements"]["11"]["pressure"]["mean"] is not None

    wind = body["wind"]["9"]
    assert 0.0 <= wind["direction"]["circular"]["circular_mean_deg"] < 360.0
    assert 0.0 <= wind["direction"]["circular"]["resultant_length"] <= 1.0
    assert wind["direction"]["n_valid"] >= 1

    assert body["trends"]
    assert all("trend not computed" in item["note"] for item in body["trends"])


def test_rems_unknown_sol_is_not_found():
    response = client.get("/api/environment/rems", params={"sol": 99})
    assert response.status_code == 404


# ---------------------------------------------------------------------- RAD
def test_radiation_keeps_detectors_separate_and_uses_microgray():
    response = client.get("/api/environment/radiation")
    assert response.status_code == 200
    body = response.json()
    assert body["instrument"] == "RAD"
    assert body["availability"] == "available"
    assert body["observation_type"] == "historical_point_measurement"
    assert body["sols"] == [1, 2, 3]
    assert body["unit"] == "microGray / Hour"
    assert body["coverage"]["route_specific"] is False
    assert set(body["detectors"]) == {"dose_rate_B", "dose_rate_E"}
    for detector in body["detectors"].values():
        assert detector["unit"] == "microGray / Hour"
        assert set(detector["sols"]) == {"1", "2", "3"}
        assert all(sol["mean"] is not None for sol in detector["sols"].values())
    assert any("qc_placeholder" in warning for warning in body["warnings"])
    assert all("trend not computed" in item["note"] for item in body["trends"])


def test_science_catalogue_is_explicitly_unavailable():
    response = client.get("/api/science/catalogs")
    assert response.status_code == 200
    body = response.json()
    assert body["availability"] == "unavailable"
    assert body["catalogs"] == []


# ------------------------------------------------------------------- layers
def test_layer_catalog_exposes_terrain_and_environment_layers():
    response = client.get("/api/layers", params={"region_id": REGION})
    assert response.status_code == 200
    body = response.json()
    assert body["region_id"] == REGION
    ids = {item["id"] for item in body["items"]}
    assert "mars_trek_mola_colorshade" in ids
    assert any(item["layer_type"] in {"raster", "overlay"} for item in body["items"])


def test_regions_return_metadata_bounds_and_crs():
    response = client.get("/api/regions")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == REGION
    assert item["crs"]
    assert item["latitude_type"] == "planetocentric"
    assert item["bounds_latlon"]["west"] < item["bounds_latlon"]["east"]
    assert item["resolution_m"] > 0
    assert item["source"]["provider"]
