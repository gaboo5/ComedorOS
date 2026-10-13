from django.core.management.base import BaseCommand
from eventos.models import ConceptoCostoPersonal

CONCEPTOS = [
    'Mozos', 'Cocineros', 'Preelaboración',
    'Fajinado y traslado de mobiliario', 'Depósito', 'Mantenimiento / Limpieza',
]


class Command(BaseCommand):
    help = 'Carga los conceptos iniciales de costo de personal.'

    def handle(self, *args, **options):
        creados = 0
        for nombre in CONCEPTOS:
            _, fue_creado = ConceptoCostoPersonal.objects.get_or_create(nombre=nombre)
            if fue_creado:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'{creados} conceptos nuevos cargados (de {len(CONCEPTOS)} totales).'))