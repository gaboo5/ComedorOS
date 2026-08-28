from django.contrib import admin
from .models import Periodo, TipoEvento, Evento, ItemPrecio, Presupuesto, ItemPresupuesto


class ItemPresupuestoInline(admin.TabularInline):
    model = ItemPresupuesto
    extra = 1


class PresupuestoAdmin(admin.ModelAdmin):
    inlines = [ItemPresupuestoInline]


admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(Evento)
admin.site.register(ItemPrecio)
admin.site.register(Presupuesto, PresupuestoAdmin)