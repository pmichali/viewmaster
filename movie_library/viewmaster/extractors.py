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


def order_genre_choices(suggested):
    """Validate provided genre choices and prepend to the list of allowable."""
    suggested_genres = [g.upper() for g in suggested.split(", ")]
    if not suggested:
        logger.debug("No suggested genres, so using defaults")
        return CATEGORY_CHOICES
    logger.debug("Have suggested genres: %s", suggested_genres)
    # Map different spellings to those we support
    suggested_genres = [sg.replace('ANIMATION', 'ANIMATED') for sg in suggested_genres]
    suggested_genres = [sg.replace('MUSIC', 'MUSICAL') for sg in suggested_genres]
    suggested_genres = [sg.replace('SCIENCE FICTION', 'SCI-FI') for sg in suggested_genres]
    suggested_genres = [sg.replace('WAR', 'MILITARY') for sg in suggested_genres]
    # Sort them
    suggested_genres.sort()
    logger.debug("Modified genres: %s", suggested_genres)
    # Convert to tuples
    recommended = [(g, g.lower()) for g in suggested_genres]
    others = list(set(CATEGORY_CHOICES) - set(recommended))
    recommended.append(('--------', '--------'))
    recommended += sorted(others)
    logger.debug("Final choices %s", recommended)
    return recommended
    
    