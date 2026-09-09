from django.core.management.base import BaseCommand
from eventos.models import Evento


class Command(BaseCommand):
    help = 'Marca como "importados automáticamente" los eventos que vinieron del Excel histórico (estado realizado).'

    def handle(self, *args, **options):
        actualizados = Evento.objects.filter(estado_evento='realizado', importado_automaticamente=False).update(
            importado_automaticamente=True
        )
        self.stdout.write(self.style.SUCCESS(f'{actualizados} eventos marcados como importados desde Excel.'))