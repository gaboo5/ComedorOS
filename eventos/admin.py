from django.contrib import admin
from .models import (
    Periodo, TipoEvento, TipoServicio, Evento, DetalleCosto,
    ItemPrecio, Extra, Presupuesto, OpcionMenu
)


class DetalleCostoInline(admin.StackedInline):
    model = DetalleCosto
    can_delete = False


class EventoAdmin(admin.ModelAdmin):
    inlines = [DetalleCostoInline]
    list_display = ['nombre', 'fecha', 'cliente', 'origen', 'costo', 'precio_facturado', 'estado_facturacion']
    list_filter = ['origen', 'estado_facturacion', 'periodo']
    search_fields = ['nombre', 'cliente', 'solicitante']


class OpcionMenuInline(admin.StackedInline):
    model = OpcionMenu
    extra = 1
    fk_name = 'presupuesto'


class PresupuestoAdmin(admin.ModelAdmin):
    inlines = [OpcionMenuInline]
    list_display = ['evento', 'lugar', 'fecha_creacion']
    filter_horizontal = ['extras_incluidos']
    autocomplete_fields = ['evento']


admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(TipoServicio)
admin.site.register(Evento, EventoAdmin)
admin.site.register(ItemPrecio)
admin.site.register(Extra)
admin.site.register(Presupuesto, PresupuestoAdmin)

from .models import InformeGestion  # sumalo al import existente de arriba

admin.site.register(InformeGestion)