"""Tests de eventos. Se corren con:  python manage.py test eventos"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import (
    CategoriaInventario, ConceptoCostoPersonal, ElementoInventario, EnvioLavanderia, Evento, ItemCostoPersonal,
    ItemEnvioLavanderia, ItemPrestamo, OpcionMenu, Pago, Periodo, PersonaEventual, Prestamo, Presupuesto,
    TipoServicio,
)


class EliminarRegistrosTests(TestCase):
    def setUp(self):
        cat = CategoriaInventario.objects.create(nombre='Vajilla')
        self.plato = ElementoInventario.objects.create(nombre='Plato', categoria=cat, cantidad_total=100)

    def test_persona_sin_pagos_se_elimina(self):
        p = PersonaEventual.objects.create(apellido='Pérez', nombre='Ana', dni='1')
        self.assertEqual(self.client.get(reverse('persona_eventual_eliminar', args=[p.pk])).status_code, 200)
        self.client.post(reverse('persona_eventual_eliminar', args=[p.pk]))
        self.assertFalse(PersonaEventual.objects.exists())

    def test_persona_con_pagos_no_se_elimina(self):
        p = PersonaEventual.objects.create(apellido='Gómez', nombre='Luis', dni='2')
        Pago.objects.create(tipo_pago='mozos', fecha=datetime.date(2026, 9, 1), persona=p, importe=30000)
        r = self.client.post(reverse('persona_eventual_eliminar', args=[p.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no se puede eliminar')
        self.assertTrue(PersonaEventual.objects.filter(pk=p.pk).exists())

    def test_eliminar_envio_lavanderia_libera_el_inventario(self):
        envio = EnvioLavanderia.objects.create(fecha_envio=datetime.date(2026, 10, 1), proveedor='Lavadero')
        ItemEnvioLavanderia.objects.create(envio=envio, elemento=self.plato, cantidad=30)
        self.assertEqual(self.plato.cantidad_disponible, 70)
        self.assertContains(self.client.get(reverse('lavanderia_lista')), '30 × Plato')
        self.client.post(reverse('lavanderia_eliminar', args=[envio.pk]))
        self.assertFalse(EnvioLavanderia.objects.exists())
        self.assertEqual(self.plato.cantidad_disponible, 100)

    def test_eliminar_prestamo(self):
        prestamo = Prestamo.objects.create(prestado_a='Facultad de Artes', fecha_prestamo=datetime.date(2026, 10, 5))
        ItemPrestamo.objects.create(prestamo=prestamo, elemento=self.plato, cantidad=10)
        self.assertContains(self.client.get(reverse('prestamo_lista')), '10 × Plato')
        self.client.post(reverse('prestamo_eliminar', args=[prestamo.pk]))
        self.assertFalse(Prestamo.objects.exists())


class PresupuestoEdicionTests(TestCase):
    """Antes, editar un presupuesto ya guardado fallaba en silencio porque faltaban los 'id' de las filas."""

    def setUp(self):
        periodo = Periodo.objects.create(anio=2026, semestre=2)
        tipo = TipoServicio.objects.create(nombre='Ágape')
        self.evento = Evento.objects.create(nombre='Ágape - Rectorado', tipo_servicio=tipo, periodo=periodo,
                                            fecha=datetime.date(2026, 11, 5), cliente='Rectorado')
        self.pres = Presupuesto.objects.create(evento=self.evento, lugar='Salón', cantidad_regular=50)
        self.opcion = OpcionMenu.objects.create(presupuesto=self.pres, nombre='Opción 1', detalle_menu='Empanadas',
                                                precio_regular=10000, orden=1)
        self.mozos = ConceptoCostoPersonal.objects.create(nombre='Mozos')
        self.cocina = ConceptoCostoPersonal.objects.create(nombre='Cocineros')
        self.item = ItemCostoPersonal.objects.create(presupuesto=self.pres, concepto=self.mozos,
                                                     cantidad_personas=4, precio_por_persona=30000)

    def datos(self, costos):
        d = {
            'tipo_servicio': self.evento.tipo_servicio_id, 'solicitante': '', 'cliente': 'Rectorado',
            'origen': 'interno', 'fecha': '2026-11-05', 'cantidad_personas': '50', 'observaciones': '',
            'lugar': 'Salón', 'otros_extras': '', 'cantidad_regular': '50', 'cantidad_vegetariano': '0',
            'cantidad_celiaco': '0',
            'opciones-TOTAL_FORMS': '1', 'opciones-INITIAL_FORMS': '1', 'opciones-MIN_NUM_FORMS': '0',
            'opciones-MAX_NUM_FORMS': '1000',
            'opciones-0-id': self.opcion.pk, 'opciones-0-nombre': 'Opción 1', 'opciones-0-detalle_menu': 'Empanadas',
            'opciones-0-precio_regular': '12000', 'opciones-0-orden': '1',
            'costopersonal-TOTAL_FORMS': str(len(costos)), 'costopersonal-INITIAL_FORMS': '1',
            'costopersonal-MIN_NUM_FORMS': '0', 'costopersonal-MAX_NUM_FORMS': '1000',
        }
        for i, c in enumerate(costos):
            for k, v in c.items():
                d[f'costopersonal-{i}-{k}'] = v
        return d

    def test_editar_presupuesto_agregando_y_quitando_costos(self):
        r = self.client.get(reverse('presupuesto_editar', args=[self.pres.pk]))
        self.assertContains(r, 'name="costopersonal-0-id"')
        self.assertContains(r, '+ Agregar costo de personal')
        costos = [
            {'id': self.item.pk, 'concepto': self.mozos.pk, 'cantidad_personas': '4', 'precio_por_persona': '30000',
             'DELETE': 'on'},                                                     # se quita
            {'concepto': self.cocina.pk, 'cantidad_personas': '2', 'precio_por_persona': '40000'},
            {'concepto': self.mozos.pk, 'cantidad_personas': '6', 'precio_por_persona': '30000'},
            {'concepto': self.mozos.pk, 'cantidad_personas': '1', 'precio_por_persona': '25000'},
        ]
        r = self.client.post(reverse('presupuesto_editar', args=[self.pres.pk]), self.datos(costos))
        self.assertEqual(r.status_code, 302)
        self.pres.refresh_from_db()
        self.assertEqual(self.pres.items_costo_personal.count(), 3)
        self.assertEqual(self.pres.total_costo_personal, Decimal('285000'))
        self.assertEqual(self.pres.opciones.get().precio_regular, Decimal('12000'))

    def test_fecha_se_muestra_al_editar(self):
        # Con el idioma en es-ar, los campos de fecha quedaban vacíos al editar (el navegador necesita AAAA-MM-DD).
        self.assertContains(self.client.get(reverse('presupuesto_editar', args=[self.pres.pk])), 'value="2026-11-05"')
        self.assertContains(self.client.get(reverse('evento_editar', args=[self.evento.pk])), 'value="2026-11-05"')
