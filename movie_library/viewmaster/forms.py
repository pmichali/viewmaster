"""Form definitions for viewmaster."""

import logging
from datetime import datetime

from django.forms import CharField, ChoiceField, DateInput, Form, HiddenInput, ModelForm
from django.forms import (
    BooleanField,
    Textarea,
    NumberInput,
    TextInput,
    TimeInput,
)
from django.core.exceptions import ValidationError

from .models import ImdbInfo, Movie


logger = logging.getLogger(__name__)

MODE_CHOICES = [
    ("alpha", "Alphabetical"),
    ("cat_alpha", "Genre/Alpha"),
    ("cat_date_alpha", "Genre/Date/Alpha"),
    ("date", "Date/Alpha"),
    ("collection", "Collection/Date"),
    ("disk", "Format/Alpha"),
]

SEARCH_CHOICES = [
    ("title", "TITLE"),
    ("plot", "PLOT"),
    ("actors", "ACTORS"),
    ("directors", "DIRECTORS"),
]


class MovieListForm(Form):
    """List movies in different modes."""

    mode = ChoiceField(choices=MODE_CHOICES)
    show_ld = BooleanField(required=False)
    show_details = BooleanField(required=False)
    search_by = ChoiceField(choices=SEARCH_CHOICES)

    def __init__(self, *args, **kwargs):
        """Setup movie list form."""
        logger.debug("List form: ARGS %s, KWARGS %s", args, kwargs)
        super().__init__(*args, **kwargs)
        self.fields["search_by"].widget.attrs["class"] = "form-select form-select-md"


class MovieFindForm(Form):
    """Search for a matching movie."""

    partial_title = CharField(label="Title", max_length=60)

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        super().__init__(*args, **kwargs)
        self.fields["partial_title"].widget.attrs.update(
            {
                "data-bs-toggle": "tooltip",
                "title": 'Enter partial movie title. Use "*" for wildcard',
                "data-bs-placement": "right",
                "placeholder": "Title to find...",
                "autofocus": True,
            }
        )


class MovieImdbCreateEditForm(ModelForm):
    """Model based form for movie IMDB info."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Model, fields, and custom widgets for form."""

        model = ImdbInfo
        fields = [
            "title_name",
            "release_date",
            "mpaa_rating",
            "run_time",
            "plot",
            "actors",
            "directors",
            "genres",
            "identifier",
            "cover_url",
            "cover_file",
        ]
        widgets = {
            "title_name": HiddenInput(),
            "release_date": DateInput(format="%Y", attrs={"size": 6, "type": "hidden"}),
            "mpaa_rating": HiddenInput(),
            "run_time": TimeInput(format="%H:%M", attrs={"size": 6, "type": "hidden"}),
            "plot": Textarea(attrs={"cols": 60, "rows": 3, "tabindex": -1}),
            "actors": TextInput(attrs={"size": 60, "tabindex": -1}),
            "directors": TextInput(attrs={"size": 60, "tabindex": -1}),
            "genres": HiddenInput(),
            "identifier": TextInput(
                attrs={"size": 12, "tabindex": -1, "readonly": True}
            ),
            "cover_url": HiddenInput(),
            "cover_file": HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        logger.debug("IMDB Init function ARGS %s KWARGS %s", args, kwargs)
        super().__init__(*args, **kwargs)

        # Set help text...
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != "":
                self.fields[field].widget.attrs.update(
                    {
                        "data-bs-toggle": "tooltip",
                        "title": help_text,
                        "data-bs-placement": "right",
                    }
                )

    def clean_release(self):
        """Ensure a four-digit year is entered, that is not in the future."""
        release = self.cleaned_data["imdb_release"]
        try:
            release_year = int(release)
        except ValueError as e:
            raise ValidationError("must be a four-digit date") from e
        this_year = datetime.today().year
        if release_year < 1900:
            raise ValidationError("date must be greater than 1900")
        if release_year > this_year:
            raise ValidationError(f"release date {release_year} is in future")
        return release

    def save(self, commit=True):
        """Save model and create file, if possible."""
        instance = super().save(commit=False)
        instance.create_cover_file()
        if commit:
            instance.save()
        return instance


class MovieCreateEditForm(ModelForm):
    """Model based form for creating a movie."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Model, fields, and custom widgets for form."""

        model = Movie
        fields = [
            "title",
            "release",
            "rating",
            "category",
            "format",
            "duration",
            "aspect",
            "audio",
            "collection",
            "cost",
            "paid",
            "bad",
        ]
        widgets = {
            "title": TextInput(attrs={"size": 60, "autofocus": True}),
            "release": DateInput(format="%Y", attrs={"size": 6}),
            "duration": TimeInput(format="%H:%M", attrs={"size": 6}),
            "aspect": TextInput(attrs={"size": 10}),
            "audio": TextInput(attrs={"size": 10}),
            "collection": TextInput(attrs={"size": 10}),
            "cost": NumberInput(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        logger.debug("Init function ARGS %s KWARGS %s", args, kwargs)
        super().__init__(*args, **kwargs)

        if kwargs.get("initial") and kwargs["initial"].get("category_choices"):
            # Create new form field to be able to set the choices. If try to just change
            # the choices attribute, it will be ignored, as there is one already.
            new_choices = kwargs["initial"]["category_choices"]
            self.fields["category"] = ChoiceField(
                choices=new_choices, help_text="Select a genre"
            )
            logger.debug("Overriding choices")
        # Set help text...
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != "":
                self.fields[field].widget.attrs.update(
                    {
                        "data-bs-toggle": "tooltip",
                        "title": help_text,
                        "data-bs-placement": "right",
                    }
                )

    def clean_release(self):
        """Ensure a four-digit year is entered, that is not in the future."""
        release = self.cleaned_data["release"]
        try:
            release_year = int(release)
        except ValueError as e:
            raise ValidationError("must be a four-digit date") from e
        this_year = datetime.today().year
        if release_year < 1900:
            raise ValidationError("date must be greater than 1900")
        if release_year > this_year:
            raise ValidationError(f"release date {release_year} is in future")
        return release

    def clean_cost(self):
        """Ensure cost is a non-negative amount."""
        cost = self.cleaned_data["cost"]
        if cost < 0:
            raise ValidationError("Cost must be a positive amount")
        return cost


class MovieClearForm(ModelForm):
    """Model based form for clearing movie IMDB info."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Model and fields for form."""

        model = Movie
        fields = []
