"""Handles REST requests to OMDb server."""

import os
import logging

import urllib

import requests
import simplejson


logger = logging.getLogger(__name__)

# Get API Key for accessing www.omdbapi.com
OMDB_API_KEY = os.environ.get('OMDB_API_KEY', 'must-be-created')
OMDB_REST_API = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}"


class APIFailure(Exception):
    """Base exception for REST API failures."""


class RequestFailed(APIFailure):
    """Indicates a failure to perform request to OMDb."""


class RESTClient:  # pylint: disable=too-few-public-methods
    """Communicate with OMDb for movie info."""

    def __init__(self, server_base_url: str, handler=requests) -> None:
        """Initialize REST client with base URL for site."""
        self.server_base_url = server_base_url
        self.handler = handler

    def request_to(self, endpoint, timeout=30) -> dict:
        """Send a GET request to OMDb."""
        logger.info("GET request to %s", endpoint)
        try:
            r = requests.get(endpoint, timeout=timeout)
        except requests.exceptions.Timeout as err:
            raise RequestFailed(f"time-out on GET request to {endpoint}") from err
        except requests.exceptions.ConnectionError as cerr:
            raise RequestFailed(
                f"connection error on POST request to {endpoint}: {str(cerr)}"
            ) from cerr
        if r.status_code == requests.codes.ok:
            response = r.json()
            logger.debug("Results:\n%s", simplejson.dumps(response, indent=4))
            return response
        try:
            fail_details = r.json()
        except requests.exceptions.JSONDecodeError:
            fail_details = {"reason": r.reason}
        raise RequestFailed(
            f"GET request {endpoint} failed: {fail_details} ({r.status_code})"
        )


def search_movies(partial_title, timeout=30) -> dict:
    """Find movies matching a title phrase.

    Use asterisk as wildcard. Format of call for "Die Hard*" is:
        http://www.omdbapi.com/?apikey=<KEY>&s=Die%20Hard%2A

    Can optionally restrict type with &type={movies,series,episode,game?}.

    """
    omdb_client = RESTClient(OMDB_REST_API)
    endpoint = f"{omdb_client.server_base_url}&s={urllib.parse.quote(partial_title)}"
    return omdb_client.request_to(endpoint, timeout)


def lookup_movie(title, release, timeout=30) -> dict:
    """Find movies matching a title and release date."""
    omdb_client = RESTClient(OMDB_REST_API)
    endpoint = (
        f"{omdb_client.server_base_url}&t={urllib.parse.quote(title)}&y={release}"
    )
    return omdb_client.request_to(endpoint, timeout)


def get_movie(movie_id, timeout=30) -> dict:
    """Get a specific movie by ID."""
    omdb_client = RESTClient(OMDB_REST_API)
    endpoint = f"{omdb_client.server_base_url}&i={movie_id}"
    return omdb_client.request_to(endpoint, timeout)
