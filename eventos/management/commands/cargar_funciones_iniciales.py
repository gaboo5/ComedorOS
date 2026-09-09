from django.core.management.base import BaseCommand
from eventos.models import Integrante, FuncionActividad

FUNCIONES = [
    (1, "Coordinación general del Área.", ["Ignacio Zoia"]),
    (2, "Recepción de solicitudes de eventos y/o servicios.", ["Ignacio Zoia", "Javier Molina"]),
    (3, "Agenda de eventos consignando área o unidad académica y/o personas que lo solicita, fecha, lugar, "
        "cantidad de personas y tipo de evento y/o servicio solicitado.", ["Ignacio Zoia", "Javier Molina"]),
    (4, "Confección de presupuestos y estimación de costos enviado vía correo electrónico al solicitante del "
        "servicio.", ["Ignacio Zoia", "Javier Molina"]),
    (5, "Confirmación de la aceptación para la realización del evento.", ["Ignacio Zoia", "Javier Molina"]),
    (6, "Coordinación con responsables a cargo de las áreas vinculadas.", ["Ignacio Zoia"]),
    (7, "Consulta y coordinación con la Dirección acerca de las particularidades de cada servicio.", ["Ignacio Zoia"]),
    (8, "Confección de planillas para el pago de los servicios tanto para el personal eventual como para el "
        "personal del Comedor.", ["Ignacio Zoia", "Javier Molina"]),
    (9, "Coordinación con Tesorería para la realización de pagos al personal que presta servicios en cada evento.",
        ["Ignacio Zoia"]),
    (10, "Control de la facturación del personal del Comedor que prestó servicios.", ["Ignacio Zoia"]),
    (11, "Mantenimiento del depósito de insumos (vajilla, mantelería, etc.).", ["Gabriel Donoso"]),
    (12, "Mantenimiento de vehículo.", ["Javier Molina"]),
    (13, "Coordinación del personal eventual afectado a cada evento.", ["Gabriel Donoso"]),
    (14, "Seguimiento del desarrollo y finalización de cada evento.", ["Ignacio Zoia"]),
    (15, "Cobro de servicios a través de distintos medios de pago (expedientes, factura, recibo).", ["Ignacio Zoia"]),
    (16, "Seguimiento del estado de cobro de los servicios a través de registro diario en informe.", ["Ignacio Zoia"]),
    (17, "Consulta posterior a usuarios y/o clientes acerca de cómo fue ejecutado el servicio según lo acordado.",
        ["Ignacio Zoia"]),
    (18, "Confección de informe con detalle de los servicios consignando: solicitante, cantidad de personas, "
        "evento a realizar, lugar, precio de cobro, gastos extraordinarios, gastos internos (materia prima "
        "utilizada, personal, mantelería, etc.), margen adquirido y facturación, a fin de obtener datos "
        "estadísticos para la realización del balance de la gestión.", ["Ignacio Zoia", "Javier Molina"]),
    (19, "Confección de Informe con gastos y/o consumos de la Secretaría de Bienestar (Coordinaciones y "
        "Direcciones).", ["Javier Molina"]),
]


class Command(BaseCommand):
    help = 'Carga las funciones/actividades iniciales extraídas del informe histórico del área.'

    def handle(self, *args, **options):
        creadas = 0
        for numero, descripcion, nombres_responsables in FUNCIONES:
            funcion, fue_creada = FuncionActividad.objects.get_or_create(
                numero=numero, defaults={'descripcion': descripcion}
            )
            if fue_creada:
                creadas += 1
            for nombre in nombres_responsables:
                integrante, _ = Integrante.objects.get_or_create(nombre=nombre)
                funcion.responsables.add(integrante)

        self.stdout.write(self.style.SUCCESS(f'Listo. {creadas} funciones nuevas cargadas (de {len(FUNCIONES)} totales).'))