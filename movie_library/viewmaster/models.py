"""Models for viewmaster app."""

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse

from auditlog.registry import auditlog

from .extractors import CATEGORY_CHOICES, RATING_CHOICES


FORMAT_CHOICES = [
    ("LD", "LD"),
    ("DVD", "DVD"),
    ("BR", "BR"),
    ("4K", "4K"),
]


class ImdbInfo(models.Model):
    """IMDB information for a movie (or series of movies)."""

    identifier = models.CharField(
        max_length=20, unique=True, help_text="IMDB movie ID."
    )
    title = models.CharField(
        max_length=60, help_text="Up to 60 characters for title. May be overridden."
    )
    release = models.IntegerField(
        help_text="Four digit year of release. May be overridden."
    )
    genres = models.CharField(help_text="List of genres applicable to the movie.")
    plot = models.CharField(blank=True, default="", help_text="Plot summary.")
    actors = models.CharField(blank=True, default="", help_text="Top cast.")
    directors = models.CharField(blank=True, default="", help_text="Director(s).")
    rating = models.CharField(
        max_length=5,
        default="?",
        choices=RATING_CHOICES,
        help_text="Select the MPAA rating. May be overridden.",
    )
    duration = models.TimeField(
        help_text="Duration in hh:mm format. May be overridden."
    )
    cover_url = models.URLField(
        blank=True, default="", help_text="URL where poster image is located."
    )
    cover_file = models.ImageField(
        blank=True,
        null=True,
        upload_to="covers",
        storage=FileSystemStorage(allow_overwrite=True),
    )

    @property
    def duration_str(self):
        """Display custom format for duration."""
        if not self.duration:
            return "?"
        hrs = int(self.duration.strftime("%H"))
        mins = int(self.duration.strftime("%M"))
        return f"{hrs}h {mins}m"

    def __str__(self):
        """Show the IMDB info."""
        return (
            f"identifier-'{self.identifier}' ({self.id}) title='{self.title} "
            f"plot='{self.plot}' actors='{self.actors}' directors='{self.directors}' "
            f"release={self.release} rating={self.rating} duration={self.duration_str} "
            f"cover_url='{self.cover_url}' cover_file='{self.cover_file.name}' "
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
