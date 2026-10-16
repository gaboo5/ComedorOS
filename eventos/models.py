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

    @property
    def costo_real_calculado(self):
        """Suma compras + pagos vinculados a este evento — para comparar contra el campo 'costo' manual."""
        total_compras = sum((c.total for c in self.compras.all()), 0)
        total_pagos = sum((p.importe for p in self.pagos.all()), 0)
        return total_compras + total_pagos

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

    @property
    def total_costo_personal(self):
        return sum((item.subtotal for item in self.items_costo_personal.all()), 0)

    @property
    def margen_estimado(self):
        """Venta estimada menos costo de personal (solo si ya hay opción elegida)."""
        if self.total is None:
            return None
        return self.total - self.total_costo_personal

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


class PersonaEventual(models.Model):
    """Personal eventual (mozos, cocineros, etc.) que cobra por evento — distinto de Integrante,
    que es el equipo fijo del área."""
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    dni = models.CharField(max_length=15, unique=True)

    class Meta:
        ordering = ['apellido', 'nombre']
        verbose_name_plural = 'Personas eventuales'

    def __str__(self):
        return f"{self.apellido}, {self.nombre} (DNI {self.dni})"


class Pago(models.Model):
    """Un pago individual: a una persona eventual (mozos, cocina, horas extra) o un gasto
    operativo (combustible, general) sin persona asociada."""
    TIPO_PAGO = [
        ('mozos', 'Mozos'),
        ('cocina_bacha_buffet', 'Cocina / Bacha / Buffet'),
        ('horas_extra', 'Horas Extra'),
        ('combustible', 'Combustible'),
        ('general', 'General'),
    ]

    tipo_pago = models.CharField(max_length=25, choices=TIPO_PAGO)
    numero_planilla = models.CharField(max_length=20, blank=True)
    fecha = models.DateField()
    persona = models.ForeignKey(
        PersonaEventual, on_delete=models.PROTECT, null=True, blank=True, related_name='pagos'
    )
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos')
    descripcion_evento = models.CharField(
        max_length=200, blank=True,
        help_text="Texto libre si el evento no está cargado como tal en el sistema (ej. 'BUFFET 01/09/2026')."
    )
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        quien = str(self.persona) if self.persona else self.get_tipo_pago_display()
        return f"{quien} - ${self.importe} ({self.fecha})"


class ConceptoCostoPersonal(models.Model):
    """Catálogo de conceptos de mano de obra: Mozos, Cocineros, Preelaboración, etc.
    Es una lista abierta — se pueden agregar nuevos conceptos sin tocar código."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ItemCostoPersonal(models.Model):
    """Un ítem de costo de personal dentro de un presupuesto: concepto + cantidad de personas
    + precio por persona. El subtotal se calcula solo."""
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='items_costo_personal')
    concepto = models.ForeignKey(ConceptoCostoPersonal, on_delete=models.PROTECT)
    cantidad_personas = models.IntegerField(default=1)
    precio_por_persona = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad_personas * self.precio_por_persona

    def __str__(self):
        return f"{self.concepto} x {self.cantidad_personas}"


class CategoriaInventario(models.Model):
    """Vajilla, Mantelería, Mobiliario, etc. — catálogo abierto."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Categorías de inventario'

    def __str__(self):
        return self.nombre


class ElementoInventario(models.Model):
    """Un elemento del inventario (ej: 'Plato playo', 'Mantel blanco 2x2')."""
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(CategoriaInventario, on_delete=models.PROTECT, related_name='elementos')
    cantidad_total = models.IntegerField(default=0, help_text="Cantidad total que posee el comedor.")

    class Meta:
        ordering = ['categoria__nombre', 'nombre']

    @property
    def cantidad_en_lavanderia(self):
        return ItemEnvioLavanderia.objects.filter(
            elemento=self, envio__fecha_retorno__isnull=True
        ).aggregate(t=models.Sum('cantidad'))['t'] or 0

    @property
    def cantidad_prestada(self):
        return ItemPrestamo.objects.filter(
            elemento=self, prestamo__fecha_devolucion__isnull=True
        ).aggregate(t=models.Sum('cantidad'))['t'] or 0

    @property
    def cantidad_disponible(self):
        return self.cantidad_total - self.cantidad_en_lavanderia - self.cantidad_prestada

    def __str__(self):
        return f"{self.nombre} ({self.categoria})"


class EnvioLavanderia(models.Model):
    """Un envío a lavandería (puede incluir varios elementos). Mientras fecha_retorno esté vacía,
    se considera 'afuera'."""
    fecha_envio = models.DateField()
    fecha_retorno = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=200, blank=True)
    factura = models.FileField(
        upload_to='facturas_lavanderia/%Y/%m/', null=True, blank=True,
        help_text="Se carga generalmente al momento de la devolución, cuando la lavandería la entrega."
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_envio']

    @property
    def esta_pendiente(self):
        return self.fecha_retorno is None

    def __str__(self):
        return f"Envío lavandería {self.fecha_envio}"


class ItemEnvioLavanderia(models.Model):
    envio = models.ForeignKey(EnvioLavanderia, on_delete=models.CASCADE, related_name='items')
    elemento = models.ForeignKey(ElementoInventario, on_delete=models.PROTECT, related_name='items_lavanderia')
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.elemento} x{self.cantidad}"


class Prestamo(models.Model):
    """Un préstamo (puede incluir varios elementos) a una persona u organismo."""
    prestado_a = models.CharField(max_length=200)
    fecha_prestamo = models.DateField()
    fecha_devolucion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_prestamo']

    @property
    def esta_pendiente(self):
        return self.fecha_devolucion is None

    def __str__(self):
        return f"Préstamo a {self.prestado_a} ({self.fecha_prestamo})"


class ItemPrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='items')
    elemento = models.ForeignKey(ElementoInventario, on_delete=models.PROTECT, related_name='items_prestamo')
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.elemento} x{self.cantidad}"
