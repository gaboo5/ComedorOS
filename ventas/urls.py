from django.urls import path

from . import views

urlpatterns = [
    # Jornadas
    path('', views.pv_jornada_lista, name='pv_jornada_lista'),
    path('jornadas/nueva/', views.pv_jornada_form, name='pv_jornada_crear'),
    path('jornadas/<int:pk>/editar/', views.pv_jornada_form, name='pv_jornada_editar'),
    path('jornadas/<int:pk>/carta/', views.pv_carta, name='pv_carta'),
    path('jornadas/<int:pk>/caja/', views.pv_caja, name='pv_caja'),
    path('jornadas/<int:pk>/tickets/', views.pv_tickets, name='pv_tickets'),
    path('jornadas/<int:pk>/tickets/<int:numero>/anular/', views.pv_ticket_anular, name='pv_ticket_anular'),
    path('jornadas/<int:pk>/cierre/', views.pv_cierre, name='pv_cierre'),
    path('jornadas/<int:pk>/estado/', views.pv_jornada_estado, name='pv_jornada_estado'),
    path('jornadas/<int:pk>/registrar-en-agenda/', views.pv_registrar_evento, name='pv_registrar_evento'),

    # Endpoints que usa la pantalla de caja
    path('ping/', views.pv_ping, name='pv_ping'),
    path('jornadas/<int:pk>/api/ticket/', views.pv_api_ticket, name='pv_api_ticket'),
    path('jornadas/<int:pk>/api/precio/', views.pv_api_precio, name='pv_api_precio'),
    path('jornadas/<int:pk>/api/promo/', views.pv_api_promo, name='pv_api_promo'),

    # Catálogo
    path('catalogo/', views.pv_catalogo, name='pv_catalogo'),
    path('catalogo/productos/nuevo/', views.pv_producto_form, name='pv_producto_crear'),
    path('catalogo/productos/<int:pk>/editar/', views.pv_producto_form, name='pv_producto_editar'),
    path('catalogo/promos/nueva/', views.pv_promo_form, name='pv_promo_crear'),
    path('catalogo/promos/<int:pk>/editar/', views.pv_promo_form, name='pv_promo_editar'),
]
