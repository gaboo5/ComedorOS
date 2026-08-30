from django.core.management.base import BaseCommand
from django.db import transaction

from eventos.models import Evento, Periodo


class Command(BaseCommand):
    help = 'Corrige errores puntuales detectados en la importación de Informe_2026.xlsx: fechas con año mal tipeado y origen mal clasificado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra qué se corregiría, sin guardar nada.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # --- 1. Fechas con año mal tipeado (año "0206" en vez de "2026") ---
        self.stdout.write(self.style.MIGRATE_HEADING('\n1. Corrigiendo fechas con año inválido'))
        eventos_fecha_mal = Evento.objects.filter(fecha__year__lt=2000)

        if not eventos_fecha_mal.exists():
            self.stdout.write('  No se encontraron eventos con año inválido (¿ya se corrigió antes?).')
        else:
            for evento in eventos_fecha_mal:
                fecha_original = evento.fecha
                fecha_corregida = fecha_original.replace(year=2026)
                self.stdout.write(
                    f'  "{evento.nombre[:50]}": {fecha_original} -> {fecha_corregida}'
                )
                if not dry_run:
                    semestre = 1 if fecha_corregida.month <= 6 else 2
                    periodo_correcto, _ = Periodo.objects.get_or_create(
                        anio=fecha_corregida.year, semestre=semestre
                    )
                    with transaction.atomic():
                        evento.fecha = fecha_corregida
                        evento.periodo = periodo_correcto
                        evento.save()

            # Limpieza: si el Período viejo (año inválido) quedó sin eventos, lo eliminamos
            if not dry_run:
                periodos_huerfanos = Periodo.objects.filter(anio__lt=2000)
                for p in periodos_huerfanos:
                    if not Evento.objects.filter(periodo=p).exists():
                        self.stdout.write(f'  Eliminando período huérfano: {p}')
                        p.delete()

        # --- 2. Origen mal clasificado por colisión de palabra clave ---
        self.stdout.write(self.style.MIGRATE_HEADING('\n2. Corrigiendo origen mal clasificado'))

        correcciones_origen = [
            ('Ministerio de salud y deportes', 'externo'),
            ('Rectora', 'interno'),  # cubre "Rectora" y "Rectorado"
        ]

        for texto_buscado, origen_correcto in correcciones_origen:
            eventos_afectados = Evento.objects.filter(
                cliente__icontains=texto_buscado
            ).exclude(origen=origen_correcto)

            if not eventos_afectados.exists():
                self.stdout.write(f'  Sin cambios para "{texto_buscado}" (ya está correcto o no hay coincidencias).')
                continue

            for evento in eventos_afectados:
                self.stdout.write(
                    f'  "{evento.nombre[:50]}": {evento.origen} -> {origen_correcto}'
                )
                if not dry_run:
                    evento.origen = origen_correcto
                    evento.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n{"[DRY RUN] " if dry_run else ""}Corrección completada.'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('No se guardó nada. Corré sin --dry-run para aplicar los cambios.'))