"""Import IMDB information into movie database."""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os

import psycopg2

from viewmaster.api import get_movie, search_movies
from viewmaster.extractors import extract_rating, extract_time, extract_year


CHECK_MARK = "\u2705"
X_MARK = "\u274c"

logger = logging.getLogger(__name__)


def setup_logging():
    """Log to file normally, and to console only if warnings or higher."""
    root = logging.getLogger()

    root.setLevel(
        logging.DEBUG
    )  # Must set to lowest level, so other handlers can be different
    file_handler = RotatingFileHandler(
        "imdb-import.log", maxBytes=5000000, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-10s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    root.addHandler(console_handler)


class MovieDatabase:
    """Represents database access to movies."""

    def __init__(self):
        """Context Manager for database."""
        self.conn = None
        self.cursor = None
        self.total = 0
        self.processed = 0

    def __enter__(self):
        """Connect to the database."""
        self.conn = psycopg2.connect(
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["DB_HOST"],
        )
        self.cursor = self.conn.cursor()
        logger.info("Connected to database")
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Close the connection."""
        self.cursor.close()
        self.conn.close()
        logger.info("Closed connection to database")

    def query(self, query):
        """Perform database query on the movie database."""
        logger.debug("QUERY: %s", query)
        self.cursor.execute(query)

    def get_movies(self):
        """Obtain list of movies that need to be processed."""
        logger.info("Getting list of movies to process")
        self.query(
            "SELECT id, title, release, rating, duration FROM "
            "viewmaster_movie as vm where vm.movie_id='' "
            "order by vm.title"
        )
        all_movies = self.cursor.fetchall()
        self.total = len(all_movies)
        logger.info("Have %d movies", self.total)
        print(f"Have {self.total} movies to process")
        return all_movies

    def show_summary(self):
        """Summarize the number of files."""
        logger.info("Processed %d movies, out of %d", self.processed, self.total)
        print(f"\nProcessed {self.processed} movies, out of {self.total}\n")

    def save(self, identifier: int, details: dict):
        """Update the database entry."""
        release = extract_year(details["Year"])
        rating = extract_rating(details["Rated"])
        duration = extract_time(details["Runtime"])
        plot = details["Plot"]
        actors = details["Actors"]
        directors = details["Director"]
        movie_id = details["imdbID"]
        cover_ref = details["Poster"]
        title = details["Title"]
        logger.info(
            "Updating movie '%s' (%d) %s %d", title, identifier, rating, release
        )
        logger.info("Plot: %s", plot)
        logger.info("ACTORS: %s DIRECTORS: %s IMDB ID: %s", actors, directors, movie_id)
        logger.info("COVER REF: %s", cover_ref)
        query = (
            f"UPDATE viewmaster_movie set title=$${title}$$, release={release}, "
            f"rating='{rating}', duration='{duration}', plot=$${plot}$$, "
            f"actors=$${actors}$$, directors=$${directors}$$, "
            f"movie_id='{movie_id}', cover_ref='{cover_ref}' "
            f"WHERE id={identifier}"
        )
        self.query(query)
        self.conn.commit()
        self.processed += 1
        print("\nSaved updates to movie\n")


def show_candidates(results: dict):
    """Display the possible match results."""
    items = results.get("Search", [])
    num = len(items)
    print(" 0) SKIP SELECTION FOR THIS MOVIE")
    if results.get("Response") == "True":
        for i in range(num):
            entry = items[i]
            print(f'{i+1:2d}) {entry["Year"]} {entry["Title"]} ({entry["Type"]})')
    num += 1
    print(f'{num:2d}) Manually enter movie ID')
    return num


def show_selection(details: dict, db_release, db_duration, db_rating):
    """Show the selection made to confirm."""
    print(f"\nTITLE: {details['Title']}")
    release = extract_year(details["Year"])
    if db_release != release:
        status = f"{X_MARK} (database had {db_release})"
    else:
        status = CHECK_MARK
    print(f"RELEASED: {release} {status}")
    rating = extract_rating(details["Rated"])
    if db_rating != rating:
        status = f"{X_MARK} (database had {db_rating})"
    else:
        status = CHECK_MARK
    print(f"RATING: {rating} {status}")
    duration = extract_time(details["Runtime"])
    db_duration = db_duration.strftime("%H:%M")
    if db_duration != duration:
        status = f"{X_MARK} (database had {db_duration})"
    else:
        status = CHECK_MARK
    print(f"DURATION: {duration} {status}")
    print(f"IMDB ID: {details['imdbID']}")
    print(f"{details['Plot']}")
    print(f"ACTORS: {details['Actors']}")
    print(f"DIRECTORS: {details['Director']}\n")


def imdb_import():
    """Entry point."""
    with MovieDatabase() as movie_access:

        all_movies = movie_access.get_movies()
        for identifier, title, release, rating, duration in all_movies:
            print(f"\nMovie: '{title}' ({identifier}) ")
            print(f"Release: {release} Rating: {rating} Duration: {duration}\n")
            results = search_movies(title)
            while True:
                print()
                num = show_candidates(results)
                limit = f"-{num}" if num else ""
                choice = input(f"\nEnter choice 0{limit},x [0]: ")
                if choice in ("x", "X"):
                    movie_access.show_summary()
                    sys.exit(0)
                if choice in ("", "0"):
                    logger.info("Skipping movie '%s' (%d)", title, release)
                    print("Skipping movie")
                    break
                choice = int(choice)
                if choice == num:
                    movie_id = input("Enter IMDB ID: ")
                else:
                    movie_id = results["Search"][choice - 1]["imdbID"]
                details = get_movie(movie_id)
                if details.get('Response') != 'True':
                    print(f"\nERROR: {details.get('Error', 'Unknown')}\n")
                    continue
                show_selection(details, release, duration, rating)
                choice = input("Enter choice Save, Back, Ignore, eXit[S]: ")
                if choice in ("x", "X"):
                    movie_access.show_summary()
                    sys.exit(0)
                if choice in ("i", "I"):
                    logger.info("Ignoring movie '%s' (%d)", title, release)
                    print("Ignoring movie")
                    break
                if choice in ("s", "S", ""):
                    movie_access.save(identifier, details)
                    break
        logger.info("Done processing movies")
        movie_access.show_summary()


if __name__ == "__main__":
    setup_logging()
    imdb_import()
