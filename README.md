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

# TODOs:

- Update sample docker-compose file
- Update instructions below
- Ensure instructions for new setup are clear (session.ini file)

## TODO: These need to be updated.

- Use the provided [docker-compose.yml](./docker-compose.yml) as an example.
  - **DEEMIX_ARL=xxx** your deezer ARL (get it from your browsers cookies)
  - **PRIO_DEEMIX=true** If albums with the same name exist, prioritize the ones comming from deemix
  - **OVERRIDE_MB=true** override MusicBrainz completely - **WARNING!** This will delete all your artists/albums imported from MusicBrainz.
  - **LIDARR_URL=http://lidarr:8686** The URL of your Lidarr instance (with port), so this library can communicate with it. Important for **OVERRIDE_MB**
  - **LIDARR_API_KEY=xxx** The Lidarr API Key. Important for **OVERRIDE_MB**
- Go to **Lidarr -> Settings -> General**
  - **Certificate Validation:** to _Disabled_
  - **Use Proxy:** ✅
  - **Proxy Type:** HTTP(S)
  - **Hostname:** container-name/IP of the machine where lidarr-deemix is running
  - **Port:** 8080 (if using container-name), otherwise the port you exposed the service to
  - **Bypass Proxy for local addresses:** ✅
