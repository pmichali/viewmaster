"""Extract ReST API info and convert for storage."""

import logging
import re
from datetime import time


CATEGORY_CHOICES = [
    ("ACTION", "action"),
    ("ADVENTURE", "adventure"),
    ("ANIMATED", "animated"),
    ("BIOGRAPHY", "biography"),
    ("CHILDRENS", "childrens"),
    ("COMEDY", "comedy"),
    ("CRIME", "crime"),
    ("DOCUMENTARY", "documentary"),
    ("DRAMA", "drama"),
    ("FAMILY", "family"),
    ("FANTASY", "fantasy"),
    ("HISTORY", "history"),
    ("HORROR", "horror"),
    ("MILITARY", "military"),
    ("MISC", "misc"),
    ("MUSICAL", "musical"),
    ("MYSTERY", "mystery"),
    ("ROMANCE", "romance"),
    ("SCI-FI", "sci-fi"),
    ("SPORTS", "sports"),
    ("SUSPENSE", "suspense"),
    ("THRILLER", "thriller"),
    ("UNKNOWN", "unknown"),
    ("WESTERN", "western"),
]


RATING_CHOICES = [
    ("G", "G"),
    ("PG", "PG"),
    ("PG-13", "PG-13"),
    ("R", "R"),
    ("X", "X"),
    ("NR", "NR"),
    ("?", "?"),
]


RATINGS_DICT = dict(RATING_CHOICES)
RATINGS_DICT["Not Rated"] = "NR"

CATEGORY_DICT = dict(CATEGORY_CHOICES)

logger = logging.getLogger(__name__)
year_re = re.compile(r"\d+")


def extract_time(time_str):
    """Convert textual time to hours/mins.

    Expect input to be "# mins" and want output "HH:MM".
    """
    logger.debug("extract time: %s", time_str)
    total_mins, _, _ = time_str.partition(" ")
    if not total_mins.isdigit():
        return "00:00"
    hours = int(total_mins) // 60
    minutes = int(total_mins) % 60
    return f"{hours:02d}:{minutes:02d}"


def extract_duration(time_str):
    """Convert textual time to hours/mins.

    Expect input to be "# mins" and want output "HH:MM".
    """
    logger.debug("extract time: %s", time_str)
    total_mins, _, _ = time_str.partition(" ")
    if not total_mins.isdigit():
        return time(hour=0, minute=0)
    hours = int(total_mins) // 60
    minutes = int(total_mins) % 60
    return time(hour=hours, minute=minutes)


def extract_rating(rating):
    """Ensure rating within set of known ratings."""
    return RATINGS_DICT.get(rating, "NR")


def extract_year(year):
    """Ensure year is just a number."""

    m = year_re.match(year)
    if not m:
        return 0
    return int(m.group())


MUSIC_RE = re.compile(r"^MUSIC$")


def order_genre_choices(suggested):
    """Validate provided genre choices and prepend to the list of allowable."""
    suggested_genres = suggested.split(", ")
    if not suggested:
        logger.debug("No suggested genres, so using defaults")
        recommended = [("", "--------")]
        recommended += CATEGORY_CHOICES
        return recommended
    logger.debug("Have suggested genres: %s", suggested_genres)
    # Convert to tuples
    recommended = [(g, g.lower()) for g in suggested_genres]
    others = list(set(CATEGORY_CHOICES) - set(recommended))
    recommended.append(("", "--------"))
    recommended += sorted(others)
    logger.debug("Final choices %s", recommended)
    return recommended


def filter_genres(provided_genres):
    """Convert genres provided, into those we support."""
    msgs = []
    genres = [g.upper() for g in provided_genres.split(", ")]
    msgs.append(f"Provided genres: {genres}")
    # Translate genre names
    filtered_genres = []
    for genre in genres:
        match genre:
            case "ANIMATION":
                filtered_genres.append("ANIMATED")
            case "N/A":
                filtered_genres.append("MISC")
            case "SCIENCE FICTION":
                filtered_genres.append("SCI-FI")
            case "MUSIC":
                filtered_genres.append("MUSICAL")
            case "WAR":
                filtered_genres.append("MILITARY")
            case "SPORT":
                filtered_genres.append("SPORTS")
            case _:
                if genre in CATEGORY_DICT:
                    filtered_genres.append(genre)
                else:
                    msgs.append(
                        f"Genre {genre} is not in set of known genres - ignoring"
                    )
    filtered_genres.sort()
    msgs.append(f"Used genres: {filtered_genres}")
    return ", ".join(filtered_genres), msgs
