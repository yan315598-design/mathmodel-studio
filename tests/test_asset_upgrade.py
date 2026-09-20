"""Real on-disk reader samples with corruption and unsupported encodings."""

import sys
from pathlib import Path
import numpy as np
import xarray as xr
from PIL import Image, TiffImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_assets import inspect, sha256


def test_ordinary_tiff_does_not_require_gis(tmp_path):
    path = tmp_path / "mask.tiff"
    original = np.arange(120, dtype=np.uint8).reshape(10, 12)
    Image.fromarray(original).save(path)
    before = sha256(path)
    result = inspect(path)
    assert result["status"] == "inspected"
    assert result["metadata"]["classification"] == "ordinary_tiff"
    assert result["metadata"]["mode"] == "L"
    assert sha256(path) == before
    np.testing.assert_array_equal(np.asarray(Image.open(path)), original)


def test_geotiff_is_not_silently_downgraded(tmp_path):
    path = tmp_path / "field.tiff"
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[33550] = (10., 10., 0.)
    tags[33922] = (0., 0., 0., 100., 200., 0.)
    Image.fromarray(np.zeros((10, 12), dtype=np.uint8)).save(path, tiffinfo=tags)
    result = inspect(path)
    # Missing rasterio is reported; installed readers must preserve the transform.
    if result["status"] == "missing_dependency":
        assert "rasterio" in result["detail"]
    else:
        assert result["status"] == "inspected"
        assert result["metadata"]["reader"] == "rasterio"
        assert result["metadata"]["transform"][0] == 10


def test_real_netcdf_preserves_time_crs_and_units(tmp_path):
    path = tmp_path / "field.nc"
    data = xr.Dataset({"speed": (("time", "y", "x"), np.ones((2, 3, 4)))},
                      coords={"time": [0, 600], "y": [0, 10, 20], "x": [0, 10, 20, 30]},
                      attrs={"crs": "synthetic local Cartesian", "height_m": 100})
    data["time"].attrs["units"] = "seconds since 2026-01-01 00:00:00"
    data["speed"].attrs["units"] = "m/s"
    data.to_netcdf(path, engine="scipy")
    before = sha256(path)
    result = inspect(path)
    assert result["status"] == "inspected"
    assert result["metadata"]["variables"]["time"]["units"].startswith("seconds since")
    assert result["metadata"]["variables"]["speed"]["units"] == "m/s"
    assert result["metadata"]["attributes"]["crs"] == "synthetic local Cartesian"
    assert result["provenance"]["input_sha256"] == before == sha256(path)
    assert result["capability"]["analysis"] == "not_run"


def test_npz_complex_array_and_object_rejection(tmp_path):
    path = tmp_path / "channel.npz"
    np.savez(path, channel=np.ones((2, 3), dtype=complex)*1j)
    result = inspect(path)
    assert result["status"] == "inspected"
    assert result["metadata"]["arrays"]["channel"]["dtype"] == "complex128"
    np.savez(path, unsafe=np.array([{}], dtype=object))
    assert inspect(path)["status"] == "error"


def test_corrupt_tiff_and_nc_are_errors(tmp_path):
    for name in ("broken.tiff", "broken.nc"):
        path = tmp_path / name
        path.write_bytes(b"broken")
        assert inspect(path)["status"] == "error"
