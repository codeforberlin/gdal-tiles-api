import io
import math
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image

resample_methods = {
    "nearest": gdal.GRA_NearestNeighbour,
    "bilinear": gdal.GRA_Bilinear,
    "cubic": gdal.GRA_Cubic,
    "cubicspline": gdal.GRA_CubicSpline,
    "lanczos": gdal.GRA_Lanczos,
}


def num2deg(xtile: int, ytile: int, zoom: int) -> tuple:
    n = 1 << zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def get_bbox(x: int, y: int, z: int) -> tuple:
    north, west = num2deg(x, y, z)
    south, east = num2deg(x + 1, y + 1, z)
    return west, east, south, north


def extract_tile(
    path: Path,
    west: float,
    east: float,
    south: float,
    north: float,
    width: int = 256,
    height: int = 256,
    resample: str = "cubic",
) -> tuple:
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if not dataset:
        raise RuntimeError(f"Failed to open source file: {path}")

    tile = gdal.Warp(
        "",
        dataset,
        format="MEM",
        dstSRS="EPSG:4326",
        outputBounds=(west, south, east, north),
        width=width,
        height=height,
        resampleAlg=resample_methods.get(resample.lower(), gdal.GRA_Cubic),
        srcNodata=0,
        dstNodata=0,
    )
    if not tile:
        raise RuntimeError("gdal.Warp failed to produce output")

    image = create_image(tile, width, height)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def create_image(dataset, width, height, alpha=False):
    channels = (1, 1, 1) if dataset.RasterCount == 1 else (1, 2, 3)

    band_arrays = []
    nodata_values = []
    for i in channels:
        band = dataset.GetRasterBand(i)
        raster = band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Byte)
        array = np.frombuffer(raster, dtype=np.uint8).reshape((height, width))
        band_arrays.append(array)
        nodata_values.append(band.GetNoDataValue())

    rgb = np.stack(band_arrays, axis=-1)

    if alpha:
        a = np.full((height, width), 255, dtype=np.uint8)
        for i, nodata in enumerate(nodata_values):
            if nodata is not None:
                a[band_arrays[i] == int(nodata)] = 0

        rgba = np.dstack([rgb, a])
        return Image.fromarray(rgba, mode="RGBA")
    else:
        return Image.fromarray(rgb, mode="RGB")
