import requests_cache
from urllib.parse import unquote
from requests.exceptions import JSONDecodeError as requestsJSONDecodeError
from json import JSONDecodeError
import os
import tidalapi
from configparser import ConfigParser
from datetime import timedelta
import logging

from helpers import title_case, normalize, remove_keys, fake_id, get_type, convert_date_format
from lidarr import get_all_lidarr_artists

logging.basicConfig(level='DEBUG')
# Cache HTTP requests for 1 minute
urls_expire_after = {
    'resources.tidal.com/*': 60 * 60 * 24 * 7, # 1 week
    'api.tidal.com/v1/sessions*': requests_cache.DO_NOT_CACHE,
    'api.tidal.com/v1/users*': requests_cache.DO_NOT_CACHE,
    'auth.tidal.com/*': requests_cache.DO_NOT_CACHE,
    'api.tidal.com/v1/*': 60 * 60 * 24, # 1 day
    'api.lidarr.audio/*': requests_cache.DO_NOT_CACHE,
    'ws.audioscrobbler.com/*': requests_cache.DO_NOT_CACHE,
}
requests_cache.install_cache(cache_name=os.environ.get('CACHE_FILE'),
                             backend='sqlite',
                             urls_expire_after=urls_expire_after,
                             expire_after=60, # default cache for a minute
                             allowable_codes=[200],
                             ignored_parameters=['sessionId'],
                             allowable_methods=('GET'))

############################################
## Establish Tidal session
############################################

session_path = os.environ.get('SESSION_CONFIG_FILE')
session = tidalapi.Session()

# If session file exists, use that
if os.path.isfile(session_path):
    config = ConfigParser()
    config.read([session_path])
    try:
        session.load_oauth_session(
            config['session']['token_type'],
            config['session']['access_token'],
            config['session'].get('refresh_token', None),
            config['session'].get('expiry_time', None)
        )
    except KeyError:
        print('supplied configuration to restore session is incomplete')
    else:
        if not session.check_login():
            print('loaded session appears to be not authenticated')


if not session.check_login():
    print('authenticating new session')
    session.login_oauth_simple()
    config = ConfigParser()
    config['session'] = {
        'token_type': session.token_type,
        'access_token': session.access_token,
        'refresh_token': session.refresh_token,
        'expiry_time': session.expiry_time
    }
    with open(session_path, 'w') as configfile:
        config.write(configfile)


def to_dict(obj, level=0):
    if level >= 4:
        return None

    if isinstance(obj, dict):
        return {k: to_dict(v, level=level+1) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(v, level=level+1) for v in obj]
    elif isinstance(obj, timedelta):
            return int(obj)
    elif hasattr(obj, '__dict__'):
        result = {}
        for k, v in obj.__dict__.items():
            try:
                result[k] = to_dict(v, level=level+1)
            except Exception:
                pass  # Skip fields that raise exceptions
        return result
    else:
        return obj


############################################
## Tidal helpers
############################################

"""
Removes duplicate entries based on the following logic:
- Any DOLBY_ATMOS are removed
- Any with "version" are removed (deluxe, remaster, mix etc)
- Keep the highest popularity if the names match
- If there are ties with popularity, keep the entry with the highest quality
"""
def filter_items(items):
    if os.environ.get('SKIP_FILTERING_ALBUMS', 'False').lower() == 'true':
        return [to_dict(i) for i in items]

    unique_items = {}
    print("Filtering items, originally received {} items".format(len(items)))
    
    for i in items:
        item = to_dict(i)
        name = item['name']
        popularity = item['popularity']
        dolby_atmos = 'DOLBY_ATMOS' in item.get('audio_modes', [])
        hires_lossless = 'HIRES_LOSSLESS' in item.get('media_metadata_tags', [])
        lossless = 'LOSSLESS' in item.get('media_metadata_tags', [])
        has_version = item.get('version') is not None and item.get('version') != ''

        # print("Processing name={}, id={}, popularity={}, dolby_atmos={}, hires_lossless={}, lossless={}, has_version={}".format(
        #     item['name'], item['id'], popularity, dolby_atmos, hires_lossless, lossless, has_version))

        if has_version:
            continue
        if name not in unique_items:
            # print("Adding {} to unique_items".format(item['id']))
            unique_items[name] = item
        elif popularity > unique_items.get(name, {}).get('popularity', 0):
            # print("Adding {} to unique_items".format(item['id']))
            unique_items[name] = item
        # elif popularity == unique_items[name]['popularity']:
        #     if not dolby_atmos and (hires_lossless or lossless):
        #         print("Adding {} to unique_items".format(item['id']))
        #         unique_items[name] = item

    print("Filtered down to {} items".format(len(unique_items.values())))
    return list(unique_items.values())

############################################
## Tidal API calls
############################################

def search_artists(query, offset, limit):
    try:
        search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.artist.Artist])["artists"]
        dicts = [to_dict(a) for a in search_results]
        for i, a in enumerate(dicts):
            a["picture_xl"] = search_results[i].image()
    except (Exception, TypeError) as e:
        print(f"Error for search artists {query}: {e}")
        dicts = []
    return { "data": dicts }

def search_albums(query, offset, limit):
    try:
        search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.album.Album])["albums"]
        dicts = [to_dict(a) for a in search_results]
        for i, a in enumerate(dicts):
            a["cover_xl"] = search_results[i].image()
    except (Exception, TypeError) as e:
        print(f"Error for search albums {query}: {e}")
        dicts = []
    return { "data": dicts }

def album(album_id):
    try:
        album = session.album(album_id)
        album_dict = to_dict(album)
        album_dict['cover_xl'] = album.image()
    except (Exception, TypeError) as e:
        print(f"Error retrieving album {album_id}: {e}")
        album_dict = {}
    return { "data": album_dict }

def artist(artist_id):
    try:
        artist = session.artist(artist_id)
        artist_dict = to_dict(artist)
        artist_dict['picture_xl'] = artist.image()
        artist_dict['top'] = filter_items(artist.get_top_tracks(limit=100))
        artist_dict['albums'] = filter_items(artist.get_albums(limit=200))
        artist_dict['albums'].extend(filter_items(artist.get_ep_singles(limit=200)))
    except (Exception, TypeError) as e:
        print(f"Error retrieving artist {artist_id}: {e}")
        artist_dict = {}

    return {"data": artist_dict}

def artist_top(artist_id):
    try:
        artist = session.artist(artist_id)
        return { "data": filter_items(artist.get_top_tracks(limit=100))}
    except (Exception, TypeError) as e:
        print(f"Error retrieving top for artist {artist_id}: {e}")
        return { "data": [] }

def album_tracks(album_id):
    try:
        album = session.album(album_id)
        return { "data": to_dict(album.tracks()) }
    except (Exception, TypeError) as e:
        print(f"Error retrieving tracks for album {album_id}: {e}")
        return { "data": [] }

def artist_albums(artist_id):
    try:
        artist = session.artist(artist_id)
        albums_dict = filter_items(artist.get_albums(limit=20))
        albums_dict.extend(filter_items(artist.get_ep_singles(limit=200)))
    except (Exception, TypeError) as e:
        print(f"Error retrieving albums for artist {artist_id}: {e}")
        albums_dict = []
    return { "data": albums_dict }

############################################
## Tidal Convenience Wrappers
############################################

def tidal_artists(name: str) -> list:
    """
    Fetches artists from Tidal based on the given name.

    Args:
    name: The name of the artist to search for.

    Returns:
    A list of artist data.
    """
    print(f"Fetching artists from Tidal for name: {name}")
    data = search_artists(query=name, offset=0, limit=100)
    return data["data"]
  
def tidal_album(id: str) -> dict:
    """
    Fetches album details from Tidal based on the album ID.

    Args:
    id: The ID of the album to fetch.

    Returns:
    A dictionary containing album details.
    """

    print(f"Fetching album from Tidal for id: {id}")
    data = album(id)
    return data["data"]

def tidal_tracks(id: str) -> list:
    """
    Fetches tracks from an album on Tidal based on the album ID.

    Args:
    id: The ID of the album to fetch tracks from.

    Returns:
    A list of track data.
    """
    print(f"Fetching tracks from Tidal for album id: {id}")
    data = album_tracks(id)
    return data.get("data", [])

def tidal_artist(id: str) -> dict:
    print(f"Fetching artist from Tidal for id: {id}")
    data = artist(id)
    j = data['data']

    return {
        "Albums": [
            {
                "Id": fake_id(a["id"], "album"),
                "OldIds": [],
                "ReleaseStatuses": ["Official"],
                "SecondaryTypes": ["Live"] if a["name"].lower().find("live") != -1 else [],
                "Title": a["name"],
                "Type": get_type(a["type"]),
            } for a in j["albums"]
        ],
        "artistaliases": [],
        "artistname": j["name"],
        "disambiguation": "",
        "genres": [],
        "id": fake_id(j["id"], "artist"),
        "images": [{ "CoverType": "Poster", "Url": j["picture_xl"] }],
        "links": [
            {
                "target": j["listen_url"],
                "type": "tidal",
            }
        ],
        "oldids": [],
        "overview": "!!--Imported from Tidal--!!",
        "sortname": ", ".join(reversed(j["name"].split(" "))),
        "status": "active",
        "type": "Artist",
    }

def tidal_albums(name: str) -> list:
    total = 0
    start = 0

    print(f"Fetching artist from Tidal for id: {id}")
    response = search_albums(query=name, offset=0, limit=1)
    total = len(j["data"])

    albums = []
    while start < total:
        print(f"Searching albums in Tidal with name {name} and offset {start}")
        response = search_albums(query=name, offset=start, limit=100)
        albums.extend(response["data"])
        start += 100

    return [a for a in albums if normalize(a["artist"]["name"]) == normalize(name) or a["artist"]["name"] == "Verschillende artiesten"]

def get_album(id: str):
    d = tidal_album(id)
    if not d or not d.get('artists', None):
        return None

    contributors = [
        {
            "id": fake_id(c["id"], "artist"),
            "artistaliases": [],
            "artistname": c["name"],
            "disambiguation": "",
            "overview": "!!--Imported from Tidal--!!",
            "genres": [],
            "images": [],
            "links": [],
            "oldids": [],
            "sortname": ", ".join(list(reversed(c["name"].split(" ")))),
            "status": "active",
            "type": "Artist",
        }
        for c in d["artists"]
    ]

    lidarr_artists = get_all_lidarr_artists()

    tidal = None
    for la in lidarr_artists:
        for c in contributors:
            if la["artistName"] == c["artistname"] or normalize(la["artistName"]) == normalize(c["artistname"]):
                tidal = c
                break

    lidarr2 = {
        "id": tidal["id"],
        "artistname": tidal["artistname"],
        "artistaliases": [],
        "disambiguation": "",
        "overview": "",
        "genres": [],
        "images": [],
        "links": [],
        "oldids": [],
        "sortname": ", ".join(list(reversed(tidal["artistname"].split(" ")))),
        "status": "active",
        "type": "Artist",
    }

    # Process album tracks
    tracks = tidal_tracks(d["id"])
    if not tracks:
        return None

    # Get unique disc/volume nums
    volume_nums = list(set([t["volume_num"] for t in tracks]))
    
    # Build media information for each unique track
    media = [
        {"Format": "CD", "Name": "", "Position": v}
        for v in volume_nums
    ]

    # Build track information for each track
    tracks_info = [
        {
            "artistid": lidarr2["id"],
            "durationms": t["duration"] * 1000,
            "id": f"{fake_id(t['id'], 'track')}",
            "mediumnumber": t["volume_num"],
            "oldids": [],
            "oldrecordingids": [],
            "recordingid": fake_id(t["id"], "recording"),
            "trackname": t["name"],
            "tracknumber": f"{idx + 1}",
            "trackposition": idx + 1,
        }
        for idx, t in enumerate(tracks)
    ]

    # Build the final album information dictionary
    return {
        "aliases": [],
        "artistid": lidarr2["id"],
        "artists": [lidarr2],
        "disambiguation": "",
        "genres": [],
        "id": f"{fake_id(d['id'], 'album')}",
        "images": [{"CoverType": "Cover", "Url": d["cover_xl"]}],
        "links": [],
        "oldids": [],
        "overview": "!!--Imported from Tidal--!!",
        "releasedate": convert_date_format(d["release_date"]),
        "releases": [
            {
                "country": ["Worldwide"],
                "disambiguation": "",
                "id": f"{fake_id(d['id'], 'release')}",
                "label": [d["copyright"]],
                "media": media,
                "oldids": [],
                "releasedate": convert_date_format(d["release_date"]),
                "status": "Official",
                "title": title_case(d["name"]),
                "track_count": d["num_tracks"],
                "tracks": tracks_info,
            },
        ],
        "secondarytypes": ["Live"] if d["name"].lower().find("live") != -1 else [],
        "title": title_case(d["name"]),
        "type": get_type(d["type"]),
    }

def search(query):
    tartists = tidal_artists(query)
    if not tartists:
        return None

    dtolartists = [
        {
            "album": None,
            "artist": {
                "artistaliases": [],
                "artistname": d["name"],
                "sortname": ", ".join(reversed(d["name"].split(" "))),
                "genres": [],
                "id": fake_id(d["id"], "artist"),
                "images": [
                    {
                        "CoverType": "Poster",
                        "Url": d["picture_xl"],
                    }
                ],
                "links": [
                    {
                        "target": d["listen_url"],
                        "type": "tidal",
                    }
                ],
                "type": "Artist",
                "status": "active",
                "disambiguation": "",
                "oldids": [],
                "overview": "",
            },
            "score": 100,
        }
        for d in tartists
    ]

    sorted_artists = []
    for a in dtolartists:
        if (
            a["artist"]["artistname"] == unquote(query)
            or normalize(a["artist"]["artistname"]) == normalize(unquote(query))
        ):
            sorted_artists.insert(0, a)
        else:
            sorted_artists.append(a)
    dtolartists = sorted_artists

    return dtolartists

def get_artist_by_name(name: str):
    artists = tidal_artists(name)
    if not artists:
        return None

    artist = next((a for a in artists if a["name"] == name or normalize(a["name"]) == normalize(name)), None)
    if artist is not None:
        return tidal_artist(artist['id'])
    return None
