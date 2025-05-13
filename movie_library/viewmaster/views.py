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

from .api import search_movies
from .extractors import order_genre_choices
from .models import ImdbInfo, Movie
from .forms import MovieClearForm, MovieCreateEditForm, MovieImdbCreateEditForm
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
        movies = Movie.objects
        if request.POST.get("phrase") or (
            request.POST.get("search.x") and request.POST.get("search.y")
        ):
            phrase = request.POST.get("phrase")
            how = request.POST.get("search_by", "title")
            if how == "actors":
                movies = movies.filter(actors__icontains=phrase)
            elif how == "directors":
                movies = movies.filter(directors__icontains=phrase)
            elif how == "plot":
                movies = movies.filter(plot__icontains=phrase)
            else:  # Default is title
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
            movies = movies.order_by("-release", Lower("title"))
        elif mode == "collection":
            movies = (
                movies.exclude(collection__isnull=True)
                .exclude(collection__exact="")
                .order_by(Lower("collection"), "release")
            )
        else:  # disk format
            movies = movies.order_by(Lower("format"), Lower("title"))
        logger.debug("POST Have %d movies with mode %s", total_movies, mode)
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
        if mode == "alpha":
            movies = movies.order_by(Lower("title"))
        elif mode == "cat_alpha":
            movies = movies.order_by(Lower("category"), Lower("title"))
        elif mode == "cat_date_alpha":
            movies = movies.order_by(Lower("category"), "-release", Lower("title"))
        elif mode == "date":
            movies = movies.order_by("-release", Lower("title"))
        elif mode == "collection":
            movies = (
                movies.exclude(collection__isnull=True)
                .exclude(collection__exact="")
                .order_by(Lower("collection"), "release")
            )
        else:  # disk format
            movies = movies.order_by(Lower("format"), Lower("title"))
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

    def get_movie_changes(self, request):
        """Obtain all the movie changes from request."""
        movie_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieCreateEditForm.Meta.fields
        }
        logger.debug("Movie request: %s", movie_changes)
        return movie_changes

    def get_imdb_changes(self, request) -> dict:
        """Obtain all the IMDB info provided in request."""
        imdb_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieImdbCreateEditForm.base_fields
        }
        if imdb_changes.get("cover_url"):
            if not imdb_changes["cover_url"].startswith("http"):
                logger.warning(
                    "Had cover URL that was not valid (%s) - clearing",
                    imdb_changes["cover_url"],
                )
                imdb_changes["cover_url"] = ""
        logger.debug("IMDB request: %s", imdb_changes)
        return imdb_changes

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
        movie = Movie.find(identifier)
        movie_changes = self.get_movie_changes(request)
        movie_form = MovieCreateEditForm(movie_changes, instance=movie)

        if "save_and_clear" in request.POST:  # Forcing clear of IMDB info
            self.success_url = reverse(
                "viewmaster:movie-clear", kwargs={"pk": identifier}
            )
            logger.debug("User selected to clear IMDB info")
            imdb_identifier = "unknown"
        else:  # see if user requested IMDB info
            imdb_identifier = request.POST.get("identifier", "unknown")
            logger.debug("IMDB ID '%s'", imdb_identifier)

        if imdb_identifier == "unknown":
            logger.debug("No IMDB info")
            imdb_info = None
        else:
            imdb_info = ImdbInfo.get(imdb_identifier)
            if not imdb_info:
                logger.debug("Using request data for IMDB info: %s", imdb_identifier)
            else:
                logger.debug("Using existing IMDB info for %s", imdb_identifier)
        imdb_changes = self.get_imdb_changes(request)
        imdb_form = MovieImdbCreateEditForm(imdb_changes, instance=imdb_info)

        if movie_form.is_valid():
            previous_imdb_id = None
            if imdb_identifier == "unknown":
                if movie and movie.imdb_info:
                    previous_imdb_id = movie.imdb_info.id
                logger.debug("No IMDB info or being cleared")
            else:  # Specifying IMDB info
                if not imdb_info:  # New IMDB info
                    if imdb_form.is_valid():
                        imdb_info = imdb_form.save()
                        logger.debug("Saved new IMDB info %s", imdb_info)
                    else:  # Bad IMDB info
                        logging.error("IMDB form failed validation")
                        return render(
                            request,
                            self.template_name,
                            {
                                "form": movie_form,
                                "imdb_form": imdb_form,
                                "movie": None,
                            },
                        )
                else:  # Existing IMDB info
                    if imdb_info.cover_url and not imdb_info.cover_file:
                        logger.debug("Trying to store cover file")
                        imdb_info.create_cover_file()
                    logger.debug("Existing IMDB info")
            saved_movie = movie_form.save(commit=False)
            saved_movie.imdb_info = imdb_info
            saved_movie.save()
            ImdbInfo.remove_unused(previous_imdb_id)
            logger.info("Save completed")
            return HttpResponseRedirect(self.success_url)
        logging.error("Movie form failed validation")
        return render(
            request,
            self.template_name,
            {
                "form": movie_form,
                "imdb_form": imdb_form,
                "movie": None,
            },
        )

    def get_movie_info(self, movie_id: str) -> ImdbInfo:
        """Get/lookup IMDB info if ID provided."""
        if movie_id == "unknown":
            return None
        imdb_info = ImdbInfo.get(movie_id, lookup=True)
        logger.debug("Have %s", imdb_info)
        return imdb_info

    def prepare_forms(self, movie: Movie, imdb_info: ImdbInfo, entered_title: str):
        """Setup initial values and overrides."""
        initial = {}
        overridden = {}
        suggested_genres = ""
        if not movie:  # New movie
            if imdb_info:
                initial.update(
                    {
                        "title": imdb_info.title_name,
                        "release": imdb_info.release_date,
                        "rating": imdb_info.mpaa_rating,
                        "duration": imdb_info.run_time,
                    }
                )
                suggested_genres = imdb_info.genres
            else:
                initial["title"] = entered_title
                suggested_genres = ""
        else:
            initial["genre"] = movie.category.upper()
            if imdb_info:
                overridden = movie.detect_overrides_from(imdb_info)
                suggested_genres = imdb_info.genres
        initial.update({"category_choices": order_genre_choices(suggested_genres)})
        logger.debug("Initial values: %s", initial)
        form = self.form_class(initial=initial, instance=movie)
        if imdb_info:
            imdb_initial = {}
        else:
            imdb_initial = {
                "identifier": "unknown",
                "release_date": "0",
                "mpaa_rating": "?",
                "run_time": "0:00",
                "genres": "?",
                "title_name": "?",
            }
        logger.debug("Initial IMDB info %s", imdb_info)
        imdb_form = MovieImdbCreateEditForm(initial=imdb_initial, instance=imdb_info)
        return (form, imdb_form, overridden)

    def get(self, request, *args, **kwargs):
        """Show form to create/update movie."""
        logger.debug(
            "Create/Update GET: REQUEST %s, ARGS %s, KWARGS %s",
            dict(request.GET),
            args,
            kwargs,
        )
        movie_id = request.GET.get("movie_id") or "unknown"
        title = request.GET.get("title") or "MISSING TITLE!"
        identifier = int(kwargs.get("pk", 0))
        logger.debug(
            "MovieID: %s, Title: %s, identifier: %d",
            movie_id,
            title,
            identifier,
        )

        movie = Movie.objects.get(pk=identifier) if identifier else None
        self.object = movie  # pylint: disable=attribute-defined-outside-init
        imdb_info = self.get_movie_info(movie_id)
        form, imdb_form, overridden = self.prepare_forms(movie, imdb_info, title)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "imdb_form": imdb_form,
                "movie": movie,
                "info": imdb_info,
                "overridden": overridden,
            },
        )


def no_imdb_id(movie):
    """Indicates whether movie does not have an IMDB ID."""
    if not movie.imdb_info:
        return True
    if movie.imdb_info.identifier == "unknown":
        return True
    return False


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
        if no_imdb_id(movie):
            logger.debug("Movie does not have IMDB info")

            return redirect(
                reverse("viewmaster:movie-find-results")
                + f"?{urlencode({'title': movie.title, 'identifier': movie.id})}"
            )

        logger.debug("Movie already has IMDB info")
        return redirect(
            reverse("viewmaster:movie-create-update", kwargs={"pk": movie.id})
            + f"?{urlencode({'title': movie.title, 'movie_id': movie.imdb_info.identifier})}"
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
        identifier = kwargs.get("pk", 0)
        imdb_id = Movie.get_imdb_id(identifier)
        logger.debug("Deleting movie with ID %d (IMDB ID %s)", identifier, imdb_id)
        result = super().post(request, *args, **kwargs)
        ImdbInfo.remove_unused(imdb_id)
        return result


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
