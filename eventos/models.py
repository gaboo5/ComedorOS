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
        partes = [self.fecha.strftime('%d/%m/%Y')]
        if self.tipo_servicio:
            partes.append(str(self.tipo_servicio))
        if self.cliente:
            partes.append(self.cliente)
        return ' - '.join(partes)


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
    """Catálogo de precios de referencia, actualizable en el tiempo. Es independiente del presupuesto
    (cada presupuesto define su propio precio por persona en cada opción de menú)."""
    nombre = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=50, blank=True, help_text="Ej: por persona, por evento, por hora")
    activo = models.BooleanField(default=True)
    actualizado = models.DateField(auto_now=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - ${self.precio_unitario}"


class Extra(models.Model):
    """Catálogo de extras/servicios que se pueden incluir en un presupuesto: vajilla, jugo, agua, mozos, etc."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Presupuesto(models.Model):
    """Presupuesto de un evento: lugar, extras incluidos y 2-3 opciones de menú con precio por persona."""
    evento = models.OneToOneField(Evento, on_delete=models.CASCADE, related_name='presupuesto')
    fecha_creacion = models.DateField(auto_now_add=True)
    lugar = models.CharField(max_length=200, blank=True)
    extras_incluidos = models.ManyToManyField(Extra, blank=True, related_name='presupuestos')
    otros_extras = models.TextField(blank=True, help_text="Cualquier extra que no esté en la lista de arriba.")
    cantidad_personas_celiaco = models.IntegerField(default=0)
    recargo_celiaco_por_persona = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    opcion_elegida = models.ForeignKey(
        'OpcionMenu', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', help_text="Se completa cuando el cliente confirma cuál opción eligió."
    )
    observaciones = models.TextField(blank=True)

    @property
    def total(self):
        """Total estimado: precio por persona de la opción elegida × cantidad de personas, + recargo celíaco."""
        if not self.opcion_elegida or not self.evento.cantidad_personas:
            return None
        personas_comunes = self.evento.cantidad_personas - self.cantidad_personas_celiaco
        base = self.opcion_elegida.precio_por_persona * personas_comunes
        recargo = (self.opcion_elegida.precio_por_persona + self.recargo_celiaco_por_persona) * self.cantidad_personas_celiaco
        return base + recargo

    def __str__(self):
        return f"Presupuesto - {self.evento.nombre}"


class OpcionMenu(models.Model):
    """Una opción de menú dentro de un presupuesto (Opción 1, 2, 3...), con su detalle y precio por persona."""
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='opciones')
    nombre = models.CharField(max_length=50, help_text="Ej: Opción 1")
    detalle_menu = models.TextField(help_text="Un plato por línea.")
    precio_por_persona = models.DecimalField(max_digits=10, decimal_places=2)
    orden = models.IntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"{self.nombre} - {self.presupuesto.evento.nombre}"

class InformeGestion(models.Model):
    """Datos manuales/narrativos del informe de gestión de un período. Los indicadores numéricos
    (cantidad de eventos, balance, etc.) se calculan en vivo desde Evento y no se guardan acá."""
    periodo = models.OneToOneField(Periodo, on_delete=models.CASCADE, related_name='informe_gestion')

    presupuesto_asignado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    servicios_adicionales_horas_extra = models.IntegerField(null=True, blank=True)
    raciones_comun = models.IntegerField(null=True, blank=True)
    raciones_vegetariano = models.IntegerField(null=True, blank=True)
    raciones_celiaco = models.IntegerField(null=True, blank=True)

    resumen_ejecutivo = models.TextField(blank=True)
    objetivos = models.TextField(blank=True)
    logros_destacados = models.TextField(blank=True)
    desafios_proximo_periodo = models.TextField(blank=True)

    actualizado = models.DateField(auto_now=True)

    def __str__(self):
        return f"Informe de gestión - {self.periodo}"