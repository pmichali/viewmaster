"""Custom template tag to provide URI for cover file or cover URL."""

from django import template

from movie_library.settings import MEDIA_URL


register = template.Library()


@register.simple_tag
def cover_image(details):
    """Provide either the cover file or cover URL for movie details."""
    if details.cover_file:
        return f"{MEDIA_URL}{details.cover_file}"
    if details.cover_url.startswith("http"):
        return details.cover_url
    return ""
