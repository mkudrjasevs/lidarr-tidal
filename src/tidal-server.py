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

@app.route('/search/artists')
def search_artists():
    (query, offset, limit) = get_search_params()
    search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.artist.Artist])["artists"]
    dicts = [to_dict(a) for a in search_results]
    for i, a in enumerate(dicts):
        a["picture_xl"] = search_results[i].image()
    return { "data": dicts }

@app.route('/search/albums')
def search_albums():
    (query, offset, limit) = get_search_params()
    search_results = session.search(query=query, offset=offset, limit=limit, models=[tidalapi.album.Album])["albums"]
    dicts = [to_dict(a) for a in search_results]
    for i, a in enumerate(dicts):
        a["cover_xl"] = search_results[i].image()
    return { "data": dicts }

@app.route('/albums/<album_id>')
def album(album_id):
    album = session.album(album_id)
    album_dict = to_dict(album)
    album_dict['cover_xl'] = album.image()
    return { "data": album_dict }

@app.route('/artists/<artist_id>')
def artist(artist_id):
    artist = session.artist(artist_id)
    artist_dict = to_dict(artist)
    artist_dict['picture_xl'] = artist.image()
    artist_dict['top'] = [to_dict(a) for a in artist.get_top_tracks(limit=100)]
    artist_dict['albums'] = [to_dict(a) for a in artist.get_albums(limit=200)]
    artist_dict['albums'].extend([to_dict(a) for a in artist.get_ep_singles(limit=200)])
    return { "data": artist_dict }

@app.route('/artists/<artist_id>/top')
def artist_top(artist_id):
    artist = session.artist(artist_id)
    return { "data": [to_dict(a) for a in artist.get_top_tracks(limit=100)] }

@app.route('/album/<album_id>/tracks')
def album_tracks(album_id):
    album = session.album(album_id)
    return { "data": to_dict(album.tracks()) }

@app.route('/artists/<artist_id>/albums')
def artist_albums(artist_id):
    artist = session.artist(artist_id)
    albums_dict = [to_dict(a) for a in artist.get_albums(limit=200)]
    albums_dict.extend([to_dict(a) for a in artist.get_ep_singles(limit=200)])
    return { "data": albums_dict }

if __name__ == '__main__':
    print("TidalApiHelper running at http://0.0.0.0:7272")
    app.run(host="0.0.0.0", port=7272, debug=True)
