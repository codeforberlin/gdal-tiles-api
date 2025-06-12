import pytest

from .utils import get_bbox, num2deg


@pytest.mark.parametrize(
    "xtile,ytile,zoom,lat,lon",
    [
        (17599, 10751, 15, 52.48947038534305, 13.348388671875),
        (549, 336, 10, 52.48278022207821, 13.0078125),
    ],
)
def test_num2deg(xtile, ytile, zoom, lat, lon):
    assert num2deg(xtile, ytile, zoom) == (lat, lon)


@pytest.mark.parametrize(
    "xtile,ytile,zoom,west,east,south,north",
    [
        (
            8798,
            5375,
            14,
            13.3154296875,
            13.33740234375,
            52.48278022207821,
            52.4961595310971,
        ),
    ],
)
def test_get_bbox(xtile, ytile, zoom, west, east, south, north):
    assert get_bbox(xtile, ytile, zoom) == (west, east, south, north)
