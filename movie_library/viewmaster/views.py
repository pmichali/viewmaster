"""Views for the app."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
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
from .models import Movie, MovieDetails
from .forms import MovieCreateEditForm, MovieDetailsCreateEditForm
from .forms import MovieFindForm, MovieListForm


logger = logging.getLogger(__name__)


class MovieListView(ListView):
    """View for display of movies in a variety of orderings."""

    template_name = "viewmaster/movie_list.html"
    form_class = MovieListForm

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
        movies = Movie.objects.all()
        if request.POST.get("phrase") or (
            request.POST.get("search.x") and request.POST.get("search.y")
        ):
            phrase = request.POST.get("phrase")
            how = request.POST.get("search_by", "title")
            if how == "actors":
                movies = movies.filter(details__actors__icontains=phrase)
            elif how == "directors":
                movies = movies.filter(details__directors__icontains=phrase)
            elif how == "plot":
                movies = movies.filter(details__plot__icontains=phrase)
            else:  # Default is title
                movies = movies.filter(details__title__icontains=phrase)
        if not show_ld:
            movies = movies.exclude(format="LD")
        logger.info("Mode: %s", mode)
        match mode:
            case "alpha":
                movies = movies.order_by(Lower("details__title"))
            case "cat_alpha":
                movies = movies.order_by(
                    Lower("details__genre"), Lower("details__title")
                )
            case "cat_date_alpha":
                movies = movies.order_by(
                    Lower("details__genre"),
                    "-details__release",
                    Lower("details__title"),
                )
            case "date":
                movies = movies.order_by("-details__release", Lower("details__title"))
            case "collection":
                movies = (
                    movies.exclude(collection__isnull=True)
                    .exclude(collection__exact="")
                    .order_by(
                        Lower("collection"), "details__release", Lower("details__title")
                    )
                )
            case _:  # disk format
                movies = movies.order_by(Lower("format"), Lower("details__title"))
        logger.debug("POST Have %d movies", movies.count())
        initial_values = {
            "mode": mode,
            "show_ld": show_ld,
            "show_details": show_details,
        }
        form = self.form_class(initial=initial_values)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "total": total_movies,
                "total_paid": total_paid,
                "stats": stats,
                "movies": movies,
            },
        )

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
        match mode:
            case "alpha":
                movies = movies.order_by(Lower("details__title"))
            case "cat_alpha":
                movies = movies.order_by(
                    Lower("details__genre"), Lower("details__title")
                )
            case "cat_date_alpha":
                movies = movies.order_by(
                    Lower("details__genre"),
                    "-details__release",
                    Lower("details__title"),
                )
            case "date":
                movies = movies.order_by("-details__release", Lower("details__title"))
            case "collection":
                movies = (
                    movies.exclude(collection__isnull=True)
                    .exclude(collection__exact="")
                    .order_by(
                        Lower("collection"), "details__release", Lower("details__title")
                    )
                )
            case _:  # disk format
                movies = movies.order_by(Lower("format"), Lower("details__title"))
        initial_values = {
            "mode": mode,
            "show_ld": show_ld,
            "show_details": show_details,
        }
        form = self.form_class(initial=initial_values)

        logger.debug("GET Have %d movies with mode %s", total_movies, mode)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "total": total_movies,
                "total_paid": total_paid,
                "stats": stats,
                "movies": movies,
            },
        )


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
        logger.debug("looking for candidates for '%s' (%s)", partial_title, existing_id)
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

    def collect_changes(self, request, identifier):
        """Gather all the changes for each model."""
        movie_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieCreateEditForm.Meta.fields
        }
        details_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieDetailsCreateEditForm.Meta.fields
        }
        logger.debug("Movie params: %s", movie_changes)
        logger.debug("Details params: %s", details_changes)

        if "save_and_clear" in request.POST:
            self.success_url = reverse(
                "viewmaster:movie-clear", kwargs={"pk": identifier}
            )
            logger.debug("Ensuring all details clear, for save/clear operation")
            details_changes.update(
                {
                    "plot": "",
                    "actors": "",
                    "directors": "",
                    "source": "unknown",
                    "cover_url": "",
                }
            )
            logger.debug("Revised details: %s", details_changes)
        return (movie_changes, details_changes)

    def get_details_to_change(self, movie, source, title):
        """Determine details to be updated.

        Can be for this movie, existing "shared" details, or None (meaning
        new details will be created from request data). If we are switching
        from unshared to shared details, we will note the old details to
        delete."""
        details_to_delete = None
        if not movie:
            logger.info("Creating new movie")
            details_to_use = MovieDetails.find(source, title)
        else:  # Editing a movie
            logger.info("Editing existing movie ID: %d", movie.id)
            details_to_use = movie.details
            logger.debug("EXISTING DETAILS %s", details_to_use)

            if movie.details_shared():
                logger.debug("Details are currently being shared")
                details_to_use = MovieDetails.find(source, title)
                if details_to_use:
                    if details_to_use.id == movie.details.id:
                        which = "same shared"
                    else:
                        which = "different shared"
                else:
                    which = "new"
                logger.debug("Using %s details", which)
            else:  # Not shared
                details_to_delete = details_to_use
                details_to_use = MovieDetails.find(source, title, details_to_delete)
                if details_to_use:
                    logger.debug(
                        "Switching from non-shared to shared details (delete old)"
                    )
                else:
                    logger.debug("Replacing (unshared) details")
        logger.debug("TARGET DETAILS %s", details_to_use)
        return (details_to_use, details_to_delete)

    def save_movie_and_details(self, movie_form, details_form):
        """Save movie and details."""
        saved_details = details_form.save()
        saved_details.update_cover_file()
        saved_movie = movie_form.save(commit=False)
        saved_movie.details = saved_details
        saved_movie.save()
        logger.debug("Saved movie and details")

    def post(self, request, *args, **kwargs):
        """Create/update a movie."""
        logger.debug(
            "Create/Update POST: POSTARGS %s, GETARGS %s, ARGS %s, KWARGS %s, SESSIION %s",
            request.POST.dict(),
            request.GET.dict(),
            args,
            kwargs,
            dict(request.session),
        )

        identifier = int(kwargs.get("pk", "0"))
        movie_changes, details_changes = self.collect_changes(request, identifier)

        source = details_changes.get("source", request.POST.get("source", "unknown"))
        title = details_changes.get(
            "title", request.POST.get("title", "MISSING TITLE!")
        )
        logger.info("Target source %s, target title '%s'", source, title)
        movie = Movie.find(identifier)
        details, old_details = self.get_details_to_change(movie, source, title)
        # Apply the changes
        movie_form = MovieCreateEditForm(movie_changes, instance=movie)
        details_form = MovieDetailsCreateEditForm(details_changes, instance=details)
        if movie_form.is_valid() and details_form.is_valid():
            self.save_movie_and_details(movie_form, details_form)
            if old_details:
                old_details.delete()
            return HttpResponseRedirect(self.success_url)
        logger.debug("Failed validation")
        return render(
            request,
            self.template_name,
            {
                "form": movie_form,
                "details_form": details_form,
                "movie": None,
            },
        )

    def get_movie_info(self, imdb_id: str) -> dict:
        """Pull IMDB info if have ID."""
        if not imdb_id.startswith("tt"):
            logger.debug("Not a valid IMDB ID: %s", imdb_id)
            return {}
        logger.debug("Looking up IMDB entry %s", imdb_id)
        results = get_movie(imdb_id)
        if results.get("Response", "Unknown") == "True":
            logger.info("Found IMDB info")
            return results
        logger.error("Unable to get movie info")
        return {}

    def prepare_form_and_overrides(
        self, movie: Movie, details: MovieDetails, imdb_info: dict, entered_title: str
    ):
        """Setup initial values and overrides."""
        details_initial = {}
        overrides = {}
        suggested_genres = ""

        rating = (
            extract_rating(imdb_info.get("Rated")) if imdb_info.get("Rated") else "?"
        )
        duration = (
            extract_time(imdb_info.get("Runtime")) if imdb_info.get("Runtime") else "?"
        )
        release = extract_year(imdb_info.get("Year")) if imdb_info.get("Year") else "?"
        if not details:  # No pre-existing details
            details_initial.update(
                {
                    "title": imdb_info.get("Title", entered_title),
                    "release": release,
                    "rating": rating,
                    "duration": duration,
                }
            )
        else:
            details_initial["genre"] = details.genre.upper()
            if rating not in ("?", details.rating):
                logger.warning(
                    "Overriding existing MPAA rating %s with IMDB value %s",
                    details.rating,
                    rating,
                )
                details_initial["rating"] = rating
                overrides["rating"] = True
                overrides["rating_value"] = details.rating
            stored_duration = details.duration.strftime("%H:%M")
            if duration not in ("?", stored_duration):
                logger.warning(
                    "Overriding existing duration '%s' with IMDB value '%s'",
                    stored_duration,
                    duration,
                )
                details_initial["duration"] = duration
                overrides["duration"] = True
                overrides["duration_value"] = stored_duration
            if release not in ("?", details.release):
                logger.warning(
                    "Overriding existing release date %s with IMDB value %s",
                    details.release,
                    release,
                )
                details_initial["release"] = release
                overrides["release"] = True
                overrides["release_value"] = details.release
        if imdb_info:  # New info provided
            logger.debug("Storing collected IMDB info")
            details_initial.update(
                {
                    "source": imdb_info.get("imdbID"),
                    "plot": imdb_info.get("Plot", ""),
                    "actors": imdb_info.get("Actors", ""),
                    "directors": imdb_info.get("Director", ""),
                    "cover_url": imdb_info.get("Poster", ""),
                }
            )
        suggested_genres = imdb_info.get("Genre", "")
        details_initial.update(
            {"category_choices": order_genre_choices(suggested_genres)}
        )
        logger.debug("Initial values: %s", details_initial)
        form = self.form_class(initial={}, instance=movie)
        details_form = MovieDetailsCreateEditForm(
            initial=details_initial, instance=details
        )
        return (form, details_form, overrides)

    def get(self, request, *args, **kwargs):
        """Show form to create/update movie."""
        logger.debug(
            "Create/Update GET: REQUEST %s, ARGS %s, KWARGS %s",
            dict(request.GET),
            args,
            kwargs,
        )
        imdb_id = request.GET.get("imdb_id") or "unknown"
        title = request.GET.get("title") or "TITLE NOT FOUND"
        identifier = int(kwargs.get("pk", 0))
        logger.debug(
            "MovieID: %s, Title: %s, identifier: %d",
            imdb_id,
            title,
            identifier,
        )

        movie = Movie.objects.get(pk=identifier) if identifier else None
        if movie:
            details = movie.details
        else:
            details = MovieDetails.find(imdb_id, title)
        imdb_info = self.get_movie_info(imdb_id)

        logger.debug("MOVIE: %s", movie)
        logger.debug("DETAILS: %s", details)
        logger.debug("IMDB: %s", imdb_info)
        self.object = movie  # pylint: disable=attribute-defined-outside-init
        form, details_form, overrides = self.prepare_form_and_overrides(
            movie, details, imdb_info, title
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "details_form": details_form,
                "movie": movie,
                "overrides": overrides,
            },
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
        if not movie.details.source or movie.details.source == "unknown":
            logger.debug("Movie does not have IMDB info")

            return redirect(
                reverse("viewmaster:movie-find-results")
                + f"?{urlencode({'title': movie.details.title, 'identifier': movie.id})}"
            )

        logger.debug("Movie already has IMDB info")
        return redirect(
            reverse("viewmaster:movie-create-update", kwargs={"pk": movie.id})
            + f"?{urlencode({'title': movie.details.title, 'imdb_id': movie.details.source})}"
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
        movie = self.get_object()
        details = movie.details
        movie.delete()
        if details.use_count() == 0:
            logger.info("Deleting details as not used any movies now")
            details.delete()
        success_url = reverse("viewmaster:movie-list")
        return HttpResponseRedirect(success_url)


class MovieClearView(LoginRequiredMixin, View):  # pylint: disable=too-many-ancestors
    """View for confirming the clearing of IMDB info."""

    model = Movie
    template_name = "viewmaster/clear_imdb.html"

    def get(self, request, *args, **kwargs):
        """Show choices after save and clear movie."""
        logger.debug(
            "CLEAR GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs
        )
        identifier = int(kwargs.get("pk", "0"))
        movie = Movie.objects.get(pk=identifier)
        return render(request, self.template_name, {"movie": movie})
