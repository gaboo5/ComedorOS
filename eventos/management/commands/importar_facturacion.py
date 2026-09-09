import re
import pandas as pd
from django.core.management.base import BaseCommand
from eventos.models import Periodo, ResumenFacturacionMensual

MESES_NOMBRE_A_NUMERO = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
    'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
}


class Command(BaseCommand):
    help = 'Importa los resúmenes mensuales de facturación/cobro desde la planilla compartida con contaduría.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        ruta = options['archivo']
        dry_run = options['dry_run']

        df = pd.read_excel(ruta, header=1)
        año_actual = None
        pendiente_mes = None  # guarda el nombre de mes de la fila "COBRADO" hasta encontrar su "PENDIENTE"
        cobrado_valor = None
        total_procesados = 0

        for _, fila in df.iterrows():
            comprob = str(fila.get('COMPROB.', '')).strip()
            razon = str(fila.get('RAZON SOCIAL', '')).strip().upper()
            valor_e = fila.get('PENDIENTES DE COBRO')
            valor_f = fila.get('IMPORTE FACT.')

            # Marca de año: ej. COMPROB.="2025", RAZON SOCIAL="FACTURACION"
            if re.match(r'^\d{4}$', comprob) and razon == 'FACTURACION':
                año_actual = int(comprob) + 1
                continue

            if razon == 'COBRADO' and comprob.upper() in MESES_NOMBRE_A_NUMERO:
                pendiente_mes = comprob.upper()
                cobrado_valor = valor_e if pd.notna(valor_e) else 0
                continue

            if razon == 'PENDIENTE' and pendiente_mes and año_actual:
                mes_numero = MESES_NOMBRE_A_NUMERO[pendiente_mes]
                pendiente_valor = valor_e if pd.notna(valor_e) else 0
                facturado_valor = valor_f if pd.notna(valor_f) else 0

                semestre = 1 if mes_numero <= 6 else 2
                self.stdout.write(
                    f'{pendiente_mes} {año_actual}: Facturado ${facturado_valor:,.2f} | '
                    f'Cobrado ${cobrado_valor:,.2f} | Pendiente ${pendiente_valor:,.2f}'
                )

                if not dry_run:
                    periodo, _ = Periodo.objects.get_or_create(anio=año_actual, semestre=semestre)
                    ResumenFacturacionMensual.objects.update_or_create(
                        periodo=periodo, mes=mes_numero,
                        defaults={
                            'facturado': facturado_valor,
                            'cobrado': cobrado_valor,
                            'pendiente': pendiente_valor,
                        }
                    )
                total_procesados += 1
                pendiente_mes = None

        self.stdout.write(self.style.SUCCESS(
            f'\n{"[DRY RUN] " if dry_run else ""}{total_procesados} meses procesados.'
        ))