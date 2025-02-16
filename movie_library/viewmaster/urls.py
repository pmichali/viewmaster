from django.urls import path

from .views import MovieCreateView, MovieDeleteView, MovieFindView, MovieFindResultsView, MovieListView, MovieUpdateView

app_name = 'viewmaster'
urlpatterns = [
    path('', MovieListView.as_view(), name='movie-list'),
    path('find/', MovieFindView.as_view(), name='movie-find'),
    path('find_results/', MovieFindResultsView.as_view(), name='movie-find-results'),
    path('create/<str:movie_id>/', MovieCreateView.as_view(), name='movie-add'),
    path('<int:pk>/update/', MovieUpdateView.as_view(), name='movie-update'),
    path('<int:pk>/delete/', MovieDeleteView.as_view(), name='movie-delete'),
]