"""Views for the app."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .api import get_movie, lookup_movie, search_movies
from .extractors import extract_rating, extract_time, extract_year, order_genre_choices
from .models import Movie
from .forms import MovieCreateEditForm, MovieFindForm
from pstats import Stats


logger = logging.getLogger(__name__)


class MovieListView(ListView):
    """View for display of movies in a variety of orderings."""
    
    context_object_name = 'movies'

    def post(self, request, **kwargs):
        """Show list based on selected ordering mode."""
        # print(request.POST)
        mode = request.POST.get("mode")
        if not mode:
            mode = request.POST.get("last_mode", "alpha")
        show_LD = True if request.POST.get("showLD") else False
        show_details = True if request.POST.get("show-details") else False
        total_movies = Movie.objects.count()
        total_paid = Movie.objects.filter(paid=True).count()
        stats = (
            Movie.objects.values('format')
            .filter(paid=True)
            .annotate(count=Count('format'), average=Avg('cost'))
            .order_by('format')
        )
        movies = Movie.objects
        if request.POST.get("search.x") and request.POST.get("search.y"):
            phrase = request.POST.get("phrase")
            movies = movies.filter(title__icontains=phrase)
        if not show_LD:
            movies = movies.exclude(format="LD")
        if mode == "alpha":
            movies = movies.order_by(Lower('title'))
        elif mode == "cat_alpha":
            movies = movies.order_by(Lower('category'), Lower('title'))
        elif mode == "cat_date_alpha":
            movies =  movies.order_by(Lower('category'), '-release', Lower('title'))
        elif mode == "date":
            movies = movies.order_by('-release', 'title')
        elif mode == "collection":
            movies = movies.exclude(collection__isnull=True).exclude(collection__exact='').order_by(Lower('collection'), 'release')
        else:  # disk format
            movies = movies.order_by(Lower('format'), Lower('title'))
        context = {
            'movies': movies,
            'mode': mode,
            'show_LD': show_LD,
            'show_details': show_details,
            'total': total_movies,
            'total_paid': total_paid,
            'stats': stats,
        }
        return render(request, 'viewmaster/movie_list.html', context)

    def get(self, request, **kwargs):
        """Initial view is alphabetical."""
        total_movies = Movie.objects.count()
        total_paid = Movie.objects.filter(paid=True).count()
        stats = (
            Movie.objects.values('format')
            .filter(paid=True)
            .annotate(count=Count('format'), average=Avg('cost'))
            .order_by('format')
        )

        movies = Movie.objects.exclude(format="LD").order_by(Lower('title'))
        context = {
            'movies': movies,
            'mode': "alpha",
            'show_LD': False,
            'show_details': False,
            'total': total_movies,
            'total_paid': total_paid,
            'stats': stats,
        }
        return render(request, 'viewmaster/movie_list.html', context)


class MovieFindView(LoginRequiredMixin, View):
    """View for finding movie info to create a movie."""
    
    template_name = "viewmaster/find_movie.html"
    form_class = MovieFindForm
    initial = {"partial_title": ""}
    success_url = reverse_lazy('viewmaster:movie-find-results')

    def get(self, request, *args, **kwargs):
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
        """Show candidate movies from OMDb for an add request."""
        logger.debug("Find Results POST: %s KWARGS %s", request.POST, kwargs)
        partial_title = request.POST.get("partial_title")
        return self.get_all_candidates(request, partial_title)
    
    
    def get_all_candidates(self, request, partial_title, existing_id=0):
        """Obtain all possible candidates and display them."""
        logging.debug("looking for candidates for '%s' (%d)", partial_title, existing_id)
        candidates = []
        if partial_title:
            results = search_movies(partial_title)
            success = results.get("Response", "Missing")
            count = results.get("totalResults", "Unknown")
            matches = results.get("Search", [])
            logger.debug("Success: %s, Count: %s, Actual %d", success, count, len(matches))
            if not matches:
                matches = [
                    {
                        "Title": partial_title,
                        "Year": "",
                        "imdbID": "unknown",
                        "Poster": ""
                    },
                ]
        context = {
            'matches': matches,
            'count': len(matches),
            'partial_title': partial_title or "",
            'identifier': existing_id,
        }
        return render(request, self.template_name, context)


class MovieCreateView(LoginRequiredMixin, UpdateView):
    """View for creating a new movie entry."""
    
    model = Movie
    template_name = "viewmaster/add_movie.html"
    form_class = MovieCreateEditForm
    success_url = reverse_lazy('viewmaster:movie-list')

    def get(self, request, *args, **kwargs):
        logger.debug("GET: REQUEST %s, ARGS %s, KWARGS %s", dict(request.GET), args, kwargs)
        movie_id = kwargs.get("movie_id", "unknown")
        title = request.GET.get('title') or ''
        identifier = int(request.GET.get('pk', 0))
        logger.debug("MovieID: %s, Title: %s, identifier: %d", movie_id, title, identifier)


        initial = {}
        suggested_genres = ""
        movie = None
        if identifier:  # Edit movie
            movie = Movie.objects.get(pk=identifier)
            logger.debug("EXISTING MOVIE: %s", movie)
            need_movie_info = (movie.movie_id == "" or movie.movie_id == "unknown")
        else:  # Add movie
            need_movie_info = True
            initial.update(
                {
                    'title': title,
                    'category': '',
                    'format': '4K',
                }
            )
        if need_movie_info and movie_id != "unknown":
            logger.debug("Looking up OMDb entry %s", movie_id)
            results = get_movie(movie_id)
            success = results.get("Response", "Unknown")
            if success == "True":
                rating = extract_rating(results.get('Rated', '?'))
                duration = extract_time(results.get('Runtime', 'Missing runtime'))
          
                if not identifier:  # New movie
                    initial.update(
                        {
                            'title': results.get('Title', ''),
                            'release': extract_year(results.get('Year','')),
                            'rating': extract_rating(results.get('Rated', '?')),
                            'duration': extract_time(results.get('Runtime', 'Missing runtime')),
                        }
                    )
                else:
                    if movie.rating != rating:
                        logging.warning("OMDb has different MPAA rating! %s vs %s", rating, movie.rating)
                    if movie.duration != duration:
                        logging.warning("OMDb has different duration! %s vs %s", duration, movie.duration)

                initial.update(
                    {
                        'movie_id': results.get("imdbID"),
                        'plot': results.get('Plot', ''),
                        'actors': results.get('Actors', ''),
                        'directors': results.get('Director', ''),
                        'cover_ref': results.get('Poster', ''),
                    }
                )
                suggested_genres = results.get('Genre', '')
                initial.update({'category_choices': order_genre_choices(suggested_genres)})
                logger.debug("Initial values: %s", initial)
            else:
                logging.error("Unable to get movie info for %s", movie_id)
        initial.update({'category_choices': order_genre_choices(suggested_genres)})
        logger.debug("Initial values: %s", initial)
        form = self.form_class(initial=initial, instance=movie)
        return render(request, self.template_name, {"form": form, 'movie': movie})


class MovieLookupView(LoginRequiredMixin, UpdateView):
    """Show prospective movies, based on the title and release date provided."""
    # template_name = "viewmaster/find_results.html"   # TODO CHANGE!!!!
    model = Movie
    template_name = "viewmaster/edit_movie.html"
    form_class = MovieCreateEditForm
    success_url = reverse_lazy('viewmaster:movie-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["more"] = "More info..."
        return context
        
    def get(self, request, *args, **kwargs):
        logger.debug("GET: ARGS %s, KWARGS %s", args, kwargs)
        movie = self.get_object()
        logger.debug("MOVIE: %s", movie)
        initial = {}
        if not movie.movie_id or movie.movie_id == "unknown":
            logging.debug("Movie does not have OMDb info")

            return redirect(reverse('viewmaster:movie-find-results') +
                            f"?{urlencode({'title': movie.title, 'identifier': movie.id})}")

        logger.debug("Movie already has OMDb info")
        return redirect(
            reverse('viewmaster:movie-add', kwargs={'movie_id': movie.movie_id}) +
                     f"?{urlencode({'title': movie.title, 'pk': movie.id})}"
        )

# REMOVE?
class MovieUpdateView(LoginRequiredMixin, UpdateView):
    """View for changing existing movie details."""
    
    model = Movie
    template_name = "viewmaster/edit_movie.html"
    form_class = MovieCreateEditForm
    success_url = reverse_lazy('viewmaster:movie-list')


class MovieDeleteView(LoginRequiredMixin, DeleteView):
    """View for confirming the deletion of a movie entry."""
    
    model = Movie
    success_url = reverse_lazy('viewmaster:movie-list')
