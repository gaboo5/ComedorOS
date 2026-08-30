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


class TipoServicio(models.Model):
    """Cafetería, Ágape, Almuerzo, Solo Salón, etc. — catálogo libre, se completa con el uso."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nombre']

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
    tipo = models.ForeignKey(TipoEvento, on_delete=models.PROTECT, null=True, blank=True)
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, null=True, blank=True)
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT)
    origen = models.CharField(max_length=10, choices=ORIGEN, default='interno')
    fecha = models.DateField()

    cliente = models.CharField(max_length=200, blank=True)
    solicitante = models.CharField(max_length=200, blank=True)
    cantidad_personas = models.IntegerField(null=True, blank=True)

    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_facturado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_facturacion = models.CharField(max_length=10, choices=ESTADO_FACTURACION, default='pendiente')
    estado_evento = models.CharField(max_length=15, choices=ESTADO_EVENTO, default='presupuestado')

    nro_factura = models.CharField(max_length=50, blank=True)
    nro_recibo = models.CharField(max_length=50, blank=True)
    expediente = models.CharField(max_length=50, blank=True)
    nro_comprobante = models.CharField(max_length=50, blank=True)

    @property
    def margen(self):
        return self.precio_facturado - self.costo

    def __str__(self):
        return f"{self.nombre} ({self.fecha})"


class DetalleCosto(models.Model):
    """Desglose del costo total de un evento. Opcional: no todos los eventos lo van a tener."""
    evento = models.OneToOneField(Evento, on_delete=models.CASCADE, related_name='detalle_costo')
    manteleria = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    materia_prima = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    personal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    planilla = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    varios = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def total(self):
        return self.manteleria + self.materia_prima + self.personal + self.planilla + self.varios

    def __str__(self):
        return f"Detalle de costo - {self.evento.nombre}"


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