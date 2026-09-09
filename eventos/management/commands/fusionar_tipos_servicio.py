import unicodedata
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from eventos.models import TipoServicio, Evento


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return texto.strip().lower()


class Command(BaseCommand):
    help = 'Detecta y fusiona TipoServicio duplicados por diferencias de tildes/mayúsculas (ej: "Ágape" vs "Agape").'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra qué se fusionaría, sin guardar nada.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        grupos = defaultdict(list)
        for tipo in TipoServicio.objects.all():
            grupos[normalizar(tipo.nombre)].append(tipo)

        duplicados_encontrados = 0

        for clave, tipos in grupos.items():
            if len(tipos) < 2:
                continue

            duplicados_encontrados += 1

            # El "válido" es el que tiene más eventos asociados. En caso de empate, el primero.
            tipos_con_conteo = [(t, Evento.objects.filter(tipo_servicio=t).count()) for t in tipos]
            tipos_con_conteo.sort(key=lambda x: x[1], reverse=True)
            valido, _ = tipos_con_conteo[0]
            duplicados = [t for t, _ in tipos_con_conteo[1:]]

            self.stdout.write(f'\nGrupo: "{clave}"')
            self.stdout.write(f'  Se conserva: "{valido.nombre}" (id={valido.id})')
            for dup in duplicados:
                cantidad_eventos = Evento.objects.filter(tipo_servicio=dup).count()
                self.stdout.write(f'  Se fusiona:  "{dup.nombre}" (id={dup.id}) — {cantidad_eventos} eventos a reasignar')

                if not dry_run:
                    with transaction.atomic():
                        Evento.objects.filter(tipo_servicio=dup).update(tipo_servicio=valido)
                        dup.delete()

        if duplicados_encontrados == 0:
            self.stdout.write(self.style.SUCCESS('No se encontraron duplicados.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n{"[DRY RUN] " if dry_run else ""}{duplicados_encontrados} grupo(s) de duplicados procesados.'
            ))
            if dry_run:
                self.stdout.write(self.style.WARNING('No se guardó nada. Corré sin --dry-run para aplicar.'))