"""Handles REST requests to OMDb server."""

import logging

import urllib
import urllib3

import requests
import simplejson


logger = logging.getLogger(__name__)


class APIFailure(Exception):
    """Base exception for REST API failures."""


class RequestFailed(APIFailure):
    """Indicates a failure to perform request to OMDb."""


class RESTClient:
    """Communicate with OMDb for movie info."""

    def __init__(self, server_base_url: str, handler=requests) -> None:
        """Initialize REST client with base URL for site."""
        self.server_base_url = server_base_url
        self.handler = handler

    def get(self, partial_title, timeout=30) -> dict:
        """Handle get requests."""
        # http://www.omdbapi.com/?apikey=<KEY>&s=Die%20Hard%2A    searches , use '*' for wildcard
        # http://www.omdbapi.com/?apikey=<KEY>&t=Die%20Hard%202   matches title (can be > 1)
        # http://www.omdbapi.com/?apikey=<KEY>&i=tt0112864     By ID. can use ID and title        
        endpoint = f"{self.server_base_url}&type=movie&s={urllib.parse.quote(partial_title)}"
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

