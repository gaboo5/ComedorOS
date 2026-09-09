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
    permite_vegetariano = models.BooleanField(
        default=False,
        help_text="Tildá esto para Almuerzos, Ágapes, Cenas, etc. — habilita el menú vegetariano en presupuestos de este tipo."
    )

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Evento(models.Model):
    ESTADO_FACTURACION = [
        ('pendiente', 'Pendiente'),
        ('facturado', 'Facturado'),
        ('cobrado', 'Cobrado'),
    ]
    
    ORIGEN = [
        ('interno', 'Interno'),
        ('externo', 'Externo'),
    ]
    ESTADO_EVENTO = [
        ('solicitud', 'Solicitud'),
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
    cantidad_personas_celiaco = models.IntegerField(null=True, blank=True)

    costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_facturado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_facturacion = models.CharField(max_length=10, choices=ESTADO_FACTURACION, default='pendiente')
    estado_evento = models.CharField(max_length=15, choices=ESTADO_EVENTO, default='presupuestado')

    nro_factura = models.CharField(max_length=50, blank=True)
    nro_recibo = models.CharField(max_length=50, blank=True)
    expediente = models.CharField(max_length=50, blank=True)
    nro_comprobante = models.CharField(max_length=50, blank=True)
    observaciones = models.TextField(blank=True)
    excluir_de_informe = models.BooleanField(
        default=False,
        help_text="Tildá esto si el costo/facturado de este evento tiene un error de carga conocido. "
                   "Se excluye de los totales normales y aparece en un apartado aparte del informe."
    )
    costo_ajustado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    facturado_ajustado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    nota_ajuste = models.TextField(blank=True, help_text="Explicación breve del error y la corrección.")
    importado_automaticamente = models.BooleanField(
        default=False,
        help_text="Si está tildado, este evento se reemplaza automáticamente la próxima vez que sincronices el Excel."
    )

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

    @property
    def color_estado_evento(self):
        mapa = {
            'solicitud': 'secondary',
            'presupuestado': 'info',
            'confirmado': 'primary',
            'realizado': 'success',
            'cancelado': 'danger',
        }
        return mapa.get(self.estado_evento, 'secondary')

    @property
    def color_estado_facturacion(self):
        mapa = {
            'pendiente': 'warning',
            'facturado': 'info',
            'cobrado': 'success',
        }
        return mapa.get(self.estado_facturacion, 'secondary')


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
    """Presupuesto de un evento: lugar, extras incluidos y 2-3 opciones de menú, con cantidades
    de personas divididas en Regular/Vegetariano/Celíaco."""
    evento = models.OneToOneField(Evento, on_delete=models.CASCADE, related_name='presupuesto')
    fecha_creacion = models.DateField(auto_now_add=True)
    lugar = models.CharField(max_length=200, blank=True)
    extras_incluidos = models.ManyToManyField(Extra, blank=True, related_name='presupuestos')
    otros_extras = models.TextField(blank=True, help_text="Cualquier extra que no esté en la lista de arriba.")

    cantidad_regular = models.IntegerField(default=0, verbose_name="Cantidad — Menú Regular")
    cantidad_vegetariano = models.IntegerField(default=0, verbose_name="Cantidad — Menú Vegetariano")
    cantidad_celiaco = models.IntegerField(default=0, verbose_name="Cantidad — Menú Celíaco")

    opcion_elegida = models.ForeignKey(
        'OpcionMenu', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', help_text="Se completa cuando el cliente confirma cuál opción eligió."
    )
    observaciones = models.TextField(blank=True)

    @property
    def total_personas(self):
        return self.cantidad_regular + self.cantidad_vegetariano + self.cantidad_celiaco

    @property
    def subtotal_regular(self):
        if not self.opcion_elegida:
            return None
        return self.cantidad_regular * self.opcion_elegida.precio_regular

    @property
    def subtotal_vegetariano(self):
        if not self.opcion_elegida or not self.cantidad_vegetariano:
            return None
        precio = self.opcion_elegida.precio_vegetariano or self.opcion_elegida.precio_regular
        return self.cantidad_vegetariano * precio

    @property
    def subtotal_celiaco(self):
        if not self.opcion_elegida or not self.cantidad_celiaco:
            return None
        precio = self.opcion_elegida.precio_celiaco or self.opcion_elegida.precio_regular
        return self.cantidad_celiaco * precio

    @property
    def total(self):
        if not self.opcion_elegida:
            return None
        return (self.subtotal_regular or 0) + (self.subtotal_vegetariano or 0) + (self.subtotal_celiaco or 0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mantiene sincronizados los totales del Evento con el desglose del presupuesto,
        # para que el dashboard y los reportes sigan funcionando sin cargar el dato dos veces.
        cambios = False
        if self.evento.cantidad_personas != self.total_personas:
            self.evento.cantidad_personas = self.total_personas
            cambios = True
        if self.evento.cantidad_personas_celiaco != self.cantidad_celiaco:
            self.evento.cantidad_personas_celiaco = self.cantidad_celiaco
            cambios = True
        if cambios:
            self.evento.save(update_fields=['cantidad_personas', 'cantidad_personas_celiaco'])

    def __str__(self):
        return f"Presupuesto - {self.evento.nombre}"
    
    observaciones = models.TextField(blank=True)

    @property
    def total(self):
        """Total estimado: precio por persona de la opción elegida × cantidad de personas, + recargo celíaco."""
        if not self.opcion_elegida or not self.evento.cantidad_personas:
            return None
        personas_comunes = self.evento.cantidad_personas - self.cantidad_personas_celiaco
        base = self.opcion_elegida.precio_regular * personas_comunes
        recargo = (self.opcion_elegida.precio_celiaco or self.opcion_elegida.precio_regular) * self.cantidad_personas_celiaco
        return base + recargo

    def __str__(self):
        return f"Presupuesto - {self.evento.nombre}"


class OpcionMenu(models.Model):
    """Una opción de menú dentro de un presupuesto (Opción 1, 2, 3...), con su detalle y
    precios por persona diferenciados: Regular, Vegetariano y Celíaco."""
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='opciones')
    nombre = models.CharField(max_length=50, help_text="Ej: Opción 1")
    detalle_menu = models.TextField(help_text="Un plato por línea.")
    precio_regular = models.DecimalField(max_digits=10, decimal_places=2)
    precio_vegetariano = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_celiaco = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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


class ResumenFacturacionMensual(models.Model):
    """Resumen mensual de facturación/cobros, cargado desde la planilla compartida con contaduría.
    No está atado a eventos puntuales — es un dato agregado por mes."""
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='resumenes_facturacion')
    mes = models.IntegerField()  # 1 a 12
    facturado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cobrado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pendiente = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ('periodo', 'mes')
        ordering = ['periodo', 'mes']

    def __str__(self):
        return f"Facturación mes {self.mes} - {self.periodo}"

class Integrante(models.Model):
    """Personas que forman parte del equipo del área de eventos."""
    nombre = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100, blank=True, help_text="Ej: Jefe de mozos")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class FuncionActividad(models.Model):
    """Una actividad/función del área, con quién es responsable de llevarla a cabo."""
    numero = models.IntegerField(help_text="Orden dentro de la lista de funciones")
    descripcion = models.TextField()
    responsables = models.ManyToManyField(Integrante, related_name='funciones', blank=True)

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f"{self.numero}. {self.descripcion[:50]}"

class Producto(models.Model):
    """Catálogo de productos comprados (materia prima, insumos, etc.)."""
    UNIDAD_MEDIDA = [
        ('kg', 'Kilogramo'), ('g', 'Gramo'), ('l', 'Litro'), ('ml', 'Mililitro'),
        ('unidad', 'Unidad'), ('paquete', 'Paquete'), ('docena', 'Docena'), ('caja', 'Caja'),
    ]
    nombre = models.CharField(max_length=150, unique=True)
    unidad_medida = models.CharField(max_length=10, choices=UNIDAD_MEDIDA)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_unidad_medida_display()})"

    @property
    def ultimo_precio_unitario(self):
        ultimo_item = self.compras.order_by('-compra__fecha').first()
        return ultimo_item.precio_unitario if ultimo_item else None


class Compra(models.Model):
    """Una compra puede tener varios productos (ítems) y opcionalmente asociarse a un evento."""
    fecha = models.DateField()
    proveedor = models.CharField(max_length=200, blank=True)
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='compras')
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']

    @property
    def total(self):
        return sum((item.total_pagado for item in self.items.all()), 0)

    def __str__(self):
        return f"Compra {self.fecha} - {self.proveedor or 'sin proveedor'}"


class ItemCompra(models.Model):
    """Un producto dentro de una compra. El precio unitario se calcula, nunca se carga a mano."""
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='compras')
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    total_pagado = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def precio_unitario(self):
        if self.cantidad:
            return round(self.total_pagado / self.cantidad, 2)
        return None

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"