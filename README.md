GDAL-Tiles-API
==============

This API cuts out tiles (e.g., for [Leaflet](https://leafletjs.com/)) from
[Cloud Optimized GeoTIFFs (COG)](https://cogeo.org) or other datasets using
[GDAL](https://gdal.org). It is used on `https://tiles.codefor.de`.

It is meant to replace [TileStache](https://github.com/TileStache/TileStache) (which seems unmaintained), but only
it's `TileStache.Goodies.Providers.GDAL:Provider`. A similar workflow could be implemented using
[TiTiler](https://developmentseed.org/titiler/) or [Terracotta](https://terracotta-python.readthedocs.io), but both
tools have a different focus, and a lot of additional features.

The core functionality of the API is provided by a call to
[gdal.Warp](https://gdal.org/en/stable/programs/gdalwarp.html)
(which is apearantly faster than `gdal.ReprojectImage` used by TileStache):

```python
gdal.Warp(
        '',
        dataset_path,
        format='MEM',
        dstSRS="EPSG:4326",
        outputBounds=(west, south, east, north),
        width=width,
        height=height,
        resampleAlg='cubic'
    )
```

For optimal performance, the input dataset should be a valid COG or a
[VRT](https://gdal.org/en/stable/drivers/raster/vrt.html) composed of COG.
Such datasets can be created with GDAL, e.g.:

```bash
gdal_translate INPUT OUTPUT \
    -of COG -b 1 -b 2 -b 3 -a_srs EPSG:25833 \
    -co COMPRESS=JPEG -co QUALITY=75 -co BLOCKSIZE=512 \
    -co OVERVIEWS=IGNORE_EXISTING -co NUM_THREADS=4 \
```

Like TiTiler, GDAL-Tiles-API is build using [FastAPI](https://fastapi.tiangolo.com/).

Setup
-----

Instal [GDAL](https://gdal.org/en/stable/), e.g. for Debian 12:

```bash
sudo apt-get install gdal-bin libgdal-dev
```

Install the matching GDAL python bindings (in a virtual environment):

```bash
pip install GDAL==3.6.2
```

Install the package

```bash
pip install gdal-tiles-api
pip install https://github.com/codeforberlin/gdal-tiles-api  # directly from GitHub
```

Usage
-----

The API expects a `config.toml` in the current directory and/or a set of `.toml` files in a `config.d` directory
(which are all merged into one config object).

The config file(s) look like this:

```toml
[tiles]
host = 'https://tiles.codefor.de'
path = "/data"

[[maps]]
name = "Digitale farbige TrueOrthophotos 2024 (DOP20RGBI)"
path = "berlin/geoportal/luftbilder/2024-dop20rgbi/tiles.vrt"
attribution.text = "Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen Berlin / Digitale farbige Orthophotos 2024 (DOP20RGBI)"
attribution.href = "https://gdi.berlin.de/geonetwork/srv/ger/catalog.search#/metadata/aff8a8a5-2b48-44e8-949b-ea5f7d382a4f"

[[maps]]
path = "berlin/geoportal/luftbilder/2023-dop20rgbi"

[[maps]]
path = "berlin/geoportal/historische-karten/1750"
dataset = "cog/Berlin_1750_2.tif"
```

The actual path to the COG of the map build from the tiles path, the map path, and the dataset
(which defaults to `tiles.vrt`). For the config above, we get:

```
/data/berlin/geoportal/luftbilder/2024-dop20rgbi/tiles.vrt
/data/berlin/geoportal/luftbilder/2023-dop20rgbi/tiles.vrt
/data/berlin/geoportal/historische-karten/1750/cog/Berlin_1750_2.tif
```

The other entries are only displayed in the root url.

### Development server

The local developtment server can be started using:

```python
fastapi dev gdal_tiles_api/main.py
```

The API is then available at http://localhost:8000.

### Production deployment

In production, [gunicorn with the uvicorn](https://www.uvicorn.org/deployment/#gunicorn) should be used. In order
to run with Systemd, the a service similar to the following should be placed in `/etc/systemd/system/tiles.service`:

```
[Unit]
Description=GDAL-Tiles-API gunicorn daemon
After=network.target

[Service]
User=tiles
Group=tiles

WorkingDirectory=/srv/tiles/tiles-config

LogsDirectory=gunicorn
RuntimeDirectory=gunicorn

Environment="PATH=/srv/tiles/tiles-config/env/"
Environment="PYTHONUNBUFFERED=1"

ExecStart=gunicorn
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 5 \
    --bind unix:/run/gunicorn/tiles.sock \
    --pid /run/gunicorn/tiles.pid \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    gdal_tiles_api.main:app

ExecReload=/bin/sh -c '/usr/bin/pkill -HUP -F ${GUNICORN_PID_FILE}'

ExecStop=/bin/sh -c '/usr/bin/pkill -TERM -F ${GUNICORN_PID_FILE}'

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

The `gunicorn` should be reverse proxied using [NGINX](https://www.nginx.com/), with the create tiles cached by the
build in [Content Caching](https://docs.nginx.com/nginx/admin-guide/content-cache/content-caching/). The following
configuration can be used for this (in `/etc/nginx/sites-enabled/default`):

```
proxy_cache_path /tmp/nginx_cache keys_zone=tiles:10m max_size=10g use_temp_path=off;

proxy_connect_timeout 5;
proxy_send_timeout 5;
proxy_read_timeout 5;
send_timeout 5;

server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html;

    server_name _;

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        proxy_redirect off;
        proxy_buffering off;
        proxy_pass unix:/run/gunicorn/tiles.sock;

        proxy_cache tiles;
        proxy_cache_valid 200 302 404 7d;
        proxy_cache_use_stale error timeout updating;
        add_header X-Cache-Status $upstream_cache_status;
    }
```
