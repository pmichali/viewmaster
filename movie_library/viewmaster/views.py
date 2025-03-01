"""Views for the app."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg
from django.db.models.functions import Lower
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import (
    DeleteView,
    UpdateView,
    ModelFormMixin,
    ProcessFormView,
)

from .api import get_movie, search_movies
from .extractors import extract_rating, extract_time, extract_year, order_genre_choices
from .models import Movie
from .forms import MovieClearForm, MovieCreateEditForm, MovieFindForm


logger = logging.getLogger(__name__)


class MovieListView(ListView):
    """View for display of movies in a variety of orderings."""

    context_object_name = "movies"

    def post(self, request, **kwargs):
        """Show list based on selected ordering mode."""
        logger.debug(
            "List POST: %s, KWARGS: %s, SESSION: %s",
            request.POST,
            kwargs,
            dict(request.session),
        )

        mode = request.POST.get("mode", request.session.get("mode", "alpha"))
        request.session["mode"] = mode
        show_ld = request.POST.get("show_ld", "")
        request.session["show_ld"] = show_ld
        show_details = request.POST.get("show_details", "")
        request.session["show_details"] = show_details

        total_movies = Movie.objects.count()
        total_paid = Movie.objects.filter(paid=True).count()
        stats = (
            Movie.objects.values("format")
            .filter(paid=True)
            .annotate(count=Count("format"), average=Avg("cost"))
            .order_by("format")
        )
        movies = Movie.objects
        if request.POST.get("phrase") or (
            request.POST.get("search.x") and request.POST.get("search.y")
        ):
            phrase = request.POST.get("phrase")
            movies = movies.filter(title__icontains=phrase)
        if not show_ld:
            movies = movies.exclude(format="LD")
        if mode == "alpha":
            movies = movies.order_by(Lower("title"))
        elif mode == "cat_alpha":
            movies = movies.order_by(Lower("category"), Lower("title"))
        elif mode == "cat_date_alpha":
            movies = movies.order_by(Lower("category"), "-release", Lower("title"))
        elif mode == "date":
            movies = movies.order_by("-release", "title")
        elif mode == "collection":
            movies = (
                movies.exclude(collection__isnull=True)
                .exclude(collection__exact="")
                .order_by(Lower("collection"), "release")
            )
        else:  # disk format
            movies = movies.order_by(Lower("format"), Lower("title"))
        logger.debug("Have %d movies with mode %s", total_movies, mode)
        context = {
            "movies": movies,
            "mode": mode,
            "show_ld": show_ld,
            "show_details": show_details,
            "total": total_movies,
            "total_paid": total_paid,
            "stats": stats,
        }
        return render(request, "viewmaster/movie_list.html", context)

    def get(self, request, *args, **kwargs):
        """Initial view is alphabetical."""
        logger.debug(
            "List GET: REQUEST %s, ARGS %s KWARGS %s, SESSION: %s",
            dict(request.GET),
            args,
            kwargs,
            dict(request.session),
        )

        mode = request.session.setdefault("mode", "alpha")
        show_ld = request.session.setdefault("show_ld", "")
        show_details = request.session.setdefault("show_details", "")

        total_movies = Movie.objects.count()
        total_paid = Movie.objects.filter(paid=True).count()
        stats = (
            Movie.objects.values("format")
            .filter(paid=True)
            .annotate(count=Count("format"), average=Avg("cost"))
            .order_by("format")
        )

        movies = Movie.objects
        if not show_ld:
            movies = movies.exclude(format="LD")
        if mode == "alpha":
            movies = movies.order_by(Lower("title"))
        elif mode == "cat_alpha":
            movies = movies.order_by(Lower("category"), Lower("title"))
        elif mode == "cat_date_alpha":
            movies = movies.order_by(Lower("category"), "-release", Lower("title"))
        elif mode == "date":
            movies = movies.order_by("-release", "title")
        elif mode == "collection":
            movies = (
                movies.exclude(collection__isnull=True)
                .exclude(collection__exact="")
                .order_by(Lower("collection"), "release")
            )
        else:  # disk format
            movies = movies.order_by(Lower("format"), Lower("title"))
        context = {
            "movies": movies,
            "mode": mode,
            "show_ld": show_ld,
            "show_details": show_details,
            "total": total_movies,
            "total_paid": total_paid,
            "stats": stats,
        }
        logger.debug("Have %d movies with mode %s", total_movies, mode)
        return render(request, "viewmaster/movie_list.html", context)


class MovieFindView(LoginRequiredMixin, View):
    """View for finding movie info to create a movie."""

    template_name = "viewmaster/find_movie.html"
    form_class = MovieFindForm
    initial = {"partial_title": ""}

    def get(self, request, *args, **kwargs):
        """Handle request to find movies."""
        logger.debug(
            "Find GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs
        )
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})


class MovieFindResultsView(LoginRequiredMixin, View):
    """Show prospective movies, based on the title provided."""

    template_name = "viewmaster/find_results.html"

    def get(self, request, *args, **kwargs):
        """Show candidate movies from OMDBb for an edit request."""
        logger.debug("Find Results GET: ARGS %s, KWARGS %s", args, kwargs)
        logger.debug("REQUEST %s", dict(request.GET))
        title = request.GET.get("title", "missing title")
        existing_id = request.GET.get("identifier", 0)
        return self.get_all_candidates(request, title, existing_id)

    def post(self, request, **kwargs):
        """Show candidate movies from IMDB for an add request."""
        logger.debug("Find Results POST: %s KWARGS %s", request.POST, kwargs)
        partial_title = request.POST.get("partial_title")
        return self.get_all_candidates(request, partial_title)

    def get_all_candidates(self, request, partial_title, existing_id=0):
        """Obtain all possible candidates and display them."""
        logger.debug("looking for candidates for '%s' (%d)", partial_title, existing_id)
        if partial_title:
            results = search_movies(partial_title)
            success = results.get("Response", "Missing")
            count = results.get("totalResults", "Unknown")
            matches = results.get("Search", [])
            logger.debug(
                "Success: %s, Count: %s, Actual %d", success, count, len(matches)
            )
        context = {
            "matches": matches,
            "count": len(matches),
            "partial_title": partial_title or "",
            "identifier": existing_id,
        }
        return render(request, self.template_name, context)


class MovieCreateUpdateView(
    LoginRequiredMixin,
    SingleObjectTemplateResponseMixin,
    ModelFormMixin,
    ProcessFormView,
):  # pylint: disable=too-many-ancestors
    """View for creating a new movie entry."""

    model = Movie
    template_name = "viewmaster/create_update_movie.html"
    form_class = MovieCreateEditForm
    success_url = reverse_lazy("viewmaster:movie-list")

    def post(self, request, *args, **kwargs):
        """Create/update a movie."""
        logger.debug(
            "Create/Update POST: REQUEST %s, ARGS %s, KWARGS %s, SESSIION %s",
            dict(request.POST),
            args,
            kwargs,
            dict(request.session),
        )
        identifier = int(kwargs.get("pk", "0"))
        if identifier:
            self.object = Movie.objects.get(   # pylint: disable=attribute-defined-outside-init
                pk=identifier
            )
        else:
            self.object = None  # pylint: disable=attribute-defined-outside-init
        logger.debug("OBJ %s", self.object)
        if "save_and_clear" in request.POST:
            self.success_url = reverse(
                "viewmaster:movie-clear", kwargs={"pk": identifier}
            )
            logger.debug("Saving and will then clear IMDB info")
            post_copy = request.POST.copy()
            post_copy.update(
                {
                    "plot": "",
                    "actors": "",
                    "directors": "",
                    "movie_id": "",
                    "cover_ref": "",
                }
            )
            request.POST = post_copy
        self.success_url = reverse("viewmaster:movie-list")
        return super().post(request, *args, **kwargs)

    def has_movie_id(self, entry: str) -> bool:
        """Indicates if have real movie ID."""
        return entry.startswith("tt")

    def get_movie_info(self, movie_id: str, movie: Movie) -> dict:
        """Pull IMDB info if selected."""
        existing_IMDB = self.has_movie_id(movie.movie_id) if movie else False  # pylint: disable=invalid-name

        if not existing_IMDB and self.has_movie_id(movie_id):
            logger.debug("Looking up IMDB entry %s", movie_id)
            results = get_movie(movie_id)
            if results.get("Response", "Unknown") == "True":
                logger.info("Found IMDB info")
                return results
            logger.error("Unable to get movie info for %s", movie_id)
        return {}

    def prepare_form_and_overrides(
        self, movie: Movie, imdb_info: dict, entered_title: str
    ):
        """Setup initial values and overrides."""
        initial = {}
        overrides = {}
        suggested_genres = ""

        rating = extract_rating(imdb_info.get("Rated", "?"))
        duration = (
            extract_time(imdb_info.get("Runtime")) if imdb_info.get("Runtime") else "?"
        )
        release = extract_year(imdb_info.get("Year")) if imdb_info.get("Year") else "?"
        if not movie:  # New movie
            initial.update(
                {
                    "title": imdb_info.get("Title", entered_title),
                    "release": release,
                    "rating": rating,
                    "duration": duration,
                }
            )
        else:
            if rating not in ("?", movie.rating):
                logger.warning(
                    "Overriding existing MPAA rating %s with IMDB value %s",
                    movie.rating,
                    rating,
                )
                initial["rating"] = rating
                overrides["rating"] = True
            stored_duration = movie.duration.strftime("%H:%M")
            if duration not in ("?", stored_duration):
                logger.warning(
                    "Overriding existing duration '%s' with IMDB value '%s'",
                    stored_duration,
                    duration,
                )
                initial["duration"] = duration
                overrides["duration"] = True
            if release not in ("?", movie.release):
                logger.warning(
                    "Overriding existing release date %s with IMDB value %s",
                    movie.release,
                    release,
                )
                initial["release"] = release
                overrides["release"] = True
        if imdb_info:  # New info provided
            logger.debug("Storing collected IMDB info")
            initial.update(
                {
                    "movie_id": imdb_info.get("imdbID"),
                    "plot": imdb_info.get("Plot", ""),
                    "actors": imdb_info.get("Actors", ""),
                    "directors": imdb_info.get("Director", ""),
                    "cover_ref": imdb_info.get("Poster", ""),
                }
            )
        suggested_genres = imdb_info.get("Genre", "")
        initial.update({"category_choices": order_genre_choices(suggested_genres)})
        logger.debug("Initial values: %s", initial)
        form = self.form_class(initial=initial, instance=movie)
        return (form, overrides)

    def get(self, request, *args, **kwargs):
        """Show form to create/update movie."""
        logger.debug(
            "GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs
        )
        movie_id = request.GET.get("movie_id") or "unknown"
        title = request.GET.get("title") or ""
        identifier = int(kwargs.get("pk", 0))
        logger.debug(
            "MovieID: %s, Title: %s, identifier: %d",
            movie_id,
            title,
            identifier,
        )

        movie = Movie.objects.get(pk=identifier) if identifier else None
        self.object = movie  # pylint: disable=attribute-defined-outside-init
        imdb_info = self.get_movie_info(movie_id, movie)
        form, overrides = self.prepare_form_and_overrides(movie, imdb_info, title)
        return render(
            request,
            self.template_name,
            {"form": form, "movie": movie, "overrides": overrides},
        )


class MovieLookupView(
    LoginRequiredMixin, UpdateView
):  # pylint: disable=too-many-ancestors
    """Show prospective movies, based on the title and release date provided."""

    model = Movie
    template_name = "viewmaster/create_update_movie.html"
    form_class = MovieCreateEditForm
    success_url = reverse_lazy("viewmaster:movie-list")

    def get(self, request, *args, **kwargs):
        """Handle editing of movie and either lookup IMDB info or go to editing."""
        logger.debug(
            "GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs
        )
        movie = self.get_object()
        logger.debug("MOVIE: %s", movie)
        if not movie.movie_id or movie.movie_id == "unknown":
            logger.debug("Movie does not have IMDB info")

            return redirect(
                reverse("viewmaster:movie-find-results")
                + f"?{urlencode({'title': movie.title, 'identifier': movie.id})}"
            )

        logger.debug("Movie already has IMDB info")
        return redirect(
            reverse("viewmaster:movie-create-update", kwargs={"pk": movie.id})
            + f"?{urlencode({'title': movie.title, 'movie_id': movie.movie_id})}"
        )


class MovieDeleteView(
    LoginRequiredMixin, DeleteView
):  # pylint: disable=too-many-ancestors
    """View for confirming the deletion of a movie entry."""

    model = Movie
    template_name = "viewmaster/movie_confirm_delete.html"
    # success_url = reverse_lazy('viewmaster:movie-list')

    def get(self, request, *args, **kwargs):
        """Form for delete confirmation."""
        logger.debug(
            "Delete GET: REQUEST %s, ARGS %s, KWARGS %s",
            dict(request.GET),
            args,
            kwargs,
        )
        identifier = int(kwargs.get("pk", "0"))
        movie = Movie.objects.get(pk=identifier)
        logger.debug("Movie to delete %s (%d)", movie, identifier)
        return render(request, self.template_name, {"movie": movie})

    def post(self, request, *args, **kwargs):
        """Delete the movie"""
        logger.debug(
            "Delete POST: REQUEST %s, ARGS %s, KWARGS %s",
            dict(request.POST),
            args,
            kwargs,
        )
        self.success_url = reverse("viewmaster:movie-list")
        return super().post(request, *args, **kwargs)


class MovieClearView(
    LoginRequiredMixin, UpdateView
):  # pylint: disable=too-many-ancestors
    """View for confirming the clearing of IMDB info."""

    model = Movie
    form_class = MovieClearForm
    template_name = "viewmaster/clear_imdb.html"
    success_url = reverse_lazy("viewmaster:movie-list")

    def post(self, request, *args, **kwargs):
        """Clear movie's IDMB info."""
        logger.debug(
            "POST: REQUEST %s, ARGS %s, KWARGS %s", dict(request.POST), args, kwargs
        )
        if "clear_and_find" in request.POST:
            identifier = int(kwargs.get("pk", "0"))
            movie = Movie.objects.get(pk=identifier)
            self.success_url = (
                reverse("viewmaster:movie-find-results")
                + f"?{urlencode({'title': movie.title, 'identifier': movie.id})}"
            )
            logger.debug("Clear and then find using '%s'", self.success_url)
        else:
            logger.debug("Clearing")
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Show confirmation form to clear IMDB info."""
        logger.debug(
            "GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs
        )
        identifier = int(kwargs.get("pk", "0"))
        movie = Movie.objects.get(pk=identifier)
        logger.debug("Movie to clear %s (%d)", movie, identifier)
        movie.movie_id = "unknown"
        movie.plot = ""
        movie.actors = ""
        movie.directors = ""
        movie.cover_ref = ""
        self.object = movie  # pylint: disable=attribute-defined-outside-init
        form = self.form_class(initial={}, instance=movie)
        return render(request, self.template_name, {"form": form, "movie": movie})
