from django.contrib import admin
from .models import Periodo, TipoEvento, Evento

admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(Evento)