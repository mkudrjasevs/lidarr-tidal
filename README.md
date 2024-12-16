<div align="center">
<h1>Lidarr++Tidal</h1>
<h4 style="font-style: italic">"If Lidarr and Tidal had a child"</h4>
</div>

(Based on [lidarr-deemix](https://github.com/ad-on-is/lidarr-deemix))

## 💡 How it works

Lidarr usually pulls artist and album infos from their own api api.lidarr.audio, which pulls the data from MusicBrainz.

However, MusicBrainz does not have many artists/albums, especially for some regional _niche_ artist.

This tool helps to enrich Lidarr, by providing a custom proxy, that _hooks into_ the process _without modifying Lidarr itself_, and **_injects additional artists/albums from Tidal_**.

#### To do that, the following steps are performed:

- [mitmproxy](https://mitmproxy.org/) runs as a proxy
- Lidarr needs to be configured to use that proxy.
- The proxy then **_redirects all_** api.lidarr.audio calls to an internally running **Python service** (_127.0.0.1:7171_)
- That Python service **replaces** the missing artists/albums with the ones found in Tidal
- Lidarr has now Tidal's artists/albums, and can do its thing.

## 💻️ Installation

> [!CAUTION]
> If you have installed an older version, please adjust the Proxy settings as described below, otherwise the HTTP-requests will fail

Use the following Docker Compose file:

```yaml
---
services:
  lidarr-tidal:
    image: ghcr.io/d3mystified/lidarr-tidal:main
    # build:
    #  context: /home/ada/apps/lidarr/lidarr-tidal-mitmproxy
    #  dockerfile: Dockerfile
    container_name: lidarr-tidal
    restart: always
    # ports: # optional - just use lidarr-tidal:8081 to connect from the lidarr container
    #   - 8687:8081
    volumes:
      - /path/to/config:/config
    environment:
      - LIDARR_URL=https://url.here
      - LIDARR_API_KEY=api.key
      - SESSION_CONFIG_FILE=/config/session.ini
      - CACHE_FILE=/config/cache.sqlite
      - SKIP_FILTERING_ALBUMS=False
```

- Use the provided Docker Compose above as an example.
  - **LIDARR_URL=http://lidarr:8686**: The URL of your Lidarr instance (with port), so this library can communicate with it.
  - **LIDARR_API_KEY=xxx**: The Lidarr API Key.
  - **SESSION_CONFIG_FILE=/config/session.ini**: Where Tidal session details are stored.
  - **CACHE_FILE=/config/cache.sqlite**: Where Tidal API calls are cached.
  - **SKIP_FILTERING_ALBUMS=False**: Suggest leaving this disabled unless you know exactly what it does.
- Go to **Lidarr -> Settings -> General**
  - **Certificate Validation:** to _Disabled_
  - **Use Proxy:** ✅
  - **Proxy Type:** HTTP(S)
  - **Hostname:** container-name/IP of the machine where lidarr-deemix is running
  - **Port:** 8081 (if using container-name), otherwise the port you exposed the service to
  - **Bypass Proxy for local addresses:** ✅


## Development

### Using Docker

```
docker compose build lidarr-tidal
docker compose up -d
```

Then run the container using docker compose.

### Without Docker

```
pip3 install -r src/requirements.txt
LIDARR_URL=https://url.here LIDARR_API_KEY=api.key SESSION_CONFIG_FILE=src/session.ini CACHE_FILE=src/cache.sqlite SKIP_FILTERING_ALBUMS=False python3 src/index.py
```
