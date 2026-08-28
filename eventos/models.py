from django.db import models


class Periodo(models.Model):
    """Representa un año o semestre. Todo el sistema se organiza en torno a esto."""
    anio = models.IntegerField(verbose_name="Año")
    semestre = models.IntegerField(choices=[(1, "1er semestre"), (2, "2do semestre")])
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('anio', 'semestre')
        ordering = ['-anio', '-semestre']

    def __str__(self):
        return f"{self.anio} - {self.semestre}° semestre"


class TipoEvento(models.Model):
    """Institucional, académico o de extensión."""
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Evento(models.Model):
    ESTADO_FACTURACION = [
        ('pendiente', 'Pendiente'),
        ('cobrado', 'Cobrado'),
    ]
    ORIGEN = [
        ('interno', 'Interno'),
        ('externo', 'Externo'),
    ]
    ESTADO_EVENTO = [
        ('presupuestado', 'Presupuestado'),
        ('confirmado', 'Confirmado'),
        ('realizado', 'Realizado'),
        ('cancelado', 'Cancelado'),
    ]

    nombre = models.CharField(max_length=200)
    tipo = models.ForeignKey(TipoEvento, on_delete=models.PROTECT)
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT)
    origen = models.CharField(max_length=10, choices=ORIGEN)
    fecha = models.DateField()
    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_facturado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_facturacion = models.CharField(max_length=10, choices=ESTADO_FACTURACION, default='pendiente')
    estado_evento = models.CharField(max_length=15, choices=ESTADO_EVENTO, default='presupuestado')

    @property
    def margen(self):
        return self.precio_facturado - self.costo

    def __str__(self):
        return f"{self.nombre} ({self.fecha})"


class ItemPrecio(models.Model):
    """Catálogo de precios por ítem o servicio, actualizable en el tiempo."""
    nombre = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=50, blank=True, help_text="Ej: por persona, por evento, por hora")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio_unitario}"


class Presupuesto(models.Model):
    evento = models.OneToOneField(Evento, on_delete=models.CASCADE, related_name='presupuesto')
    fecha_creacion = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.all()), 0)

    def __str__(self):
        return f"Presupuesto - {self.evento.nombre}"


class ItemPresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='items')
    item_precio = models.ForeignKey(ItemPrecio, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)

    @property
    def subtotal(self):
        return self.cantidad * self.item_precio.precio_unitario

    def __str__(self):
        return f"{self.item_precio.nombre} x {self.cantidad}"