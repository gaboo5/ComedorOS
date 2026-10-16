from django.contrib import admin

from .models import (
    CategoriaInventario,
    Compra,
    ConceptoCostoPersonal,
    DetalleCosto,
    ElementoInventario,
    EnvioLavanderia,
    Evento,
    Extra,
    FuncionActividad,
    InformeGestion,
    Integrante,
    ItemCompra,
    ItemCostoPersonal,
    ItemEnvioLavanderia,
    ItemPrestamo,
    OpcionMenu,
    Pago,
    Periodo,
    PersonaEventual,
    Prestamo,
    Presupuesto,
    Producto,
    ResumenFacturacionMensual,
    TipoEvento,
    TipoServicio,
)


# ---------------------------------------------------------------- Eventos
class DetalleCostoInline(admin.StackedInline):
    model = DetalleCosto
    can_delete = False


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    inlines = [DetalleCostoInline]
    list_display = ['nombre', 'fecha', 'cliente', 'origen', 'costo', 'precio_facturado', 'estado_facturacion']
    list_filter = ['origen', 'estado_facturacion', 'periodo', 'excluir_de_informe']
    search_fields = ['nombre', 'cliente', 'solicitante']

    def save_model(self, request, obj, form, change):
        # Si lo editás a mano, la sincronización con Excel ya no lo pisa.
        if change:
            obj.importado_automaticamente = False
        super().save_model(request, obj, form, change)


admin.site.register(Periodo)
admin.site.register(TipoEvento)
admin.site.register(TipoServicio)
admin.site.register(Extra)


# ---------------------------------------------------------------- Presupuestos
class OpcionMenuInline(admin.StackedInline):
    model = OpcionMenu
    extra = 1
    fk_name = 'presupuesto'


class ItemCostoPersonalInline(admin.TabularInline):
    model = ItemCostoPersonal
    extra = 1


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    inlines = [OpcionMenuInline, ItemCostoPersonalInline]
    list_display = ['evento', 'lugar', 'fecha_creacion']
    filter_horizontal = ['extras_incluidos']


admin.site.register(ConceptoCostoPersonal)


# ---------------------------------------------------------------- Informes
admin.site.register(InformeGestion)
admin.site.register(ResumenFacturacionMensual)


# ---------------------------------------------------------------- Equipo
admin.site.register(Integrante)
admin.site.register(FuncionActividad)


# ---------------------------------------------------------------- Compras
class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    inlines = [ItemCompraInline]
    list_display = ['fecha', 'proveedor', 'evento']
    list_filter = ['fecha']
    autocomplete_fields = ['evento']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    search_fields = ['nombre']


# ---------------------------------------------------------------- Pagos
@admin.register(PersonaEventual)
class PersonaEventualAdmin(admin.ModelAdmin):
    search_fields = ['apellido', 'nombre', 'dni']


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'tipo_pago', 'persona', 'evento', 'importe']
    list_filter = ['tipo_pago', 'fecha']
    autocomplete_fields = ['evento']


# ---------------------------------------------------------------- Inventario
@admin.register(ElementoInventario)
class ElementoInventarioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'cantidad_total', 'cantidad_disponible']
    list_filter = ['categoria']
    search_fields = ['nombre']


class ItemEnvioLavanderiaInline(admin.TabularInline):
    model = ItemEnvioLavanderia
    extra = 1


@admin.register(EnvioLavanderia)
class EnvioLavanderiaAdmin(admin.ModelAdmin):
    inlines = [ItemEnvioLavanderiaInline]


class ItemPrestamoInline(admin.TabularInline):
    model = ItemPrestamo
    extra = 1


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    inlines = [ItemPrestamoInline]


admin.site.register(CategoriaInventario)
