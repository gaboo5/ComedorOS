from django.core.management.base import BaseCommand
from eventos.models import Evento

FECHAS = ['2026-03-12', '2026-05-08', '2026-06-25', '2026-06-26', '2026-05-23', '2026-06-05']


class Command(BaseCommand):
    help = 'Lista eventos en fechas específicas, con su ID, para identificar cuáles ajustar.'

    def handle(self, *args, **options):
        for fecha in FECHAS:
            self.stdout.write(f'\n--- {fecha} ---')
            eventos = Evento.objects.filter(fecha=fecha).order_by('id')
            if not eventos.exists():
                self.stdout.write('  (sin eventos)')
            for e in eventos:
                self.stdout.write(
                    f'  ID {e.id:4d} | {e.nombre[:55]:55s} | cliente: {e.cliente[:30]:30s} | '
                    f'costo: ${e.costo} | facturado: ${e.precio_facturado}'
                )