"""Redirect HTTP requests to another server."""

from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    # pretty_host takes the "Host" header of the request into account,
    # which is useful in transparent mode where we usually only have the IP
    # otherwise.
    if flow.request.pretty_host == "https://api.musicinfo.pro/api/v0.4/spotify/":
        pass
    elif flow.request.pretty_host == "api.musicinfo.pro" or flow.request.pretty_host == "ws.audioscrobbler.com":
        print("flow")
        flow.request.headers["X-Proxy-Host"] = flow.request.pretty_host
        flow.request.scheme = "http"
        flow.request.host = "127.0.0.1"
        flow.request.port = 7171
