from datetime import datetime

from django.forms import CharField, DateInput, Form, HiddenInput, ModelForm, TextInput, TimeInput
from django.core.exceptions import ValidationError

from .models import Movie


class MovieFindForm(Form):
    """Search for a matching movie."""

    partial_title = CharField(label="Title", max_length=60)

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        super(MovieFindForm, self).__init__(*args, **kwargs)
        self.fields['partial_title'].widget.attrs.update(
            {
                'data-bs-toggle':'tooltip',
                'title': 'Enter partial movie title. Use "*" for wildcard',
                'data-bs-placement':'right',
            }
        )


class MovieCreateForm(ModelForm):
    """Model based form for creating a movie."""

    class Meta:
        """Model, fields, and custom widgets for form."""
        model = Movie
        fields = ['title', 'plot', 'actors', 'directors', 
                  'release', 'rating', 'category',
                  'format', 'duration', 'aspect', 'audio',
                  'collection', 'cost', 'paid', 'bad',
                  'movie_id', 'cover_ref',
                  ]
        widgets = {
            'title' : TextInput(attrs={'autofocus': True}),
            'duration' : TimeInput(format='%H:%M'),
            'release' : DateInput(format='%Y'),
        }

    def __init__(self, *args, **kwargs):
        """Enabling tool tips for the form."""
        super(MovieCreateForm, self).__init__(*args, **kwargs)
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
        self.fields['plot'].disabled = True
        self.fields['actors'].disabled = True
        self.fields['directors'].disabled = True
        self.fields['movie_id'].disabled = True
        self.fields['cover_ref'].widget = HiddenInput()

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


class MovieForm(ModelForm):
    """Model based form for creating/editing a movie."""

    class Meta:
        """Model, fields, and custom widgets for form."""
        model = Movie
        fields = ['title', 'release', 'category', 'rating', 'duration',
                  'plot', 'actors', 'directors', 'movie_id', 'cover_ref',
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
        self.fields['plot'].disabled = True
        self.fields['actors'].disabled = True
        self.fields['directors'].disabled = True
        self.fields['movie_id'].disabled = True
        self.fields['cover_ref'].widget = HiddenInput()

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
