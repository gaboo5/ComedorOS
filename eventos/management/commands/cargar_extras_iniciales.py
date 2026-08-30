from django.core.management.base import BaseCommand
from eventos.models import Extra

EXTRAS_INICIALES = [
    'Agua con gas',
    'Agua sin gas',
    'Agua saborizada',
    'Gaseosa',
    'Jugo',
    'Vino tinto',
    'Vino blanco',
    'Vajilla y mantelería de primera calidad',
    'Servicio de mozos',
    'Servicio de cocina',
    'Mobiliario necesario',
]


class Command(BaseCommand):
    help = 'Carga el catálogo inicial de extras para presupuestos.'

    def handle(self, *args, **options):
        creados = 0
        for nombre in EXTRAS_INICIALES:
            _, fue_creado = Extra.objects.get_or_create(nombre=nombre)
            if fue_creado:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'Listo. {creados} extras nuevos creados (de {len(EXTRAS_INICIALES)} totales).'))