import re
import unicodedata
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from eventos.models import Periodo, TipoServicio, Evento, DetalleCosto


# Palabras clave para detectar clientes "internos" (dependencias de la propia UNCuyo).
# Es una aproximación: después de importar, revisá y corregí a mano los casos dudosos.
PALABRAS_INTERNO = [
    'facultad', 'secretaria', 'secretaría', 'direccion', 'dirección',
    'rectorado', 'deportes', 'bienestar', 'comedor', 'das', 'extension',
    'extensión', 'genero', 'género', 'salud estudiantil', 'relaciones estudiantiles',
    'educacion a distancia', 'educación a distancia', 'uncuyo', 'dge', 'ffyl',
    'derecho', 'odontologia', 'odontología', 'coordinacion', 'coordinación',
    'irrigacion', 'irrigación', 'obras',
]


def normalizar(texto):
    """Quita tildes y pasa a mayúsculas, para comparar encabezados de columnas sin líos de acentos."""
    if not isinstance(texto, str):
        return ''
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return texto.strip().upper()


def buscar_columna(columnas_normalizadas, *posibles_nombres):
    """Devuelve el nombre real de columna que matchea alguno de los posibles nombres normalizados."""
    for nombre in posibles_nombres:
        if nombre in columnas_normalizadas:
            return columnas_normalizadas[nombre]
    return None


def a_decimal(valor):
    """Convierte valores sucios del Excel (NaN, '*', texto) a Decimal, con 0 como default seguro."""
    if valor is None:
        return Decimal('0')
    if isinstance(valor, str) and valor.strip() in ('', '*'):
        return Decimal('0')
    try:
        if pd.isna(valor):
            return Decimal('0')
    except (TypeError, ValueError):
        pass
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def a_texto(valor):
    if valor is None:
        return ''
    try:
        if pd.isna(valor):
            return ''
    except (TypeError, ValueError):
        pass
    return str(valor).strip()


def inferir_origen(cliente):
    cliente_normalizado = normalizar(cliente)
    for palabra in PALABRAS_INTERNO:
        if normalizar(palabra) in cliente_normalizado:
            return 'interno'
    return 'externo'


class Command(BaseCommand):
    help = 'Importa eventos históricos desde el Excel de informes mensuales (una hoja por mes).'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta al archivo .xlsx')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra qué se importaría, sin guardar nada en la base de datos.'
        )

    def handle(self, *args, **options):
        ruta = options['archivo']
        dry_run = options['dry_run']

        hojas = pd.read_excel(ruta, sheet_name=None)  # dict: nombre_hoja -> DataFrame

        total_creados = 0
        total_saltados = 0
        conteo_interno = 0
        conteo_externo = 0

        for nombre_hoja, df in hojas.items():
            self.stdout.write(f'\n--- Hoja: {nombre_hoja} ---')

            columnas_normalizadas = {normalizar(c): c for c in df.columns}

            col_fecha = buscar_columna(columnas_normalizadas, 'FECHA')
            col_solicitante = buscar_columna(columnas_normalizadas, 'SOLICITANTE')
            col_cliente = buscar_columna(columnas_normalizadas, 'CLIENTE')
            col_tipo_serv = buscar_columna(columnas_normalizadas, 'TIPO DE EVENTO')
            col_personas = buscar_columna(columnas_normalizadas, 'CANT DE PERSONAS')
            col_total = buscar_columna(columnas_normalizadas, 'TOTAL')
            col_costo_total = buscar_columna(columnas_normalizadas, 'COSTO TOTAL')
            col_nro_fac = buscar_columna(columnas_normalizadas, 'N DE FAC', 'NRO DE FAC', 'N° DE FAC')
            col_nro_rec = buscar_columna(columnas_normalizadas, 'N DE REC', 'NRO DE REC', 'N° DE REC')
            col_expediente = buscar_columna(columnas_normalizadas, 'EXPEDIENTE')
            col_comprobante = buscar_columna(columnas_normalizadas, 'N DE COMP.', 'NRO DE COMP.', 'N° DE COMP.')
            col_manteleria = buscar_columna(columnas_normalizadas, 'MANTELERIA', 'MANTELERÍA')
            col_cmp = buscar_columna(columnas_normalizadas, 'C.M.P', 'C.M.P.')
            col_personal = buscar_columna(columnas_normalizadas, 'PERSONAL')
            col_planilla_gral = buscar_columna(
                columnas_normalizadas, 'PLANILLA GENERAL', 'PLANILLA GRAL'
            )
            col_planilla_tes = buscar_columna(columnas_normalizadas, 'PLANILLA TESORERIA', 'PLANILLA TESORERÍA')
            col_varios = buscar_columna(columnas_normalizadas, 'VARIOS')

            if not col_fecha:
                self.stdout.write(self.style.WARNING(f'  Sin columna FECHA, salteo la hoja.'))
                continue

            for _, fila in df.iterrows():
                fecha = fila.get(col_fecha)
                if pd.isna(fecha):
                    total_saltados += 1
                    continue

                fecha = pd.to_datetime(fecha).date()
                cliente = a_texto(fila.get(col_cliente))
                solicitante = a_texto(fila.get(col_solicitante))
                tipo_servicio_nombre = a_texto(fila.get(col_tipo_serv)) or 'Sin especificar'
                personas = fila.get(col_personas)
                personas = int(personas) if pd.notna(personas) else None

                total_facturado = a_decimal(fila.get(col_total))
                costo_total = a_decimal(fila.get(col_costo_total))

                origen = inferir_origen(cliente)
                if origen == 'interno':
                    conteo_interno += 1
                else:
                    conteo_externo += 1

                nombre_evento = f"{tipo_servicio_nombre} - {cliente}" if cliente else tipo_servicio_nombre
                nombre_evento = nombre_evento[:200]

                semestre = 1 if fecha.month <= 6 else 2

                self.stdout.write(
                    f'  {fecha} | {nombre_evento[:50]:50s} | {origen:8s} | '
                    f'facturado ${total_facturado} | costo ${costo_total}'
                )

                if dry_run:
                    total_creados += 1
                    continue

                with transaction.atomic():
                    periodo, _ = Periodo.objects.get_or_create(anio=fecha.year, semestre=semestre)
                    tipo_servicio, _ = TipoServicio.objects.get_or_create(nombre=tipo_servicio_nombre)

                    evento = Evento.objects.create(
                        nombre=nombre_evento,
                        tipo_servicio=tipo_servicio,
                        periodo=periodo,
                        origen=origen,
                        fecha=fecha,
                        cliente=cliente,
                        solicitante=solicitante,
                        cantidad_personas=personas,
                        costo=costo_total,
                        precio_facturado=total_facturado,
                        estado_facturacion='cobrado' if a_texto(fila.get(col_nro_fac)) else 'pendiente',
                        estado_evento='realizado',
                        nro_factura=a_texto(fila.get(col_nro_fac)),
                        nro_recibo=a_texto(fila.get(col_nro_rec)),
                        expediente=a_texto(fila.get(col_expediente)),
                        nro_comprobante=a_texto(fila.get(col_comprobante)),
                    )

                    DetalleCosto.objects.create(
                        evento=evento,
                        manteleria=a_decimal(fila.get(col_manteleria)),
                        materia_prima=a_decimal(fila.get(col_cmp)),
                        personal=a_decimal(fila.get(col_personal)),
                        planilla=a_decimal(fila.get(col_planilla_gral)) + a_decimal(fila.get(col_planilla_tes)),
                        varios=a_decimal(fila.get(col_varios)),
                    )

                total_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n{"[DRY RUN] " if dry_run else ""}Filas procesadas: {total_creados} '
            f'(interno: {conteo_interno}, externo: {conteo_externo}) — saltadas (sin fecha): {total_saltados}'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('No se guardó nada. Corré sin --dry-run para importar de verdad.'))