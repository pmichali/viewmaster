"""Custom template tag to provide URI for cover file or cover URL."""

import logging

from django import template
from django.utils.safestring import mark_safe

from movie_library.settings import MEDIA_URL, STATIC_URL


register = template.Library()

logger = logging.getLogger(__name__)


@register.simple_tag
def movie_cover(movie):
    """Provides src for image (and optionally a class)."""

    css_clause = ""
    info = movie.imdb_info
    if not info:
        logger.debug("Movie '%s' does not have any IMDB info", movie.title)
        source = f"/{STATIC_URL}viewmaster/no-image.png"
    elif info.cover_file:
        source = f"{MEDIA_URL}{info.cover_file}"
    elif info.cover_url.startswith("http"):
        logger.warning(
            "Movie '%s' (%s) has URL but no file for cover",
            movie.title,
            info.identifier,
        )
        source = info.cover_url
        css_clause = 'class="missing"'
    else:
        logger.debug(
            "Movie '%s' (%s) does not have cover information (URL=%s)",
            movie.title,
            info.identifier,
            info.cover_url,
        )
        source = f"/{STATIC_URL}viewmaster/no-imdb.png"
    return mark_safe(f'{css_clause} src="{source}"')


@register.simple_tag
def plot(imdb_info):
    """Provide plot, if there is IMDB info."""
    if not imdb_info:
        return "?"
    return imdb_info.plot or "?"


@register.simple_tag
def directors(imdb_info):
    """Provide directors, if there is IMDB info."""
    if not imdb_info:
        return "?"
    return imdb_info.directors or "?"


@register.simple_tag
def actors(imdb_info):
    """Provide actors, if there is IMDB info."""
    if not imdb_info:
        return "?"
    return imdb_info.actors or "?"


@register.simple_tag
def identifier(imdb_info):
    """Provide IMDB ID#, if there is IMDB info."""
    if not imdb_info:
        return "UNKNOWN"
    return imdb_info.identifier or "UNKNOWN"
