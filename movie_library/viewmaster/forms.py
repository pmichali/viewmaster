"""Form definitions for viewmaster."""
import logging

from datetime import datetime

from django.forms import CharField, ChoiceField, DateInput, Form, HiddenInput, ModelForm
from django.forms import Textarea, NumberInput, TextInput, TimeInput
from django.core.exceptions import ValidationError

from .models import Movie


logger = logging.getLogger(__name__)


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


class MovieCreateEditForm(ModelForm):
    """Model based form for creating a movie."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Model, fields, and custom widgets for form."""

        model = Movie
        fields = [
            "title",
            "plot",
            "actors",
            "directors",
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
            "movie_id",
            "cover_ref",
        ]
        widgets = {
            "title": TextInput(attrs={"size": 60, "autofocus": True}),
            "plot": Textarea(attrs={"cols": 60, "rows": 3, "tabindex": -1}),
            "actors": TextInput(attrs={"size": 60, "tabindex": -1}),
            "directors": TextInput(attrs={"size": 60, "tabindex": -1}),
            "release": DateInput(format="%Y", attrs={"size": 6}),
            "duration": TimeInput(format="%H:%M", attrs={"size": 6}),
            "aspect": TextInput(attrs={"size": 10}),
            "audio": TextInput(attrs={"size": 10}),
            "collection": TextInput(attrs={"size": 10}),
            "cost": NumberInput(attrs={"size": 6}),
            "movie_id": TextInput(attrs={"size": 12, "tabindex": -1}),
            "cover_ref": HiddenInput(),
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
        fields = ["plot", "actors", "directors", "movie_id", "cover_ref"]

        widgets = {
            "plot": HiddenInput(),
            "actors": HiddenInput(),
            "directors": HiddenInput(),
            "movie_id": HiddenInput(),
            "cover_ref": HiddenInput(),
        }
