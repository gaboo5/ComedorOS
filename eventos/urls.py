from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('agenda/', views.agenda, name='agenda'),
    path('eventos/nuevo/', views.evento_crear, name='evento_crear'),
    path('eventos/<int:pk>/editar/', views.evento_editar, name='evento_editar'),
    path('eventos/<int:pk>/eliminar/', views.evento_eliminar, name='evento_eliminar'),
]