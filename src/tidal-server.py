import os
import tidalapi
from pathlib import Path
from configparser import ConfigParser
from datetime import timedelta

from flask import Flask
from flask import request

app = Flask(__name__)

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

def get_search_params():
    return request.args.get('q'), request.args.get('offset'), request.args.get('limit')

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

@app.route('/search/artists')
def search_artists():
    (query, offset, limit) = get_search_params()
    try:
        search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.artist.Artist])["artists"]
        dicts = [to_dict(a) for a in search_results]
        for i, a in enumerate(dicts):
            a["picture_xl"] = search_results[i].image()
    except Exception as e:
        print(f"Error: {e}")
        dicts = []
    return { "data": dicts }

@app.route('/search/albums')
def search_albums():
    (query, offset, limit) = get_search_params()
    try:
        search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.album.Album])["albums"]
        dicts = [to_dict(a) for a in search_results]
        for i, a in enumerate(dicts):
            a["cover_xl"] = search_results[i].image()
    except Exception as e:
        print(f"Error: {e}")
        dicts = []
    return { "data": dicts }

@app.route('/albums/<album_id>')
def album(album_id):
    try:
        album = session.album(album_id)
        album_dict = to_dict(album)
        album_dict['cover_xl'] = album.image()
    except Exception as e:
        print(f"Error: {e}")
        album_dict = {}
    return { "data": album_dict }

@app.route('/artists/<artist_id>')
def artist(artist_id):
    try:
        artist = session.artist(artist_id)
        artist_dict = to_dict(artist)
        artist_dict['picture_xl'] = artist.image()
        artist_dict['top'] = filter_items(artist.get_top_tracks(limit=100))
        artist_dict['albums'] = filter_items(artist.get_albums(limit=200))
        artist_dict['albums'].extend(filter_items(artist.get_ep_singles(limit=200)))
    except Exception as e:
        print(f"Error: {e}")
        artist_dict = {}

    return {"data": artist_dict}

@app.route('/artists/<artist_id>/top')
def artist_top(artist_id):
    try:
        artist = session.artist(artist_id)
        return { "data": filter_items(artist.get_top_tracks(limit=100))}
    except Exception as e:
        print(f"Error: {e}")
        return { "data": [] }

@app.route('/album/<album_id>/tracks')
def album_tracks(album_id):
    try:
        album = session.album(album_id)
        return { "data": to_dict(album.tracks()) }
    except Exception as e:
        print(f"Error: {e}")
        return { "data": [] }

@app.route('/artists/<artist_id>/albums')
def artist_albums(artist_id):
    try:
        artist = session.artist(artist_id)
        albums_dict = filter_items(artist.get_albums(limit=20))
        albums_dict.extend(filter_items(artist.get_ep_singles(limit=200)))
    except Exception as e:
        print(f"Error: {e}")
        albums_dict = []
    return { "data": albums_dict }

if __name__ == '__main__':
    from waitress import serve
    print("TidalServer running at http://0.0.0.0:7272")
    serve(app, host="0.0.0.0", port=7272)
