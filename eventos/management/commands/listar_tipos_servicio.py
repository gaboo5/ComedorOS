from django.core.management.base import BaseCommand
from django.db.models import Count
from eventos.models import TipoServicio


class Command(BaseCommand):
    help = 'Lista todos los TipoServicio actuales con la cantidad de eventos que tiene cada uno.'

    def handle(self, *args, **options):
        tipos = TipoServicio.objects.annotate(cantidad=Count('evento')).order_by('-cantidad')
        for tipo in tipos:
            self.stdout.write(f'{tipo.cantidad:4d}  {tipo.nombre}')
        self.stdout.write(self.style.SUCCESS(f'\nTotal: {tipos.count()} tipos de servicio distintos'))