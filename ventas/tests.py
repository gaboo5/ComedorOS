"""Tests del punto de venta. Se corren con:  python manage.py test ventas"""
import datetime
import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from eventos.models import Evento

from .models import CategoriaVenta, ComponentePromo, ItemCarta, Jornada, ProductoVenta, Promo, VarianteVenta


class PuntoDeVentaTests(TestCase):
    def setUp(self):
        comidas = CategoriaVenta.objects.create(nombre='Comidas')
        bebidas = CategoriaVenta.objects.create(nombre='Bebidas')
        hamburguesa = ProductoVenta.objects.create(nombre='Hamburguesa', categoria=comidas)
        gaseosa = ProductoVenta.objects.create(nombre='Gaseosa', categoria=bebidas)
        self.hambur = VarianteVenta.objects.create(producto=hamburguesa, precio_referencia=5000)
        self.vaso = VarianteVenta.objects.create(producto=gaseosa, nombre='Vaso', precio_referencia=1500)
        self.botella = VarianteVenta.objects.create(producto=gaseosa, nombre='1,5 L', precio_referencia=4000)

        self.jornada = Jornada.objects.create(fecha=datetime.date(2026, 10, 20), nombre='Peña de prueba')
        ItemCarta.objects.create(jornada=self.jornada, variante=self.hambur, precio=5000, stock_inicial=50)
        ItemCarta.objects.create(jornada=self.jornada, variante=self.vaso, precio=1500)            # sin stock
        ItemCarta.objects.create(jornada=self.jornada, variante=self.botella, precio=4000, stock_inicial=10)
        self.promo = Promo.objects.create(jornada=self.jornada, nombre='Hambur + vaso', precio=6000)
        ComponentePromo.objects.create(promo=self.promo, variante=self.hambur, cantidad=1)
        ComponentePromo.objects.create(promo=self.promo, variante=self.vaso, cantidad=1)

    def cobrar(self, lineas, efectivo=None, qr=0, jornada=None):
        jornada = jornada or self.jornada
        total = sum(l['cantidad'] * l['precio'] for l in lineas)
        datos = {'caja': 'Caja 1', 'lineas': lineas, 'efectivo': total - qr if efectivo is None else efectivo, 'qr': qr}
        return self.client.post(reverse('pv_api_ticket', args=[jornada.pk]), json.dumps(datos),
                                content_type='application/json')

    def test_ticket_descuenta_stock_incluso_dentro_de_promos(self):
        r = self.cobrar([
            {'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 2, 'precio': 5000},
            {'tipo': 'promo', 'id': self.promo.pk, 'cantidad': 3, 'precio': 6000},
            {'tipo': 'variante', 'id': self.botella.pk, 'cantidad': 1, 'precio': 4000},
        ])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['numero'], 1)
        restante = self.jornada.stock_restante()
        self.assertEqual(restante[self.hambur.pk], 50 - 2 - 3)
        self.assertEqual(restante[self.botella.pk], 9)
        self.assertNotIn(self.vaso.pk, restante)                     # el vaso no controla stock
        vendidos = self.jornada.vendidos_por_variante()
        self.assertEqual(vendidos[self.vaso.pk], {'sueltos': 0, 'en_promos': 3})
        self.assertEqual(self.jornada.totales()['total'], Decimal('32000'))

    def test_pago_dividido_tiene_que_sumar_el_total(self):
        lineas = [{'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 1, 'precio': 5000}]
        self.assertEqual(self.cobrar(lineas, efectivo=2000, qr=3000).status_code, 200)
        self.assertEqual(self.cobrar(lineas, efectivo=2000, qr=1000).status_code, 400)
        t = self.jornada.totales()
        self.assertEqual((t['efectivo'], t['qr']), (Decimal('2000'), Decimal('3000')))

    def test_no_acepta_productos_fuera_de_la_carta_ni_jornada_cerrada(self):
        otro = VarianteVenta.objects.create(producto=self.hambur.producto, nombre='Doble', precio_referencia=7000)
        self.assertEqual(self.cobrar([{'tipo': 'variante', 'id': otro.pk, 'cantidad': 1, 'precio': 7000}]).status_code, 400)
        self.jornada.estado = 'cerrada'
        self.jornada.save()
        self.assertEqual(self.cobrar([{'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 1, 'precio': 5000}]).status_code, 400)

    def test_anular_saca_el_ticket_de_totales_y_stock(self):
        self.cobrar([{'tipo': 'variante', 'id': self.botella.pk, 'cantidad': 4, 'precio': 4000}])
        r = self.client.post(reverse('pv_ticket_anular', args=[self.jornada.pk, 1]), {'motivo': 'Cargado dos veces'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.jornada.totales()['total'], 0)
        self.assertEqual(self.jornada.stock_restante()[self.botella.pk], 10)

    def test_cambiar_precio_no_modifica_tickets_ya_cobrados(self):
        self.cobrar([{'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 1, 'precio': 5000}])
        r = self.client.post(reverse('pv_api_precio', args=[self.jornada.pk]),
                             json.dumps({'tipo': 'variante', 'id': self.hambur.pk, 'precio': '5500'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.jornada.tickets.get().lineas.get().precio_unitario, Decimal('5000'))
        self.hambur.refresh_from_db()
        self.assertEqual(self.hambur.precio_referencia, Decimal('5500'))   # queda como referencia

    def test_nueva_jornada_copia_carta_y_promos(self):
        r = self.client.post(reverse('pv_jornada_crear'), {
            'fecha': '2026-11-10', 'nombre': 'Peña 2', 'copiar_de': self.jornada.pk, 'evento': '', 'observaciones': '',
        })
        self.assertEqual(r.status_code, 302)
        nueva = Jornada.objects.get(nombre='Peña 2')
        self.assertEqual(nueva.carta.count(), 3)
        self.assertEqual(nueva.carta.get(variante=self.hambur).stock_inicial, None)   # el stock se carga de nuevo
        self.assertEqual(nueva.promos.get().componentes.count(), 2)

    def test_registrar_en_agenda(self):
        self.cobrar([{'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 2, 'precio': 5000}])
        self.client.post(reverse('pv_registrar_evento', args=[self.jornada.pk]))
        self.jornada.refresh_from_db()
        self.assertIsNotNone(self.jornada.evento)
        self.assertEqual(self.jornada.evento.precio_facturado, Decimal('10000'))
        self.assertEqual(self.jornada.evento.tipo_servicio.nombre, 'Punto de Venta')
        # Si se vuelve a registrar, actualiza el mismo evento
        self.cobrar([{'tipo': 'variante', 'id': self.hambur.pk, 'cantidad': 1, 'precio': 5000}])
        self.client.post(reverse('pv_registrar_evento', args=[self.jornada.pk]))
        self.assertEqual(Evento.objects.count(), 1)
        self.assertEqual(Evento.objects.get().precio_facturado, Decimal('15000'))

    def test_pantallas_cargan(self):
        pk = self.jornada.pk
        for nombre, args in [('pv_jornada_lista', []), ('pv_jornada_crear', []), ('pv_carta', [pk]),
                             ('pv_caja', [pk]), ('pv_tickets', [pk]), ('pv_cierre', [pk]),
                             ('pv_catalogo', []), ('pv_producto_crear', []), ('pv_promo_crear', []),
                             ('pv_producto_editar', [self.hambur.producto.pk]), ('pv_promo_editar', [self.promo.pk]),
                             ('inicio', [])]:
            r = self.client.get(reverse(nombre, args=args))
            self.assertEqual(r.status_code, 200, nombre)

    def test_precio_escrito_con_punto_de_miles(self):
        self.client.post(reverse('pv_api_precio', args=[self.jornada.pk]),
                         json.dumps({'tipo': 'variante', 'id': self.botella.pk, 'precio': '4.200'}),
                         content_type='application/json')
        self.assertEqual(self.jornada.carta.get(variante=self.botella).precio, Decimal('4200'))
