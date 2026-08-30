from django.contrib import admin
from .models import (
    Periodo, TipoEvento, TipoServicio, Evento, DetalleCosto,
    ItemPrecio, Presupuesto, ItemPresupuesto
)


class DetalleCostoInline(admin.StackedInline):
    model = DetalleCosto
    can_delete = False


class EventoAdmin(admin.ModelAdmin):
    inlines = [DetalleCostoInline]
    list_display = ['nombre', 'fecha', 'cliente', 'origen', 'costo', 'precio_facturado', 'estado_facturacion']
    list_filter = ['origen', 'estado_facturacion', 'periodo']
    search_fields = ['nombre', 'cliente', 'solicitante']


class ItemPresupuestoInline(admin.TabularInline):
    model = ItemPresupuesto
    extra = 1


class PresupuestoAdmin(admin.ModelAdmin):
    inlines = [ItemPresupuestoInline]


admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(TipoServicio)
admin.site.register(Evento, EventoAdmin)
admin.site.register(ItemPrecio)
admin.site.register(Presupuesto, PresupuestoAdmin)