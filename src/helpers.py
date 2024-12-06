import datetime
import unicodedata


def title_case(text: str) -> str:
    """Converts a string to title case."""
    words = text.lower().split()
    return ' '.join(word.capitalize() for word in words)


def normalize(text: str) -> str:
    """Normalizes a string by converting it to lowercase and removing accents."""
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode('ascii')


def remove_keys(obj: dict, keys: list) -> dict:
    """Removes keys from a dictionary, recursively if necessary."""
    for key in keys:
        if key in obj:
            del obj[key]
        elif isinstance(obj, dict):
            remove_keys(obj[key], keys)
    return obj


def fake_id(id: any, type: str) -> str:
  """
  Generates a fake ID based on the given ID and type.

  Args:
    id: The base ID to use.
    type: The type of ID, which determines the prefix character.

  Returns:
    The generated fake ID.
  """

  prefix = "a"
  if type == "album":
    prefix = "b"
  elif type == "track":
    prefix = "c"
  elif type == "release":
    prefix = "d"
  elif type == "recording":
    prefix = "e"

  id_str = str(id).zfill(12)
  return f"{prefix * 8}-{prefix * 4}-{prefix * 4}-{prefix * 4}-{id_str}"


def get_type(rc: str) -> str:
    type = rc.lower()
    if type == "ep":
        return "EP"
    return title_case(type)


def convert_date_format(date_string):
  """Converts a date string in the format 'Fri, 31 Jan 2020 00:00:00 GMT' to 'YYYY-MM-DD'.

  Args:
    date_string: The date string to convert.

  Returns:
    The converted date string in the format 'YYYY-MM-DD'.
  """

  date_object = datetime.datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %Z')
  formatted_date = date_object.strftime('%Y-%m-%d')
  return formatted_date