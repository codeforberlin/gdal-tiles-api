import tomllib
from pathlib import Path

from deepmerge import always_merger
from pydantic import BaseModel


class Tiles(BaseModel):
    host: str
    path: Path


class Map(BaseModel):
    path: Path
    dataset: str | None = None
    name: str | None = None
    attribution: dict | None = None

    def get_url(self, host):
        return f"{host}/{self.path}/{{z}}/{{x}}/{{y}}.png"

    def get_dataset_path(self, path):
        return path / (self.dataset or (self.path / "tiles.vrt"))


class Config(BaseModel):
    tiles: Tiles
    maps: list[Map]


def load_config() -> Config:
    config = {}

    if Path("config.toml").is_file():
        with open("config.toml", "rb") as f:
            always_merger.merge(config, tomllib.load(f))

    if Path("config.d").is_dir():
        for file_path in sorted(Path("config.d").glob("*.toml")):
            with open(file_path, "rb") as f:
                always_merger.merge(config, tomllib.load(f))

    if not config:
        raise RuntimeError(
            "No config found. Please place a config.toml and/or a config.d directory"
            " in the current working directory."
        )

    return Config(**config)


def find_map(config, path):
    try:
        return next(filter(lambda m: (m.path == path), config.maps))
    except StopIteration:
        return None
