"""
test_pipeline.py - automated tests for the DHRUVION processing scripts.

SOFTWARE TEST FIXTURES ONLY
---------------------------
Every raster and table used here is an ANALYTIC surface or a miniature,
hand-written PDS3 label created inside pytest's temporary directory and
deleted afterwards. Column names are deliberately generic (VALUE_A, QFLAG...)
so they cannot be mistaken for real REMS or RAD structures. Nothing here is,
or imitates, a NASA measurement, and no fixture is written into raw/ or
processed/.

Run:  python -m pytest -v scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import dhruvion_common as common  # noqa: E402
import terrain_math as tm  # noqa: E402
from pds3_table import UnsupportedProduct, read_pds3_tables  # noqa: E402

R = 3_396_190.0


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), SCRIPTS / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_data_root(tmp_path):
    root = tmp_path / "DHRUVION_DATA"
    for d in ("raw/terrain", "raw/ctx", "raw/rems", "raw/rad", "processed/terrain",
              "metadata", "scripts/config"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return root


def write_geotiff(path, arr, crs, transform, nodata=None, units=None):
    import rasterio
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0],
                       count=1, dtype=arr.dtype, crs=crs, transform=transform,
                       nodata=nodata) as dst:
        dst.write(arr, 1)
        if units:
            dst.units = (units,)


# ---------------------------------------------------------------- terrain math
def geographic_grid(lat_top=-3.8, lon_left=136.2, res=0.05, n=40):
    from affine import Affine
    t = Affine(res, 0, lon_left, 0, -res, lat_top)
    lat = lat_top - (np.arange(n) + 0.5) * res
    lon = lon_left + (np.arange(n) + 0.5) * res
    return t, lat, lon


def test_geographic_spacing_is_metres_not_degrees():
    from pyproj import CRS
    t, lat, _ = geographic_grid()
    dx, dy = tm.pixel_ground_spacing(CRS("IAU_2015:49900"), t, 40, 40)
    assert np.allclose(dy, R * math.radians(0.05), rtol=1e-9)
    assert np.allclose(dx[:, 0], R * np.cos(np.radians(lat)) * math.radians(0.05), rtol=1e-4)
    assert dx.min() > 2000  # metres, not 0.05 "degrees"


def test_horn_slope_north_plane_exact():
    from pyproj import CRS
    t, lat, _ = geographic_grid()
    s = 0.1
    z = np.repeat((s * R * np.radians(lat))[:, None], 40, axis=1)
    dx, dy = tm.pixel_ground_spacing(CRS("IAU_2015:49900"), t, 40, 40)
    slope = tm.horn_slope_deg(z, dx, dy)
    inner = slope[1:-1, 1:-1]
    assert np.allclose(inner, math.degrees(math.atan(s)), atol=1e-6)
    assert np.isnan(slope[0]).all() and np.isnan(slope[:, -1]).all()  # edges NoData


def test_horn_slope_east_plane_geographic():
    from pyproj import CRS
    t, lat, lon = geographic_grid()
    s = 0.05
    lam = np.radians(lon - lon.mean())
    phi = np.radians(lat)
    # z = s * R cos(phi) * lambda: east gradient s, north gradient -s*lambda*sin(phi)
    z = s * R * np.cos(phi)[:, None] * lam[None, :]
    dx, dy = tm.pixel_ground_spacing(CRS("IAU_2015:49900"), t, 40, 40)
    slope = tm.horn_slope_deg(z, dx, dy)[1:-1, 1:-1]
    north = s * lam[None, 1:-1] * np.sin(phi)[1:-1, None]
    expected = np.degrees(np.arctan(np.hypot(s, north)))
    assert np.allclose(slope, expected, atol=2e-3)


def test_projected_equirectangular_distortion_corrected():
    from affine import Affine
    from pyproj import CRS
    crs = CRS("IAU_2015:49910")  # equirectangular, metres, standard parallel 0
    res = 2000.0
    y_top = R * math.radians(-5.0)
    t = Affine(res, 0, R * math.radians(137.0), 0, -res, y_top)
    n, s = 30, 0.1
    x = t.c + (np.arange(n) + 0.5) * res
    z = np.tile(s * x, (n, 1))  # plane in PROJECTED metres, eastward
    dx, dy = tm.pixel_ground_spacing(crs, t, n, n)
    slope = tm.horn_slope_deg(z, dx, dy)[1:-1, 1:-1]
    lat = np.degrees((y_top - (np.arange(n) + 0.5) * res) / R)[1:-1]
    expected = np.degrees(np.arctan(s / np.cos(np.radians(lat))))
    assert np.allclose(slope, expected[:, None], atol=1e-3)
    assert not np.allclose(slope, math.degrees(math.atan(s)), atol=1e-4)


def test_nodata_propagates_never_zero():
    z = np.full((10, 10), 100.0)
    z += np.arange(10)[None, :] * 5.0
    z[5, 5] = np.nan
    dx = np.full((10, 1), 10.0)
    dy = np.full((10, 1), 10.0)
    slope = tm.horn_slope_deg(z, dx, dy)
    assert np.isnan(slope[4:7, 4:7]).all()
    assert (slope[np.isfinite(slope)] > 0).all()
    tri = tm.tri_riley(z)
    assert np.isnan(tri[4:7, 4:7]).all()


def test_tri_riley_known_values():
    z = np.tile(np.arange(12, dtype=float) * 2.0, (12, 1))
    tri = tm.tri_riley(z)
    assert np.allclose(tri[1:-1, 1:-1], 2.0 * math.sqrt(6))
    assert np.allclose(tm.tri_riley(np.full((6, 6), 7.0))[1:-1, 1:-1], 0.0)


def test_detrended_rms_plane_and_checkerboard():
    yy, xx = np.mgrid[0:20, 0:20].astype(float)
    plane = 3.0 * xx - 2.0 * yy - 4500.0
    assert np.nanmax(tm.detrended_rms(plane, 3)) < 1e-6
    h = 1.5
    chk = plane + h * (-1.0) ** (xx + yy)
    rms = tm.detrended_rms(chk, 3)[1:-1, 1:-1]
    assert np.allclose(rms, h * math.sqrt(80 / 81), atol=1e-6)


def test_blockwise_equals_single_block():
    rng = np.random.default_rng(0)
    z = np.cumsum(rng.normal(size=(300, 50)), axis=0)
    dx = np.full((300, 1), 5.0)
    a = tm.horn_slope_deg(z, dx, dx, block_rows=37)
    b = tm.horn_slope_deg(z, dx, dx, block_rows=1000)
    assert np.allclose(a, b, equal_nan=True)
    assert np.allclose(tm.detrended_rms(z, 5, block_rows=41),
                       tm.detrended_rms(z, 5, block_rows=1000), equal_nan=True)


def test_units_helper_strict():
    assert tm.units_to_metre_factor("metre") == 1.0
    assert tm.units_to_metre_factor("KM") == 1000.0
    for bad in (None, "", "mm", "DN", "feet"):
        assert tm.units_to_metre_factor(bad) is None


# ---------------------------------------------------------------- validators + terrain CLI
def gale_dem(path, nodata_hole=True, units="metre", lat_top=-3.8, values_scale=1.0,
             crs="IAU_2015:49900"):
    t, lat, lon = geographic_grid(lat_top=lat_top, res=0.08, n=40)
    z = (-4000.0 + 50.0 * np.sin(np.radians(lon * 40))[None, :]
         + 30.0 * np.cos(np.radians(lat * 40))[:, None]) * values_scale
    z = z.astype(np.int16) if values_scale == 1.0 else z.astype(np.float32)
    nod = -32768 if z.dtype == np.int16 else None
    if nodata_hole and nod is not None:
        z[10:13, 20:24] = nod
    write_geotiff(path, z, crs, t, nodata=nod, units=units)
    return path


def test_raster_validator_statuses(tmp_path):
    v = load_script("03_validate_rasters.py")
    root = make_data_root(tmp_path)
    aoi = common.parse_aoi(None)
    good = gale_dem(root / "raw/terrain/test_dem.tif")
    r = v.validate_one(good, "elevation", aoi, {}, root, None)
    assert r["validation_status"] == "VALIDATED WITH LIMITATIONS" or r["validation_status"] == "VALIDATED"
    assert r["gale_center_covered_valid"] and r["approved_for_processing"]
    assert r["pixel_counts"]["nodata_value"] == 12

    earth = gale_dem(root / "raw/terrain/earth_dem.tif", crs="EPSG:4326")
    assert v.validate_one(earth, "elevation", aoi, {}, root, None)["validation_status"] == "INVALID"

    north = gale_dem(root / "raw/terrain/north_dem.tif", lat_top=45.0)
    assert v.validate_one(north, "elevation", aoi, {}, root, None)["validation_status"] == "INCOMPLETE"

    scaled = gale_dem(root / "raw/terrain/mm_dem.tif", values_scale=1000.0, nodata_hole=False)
    rr = v.validate_one(scaled, "elevation", aoi, {}, root, None)
    assert rr["validation_status"] == "INVALID"  # implausible for metres

    nounits = gale_dem(root / "raw/terrain/nounits_dem.tif", units=None)
    rn = v.validate_one(nounits, "elevation", aoi, {}, root, None)
    assert rn["approved_for_processing"] is False


def test_terrain_cli_end_to_end(tmp_path):
    import rasterio
    from PIL import Image
    p = load_script("05_process_terrain.py")
    root = make_data_root(tmp_path)
    dem = gale_dem(root / "raw/terrain/test_dem.tif")
    out = root / "processed/terrain"
    # gate: no validated catalog -> refuse
    assert p.main(["--data-root", str(root), "--dem", str(dem),
                   "--elevation-units", "metre"]) == 3
    # unknown units -> refuse
    assert p.main(["--data-root", str(root), "--dem", str(dem), "--elevation-units", "feet",
                   "--skip-catalog-check"]) == 4
    assert p.main(["--data-root", str(root), "--dem", str(dem), "--elevation-units", "metre",
                   "--skip-catalog-check"]) == 0
    with rasterio.open(dem) as s, rasterio.open(out / "test_dem_elevation_m.tif") as e, \
            rasterio.open(out / "test_dem_slope_deg.tif") as sl, \
            rasterio.open(out / "test_dem_coverage_mask.tif") as cv:
        assert e.crs == s.crs and e.transform == s.transform and e.shape == s.shape
        assert sl.crs == s.crs and sl.transform == s.transform
        ev = e.read(1)
        assert np.isnan(ev[10:13, 20:24]).all()            # NoData stays NoData
        assert not (ev[10:13, 20:24] == 0).any()           # never zero
        assert e.units[0] == "metre" and sl.units[0] == "degree"
        cov = cv.read(1)
        assert (cov[10:13, 20:24] == 0).all() and (cov[0] == 2).all()
    rgba = np.array(Image.open(out / "test_dem_elevation.png"))
    assert rgba.shape[2] == 4 and (rgba[10:13, 20:24, 3] == 0).all()
    prov = json.loads((out / "test_dem_terrain_provenance.json").read_text())
    assert prov["input"]["sha256"] and prov["statistics"]["slope_deg"]["n_valid"] > 0
    mtime = (out / "test_dem_slope_deg.tif").stat().st_mtime
    assert p.main(["--data-root", str(root), "--dem", str(dem), "--elevation-units", "metre",
                   "--skip-catalog-check"]) == 0
    assert (out / "test_dem_slope_deg.tif").stat().st_mtime == mtime  # not recomputed


def test_ctx_cli_clip_preserves_values(tmp_path):
    import rasterio
    c = load_script("06_process_ctx.py")
    root = make_data_root(tmp_path)
    t, _, _ = geographic_grid(lat_top=-3.0, lon_left=135.5, res=0.02, n=250)
    img = (np.arange(250 * 250) % 251).astype(np.uint8).reshape(250, 250)
    src = root / "raw/ctx/test_img.tif"
    write_geotiff(src, img, "IAU_2015:49900", t, nodata=0)
    dem = gale_dem(root / "raw/terrain/test_dem.tif")
    assert c.main(["--data-root", str(root), "--image", str(src),
                   "--reference-dem", str(dem), "--skip-catalog-check"]) == 0
    clip = root / "processed/ctx/test_img__GaleAOI_clip.tif"
    with rasterio.open(clip) as cl, rasterio.open(src) as s:
        win = rasterio.windows.from_bounds(*cl.bounds, s.transform).round_offsets().round_lengths()
        assert np.array_equal(cl.read(1), s.read(1, window=win))
    meta = json.loads((root / "processed/ctx/test_img__GaleAOI_overlay_metadata.json").read_text())
    assert meta["alignment_with_dem"]["result"] == "SAME_CRS_DIFFERENT_GRID"


# ---------------------------------------------------------------- PDS3 tables
LABEL = """PDS_VERSION_ID = PDS3
/* SOFTWARE TEST FIXTURE - NOT A REAL PDS PRODUCT */
RECORD_TYPE = FIXED_LENGTH
RECORD_BYTES = 32
FILE_RECORDS = 5
^TABLE = "FIXTURE.TAB"
OBJECT = TABLE
  INTERCHANGE_FORMAT = ASCII
  ROWS = 5
  ROW_BYTES = 32
  COLUMNS = 4
  {cols}
END_OBJECT = TABLE
END
"""
COLS = """OBJECT = COLUMN
    NAME = INDEX_A
    DATA_TYPE = ASCII_INTEGER
    START_BYTE = 1
    BYTES = 5
    UNIT = "N/A"
  END_OBJECT = COLUMN
  OBJECT = COLUMN
    NAME = VALUE_A
    DATA_TYPE = ASCII_REAL
    START_BYTE = 7
    BYTES = 9
    UNIT = "UNIT_X"
    MISSING_CONSTANT = -9999.0
    DESCRIPTION = "Generic fixture value"
  END_OBJECT = COLUMN
  OBJECT = COLUMN
    NAME = TIME_S
    DATA_TYPE = ASCII_REAL
    START_BYTE = 17
    BYTES = 8
    UNIT = "s"
  END_OBJECT = COLUMN
  OBJECT = COLUMN
    NAME = QFLAG
    DATA_TYPE = ASCII_INTEGER
    START_BYTE = 26
    BYTES = 5
  END_OBJECT = COLUMN"""
ROWS = ["    1,      1.5,     0.0,    0",
        "    1,      UNK,     1.0,    0",
        "    1,  -9999.0,     2.0,    1",
        "    2,     NULL,  5000.0,    0",
        "    2,      2.5,  5001.0,    0"]


def write_fixture(d: Path, structure=False, unit="UNIT_X", name="FIXTURE"):
    d.mkdir(parents=True, exist_ok=True)
    tab = "".join(r.ljust(30) + "\r\n" for r in ROWS)
    (d / f"{name}.TAB").write_text(tab, encoding="latin-1", newline="")
    cols = COLS.replace('"UNIT_X"', f'"{unit}"')
    if structure:
        (d / "FIXTURE.FMT").write_text(cols.replace("  OBJECT", "OBJECT") + "\nEND\n")
        cols = '^STRUCTURE = "FIXTURE.FMT"'
    (d / f"{name}.LBL").write_text(LABEL.format(cols=cols).replace("FIXTURE.TAB", f"{name}.TAB"))
    return d / f"{name}.LBL"


@pytest.mark.parametrize("structure", [False, True])
def test_pds3_reader_special_values(tmp_path, structure):
    lbl = write_fixture(tmp_path, structure)
    [t] = read_pds3_tables(lbl)
    df = t.data
    assert list(df.columns) == ["INDEX_A", "VALUE_A", "TIME_S", "QFLAG"]
    assert df["VALUE_A"].isna().sum() == 3 and not (df["VALUE_A"] == 0).any()
    q = t.qc["columns"]["VALUE_A"]
    assert (q["unk"], q["null"], q["missing_constant"], q["n_valid"]) == (1, 1, 1, 2)
    assert t.columns[1].unit == "UNIT_X" and t.qc["row_count_matches_label"]


def test_pds3_binary_rejected(tmp_path):
    lbl = write_fixture(tmp_path)
    lbl.write_text(lbl.read_text().replace("INTERCHANGE_FORMAT = ASCII",
                                           "INTERCHANGE_FORMAT = BINARY"))
    with pytest.raises(UnsupportedProduct):
        read_pds3_tables(lbl)


def test_pds_validator(tmp_path):
    v = load_script("04_validate_pds_tables.py")
    root = make_data_root(tmp_path)
    lbl = write_fixture(root / "raw/rems/SOL00001")
    rec = v.validate_label(lbl, "rems", [], root)
    assert rec["validation_status"] == "VALIDATED WITH LIMITATIONS"
    assert rec["tables"][0]["candidate_quality_columns_name_based"] == ["QFLAG"]
    assert "Curiosity rover location only" in rec["spatial_coverage"]


# ---------------------------------------------------------------- rover processing
def confirmed_map(path, rad=False, detector=True, status="CONFIRMED"):
    m = {"status": status, "confirmed_by": "pytest", "confirmed_against": "fixture",
         "time": {"sol_from_path_regex": r"SOL(\d{4,5})", "session_time_column": "TIME_S",
                  "session_time_type": "numeric_seconds", "session_gap_seconds": 600},
         "measurements": {"value_a": {"column": "VALUE_A", "quantity": "fixture",
                                      "expected_unit": "UNIT_X", "quality_column": "QFLAG",
                                      "good_quality_values": [0]}}}
    if rad and detector:
        m["measurements"]["value_a"]["detector"] = "DET_1"
    path.write_text(json.dumps(m))
    return path


def test_rover_processing_stats_and_sessions(tmp_path):
    import logging
    import rover_tables as rt
    root = make_data_root(tmp_path)
    lbl = write_fixture(root / "raw/rems/SOL00012")
    cmap = confirmed_map(root / "scripts/config/m.json")
    prov = rt.process("rems", cmap, root, root / "processed/rems", logging.getLogger("t"),
                      labels=[lbl], skip_validation_gate=True)
    assert prov["n_clean_rows"] == 5
    rows = json.loads((root / "processed/rems/rems_sol_summary.json").read_text())["rows"]
    allv = [r for r in rows if r["filter"] == "all_valid_values"][0]
    assert allv["sol"] == 12 and allv["n_valid"] == 2 and allv["n_missing"] == 3
    assert math.isclose(allv["mean"], 2.0) and allv["unit"] == "UNIT_X"
    sess = json.loads((root / "processed/rems/rems_session_summary.json").read_text())["rows"]
    assert len({r["session_id"] for r in sess}) == 2  # 5000 s gap splits sessions
    clean = json.loads((root / "processed/rems/rems_observations_clean.json").read_text())
    assert clean["records"][1]["VALUE_A"] is None      # UNK -> null, not 0
    assert "QFLAG" in clean["records"][0]              # quality field preserved


def test_rover_mapping_guards(tmp_path):
    import logging
    import rover_tables as rt
    root = make_data_root(tmp_path)
    lbl = write_fixture(root / "raw/rad/SOL00003")
    log = logging.getLogger("t")
    with pytest.raises(rt.MappingError):  # suggested maps refused
        rt.process("rad", confirmed_map(root / "a.json", rad=True, status="SUGGESTED"),
                   root, root / "processed/rad", log, labels=[lbl], skip_validation_gate=True)
    with pytest.raises(rt.MappingError):  # RAD key without detector refused
        rt.process("rad", confirmed_map(root / "b.json", rad=True, detector=False),
                   root, root / "processed/rad", log, labels=[lbl], skip_validation_gate=True)
    lbl2 = write_fixture(root / "raw/rad/SOL00004", unit="OTHER_UNIT", name="FIX2")
    m = json.loads(confirmed_map(root / "c.json", rad=True).read_text())
    m["measurements"]["value_a"]["expected_unit"] = None
    (root / "c.json").write_text(json.dumps(m))
    with pytest.raises(rt.MappingError):  # inconsistent units across products refused
        rt.process("rad", root / "c.json", root, root / "processed/rad", log,
                   labels=[lbl, lbl2], skip_validation_gate=True)
    # unit mismatch against expected_unit -> measurement skipped, not converted
    m["measurements"]["value_a"]["expected_unit"] = "UNIT_X"
    (root / "d.json").write_text(json.dumps(m))
    prov = rt.process("rad", root / "d.json", root, root / "processed/rad", log,
                      labels=[lbl, lbl2], skip_validation_gate=True)
    assert any("unit mismatch" in s.get("reason", "") for s in prov["skipped"])


# ---------------------------------------------------------------- downloader / common
def test_no_overwrite_and_safe_extract(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("a")
    with pytest.raises(common.OverwriteRefused):
        common.ensure_writable(f)
    d = load_script("02_download_datasets.py")
    root = make_data_root(tmp_path)
    z = root / "raw/ctx/evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../../evil.txt", "x")
    man = d.Manifest(root)
    with pytest.raises(IOError):
        d.extract_archive(z, {"id": "T"}, man, None, root)
    assert not (root / "evil.txt").exists()


def test_json_writer_nan_to_null(tmp_path):
    p = common.write_json(tmp_path / "a.json", {"v": float("nan"), "w": [1.0, float("inf")]})
    assert json.loads(p.read_text()) == {"v": None, "w": [1.0, None]}


def test_catalog_builder_marks_not_available(tmp_path):
    b = load_script("09_build_catalogs.py")
    root = make_data_root(tmp_path)
    common.write_json(root / "metadata/dataset_discovery_catalog.json",
                      {"candidates": [{"candidate_id": "CX", "dataset_name": "x",
                                       "category": "terrain", "plan_item_id": "P1"}]})
    common.write_json(root / "metadata/download_manifest.json",
                      {"records": [{"item_id": "P1", "status": "FAILED", "error": "DNS"}]})
    assert b.main(["--data-root", str(root)]) == 0
    cat = json.loads((root / "metadata/validated_dataset_catalog.json").read_text())
    assert cat["datasets"][0]["validation_status"] == "NOT AVAILABLE"
    assert "DNS" in cat["datasets"][0]["not_available_reason"]


# ---------------------------------------------------------------- downloader over local HTTP
@pytest.fixture
def local_http(tmp_path):
    """Serve a temporary directory on 127.0.0.1 (supports Range requests)."""
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    serve = tmp_path / "served"
    serve.mkdir()
    handler = functools.partial(_RangeHandler, directory=str(serve))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    yield serve, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


from http.server import SimpleHTTPRequestHandler  # noqa: E402


class _RangeHandler(SimpleHTTPRequestHandler):
    """Minimal single-range support so GDAL /vsicurl/ can read windows."""
    def log_message(self, *a):
        pass

    def send_head(self):
        rng = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not rng or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        start, _, end = rng.replace("bytes=", "").partition("-")
        start, end = int(start), min(int(end) if end else size - 1, size - 1)
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        import io
        data = f.read(end - start + 1)
        f.close()
        return io.BytesIO(data)


def test_downloader_end_to_end_local_http(tmp_path, local_http):
    import rasterio
    serve, base = local_http
    d = load_script("02_download_datasets.py")
    root = make_data_root(tmp_path)
    # analytic "global" raster on a Mars CRS, served over HTTP
    from affine import Affine
    t = Affine(0.5, 0, -180, 0, -0.5, 90)
    z = (np.arange(360 * 720) % 997).astype(np.int16).reshape(360, 720)
    write_geotiff(serve / "fixture_global.tif", z, "IAU_2015:49900", t, nodata=-32768,
                  units="metre")
    (serve / "pds").mkdir()
    for n in ("A.TAB", "A.LBL", "B.TAB", "notes.html"):
        (serve / "pds" / n).write_text(f"fixture {n}\n")
    plan = {"items": [
        {"id": "SUB", "enabled": True, "type": "raster_subset",
         "url": f"{base}/fixture_global.tif", "dest_dir": "raw/terrain",
         "dest_name": "fixture_window.tif", "documented_units": "metre"},
        {"id": "DIR", "enabled": True, "type": "pds_directory", "index_url": f"{base}/pds/",
         "include_regex": r"\.(TAB|LBL)$", "max_files": 10, "dest_dir": "raw/rems"},
        {"id": "OFF", "enabled": False, "type": "http_file", "url": None, "dest_dir": "raw/ctx"}]}
    plan_path = root / "scripts/config/plan.json"
    plan_path.write_text(json.dumps(plan))
    args = ["--data-root", str(root), "--plan", str(plan_path), "--record-disabled"]
    assert d.main(args) == 0
    man = json.loads((root / "metadata/download_manifest.json").read_text())["records"]
    st = {r["item_id"] + ":" + str(r["original_filename"]): r["status"] for r in man}
    assert st["SUB:fixture_global.tif"] == "SUBSET_EXTRACTED"
    assert sum(v == "DOWNLOADED" for k, v in st.items() if k.startswith("DIR")) == 3
    assert not (root / "raw/rems/notes.html").exists()
    assert any(r["status"] == "NOT_ATTEMPTED" for r in man)
    assert all(r["sha256"] for r in man if r["status"] in ("DOWNLOADED", "SUBSET_EXTRACTED"))
    with rasterio.open(root / "raw/terrain/fixture_window.tif") as w, \
            rasterio.open(serve / "fixture_global.tif") as s:
        assert w.crs == s.crs and w.nodata == s.nodata and w.units[0] == "metre"
        win = rasterio.windows.from_bounds(*w.bounds, s.transform)
        assert np.array_equal(w.read(1), s.read(1, window=win))   # values unchanged
        b = w.bounds
        assert b.left <= 136.2 and b.right >= 139.4 and b.bottom <= -7.0 and b.top >= -3.8
    # second run: nothing re-downloaded, nothing overwritten
    assert d.main(args) == 0
    man2 = json.loads((root / "metadata/download_manifest.json").read_text())["records"]
    new = man2[len(man):]
    assert {r["status"] for r in new if r["item_id"] != "OFF"} <= {"SKIPPED_EXISTS",
                                                                   "SKIPPED_DUPLICATE"}


# ---------------------------------------------------------------- rules added after real-archive inspection
def test_quality_rules_circular_and_sentinels(tmp_path):
    import logging
    import pandas as pd
    import rover_tables as rt
    qr = rt.QUALITY_RULES
    assert qr["all_ones"]("  1111") and not qr["all_ones"]("1X11") and not qr["all_ones"]("   ")
    assert qr["no_zeros"]("1X11") and not qr["no_zeros"]("1011") and not qr["no_zeros"](None)
    s = rt._stats(pd.Series([350.0, 10.0]), circular=True)
    assert min(s["circular_mean_deg"], 360 - s["circular_mean_deg"]) < 1e-6  # 0 deg, not 180
    assert "mean" not in s
    root = make_data_root(tmp_path)
    lbl = write_fixture(root / "raw/rems/SOL00012")
    m = json.loads(confirmed_map(root / "m.json").read_text())
    m["missing_value_sentinels"] = {"values": [2.5], "source": "fixture"}
    (root / "m.json").write_text(json.dumps(m))
    rt.process("rems", root / "m.json", root, root / "processed/rems", logging.getLogger("t"),
               labels=[lbl], skip_validation_gate=True)
    rows = json.loads((root / "processed/rems/rems_sol_summary.json").read_text())["rows"]
    allv = [r for r in rows if r["filter"] == "all_valid_values"][0]
    assert allv["n_valid"] == 1 and allv["mean"] == 1.5      # sentinel excluded, not averaged


RAW = SCRIPTS.parent / "raw"


@pytest.mark.skipif(not (RAW / "rad/SOL_00000_00089").exists(), reason="real RAD data absent")
def test_real_rad_label_offsets_match_text():
    from rad_rdr import read_rad_rdr
    labels = sorted((RAW / "rad/SOL_00000_00089").glob("*.LBL"))
    assert labels
    for lbl in labels:
        r = read_rad_rdr(lbl)
        assert r["elements"] and all(e["crosscheck_ok"] for e in r["elements"])
        assert {e["unit"] for e in r["elements"]} == {"microGray / Hour"}
        assert len(r["headers"]) * 2 == len(r["elements"])


@pytest.mark.skipif(not (RAW / "rems/SOL00009").exists(), reason="real REMS data absent")
def test_real_rems_label_structure_and_sentinel():
    [t] = read_pds3_tables(RAW / "rems/SOL00009/RME_398245439RMD00090000000_______PA.LBL",
                           [RAW / "rems/documentation"])
    assert len(t.data) == 5520 and len(t.columns) == 40 and t.qc["row_count_matches_label"]
    assert t.columns[15].name == "AMBIENT_TEMP" and t.columns[15].unit == "KELVIN"
    assert (t.data["UV_A"] == -999.0).any()   # raw parse keeps sentinel; processing masks it


def test_planetocentric_helpers_sphere_and_ellipsoid():
    from pyproj import CRS
    sphere = CRS("+proj=eqc +lat_ts=0 +lon_0=0 +R=3396190 +units=m +no_defs")
    to_s, fr_s = common.planetocentric_lonlat(sphere)
    x, y = fr_s(137.8, -5.4)
    assert abs(y - math.radians(-5.4) * R) < 1e-6 and abs(float(to_s(x, y)[1]) + 5.4) < 1e-9
    ctx = RAW / "ctx/MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10.tif"
    if ctx.exists():  # real Murray Lab "Mars_2015_Ocentric" ellipsoidal CRS
        import rasterio
        c = CRS.from_wkt(rasterio.open(ctx).crs.to_wkt())
        lat = float(common.planetocentric_lonlat(c)[0](137.0 * math.pi / 180 * R,
                                                       -4.0 * math.pi / 180 * R)[1])
        assert abs(lat + 4.0) < 1e-4          # planetocentric, not planetographic -4.047
        assert common.crs_max_offset_m(sphere, c) < 25.0   # measured ~12 m over the AOI
