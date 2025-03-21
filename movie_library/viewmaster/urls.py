"""URL definitions for viewmaster sections."""

from django.urls import path

from .views import MovieClearView, MovieCreateUpdateView, MovieDeleteView, MovieFindView
from .views import MovieFindResultsView, MovieListView, MovieLookupView

app_name = "viewmaster"  # pylint: disable=invalid-name
urlpatterns = [
    path("", MovieListView.as_view(), name="movie-list"),
    path("find/", MovieFindView.as_view(), name="movie-find"),
    path("find_results/", MovieFindResultsView.as_view(), name="movie-find-results"),
    path(
        "create_update/<int:pk>/",
        MovieCreateUpdateView.as_view(),
        name="movie-create-update",
    ),
    path("<int:pk>/lookup/", MovieLookupView.as_view(), name="movie-lookup"),
    path("<int:pk>/delete/", MovieDeleteView.as_view(), name="movie-delete"),
    path("<int:pk>/clear/", MovieClearView.as_view(), name="movie-clear"),
]
