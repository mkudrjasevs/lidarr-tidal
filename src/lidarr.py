import requests
from typing import Optional, Dict, Any
import os

from helpers import normalize

lidarr_api_url = "https://api.musicinfo.pro"


def get_lidarr_artist(name: str) -> Optional[Dict[str, Any]]:
  """
  Fetches artist information from Lidarr API based on a name (fuzzy match).

  Args:
      name: The artist name to search for.

  Returns:
      A dictionary containing artist information if found, otherwise None.
  """
  url = f"{lidarr_api_url}/api/v0.4/search?type=all&query={name}"
  with requests.get(url) as response:
    response.raise_for_status()  # Raise exception for non-2xx status codes
    json_data = response.json()

    artist = next((item for item in json_data
                   if item.get("album") is None
                   and item.get("artist") is not None
                   and normalize(item["artist"]["artistname"]) == normalize(name)), None)

    return artist.get("artist") if artist else None


def get_all_lidarr_artists() -> list[Dict[str, Any]]:
  """
  Fetches all artists from Lidarr API.

  Returns:
      A list of dictionaries containing artist information.
  """
  url = f"{os.environ.get('LIDARR_URL')}/api/v1/artist"
  headers = {"X-Api-Key": os.environ.get("LIDARR_API_KEY")}
  with requests.get(url, headers=headers) as response:
    response.raise_for_status()
    return response.json()
