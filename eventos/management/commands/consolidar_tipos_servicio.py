from django.core.management.base import BaseCommand
from django.db import transaction

from eventos.models import TipoServicio, Evento

# Todas las categorías que deben existir al final, aunque hoy no tengan eventos
# (por ejemplo "Peña", para que esté disponible al cargar presupuestos nuevos).
CATEGORIAS_FINALES = [
    'Actividad', 'Ágape', 'Almuerzo', 'Armado de Salón', 'Bebidas', 'Bingo',
    'Cafetería', 'Capacitación', 'Cena', 'Charla', 'Chocolate', 'Clases de Tango',
    'Desayuno', 'Entrega Mercadería', 'Insumos', 'Peña', 'Punto de venta',
    'Reunión', 'Salón Azul', 'Salón Blanco', 'Salón Grande', 'Salón Verde',
    'Solo Salón', 'Sunset', 'Torneo', 'Varios', 'Viandas',
]

# Mapeo: nombre actual (tal cual está cargado) -> categoría final
MAPEO = {
    'Cafeteria': 'Cafetería',
    'Cafetería/ sin tacc': 'Cafetería',
    'Solo Salón': 'Solo Salón',
    'Agape': 'Ágape',
    'Reunion': 'Reunión',
    'varios': 'Varios',
    'Almuerzos': 'Almuerzo',
    'Almuerzo': 'Almuerzo',
    'Almuerzo Vegetariano': 'Almuerzo',
    'Almuerzos Común': 'Almuerzo',
    'Almuerzos Sin Tacc': 'Almuerzo',
    'Punto de Venta': 'Punto de venta',
    'Venta': 'Punto de venta',
    'Peña / Punto de Venta': 'Punto de venta',
    'Salon Grande': 'Salón Grande',
    '1 doc. media/1 doc. torta': 'Varios',
    'Celiacos': 'Varios',
    'Curso': 'Varios',
    'Capacitación': 'Capacitación',
    'Desayunos / Merienda Común': 'Desayuno',
    'Desayunos / Merienda Sin TACC': 'Desayuno',
    'Desayunos': 'Desayuno',
    'Desayuno': 'Desayuno',
    'Viandas Almuerzos': 'Viandas',
    'Vianda': 'Viandas',
    'Salon': 'Armado de Salón',
    'Armado salón': 'Armado de Salón',
    'Actividad / salón': 'Armado de Salón',
    'Salon Azul': 'Salón Azul',
    'Entrega Mercadería': 'Entrega Mercadería',
    'Charla': 'Charla',
    'Agape Celíaco': 'Ágape',
    'Sunset - Entradas': 'Sunset',
    'Sunset Varios': 'Sunset',
    'Clases de Tango': 'Clases de Tango',
    'Bingo / Varios': 'Bingo',
    'Bingo': 'Bingo',
    'Varios Bebidas': 'Bebidas',
    'Torneo': 'Torneo',
    'Chocolate': 'Chocolate',
    'Insumos': 'Insumos',
    'Cumpleaños Comedor': 'Actividad',
    # Casos combinados: se dejan en una categoría provisoria y se avisa para dividir a mano
    'Cafetería/Agape': 'Cafetería',
    'Cafeteria/ Agape': 'Cafetería',
    'Desayuno - Almuerzo - Cena': 'Desayuno',
}

CASOS_A_DIVIDIR_MANUALMENTE = ['Cafetería/Agape', 'Cafeteria/ Agape', 'Desayuno - Almuerzo - Cena']


class Command(BaseCommand):
    help = 'Consolida los TipoServicio actuales en la lista final definida junto con el usuario.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if not dry_run:
            for nombre in CATEGORIAS_FINALES:
                TipoServicio.objects.get_or_create(nombre=nombre)

        eventos_a_revisar = []

        for nombre_actual, nombre_final in MAPEO.items():
            try:
                tipo_actual = TipoServicio.objects.get(nombre=nombre_actual)
            except TipoServicio.DoesNotExist:
                continue

            eventos = Evento.objects.filter(tipo_servicio=tipo_actual)
            cantidad = eventos.count()

            if nombre_actual in CASOS_A_DIVIDIR_MANUALMENTE:
                for e in eventos:
                    eventos_a_revisar.append(e)

            self.stdout.write(f'"{nombre_actual}" ({cantidad} eventos) -> "{nombre_final}"')

            if not dry_run and cantidad:
                tipo_final = TipoServicio.objects.get(nombre=nombre_final)
                eventos.update(tipo_servicio=tipo_final)

        if not dry_run:
            # Borra los TipoServicio viejos que ya quedaron sin eventos y no son parte de la lista final
            for tipo in TipoServicio.objects.exclude(nombre__in=CATEGORIAS_FINALES):
                if not Evento.objects.filter(tipo_servicio=tipo).exists():
                    tipo.delete()

        if eventos_a_revisar:
            self.stdout.write(self.style.WARNING(
                '\nEstos eventos combinan varios servicios y necesitan que los dividas manualmente:'
            ))
            for e in eventos_a_revisar:
                self.stdout.write(self.style.WARNING(f'  - {e.fecha} | {e.nombre} | ${e.precio_facturado}'))

        self.stdout.write(self.style.SUCCESS(f'\n{"[DRY RUN] " if dry_run else ""}Listo.'))