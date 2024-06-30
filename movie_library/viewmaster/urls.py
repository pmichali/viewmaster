from django.urls import path

from .views import MovieCreateView, MovieDeleteView, MovieListView, MovieUpdateView

app_name = 'viewmaster'
urlpatterns = [
    path('', MovieListView.as_view(), name='movie-list'),
    path('create/', MovieCreateView.as_view(), name='movie-add'),
    path('<int:pk>/update/', MovieUpdateView.as_view(), name='movie-update'),
    path('<int:pk>/delete/', MovieDeleteView.as_view(), name='movie-delete'),
]