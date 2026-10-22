"""Punto de venta: ventas en gazebo, foodtruck, peñas, etc.

Cómo se relacionan los modelos:

    CategoriaVenta ─< ProductoVenta ─< VarianteVenta        (catálogo: lo que se puede vender)
                                            │
    Jornada ─< ItemCarta >──────────────────┘                (lo que se vende ESE día, con su precio y stock)
       │
       ├─< Promo ─< ComponentePromo >── VarianteVenta       (combos del día; con jornada vacía = promo de catálogo)
       │
       └─< Ticket ─< LineaTicket                            (cada venta, con el precio que se cobró en ese momento)
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum


# ----------------------------------------------------------------- Catálogo
class CategoriaVenta(models.Model):
    """Comidas, Bebidas, Peña, Postres... — se crean a medida que hacen falta."""
    nombre = models.CharField(max_length=60, unique=True)
    orden = models.PositiveIntegerField(default=0, help_text="Orden en que aparece en la caja (menor = primero).")

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría de venta'
        verbose_name_plural = 'categorías de venta'

    def __str__(self):
        return self.nombre


class ProductoVenta(models.Model):
    """Un producto que se vende, ej. 'Cono de papas'. Sus tamaños/opciones son las variantes."""
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaVenta, on_delete=models.PROTECT, related_name='productos')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['categoria__orden', 'categoria__nombre', 'nombre']
        verbose_name = 'producto de venta'
        verbose_name_plural = 'productos de venta'

    def __str__(self):
        return self.nombre


class VarianteVenta(models.Model):
    """Cada opción que se cobra por separado: 'Chico', 'Grande', 'Vaso', '1,5 L'...
    Si el producto tiene un solo precio, se deja el nombre vacío."""
    producto = models.ForeignKey(ProductoVenta, on_delete=models.CASCADE, related_name='variantes')
    nombre = models.CharField(max_length=60, blank=True, help_text="Ej: Chico, Grande, Vaso. Vacío si tiene un solo precio.")
    precio_referencia = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Último precio usado. Se actualiza solo cuando cambiás el precio en una jornada.",
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['producto__categoria__orden', 'producto__nombre', 'orden', 'id']
        verbose_name = 'variante'
        verbose_name_plural = 'variantes'

    @property
    def nombre_completo(self):
        return f"{self.producto.nombre} {self.nombre}".strip()

    def __str__(self):
        return self.nombre_completo


# ----------------------------------------------------------------- Jornadas
class Jornada(models.Model):
    """Una salida de venta: el equivalente a una hoja del cuaderno."""
    ESTADOS = [('abierta', 'Abierta'), ('cerrada', 'Cerrada')]

    fecha = models.DateField()
    nombre = models.CharField(max_length=150, help_text="Lugar o evento, ej. 'Peña Día del Estudiante'.")
    estado = models.CharField(max_length=10, choices=ESTADOS, default='abierta')
    evento = models.ForeignKey(
        'eventos.Evento', on_delete=models.SET_NULL, null=True, blank=True, related_name='jornadas_venta',
        help_text="Evento de la Agenda donde se registra el total vendido.",
    )
    observaciones = models.TextField(blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.nombre} ({self.fecha:%d/%m/%Y})"

    @property
    def abierta(self):
        return self.estado == 'abierta'

    def tickets_validos(self):
        return self.tickets.filter(anulado=False)

    def totales(self):
        t = self.tickets_validos().aggregate(efectivo=Sum('pago_efectivo'), qr=Sum('pago_qr'), total=Sum('total'))
        return {k: v or Decimal('0') for k, v in t.items()}

    def vendidos_por_variante(self):
        """{variante_id: {'sueltos': n, 'en_promos': n}} contando solo tickets no anulados."""
        resultado = {}
        lineas = LineaTicket.objects.filter(ticket__jornada=self, ticket__anulado=False)
        for fila in lineas.filter(variante__isnull=False).values('variante').annotate(c=Sum('cantidad')):
            resultado.setdefault(fila['variante'], {'sueltos': 0, 'en_promos': 0})['sueltos'] += fila['c']
        for linea in lineas.filter(promo__isnull=False).prefetch_related('promo__componentes'):
            for comp in linea.promo.componentes.all():
                d = resultado.setdefault(comp.variante_id, {'sueltos': 0, 'en_promos': 0})
                d['en_promos'] += comp.cantidad * linea.cantidad
        return resultado

    def stock_restante(self):
        """{variante_id: restante} solo para los ítems de la carta que tienen stock cargado."""
        vendidos = self.vendidos_por_variante()
        restante = {}
        for item in self.carta.exclude(stock_inicial__isnull=True):
            v = vendidos.get(item.variante_id, {'sueltos': 0, 'en_promos': 0})
            restante[item.variante_id] = item.stock_inicial - v['sueltos'] - v['en_promos']
        return restante


class ItemCarta(models.Model):
    """Una variante que se ofrece en una jornada, con el precio del día y (opcional) cuánto se llevó."""
    jornada = models.ForeignKey(Jornada, on_delete=models.CASCADE, related_name='carta')
    variante = models.ForeignKey(VarianteVenta, on_delete=models.PROTECT, related_name='en_cartas')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock_inicial = models.PositiveIntegerField(
        null=True, blank=True, help_text="Cuántos se llevaron. Vacío = no se controla stock de este ítem.",
    )

    class Meta:
        unique_together = ('jornada', 'variante')
        ordering = ['variante__producto__categoria__orden', 'variante__producto__nombre', 'variante__orden']

    def __str__(self):
        return f"{self.variante} - ${self.precio}"


class Promo(models.Model):
    """Combo o promo con precio propio. Con jornada = promo del día; sin jornada = guardada en el catálogo."""
    jornada = models.ForeignKey(Jornada, on_delete=models.CASCADE, null=True, blank=True, related_name='promos')
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def descripcion_componentes(self):
        return ' + '.join(
            f"{c.cantidad}× {c.variante.nombre_completo}" if c.cantidad > 1 else c.variante.nombre_completo
            for c in self.componentes.all()
        )

    def copiar_a(self, jornada):
        nueva = Promo.objects.create(jornada=jornada, nombre=self.nombre, precio=self.precio)
        for c in self.componentes.all():
            ComponentePromo.objects.create(promo=nueva, variante=c.variante, cantidad=c.cantidad)
        return nueva


class ComponentePromo(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE, related_name='componentes')
    variante = models.ForeignKey(VarianteVenta, on_delete=models.PROTECT, related_name='en_promos')
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.variante}"


# ----------------------------------------------------------------- Ventas
class Ticket(models.Model):
    jornada = models.ForeignKey(Jornada, on_delete=models.PROTECT, related_name='tickets')
    numero = models.PositiveIntegerField()
    caja = models.CharField(max_length=30, default='Caja 1')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pago_efectivo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_qr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('jornada', 'numero')
        ordering = ['-numero']

    def __str__(self):
        return f"Ticket #{self.numero} - {self.jornada}"

    @property
    def medio_pago(self):
        if self.pago_efectivo and self.pago_qr:
            return 'Dividido'
        return 'QR' if self.pago_qr else 'Efectivo'


class LineaTicket(models.Model):
    """Una línea del ticket. Guarda nombre y precio tal como se cobraron, aunque después cambien."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='lineas')
    variante = models.ForeignKey(VarianteVenta, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    promo = models.ForeignKey(Promo, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    descripcion = models.CharField(max_length=150)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion}"
