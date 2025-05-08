"""Models for viewmaster app."""

import logging

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse

from auditlog.registry import auditlog

from .api import RequestFailed, get_movie
from .extractors import extract_rating, extract_duration, extract_year
from .extractors import filter_genres, CATEGORY_CHOICES, RATING_CHOICES


FORMAT_CHOICES = [
    ("LD", "LD"),
    ("DVD", "DVD"),
    ("BR", "BR"),
    ("4K", "4K"),
]

logger = logging.getLogger(__name__)


class ImdbInfo(models.Model):
    """IMDB information for a movie (or series of movies)."""

    title_name = models.CharField(
        max_length=60, help_text="Up to 60 characters for title. May be overridden."
    )
    release_date = models.IntegerField(
        help_text="Four digit year of release. May be overridden."
    )
    genres = models.CharField(help_text="List of genres applicable to the movie.")
    mpaa_rating = models.CharField(
        max_length=5,
        default="?",
        choices=RATING_CHOICES,
        help_text="Select the MPAA rating. May be overridden.",
    )
    run_time = models.TimeField(
        help_text="Duration in hh:mm format. May be overridden."
    )

    # These will be common to every movie with this IMDB #
    identifier = models.CharField(
        max_length=20, unique=True, help_text="IMDB movie ID."
    )
    plot = models.CharField(blank=True, default="", help_text="Plot summary.")
    actors = models.CharField(blank=True, default="", help_text="Top cast.")
    directors = models.CharField(blank=True, default="", help_text="Director(s).")
    cover_url = models.URLField(
        blank=True, default="", help_text="URL where poster image is located."
    )
    cover_file = models.ImageField(
        blank=True,
        null=True,
        upload_to="covers",
        storage=FileSystemStorage(allow_overwrite=True),
    )

    @classmethod
    def get(cls, identifier, lookup=False):
        """Obtain IMDB info. Lookup, if requested and doesn't already exist."""
        try:
            info = cls.objects.get(identifier=identifier)
            logger.debug("Have existing IMDB info for %s", identifier)
            return info
        except cls.DoesNotExist:
            if lookup:
                return cls.from_lookup(identifier)
            logger.debug("No exisitng IMDB info for %s", identifier)
            return None

    @classmethod
    def from_lookup(cls, identifier):
        """Create IMDB info from a request lookup."""
        logger.info("Looking up IMDB entry %s", identifier)
        try:
            details = get_movie(identifier)
        except RequestFailed as rf:
            logger.error("Failed to get IMDB info for %s: %s", identifier, rf)
            return None
        rating = extract_rating(details.get("Rated", "?"))
        duration = extract_duration(details.get("Runtime", "?"))
        release = extract_year(details.get("Year", "?"))
        genres_list, processing_msgs = filter_genres(details.get("Genre", ""))
        for msg in processing_msgs:
            logger.debug(msg)
        new_imdb = cls(
            title_name=details.get("Title", "MISSING TITLE!!!"),
            release_date=release,
            mpaa_rating=rating,
            run_time=duration,
            identifier=identifier,
            plot=details.get("Plot", ""),
            actors=details.get("Actors", ""),
            directors=details.get("Director", ""),
            cover_url=details.get("Poster", ""),
            genres=genres_list,
        )
        logger.debug("New IMDB %s", new_imdb)
        return new_imdb

    @classmethod
    def remove_unused(cls, imdb_id):
        """Remove the IMDB info, if not used."""
        if not imdb_id:
            logger.debug("No IMDB ID - delete check skipped")
            return
        if Movie.objects.filter(imdb_info__id=imdb_id).count() > 0:
            logger.debug("IMDB info %s still in use - keeping", imdb_id)
            return
        try:
            cls.objects.filter(pk=imdb_id).delete()
            logger.info("Deleting IMDB info %s no longer used - deleting", imdb_id)
        except cls.DoesNotExist:
            logger.warning("Unable to find IMDB info %s to check usage", imdb_id)

    @property
    def duration_str(self):
        """Display custom format for duration."""
        if not self.run_time:
            return "?"
        hrs = int(self.run_time.strftime("%H"))
        mins = int(self.run_time.strftime("%M"))
        return f"{hrs}h {mins}m"

    def __str__(self):
        """Show the IMDB info."""
        return (
            f"identifier='{self.identifier}' ({self.id}) "
            f"title_name='{self.title_name}' "
            f"plot='{self.plot}' "
            f"actors='{self.actors}' "
            f"directors='{self.directors}' "
            f"release_date={self.release_date} "
            f"mpaa_rating={self.mpaa_rating} "
            f"run_time={self.duration_str} "
            f"cover_url='{self.cover_url}' "
            f"cover_file='{self.cover_file.name}' "
            f"genres='{self.genres}'"
        )


class Movie(models.Model):
    """Movie information for the catalog."""

    title = models.CharField(max_length=60, help_text="Up to 60 characters for title.")
    release = models.IntegerField(help_text="Four digit year of release.")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, help_text="Select a genre"
    )
    rating = models.CharField(
        max_length=5,
        default="?",
        choices=RATING_CHOICES,
        help_text="Select the MPAA rating",
    )
    duration = models.TimeField(help_text="Duration in hh:mm format.")
    format = models.CharField(
        max_length=3, choices=FORMAT_CHOICES, help_text="Select media format"
    )
    aspect = models.CharField(
        max_length=10, default="?", help_text="Screen aspect ratio (10 chars)."
    )
    audio = models.CharField(
        max_length=10, default="?", help_text="Main audio format (10 chars)."
    )
    collection = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Name for a collection of movies.",
    )
    cost = models.DecimalField(max_digits=5, decimal_places=2, help_text="In USD.")
    paid = models.BooleanField(
        default=True, help_text="Indicates movie was purchased, versus being a gift."
    )
    bad = models.BooleanField(
        default=False,
        help_text="Indicates that movie is not playable, or has playback issues.",
    )
    # New fields...
    plot = models.CharField(blank=True, default="", help_text="Plot summary (imported)")
    actors = models.CharField(blank=True, default="", help_text="Top cast (imported)")
    directors = models.CharField(
        blank=True, default="", help_text="Director(s) (imported)"
    )
    cover_ref = models.URLField(
        blank=True, default="", help_text="URL where poster image is located (imported)"
    )
    movie_id = models.CharField(
        blank=True, default="unknown", help_text="IMDB movie ID (imported)"
    )

    imdb_info = models.ForeignKey(ImdbInfo, null=True, on_delete=models.CASCADE)

    def get_absolute_url(self):
        """Link used when updating movie?"""
        return reverse("viewmaster:movie-update", args=[self.id])

    @property
    def alpha_order(self):
        """Code indicating the alphabetical order."""
        first = self.title[0].upper()  # pylint: disable=unsubscriptable-object
        if first in "0123456789":
            return "#"
        return first

    @property
    def category_order(self):
        """Code indicating the category name order."""
        return self.category.upper()

    @property
    def release_order(self):
        """Code indicating the release date order."""
        return self.release

    @property
    def collection_order(self):
        """Code indicating the collection key order."""
        return self.collection

    @property
    def format_order(self):
        """Code indicating the disk format order."""
        return self.format.upper()

    @property
    def duration_str(self):
        """Display custom format for duration."""
        if not self.duration:
            return "?"
        hrs = int(self.duration.strftime("%H"))
        mins = int(self.duration.strftime("%M"))
        return f"{hrs}h {mins}m"

    def detect_overrides_from(self, imdb_info):
        """Build dict of values overridden from IMDB data."""
        overridden = {}
        if imdb_info.mpaa_rating not in ("?", self.rating):
            logger.warning(
                "IMDB entry has MPAA rating %s instead of %s",
                imdb_info.mpaa_rating,
                self.rating,
            )
            overridden["rating"] = True
            overridden["rating_value"] = imdb_info.mpaa_rating
        stored_duration = self.duration.strftime("%H:%M")
        imdb_duration = imdb_info.run_time.strftime("%H:%M")
        if imdb_duration not in ("?", stored_duration):
            logger.warning(
                "IMDB entry has duration '%s' instead of '%s'",
                imdb_duration,
                stored_duration,
            )
            overridden["duration"] = True
            overridden["duration_value"] = imdb_duration
        if imdb_info.release_date not in ("?", self.release):
            logger.warning(
                "IMDB entry has release date %s instead of %s",
                imdb_info.release_date,
                self.release,
            )
            overridden["release"] = True
            overridden["release_value"] = imdb_info.release_date
        return overridden

    @classmethod
    def find(cls, identifier):
        """Get movie by ID."""
        try:
            return cls.objects.get(pk=identifier)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_imdb_id(cls, identifier):
        """Provide the IMDB info ID, if it exists."""
        movie = cls.find(identifier)
        if not movie or not movie.imdb_info:
            return None
        return movie.imdb_info.id

    @classmethod
    def uses_imdb_info(cls, identifier):
        """Indicate if any movie(s) are using this IMDB identifier."""
        return cls.objects.filter(imdb_info__identifier=identifier).count() > 0

    def __str__(self):
        """Show the movie entry for debug."""
        return (
            f"title='{self.title}' ({self.id}) plot='{self.plot}' actors='{self.actors}' "
            f"directors='{self.directors}' cat={self.category} release={self.release} "
            f"rating={self.rating} duration={self.duration_str} format={self.format} "
            f"aspect='{self.aspect}' audio='{self.audio}' coll='{self.collection}' "
            f"movie_id={self.movie_id} cost=${self.cost:6.2f} "
            f"paid={'y' if self.paid else 'N'} bad={'Y' if self.bad else 'N'} "
            f"cover_ref={self.cover_ref}"
        )


auditlog.register(ImdbInfo)
auditlog.register(Movie)
