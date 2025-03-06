"""Extract ReST API info and convert for storage."""

import logging
import re


CATEGORY_CHOICES = [
    ("ACTION", "action"),
    ("ADVENTURE", "adventure"),
    ("ANIMATED", "animated"),
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

logger = logging.getLogger(__name__)
year_re = re.compile(r"\d+")


def extract_time(time_str):
    """Convert textual time to hours/mins.

    Expect input to be "# mins" and want output "HH:MM".
    """
    total_mins, _, _ = time_str.partition(" ")
    if not total_mins.isdigit():
        logging.warning("Unable to parse time string '%s'", time_str)
        return "00:00"
    hours = int(total_mins) // 60
    minutes = int(total_mins) % 60
    return f"{hours:02d}:{minutes:02d}"


def extract_rating(rating):
    """Ensure rating within set of known ratings."""
    return RATINGS_DICT.get(rating, "NR")


def extract_year(year):
    """Ensure year is just a number."""
    m = year_re.match(year)
    if not m:
        return 0
    return int(m.group())


def order_genre_choices(suggested):
    """Validate provided genre choices and prepend to the list of allowable."""
    suggested_genres = [g.upper() for g in suggested.split(", ")]
    if not suggested:
        logger.debug("No suggested genres, so using defaults")
        recommended = [("", "--------")]
        recommended += CATEGORY_CHOICES
        return recommended
    logger.debug("Have suggested genres: %s", suggested_genres)
    # Map different spellings to those we support
    suggested_genres = [sg.replace("ANIMATION", "ANIMATED") for sg in suggested_genres]
    suggested_genres = [sg.replace("MUSIC", "MUSICAL") for sg in suggested_genres]
    suggested_genres = [
        sg.replace("SCIENCE FICTION", "SCI-FI") for sg in suggested_genres
    ]
    suggested_genres = [sg.replace("WAR", "MILITARY") for sg in suggested_genres]
    # Sort them
    suggested_genres.sort()
    logger.debug("Modified genres: %s", suggested_genres)
    # Convert to tuples
    recommended = [(g, g.lower()) for g in suggested_genres]
    others = list(set(CATEGORY_CHOICES) - set(recommended))
    recommended.append(("", "--------"))
    recommended += sorted(others)
    logger.debug("Final choices %s", recommended)
    return recommended
