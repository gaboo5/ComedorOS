from django.contrib import admin

from .models import (
    CategoriaVenta,
    ComponentePromo,
    ItemCarta,
    Jornada,
    LineaTicket,
    ProductoVenta,
    Promo,
    Ticket,
    VarianteVenta,
)


class VarianteInline(admin.TabularInline):
    model = VarianteVenta
    extra = 1


@admin.register(ProductoVenta)
class ProductoVentaAdmin(admin.ModelAdmin):
    inlines = [VarianteInline]
    list_display = ['nombre', 'categoria', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre']


admin.site.register(CategoriaVenta)


class ComponenteInline(admin.TabularInline):
    model = ComponentePromo
    extra = 1


@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    inlines = [ComponenteInline]
    list_display = ['nombre', 'precio', 'jornada', 'activo']
    list_filter = ['jornada']


class ItemCartaInline(admin.TabularInline):
    model = ItemCarta
    extra = 0


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    inlines = [ItemCartaInline]
    list_display = ['fecha', 'nombre', 'estado', 'evento']
    list_filter = ['estado']


class LineaInline(admin.TabularInline):
    model = LineaTicket
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    inlines = [LineaInline]
    list_display = ['numero', 'jornada', 'caja', 'creado', 'total', 'pago_efectivo', 'pago_qr', 'anulado']
    list_filter = ['jornada', 'caja', 'anulado']
