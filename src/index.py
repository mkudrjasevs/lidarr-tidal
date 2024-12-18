from flask import Flask, request, jsonify
import requests
import os

from tidal import (
    search,
    get_album,
    tidal_artist,
    get_artist_by_name,
)
from helpers import remove_keys

app = Flask(__name__)

lidarr_api_url = "https://api.lidarr.audio"
scrobbler_api_url = "https://ws.audioscrobbler.com"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    headers = request.headers
    host = headers.get("x-proxy-host")
    if host == "ws.audioscrobbler.com":
        return do_scrobbler(request)
    return do_api(request, path)


def do_scrobbler(req):
    url = f"{scrobbler_api_url}{req.path}{req.query_string}"
    method = req.method
    body = req.get_data()

    headers = {key: value for key, value in req.headers.items() if key not in ("host", "connection")}

    try:
        response = requests.request(method, url, headers=headers, data=body)
        response.headers.pop("content-encoding", None)  # Remove content-encoding header
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    # Override MB data
    data = remove_keys(response.json(), "mbid")
    return jsonify(data), response.status_code


def do_api(req, path):
    url = f"{lidarr_api_url}/{path}"
    method = req.method
    body = req.get_data()
    # TODO: do I need these headers?
    # headers = {key: value for key, value in req.headers.items() if key not in ("host", "connection")}
    headers = {}
    try:
        response = requests.request(method, url, headers=headers, data=body)
        response.headers.pop("content-encoding", None)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    lidarr_data = response.json()
    status_code = 200 if lidarr_data is not None else 404

    if "/ping" in url:
        return jsonify({ "health": "pong" }), 200

    elif "/v0.4/search" in url or "/v1/search" in url:
        query = req.args.get("query")
        lidarr_data = search(query)
        status_code = 200 if lidarr_data is not None else 404
        return jsonify(lidarr_data), status_code

    elif "/v0.4/artist/" in url or "/v1/artist/" in url:
        if "-aaaa-" in path:
            artist_id = path.split("/")[-1].split("-")[-1].replace("a", "")
            lidarr_data = tidal_artist(artist_id)
            status_code = 200 if lidarr_data is not None else 404
        else:
            # This is added to make the service work with existing artists in
            # lidarr that use MBID.
            lidarr_data = get_artist_by_name(lidarr_data['artistname'])
            # Set old ID here (MBID)
            lidarr_data['oldids'] = [lidarr_data['id']]
            status_code = 200 if lidarr_data is not None else 404
        return jsonify(lidarr_data), status_code

    elif "/v0.4/album/" in url or "/v1/album/" in url:
        if "-bbbb-" in path:
            album_id = path.split("/")[-1].split("-")[-1].replace("b", "")
            lidarr_data = get_album(album_id)
            # 502 because the album definitely exists, might be running into rate limit
            status_code = 200 if lidarr_data is not None else 502
        return jsonify(lidarr_data), status_code

    # Passthrough to Lidarr api (for example for Charts and Series)
    return jsonify(lidarr_data), status_code


if __name__ == "__main__":
    from waitress import serve
    print("lidarr-tidal running at http://0.0.0.0:7171")
    serve(app, host="0.0.0.0", port=7171)