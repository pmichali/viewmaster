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


def bad_url(cover_ref):
    """If present, does simple check to see if URL is valid"""
    return cover_ref and not cover_ref.startswith("http")


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

    def bad_cover_ref(self, post_data):
        """Check to see if current or to be changed cover URL is valid."""
        if bad_url(post_data.get("cover_ref")):
            logger.debug("Cover URL being set is invalid (%s)", post_data["cover_ref"])
            return True
        if self.object and bad_url(self.object.cover_ref):
            logger.debug("Existing cover URL is not valid (%s)", self.object.cover_ref)
            return True
        return False

    def collect_changes(self, request, identifier):
        """Gather all the changes for each model."""
        # TODO: Change this to use imdb_info vs details, and make sure we have meta fields set right
        movie_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieCreateEditForm.Meta.fields
        }
        logger.debug("Movie params: %s", movie_changes)
        imdb_changes = {
            k: v
            for k, v in request.POST.items()
            if k in MovieImdbCreateEditForm.Meta.fields
        }
        if imdb_changes.get("imdb_cover_url"):
            if not imdb_changes["imdb_cover_url"].startswith("http"):
                logger.warning(
                    "Had cover URL that was not valid (%s) - clearing",
                    imdb_changes["imdb_cover_url"],
                )
                imdb_changes["imdb_cover_url"] = ""
        logger.debug("IMDB params: %s", imdb_changes)

        # if "save_and_clear" in request.POST:
        #     self.success_url = reverse(
        #         "viewmaster:movie-clear", kwargs={"pk": identifier}
        #     )
        #     logger.debug("Ensuring all IMDB info is clear, for save/clear operation")
        #     imdb_changes.update(
        #         {
        #             "plot": "",
        #             "actors": "",
        #             "directors": "",
        #             "identifier": "unknown",  # needed or do we disconnect movie from imdb?
        #             "cover_url": "",
        #             # TODO: What about cover_file? identifier? movie ref to imdb_info?
        #         }
        #     )
        #     logger.debug("Revised IMDB: %s", imdb_changes)
        return (movie_changes, imdb_changes)

    # def get_imdb_info_to_change(self, movie, imdb_id, title):
    #     """Determine details to be updated.
    #     If currently sharing details, could edit same details,
    #     switch to another shared details, or create new details (None).
    #
    #     If not sharing details, could edit same details, switch
    #     to a shared detail, or to another non-shared (new)
    #     details. In all three cases, must flag to delete any
    #     existing cover file. New cover files may be created
    #     by the new detail selection."""
    #     old_details = None
    #     if not movie:
    #         logger.info("Creating new movie")
    #         details_to_use = MovieDetails.find(source, title)
    #     else:  # Editing a movie
    #         logger.info("Editing existing movie ID: %d", movie.id)
    #         details_to_use = movie.details
    #         logger.debug("EXISTING DETAILS %s", details_to_use)
    #
    #         if movie.details_shared():
    #             was = ""
    #         else:  # Not shared
    #             was = "un"
    #             old_details = movie.details
    #         details_to_use = MovieDetails.find(source, title)
    #         logger.error("SOURCE=%s TITLE=%s DETAILS %s", source, title, details_to_use)
    #         if details_to_use:
    #             if details_to_use.id == movie.details.id:
    #                 which = "same"
    #             else:
    #                 which = "different shared"
    #         else:
    #             which = "new"
    #         logger.debug("For currently %sshared details using %s details", was, which)
    #     logger.debug("TARGET DETAILS %s", details_to_use)
    #     return (details_to_use, old_details)

    # def save_movie_and_details(self, movie_form, details_form):
    #     """Save movie and details."""
    #     saved_details = details_form.save()
    #     saved_details.update_cover_file()
    #     saved_movie = movie_form.save(commit=False)
    #     saved_movie.details = saved_details
    #     saved_movie.save()
    #     logger.debug("Saved movie and details")

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
        movie_changes, imdb_changes = self.collect_changes(request, identifier)

        imdb_id = imdb_changes.get(
            "identifier", request.POST.get("identifier", "unknown")
        )
        title = movie_changes.get("title", request.POST.get("title", "MISSING TITLE!"))
        logger.info("Target IMDB %s, target title '%s'", imdb_id, title)
        movie = Movie.find(identifier)
        imdb_info = ImdbInfo.find_or_retrieve(imdb_id)
        # imdb_info, old_imdb_info = self.get_imdb_info_to_change(movie, imdb_id, title)
        # Apply the changes
        movie_form = MovieCreateEditForm(movie_changes, instance=movie)
        imdb_form = MovieImdbCreateEditForm(imdb_changes, instance=imdb_info)
        # if movie_form.is_valid() and imdb_form.is_valid():
        #     logger.info("Valid forms")
        #     # if old_imdb_info:   # TOOD: This should delete IMDB entry, if no refs, including file...
        #     #     old_imdb_info.delete_cover()
        #     # self.save_movie_and_details(movie_form, imdb_form)
        #     return HttpResponseRedirect(self.success_url)
        # logger.debug(
        #     "Failed validation: Movie is %svalid. Details are %svalid",
        #     "" if movie_form.is_valid() else "not ",
        #     "" if imdb_form.is_valid() else "not ",
        # )
        return render(
            request,
            self.template_name,
            {
                "form": movie_form,
                "imdb_form": imdb_form,
                "movie": None,
            },
        )

    def has_movie_id(self, entry: str) -> bool:
        """Indicates if have real movie ID."""
        return entry.startswith("tt")

    def get_movie_info(self, movie_id: str) -> ImdbInfo:
        """Get/lookup IMDB info if ID provided."""
        if movie_id == "unknown":
            return {}
        imdb_info = ImdbInfo.find_or_retrieve(movie_id)
        logger.debug("Have %s", imdb_info)
        return imdb_info

    def prepare_forms(self, movie: Movie, imdb_info: ImdbInfo, entered_title: str):
        """Setup initial values and overrides."""
        initial = {}
        overridden = {}
        if not movie:  # New movie
            if imdb_info:
                initial.update(
                    {
                        "title": imdb_info.title,
                        "release": imdb_info.release,
                        "rating": imdb_info.rating,
                        "duration": imdb_info.duration,
                    }
                )
                suggested_genres = imdb_info.genres
            else:
                initial["title"] = entered_title
                suggested_genres = ""
        else:
            initial["genre"] = movie.category.upper()
            overridden = movie.detect_overrides_from(imdb_info)
            suggested_genres = imdb_info.genres
        initial.update({"category_choices": order_genre_choices(suggested_genres)})
        logger.debug("Initial values: %s", initial)
        form = self.form_class(initial=initial, instance=movie)
        imdb_form = MovieImdbCreateEditForm(initial={}, instance=imdb_info)
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
                "overridden": overridden,
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
