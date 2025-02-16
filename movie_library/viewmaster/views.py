"""Views for the app."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .api import RESTClient
from .models import Movie
from .forms import MovieCreateForm, MovieFindForm, MovieForm
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


class MovieFindResultsView(LoginRequiredMixin, ListView):
    """Show prospective movies, based on the title provided."""
    template_name = "viewmaster/find_results.html"
    
    def post(self, request, **kwargs):
        """Show candidate movies from OMDb."""
        logger.debug(request.POST)
        partial_title = request.POST.get("partial_title")
        candidates = []
        if partial_title:
            omdb_client = RESTClient("http://www.omdbapi.com/?apikey=REDACTED")
            results = omdb_client.get(partial_title)
            success = results.get("Response", "Missing")
            count = results.get("totalResults", "Unknown")
            matches = results.get("Search", [])
            logger.debug("Success: %s, Count: %s, Actual %d", success, count, len(matches))
            # TODO: handle failure (display error and give option to go back? Or go back w/form error?)
            # TODO: Handle no results (option to go back and retry, or to continue - providing empty choice)
        context = {
            'matches': matches,
            'count': len(matches),
            'partial_title': partial_title or "",
        }
        return render(request, self.template_name, context)


class MovieCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new movie entry."""
    
    model = Movie
    template_name = "viewmaster/add_movie.html"
    form_class = MovieCreateForm
    initial = {
        'title': '',
        'format': '4K',
        'bad': False
    }
    success_url = reverse_lazy('viewmaster:movie-list')

    def get(self, request, *args, **kwargs):
        logger.debug("ARGS %s, KWARGS %s", args, kwargs)
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    # def get_initial(self, *args, **kwargs):
    #     """Set default values whenc creating a new movie."""
    #     initial = super(MovieCreateView, self).get_initial(**kwargs)
    #     logger.debug("ARGS %s, KWARGS %s", args, kwargs)
    #     initial['format'] = '4K'
    #     initial['bad'] = False
    #     return initial


class MovieUpdateView(LoginRequiredMixin, UpdateView):
    """View for changing existing movie details."""
    
    model = Movie
    template_name = "viewmaster/edit_movie.html"
    form_class = MovieForm
    success_url = reverse_lazy('viewmaster:movie-list')


class MovieDeleteView(LoginRequiredMixin, DeleteView):
    """View for confirming the deletion of a movie entry."""
    
    model = Movie
    success_url = reverse_lazy('viewmaster:movie-list')
