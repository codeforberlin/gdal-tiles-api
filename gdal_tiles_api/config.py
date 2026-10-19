import tomllib
from html import escape
from pathlib import Path

from deepmerge import always_merger
from pydantic import BaseModel


class Reference(BaseModel):
    text: str
    href: str | None = None

    def to_html(self):
        if self.href:
            return (
                f'<a href="{escape(self.href)}" target="_blank" rel="noopener">'
                f"{escape(self.text)}</a>"
            )
        return escape(self.text)


class Tiles(BaseModel):
    host: str
    path: Path
    min_zoom: int | None = None
    max_zoom: int | None = None


class Map(BaseModel):
    path: Path
    dataset: str | None = None
    name: str | None = None
    attribution: Reference | None = None
    rights: Reference | None = None
    min_zoom: int | None = None
    max_zoom: int | None = None

    def get_dataset_path(self, path):
        return path / (self.dataset or (self.path / "tiles.vrt"))

    def get_url(self, config):
        return f"{config.tiles.host}/{self.path}/{{z}}/{{x}}/{{y}}.png"

    def get_attribution(self):
        parts = [ref.to_html() for ref in (self.attribution, self.rights) if ref]
        return " / ".join(parts) or None

    def get_options(self, config):
        options = {}

        attribution = self.get_attribution()
        if attribution is not None:
            options["attribution"] = attribution

        min_zoom = self.min_zoom if self.min_zoom is not None else config.tiles.min_zoom
        if min_zoom is not None:
            options["minZoom"] = min_zoom

        max_zoom = self.max_zoom if self.max_zoom is not None else config.tiles.max_zoom
        if max_zoom is not None:
            options["maxZoom"] = max_zoom

        return options

    def to_dict(self, config):
        data = {
            "name": self.name,
            "url": self.get_url(config),
        }

        options = self.get_options(config)
        if options:
            data["options"] = options

        return data


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
