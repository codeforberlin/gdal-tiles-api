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
        options=["-dstalpha"],
    )
    if not tile:
        raise RuntimeError("gdal.Warp failed to produce output")

    image = create_image(tile, width, height)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def create_image(dataset, width, height):
    raster_count = dataset.RasterCount

    bands = []
    for i in range(1, raster_count + 1):
        band = dataset.GetRasterBand(i)
        raster = band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Byte)
        array = np.frombuffer(raster, dtype=np.uint8).reshape((height, width))
        bands.append(array)

    if raster_count == 1:
        return Image.fromarray(bands[0], mode="L")
    elif raster_count == 2:
        return Image.merge("LA", (Image.fromarray(bands[0]), Image.fromarray(bands[1])))
    elif raster_count == 3:
        return Image.merge("RGB", tuple(Image.fromarray(a) for a in bands))
    elif raster_count == 4:
        return Image.merge("RGBA", tuple(Image.fromarray(a) for a in bands))
    else:
        raise ValueError(f"Unsupported number of bands: {raster_count}")
