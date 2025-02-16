"""Extract ReST API info and convert for storage."""

import logging

from .models import CATEGORY_CHOICES, RATING_CHOICES


RATINGS_DICT = dict(RATING_CHOICES)
RATINGS_DICT['Not Rated'] = 'NR'

logger = logging.getLogger(__name__)


def extract_time(time_str):
    """Convert textual time to hours/mins.
    
    Expect input to be "# mins" and want output "HH:MM".
    """
    total_mins, _, _ = time_str.partition(' ')
    if not total_mins.isdigit():
        logging.warning("Unable to parse time string '%s'", time_str)
        return "0:00"
    hours = int(total_mins) // 60
    minutes = int(total_mins) % 60
    return "{}:{}".format(hours, minutes)


def extract_rating(rating):
    """Ensure rating within set of known ratings."""
    return RATINGS_DICT.get(rating, '?')


def extract_genre_choices(genres):
    """Verify valid genres and form list of allowable values."""
    all_genres = [g.upper() for g in genres.split(", ")]
    logger.debug("have genres: %s", all_genres)
    return CATEGORY_CHOICES[0][1]
    
    