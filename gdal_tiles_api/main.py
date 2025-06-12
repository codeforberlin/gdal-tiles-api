from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .config import find_map, load_config
from .utils import extract_tile, get_bbox

config = load_config()

app = FastAPI()


@app.get("/")
def read_root():
    return (
        {
            "name": m.name,
            "url": m.get_url(config.tiles.host),
            "attribution": m.attribution,
        }
        for m in config.maps
    )


@app.get("/{path:path}/{z:int}/{x:int}/{y:int}.png")
def read_tile(path: Path, z: int, x: int, y: int):
    map_config = find_map(config, path)
    if map_config is None:
        raise HTTPException(status_code=404, detail="No map found under this path.")

    dataset_path = map_config.get_dataset_path(config.tiles.path)
    if dataset_path.exists():
        bbox = get_bbox(x, y, z)
        stream = extract_tile(dataset_path, *bbox)
        return StreamingResponse(stream, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="No tiles found under this path.")
