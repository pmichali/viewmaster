from datetime import datetime

from django.forms import ModelForm, TextInput, TimeInput
from django.core.exceptions import ValidationError

from .models import Movie


class MovieForm(ModelForm):
    """Model based form for creating/editing a movie."""

    class Meta:
        """Model, fields, and custom widgets for form."""
        model = Movie
        fields = ['title', 'release', 'category', 'rating', 'duration',
                  'format', 'aspect', 'audio', 'collection', 'cost',
                  'paid', 'bad']
        widgets = {
            'title' : TextInput(attrs={'autofocus': True}),
            'duration' : TimeInput(format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        super(MovieForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update(
                    {
                        'data-bs-toggle':'tooltip',
                        'title':help_text,
                        'data-bs-placement':'right',
                    }
                )

    def clean_release(self):
        """Ensure a four-digit year is entered, that is not in the future."""
        release = self.cleaned_data['release']
        try:
            release_year = int(release)
        except ValueError as e:
            raise ValidationError("must be a four-digit date")
        this_year = datetime.today().year
        if release_year < 1900:
            raise ValidationError("date must be greater than 1900")
        if release_year > this_year:
            raise ValidationError(f"release date {release_year} is in future")
        return release

    def clean_cost(self):
        """Ensure cost is a non-negative amount."""
        cost = self.cleaned_data['cost']
        if cost < 0:
            raise ValidationError("Cost must be a positive amount")
        return cost