from django.urls import path

from .views import MovieCreateView, MovieCreateUpdateView, MovieDeleteView, MovieFindView
from .views import MovieFindResultsView, MovieListView, MovieLookupView, MovieUpdateView

app_name = 'viewmaster'
urlpatterns = [
    path('', MovieListView.as_view(), name='movie-list'),
    path('find/', MovieFindView.as_view(), name='movie-find'),
    path('find_results/', MovieFindResultsView.as_view(), name='movie-find-results'),
    path('create/<str:movie_id>/', MovieCreateView.as_view(), name='movie-add'),
    path('create_update/<int:pk>/', MovieCreateUpdateView.as_view(), name='movie-create-update'),
    path('<int:pk>/lookup/', MovieLookupView.as_view(), name='movie-lookup'),
    path('<int:pk>/update/', MovieUpdateView.as_view(), name='movie-update'),
    path('<int:pk>/delete/', MovieDeleteView.as_view(), name='movie-delete'),
]