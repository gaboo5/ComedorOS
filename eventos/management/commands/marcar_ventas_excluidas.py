from django.core.management.base import BaseCommand
from eventos.models import Evento

AJUSTES = [
    (190, 474500),
    (243, 424000),
    (266, 694500),
    (275, 431200),
    (307, 1543100),
    (313, 1772200),
]


class Command(BaseCommand):
    help = 'Marca eventos puntuales como excluidos del cálculo mensual normal, con su monto de venta correcto.'

    def handle(self, *args, **options):
        for id_evento, monto in AJUSTES:
            try:
                evento = Evento.objects.get(pk=id_evento)
            except Evento.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No existe el evento ID {id_evento}'))
                continue
            evento.excluir_de_informe = True
            evento.facturado_ajustado = monto
            evento.nota_ajuste = (
                'Error de carga detectado en el circuito normal: excluido del cálculo mensual '
                'y reportado aparte como Punto de Venta.'
            )
            evento.save()
            self.stdout.write(f'ID {id_evento}: marcado, monto de venta = ${monto}')
        self.stdout.write(self.style.SUCCESS('Listo.'))