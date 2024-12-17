"""
Randomly refresh an artist in Lidarr.
Configure with crontab to run at least every 10 minutes.
"""
import requests
import json
from random import choice
import sys

# Define API details
base_url = "URL"
api_key = "API KEY"


def get_lidarr_data(url, headers):
    """Fetches data from the specified Lidarr API endpoint."""
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise exception for non-200 status codes

    return json.loads(response.text)


def refresh_random_artist(base_url, api_key):
    """Refreshes a random artist in Lidarr."""
    headers = {"Content-type": "application/json", "X-Api-Key": api_key}

    # Fetch all artists data
    print("Downloading Lidarr Artist Data. :)")
    url = f"{base_url}/api/v1/artist"
    artists = get_lidarr_data(url, headers)

    # Randomly pick an artist
    chosen_artist = choice(artists)
    artist_id = chosen_artist["id"]

    print(f"Processing {chosen_artist['artistName']} (ID {artist_id})...", end="")

    url = f"{base_url}/api/v1/command"

    # Send refresh command
    refresh_response = requests.post(
        url, headers=headers, json={"name": "RefreshArtist", "artistId": artist_id}
    )
    refresh_response.raise_for_status()

    print(" Success")


if __name__ == "__main__":
    try:
        refresh_random_artist(base_url, api_key)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        sys.exit(-1)
