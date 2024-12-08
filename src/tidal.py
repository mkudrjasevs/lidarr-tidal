import requests
from urllib.parse import unquote
from requests.exceptions import JSONDecodeError as requestsJSONDecodeError
from json import JSONDecodeError

from helpers import title_case, normalize, remove_keys, fake_id, get_type, convert_date_format
from lidarr import get_all_lidarr_artists

tidal_url = "http://127.0.0.1:7272"

def tidal_artists(name: str) -> list:
    """
    Fetches artists from Tidal based on the given name.

    Args:
    name: The name of the artist to search for.

    Returns:
    A list of artist data.
    """
    print(f"Fetching artists from Tidal for name: {name}")
    response = requests.get(f"{tidal_url}/search/artists?limit=100&offset=0&q={name}")
    try:
        data = response.json()
    except (JSONDecodeError, requestsJSONDecodeError) as e:
        print(f"Error getting artists by name {name}: {e}")
        return []
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
    response = requests.get(f"{tidal_url}/albums/{id}")
    try:
        data = response.json()
    except (JSONDecodeError, requestsJSONDecodeError) as e:
        print(f"Error getting album by id {id}: {e}")
        return None
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
    response = requests.get(f"{tidal_url}/album/{id}/tracks")
    try:
        data = response.json()
    except (JSONDecodeError, requestsJSONDecodeError) as e:
        print(f"Error getting tracks for album {id}: {e}")
        return []
    return data.get("data", [])

def tidal_artist(id: str) -> dict:
    print(f"Fetching artist from Tidal for id: {id}")
    response = requests.get(f"{tidal_url}/artists/{id}")
    try:
        j = response.json()['data']
    except (JSONDecodeError, requestsJSONDecodeError) as e:
        print(f"Error getting artist by id {id}: {e}")
        return None

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
    response = requests.get(f"{tidal_url}/search/albums?limit=1&offset=0&q={name}")
    try:
        j = response.json()
        total = len(j["data"])
    except (JSONDecodeError, requestsJSONDecodeError) as e:
        print(f"Error getting artist by id {id}: {e}")
        return []

    albums = []
    while start < total:
        print(f"Searching albums in Tidal with name {name} and offset {start}")
        response = requests.get(f"{tidal_url}/search/albums?limit=100&offset={start}&q={name}")
        try:
            j = response.json()
            albums.extend(j["data"])
            start += 100
        except (JSONDecodeError, requestsJSONDecodeError) as e:
            print(f"Error getting albums by name {name}, offset={start}: {e}")
            continue

    return [a for a in albums if normalize(a["artist"]["name"]) == normalize(name) or a["artist"]["name"] == "Verschillende artiesten"]

def get_album(id: str):
    d = tidal_album(id)
    if d is None:
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

# def get_albums(name: str):
#     """Fetches and processes album data from Tidal based on a search term.

#     This function retrieves information about albums matching the provided name
#     from a service like Tidal (replace with your actual Tidal API implementation)
#     and then processes it to conform to a specific format.

#     Args:
#     name: The search term to use for finding albums in Tidal.

#     Returns:
#     A list of dictionaries containing processed album information.
#     """
#     # Fetch album data from Tidal
#     talbums = tidal_albums(name)

#     # Process album information
#     dto_ralbums = [
#         {
#             "Id": f"{fake_id(d['id'], 'album')}",
#             "OldIds": [],
#             "ReleaseStatuses": ["Official"],
#             "SecondaryTypes": ["Live"] if d["name"].lower().find("live") != -1 else [],
#             "Title": title_case(d["name"]),
#             "LowerTitle": d["name"].lower(),
#             "Type": get_type(d["type"]),
#         }
#         for d in talbums
#     ]

#     # Remove duplicates based on lowercase title
#     unique_albums = list(
#         {
#             a['LowerTitle']: a
#             for a in dto_ralbums
#         }.values()
#     )
#     return unique_albums

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