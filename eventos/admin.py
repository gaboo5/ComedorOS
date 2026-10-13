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
    list_filter = ['origen', 'estado_facturacion', 'periodo', 'excluir_de_informe']
    search_fields = ['nombre', 'cliente', 'solicitante']

    def save_model(self, request, obj, form, change):
        if change:
            obj.importado_automaticamente = False
        super().save_model(request, obj, form, change)


class OpcionMenuInline(admin.StackedInline):
    model = OpcionMenu
    extra = 1
    fk_name = 'presupuesto'


class PresupuestoAdmin(admin.ModelAdmin):
    inlines = [OpcionMenuInline]
    list_display = ['evento', 'lugar', 'fecha_creacion']
    filter_horizontal = ['extras_incluidos']


admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(TipoServicio)
admin.site.register(Evento, EventoAdmin)
admin.site.register(ItemPrecio)
admin.site.register(Extra)
admin.site.register(Presupuesto, PresupuestoAdmin)

from .models import InformeGestion  # sumalo al import existente de arriba

admin.site.register(InformeGestion)

from .models import Integrante, FuncionActividad  # sumalo al import existente

admin.site.register(Integrante)
admin.site.register(FuncionActividad)

from .models import Producto, Compra, ItemCompra  # sumalo al import existente


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1


class CompraAdmin(admin.ModelAdmin):
    inlines = [ItemCompraInline]
    list_display = ['fecha', 'proveedor', 'evento']
    list_filter = ['fecha']
    autocomplete_fields = ['evento']


admin.site.register(Producto)
admin.site.register(Compra, CompraAdmin)

from .models import PersonaEventual, Pago  # sumalo al import existente


class PagoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'tipo_pago', 'persona', 'evento', 'importe']
    list_filter = ['tipo_pago', 'fecha']
    autocomplete_fields = ['evento']


admin.site.register(PersonaEventual, search_fields=['apellido', 'nombre', 'dni'])
admin.site.register(Pago, PagoAdmin)

from .models import ConceptoCostoPersonal, ItemCostoPersonal  # sumalo al import existente

admin.site.register(ConceptoCostoPersonal)

from .models import CategoriaInventario, ElementoInventario, EnvioLavanderia, Prestamo  # sumalo al import


class ElementoInventarioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'cantidad_total', 'cantidad_disponible']
    list_filter = ['categoria']


admin.site.register(CategoriaInventario)
admin.site.register(ElementoInventario, ElementoInventarioAdmin)
admin.site.register(EnvioLavanderia)
admin.site.register(Prestamo)