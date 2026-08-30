from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('agenda/', views.agenda, name='agenda'),
    path('eventos/nuevo/', views.evento_crear, name='evento_crear'),
    path('eventos/<int:pk>/editar/', views.evento_editar, name='evento_editar'),
    path('eventos/<int:pk>/eliminar/', views.evento_eliminar, name='evento_eliminar'),
    path('presupuestos/', views.presupuesto_lista, name='presupuesto_lista'),
    path('presupuestos/nuevo/', views.presupuesto_form, name='presupuesto_crear'),
    path('presupuestos/<int:pk>/', views.presupuesto_detalle, name='presupuesto_detalle'),
    path('presupuestos/<int:pk>/editar/', views.presupuesto_form, name='presupuesto_editar'),
    path('presupuestos/<int:pk>/exportar-word/', views.presupuesto_exportar_word, name='presupuesto_exportar_word'),
]