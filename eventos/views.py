from django.shortcuts import render
from django.db.models import Sum
from .models import Evento, Periodo
import pandas as pd
from .models import ItemEnvioLavanderia, ItemPrestamo
from .forms import ItemEnvioLavanderiaFormSet, ItemPrestamoFormSet

from itertools import groupby

MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

def formato_moneda_ar(valor):
    """Formatea un número al estilo argentino: punto para miles, coma para decimales."""
    texto = f"{valor:,.2f}"
    texto = texto.replace(',', 'X').replace('.', ',').replace('X', '.')
    return texto


def pluralizar(cantidad, singular, plural):
    return singular if cantidad == 1 else plural

def agenda(request):
    periodo_id = request.GET.get('periodo')
    estado_id = request.GET.get('estado')

    periodos = Periodo.objects.all()
    eventos = Evento.objects.select_related('tipo_servicio', 'periodo').order_by('fecha')

    if periodo_id:
        eventos = eventos.filter(periodo_id=periodo_id)
    if estado_id:
        eventos = eventos.filter(estado_evento=estado_id)

    grupos = []
    for (anio, mes), eventos_del_mes in groupby(eventos, key=lambda e: (e.fecha.year, e.fecha.month)):
        grupos.append({
            'etiqueta': f'{MESES_ES[mes]} {anio}',
            'eventos': list(eventos_del_mes),
        })

    context = {
        'grupos': grupos,
        'periodos': periodos,
        'periodo_seleccionado': periodo_id,
        'estado_seleccionado': estado_id,
        'estados_evento': Evento.ESTADO_EVENTO,
    }
    return render(request, 'eventos/agenda.html', context)


def dashboard(request):
    periodo_id = request.GET.get('periodo')
    periodos = Periodo.objects.all()
    eventos = Evento.objects.all()
    if periodo_id:
        eventos = eventos.filter(periodo_id=periodo_id)

    internos = eventos.filter(origen='interno')
    externos = eventos.filter(origen='externo')

    costo_interno = internos.aggregate(t=Sum('costo'))['t'] or 0
    costo_externo = externos.aggregate(t=Sum('costo'))['t'] or 0
    facturado_interno = internos.aggregate(t=Sum('precio_facturado'))['t'] or 0
    facturado_externo = externos.aggregate(t=Sum('precio_facturado'))['t'] or 0

    context = {
        'periodos': periodos,
        'periodo_seleccionado': periodo_id,
        'total_eventos': eventos.count(),
        'total_internos': internos.count(),
        'total_externos': externos.count(),
        'costo_interno': costo_interno,
        'costo_externo': costo_externo,
        'margen_interno': facturado_interno - costo_interno,
        'margen_externo': facturado_externo - costo_externo,
        'cobrados': eventos.filter(estado_facturacion='cobrado').count(),
        'pendientes': eventos.filter(estado_facturacion='pendiente').count(),
        'balance': (facturado_interno + facturado_externo) - (costo_interno + costo_externo),
    }
    return render(request, 'eventos/dashboard.html', context)

from django.shortcuts import redirect, get_object_or_404
from .forms import EventoForm, ItemCostoPersonalFormSet


def evento_crear(request):
    if request.method == 'POST':
        form = EventoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('agenda')
    else:
        form = EventoForm()
    return render(request, 'eventos/evento_form.html', {'form': form, 'titulo': 'Nuevo evento'})


def evento_editar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        form = EventoForm(request.POST, instance=evento)
        if form.is_valid():
            evento_editado = form.save(commit=False)
            evento_editado.importado_automaticamente = False
            evento_editado.save()
            return redirect('agenda')
    else:
        form = EventoForm(instance=evento)
    return render(request, 'eventos/evento_form.html', {'form': form, 'titulo': 'Editar evento'})


def evento_eliminar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        evento.delete()
        return redirect('agenda')
    return render(request, 'eventos/evento_confirmar_eliminar.html', {'evento': evento})

from django.db import transaction
from .models import Presupuesto, Periodo, OpcionMenu, DetalleCosto, TipoServicio
from .forms import EventoPresupuestoForm, PresupuestoForm, OpcionMenuFormSet, ItemCostoPersonalFormSet


def presupuesto_form(request, pk=None):
    if pk:
        presupuesto = get_object_or_404(Presupuesto, pk=pk)
        evento = presupuesto.evento
    else:
        presupuesto = Presupuesto()
        evento_id = request.POST.get('evento_id') or request.GET.get('evento_id')
        evento = get_object_or_404(Evento, pk=evento_id) if evento_id else Evento()

    if request.method == 'POST':
        evento_form = EventoPresupuestoForm(request.POST, instance=evento)
        presupuesto_form_obj = PresupuestoForm(request.POST, instance=presupuesto)
        formset = OpcionMenuFormSet(request.POST, instance=presupuesto)
        formset_costo_personal = ItemCostoPersonalFormSet(request.POST, instance=presupuesto, prefix='costopersonal')

        if evento_form.is_valid() and presupuesto_form_obj.is_valid() and formset.is_valid() and formset_costo_personal.is_valid():
            with transaction.atomic():
                evento = evento_form.save(commit=False)
                semestre = 1 if evento.fecha.month <= 6 else 2
                periodo, _ = Periodo.objects.get_or_create(anio=evento.fecha.year, semestre=semestre)
                evento.periodo = periodo
                nombre_partes = [str(evento.tipo_servicio)] if evento.tipo_servicio else []
                if evento.cliente:
                    nombre_partes.append(evento.cliente)
                evento.nombre = ' - '.join(nombre_partes) or 'Evento sin nombre'
                if not pk:
                    evento.estado_evento = 'presupuestado'
                evento.save()

                presupuesto_obj = presupuesto_form_obj.save(commit=False)
                presupuesto_obj.evento = evento
                presupuesto_obj.save()
                presupuesto_form_obj.save_m2m()

                formset.instance = presupuesto_obj
                formset.save()

                formset_costo_personal.instance = presupuesto_obj
                formset_costo_personal.save()

            return redirect('presupuesto_detalle', pk=presupuesto_obj.pk)
    else:
        evento_form = EventoPresupuestoForm(instance=evento)
        presupuesto_form_obj = PresupuestoForm(instance=presupuesto)
        formset = OpcionMenuFormSet(instance=presupuesto)
        formset_costo_personal = ItemCostoPersonalFormSet(instance=presupuesto, prefix='costopersonal')

    return render(request, 'eventos/presupuesto_form.html', {
        'evento_form': evento_form,
        'presupuesto_form': presupuesto_form_obj,
        'formset': formset,
        'formset_costo_personal': formset_costo_personal,
        'editando': pk is not None,
    })


def presupuesto_lista(request):
    presupuestos = Presupuesto.objects.select_related('evento').order_by('-fecha_creacion')
    return render(request, 'eventos/presupuesto_lista.html', {'presupuestos': presupuestos})


def presupuesto_detalle(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    return render(request, 'eventos/presupuesto_detalle.html', {'presupuesto': presupuesto})

from io import BytesIO
from django.http import HttpResponse
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


def presupuesto_exportar_word(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    evento = presupuesto.evento

    doc = Document()

    # Título
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run('PRESUPUESTO')
    run.bold = True
    run.font.size = Pt(16)

    doc.add_paragraph()

    # Datos generales
    p = doc.add_paragraph()
    p.add_run('SOLICITANTE: ').bold = True
    p.add_run(evento.solicitante or '-')

    p = doc.add_paragraph()
    p.add_run('CLIENTE / ORGANISMO: ').bold = True
    p.add_run(evento.cliente or '-')

    p = doc.add_paragraph()
    p.add_run('FECHA: ').bold = True
    p.add_run(evento.fecha.strftime('%d de %B de %Y'))

    p = doc.add_paragraph()
    p.add_run('LUGAR: ').bold = True
    p.add_run(presupuesto.lugar or '-')

    if presupuesto.total_personas:
        p = doc.add_paragraph()
        p.add_run('CANTIDAD DE PERSONAS: ').bold = True
        detalle_personas = f'{presupuesto.total_personas} total (Regular: {presupuesto.cantidad_regular}'
        if presupuesto.cantidad_vegetariano:
            detalle_personas += f', Vegetariano: {presupuesto.cantidad_vegetariano}'
        if presupuesto.cantidad_celiaco:
            detalle_personas += f', Celíaco: {presupuesto.cantidad_celiaco}'
        detalle_personas += ')'
        p.add_run(detalle_personas)

    doc.add_paragraph()

    # Opciones de menú
    for opcion in presupuesto.opciones.all():
        p = doc.add_paragraph()
        run = p.add_run(f'OPCIÓN {opcion.orden}: ' if opcion.orden else f'{opcion.nombre.upper()}: ')
        run.bold = True
        run.italic = True

        for linea in opcion.detalle_menu.splitlines():
            linea = linea.strip()
            if linea:
                p_plato = doc.add_paragraph()
                p_plato.add_run(linea).italic = True

        doc.add_paragraph()

    # Servicios incluidos
    p = doc.add_paragraph()
    p.add_run('Además, el servicio incluye:').bold = True

    extras = list(presupuesto.extras_incluidos.all())
    if extras:
        doc.add_paragraph(', '.join(str(e) for e in extras))
    if presupuesto.otros_extras:
        doc.add_paragraph(presupuesto.otros_extras)

    doc.add_paragraph()

    # Precios por opción
    p = doc.add_paragraph()
    p.add_run('PRECIO POR PERSONA:').bold = True

    for opcion in presupuesto.opciones.all():
        nombre_op = f'Opción {opcion.orden}' if opcion.orden else opcion.nombre
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        run = p.add_run(f'{nombre_op} — Regular: ')
        run.bold = True
        p.add_run(f'${opcion.precio_regular:,.2f} por persona')

        if opcion.precio_vegetariano:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            p.add_run(f'   Vegetariano: ${opcion.precio_vegetariano:,.2f} por persona')

        if opcion.precio_celiaco:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            p.add_run(f'   Celíaco: ${opcion.precio_celiaco:,.2f} por persona')

    doc.add_paragraph()

    p = doc.add_paragraph()
    run = p.add_run(
        'Nota: El presente presupuesto puede sufrir modificaciones al momento de realizarse el evento. '
        'Se actualizará cada 30 días o cuando sea necesario.'
    )
    run.bold = True

    if presupuesto.observaciones:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run('Observaciones: ').bold = True
        p.add_run(presupuesto.observaciones)

    # Guardar en memoria y devolver como descarga
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nombre_archivo = f'Presupuesto_{evento.cliente or "evento"}_{evento.fecha}.docx'.replace(' ', '_')
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response

from django.db.models import Sum, Count
from .models import InformeGestion
from .forms import InformeGestionForm


def calcular_indicadores_periodo(periodo):
    eventos = Evento.objects.filter(periodo=periodo, excluir_de_informe=False)

    totales = eventos.aggregate(
        total_costo=Sum('costo'),
        total_facturado=Sum('precio_facturado'),
        total_personas=Sum('cantidad_personas'),
    )
    costo = totales['total_costo'] or 0
    facturado = totales['total_facturado'] or 0

    servicios_por_tipo = list(
        eventos.exclude(tipo_servicio__isnull=True)
        .values('tipo_servicio__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    unidades_destino = eventos.exclude(cliente='').values('cliente').distinct().count()

    return {
        'periodo': periodo,
        'total_eventos': eventos.count(),
        'internos': eventos.filter(origen='interno').count(),
        'externos': eventos.filter(origen='externo').count(),
        'total_personas': totales['total_personas'] or 0,
        'costo_total': costo,
        'facturado_total': facturado,
        'margen_total': facturado - costo,
        'cobrados': eventos.filter(estado_facturacion='cobrado').count(),
        'pendientes': eventos.filter(estado_facturacion='pendiente').count(),
        'servicios_por_tipo': servicios_por_tipo,
        'unidades_destino': unidades_destino,
    }

def calcular_desglose_mensual(periodo):
    eventos = Evento.objects.filter(periodo=periodo, excluir_de_informe=False).order_by('fecha')
    meses = []
    for (anio, mes), eventos_del_mes in groupby(eventos, key=lambda e: (e.fecha.year, e.fecha.month)):
        eventos_del_mes = list(eventos_del_mes)
        facturado = sum(e.precio_facturado for e in eventos_del_mes)
        costo = sum(e.costo for e in eventos_del_mes)
        meses.append({
            'etiqueta': f'{MESES_ES[mes]} {anio}',
            'facturado': facturado,
            'costo': costo,
            'margen': facturado - costo,
        })
    return meses

def calcular_puntos_venta_excluidos(periodo):
    eventos = Evento.objects.filter(periodo=periodo, excluir_de_informe=True).order_by('fecha')
    filas = []
    total = 0
    for e in eventos:
        monto = e.facturado_ajustado if e.facturado_ajustado is not None else e.precio_facturado
        filas.append({
            'fecha': e.fecha,
            'tipo_servicio': e.tipo_servicio,
            'cliente': e.cliente,
            'monto': monto,
        })
        total += monto
    return {'filas': filas, 'total': total}

def calcular_raciones_periodo(periodo, total_personas):
    eventos = Evento.objects.filter(periodo=periodo, excluir_de_informe=False)
    total_celiaco = eventos.aggregate(t=Sum('cantidad_personas_celiaco'))['t'] or 0
    total_vegetariano = Presupuesto.objects.filter(
        evento__periodo=periodo
    ).aggregate(t=Sum('cantidad_vegetariano'))['t'] or 0
    total_comun = max(total_personas - total_celiaco - total_vegetariano, 0)
    return {'comun': total_comun, 'vegetariano': total_vegetariano, 'celiaco': total_celiaco}

def informe_gestion_detalle(request, periodo_id):
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    indicadores = calcular_indicadores_periodo(periodo)
    informe, _ = InformeGestion.objects.get_or_create(periodo=periodo)

    return render(request, 'eventos/informe_gestion_detalle.html', {
        'indicadores': indicadores,
        'informe': informe,
    })


def informe_gestion_form(request, periodo_id):
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    informe, _ = InformeGestion.objects.get_or_create(periodo=periodo)

    if request.method == 'POST':
        form = InformeGestionForm(request.POST, instance=informe)
        if form.is_valid():
            form.save()
            return redirect('informe_gestion_detalle', periodo_id=periodo.id)
    else:
        form = InformeGestionForm(instance=informe)

    return render(request, 'eventos/informe_gestion_form.html', {'form': form, 'periodo': periodo})

def informe_gestion_exportar_word(request, periodo_id):
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    indicadores = calcular_indicadores_periodo(periodo)
    informe, _ = InformeGestion.objects.get_or_create(periodo=periodo)
    resumen_fact = calcular_resumen_facturacion(periodo)
    raciones = calcular_raciones_periodo(periodo, indicadores['total_personas'])
    doc = Document()

    nombre_semestre = 'primer' if periodo.semestre == 1 else 'segundo'
    texto_titulo = f'Informe - Balance de gestión {nombre_semestre} semestre año {periodo.anio} área de eventos UNCuyo'

    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run(texto_titulo)
    run.bold = True
    run.font.size = Pt(15)
    doc.add_paragraph()

    def agregar_titulo(texto):
        p = doc.add_paragraph()
        r = p.add_run(texto)
        r.bold = True
        r.font.size = Pt(13)

    def agregar_texto(texto):
        doc.add_paragraph(texto or '(sin completar)')

    agregar_titulo('1. Resumen Ejecutivo')
    agregar_texto(informe.resumen_ejecutivo)

    agregar_titulo('2. Objetivos del Período')
    agregar_texto(informe.objetivos)

    agregar_titulo('3. Indicadores Clave y Cuadro Operativo')
    tabla = doc.add_table(rows=1, cols=3)
    tabla.style = 'Light Grid Accent 1'
    hdr = tabla.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Categoría / Métrica', 'Detalle / Unidad', 'Total del Período'

    filas = [
        ('Eventos Atendidos', 'Internos / Externos',
         f"{indicadores['total_eventos']} eventos ({indicadores['internos']} internos, {indicadores['externos']} externos)"),
        ('Raciones / Menús Especiales', 'Común, vegetariano, celíaco',
         f"{raciones['comun']} común, {raciones['vegetariano']} vegetariano, {raciones['celiaco']} celíaco"),
        ('Asistencia Estimada', 'Personas atendidas', f"{indicadores['total_personas']} personas"),
        ('Servicios Adicionales', 'Horas extra / servicios',
         str(informe.servicios_adicionales_horas_extra) if informe.servicios_adicionales_horas_extra is not None else 'Sin datos cargados'),
        ('Unidades de Destino', 'Facultades, dependencias, Rectorado', str(indicadores['unidades_destino'])),
    ]
    for cat, detalle, total in filas:
        fila = tabla.add_row().cells
        fila[0].text, fila[1].text, fila[2].text = cat, detalle, total

    p = doc.add_paragraph()
    run = p.add_run(
        'Nota: la cifra de Unidades de Destino puede incluir variantes de escritura del mismo organismo '
        '(ej. nombres abreviados), por lo que es una estimación.'
        'Nota: el desglose de Raciones/Menús Especiales solo refleja el detalle vegetariano/celíaco '
        'para los eventos donde se cargó esa información puntualmente; los eventos importados en bloque '
        'desde registros históricos pueden no tener ese detalle disponible.'
    )
    run.italic = True
    run.font.size = Pt(9)

    doc.add_paragraph()
    agregar_titulo('4. Desglose de Servicios Realizados')
    if indicadores['servicios_por_tipo']:
        for item in indicadores['servicios_por_tipo']:
            palabra = pluralizar(item['cantidad'], 'evento', 'eventos')
            doc.add_paragraph(f"{item['tipo_servicio__nombre']}: {item['cantidad']} {palabra}", style='List Bullet')
    else:
        doc.add_paragraph('(sin datos de tipo de servicio para este período)')

    agregar_titulo('5. Balance Económico y Financiero')

    if informe.presupuesto_asignado is not None:
        doc.add_paragraph(f"Presupuesto asignado: ${formato_moneda_ar(informe.presupuesto_asignado)}")
    else:
        doc.add_paragraph("Presupuesto asignado: Sin datos cargados")

    doc.add_paragraph(f"Ejecución presupuestaria (costos operativos): ${formato_moneda_ar(indicadores['costo_total'])}")
    doc.add_paragraph(
        f"Facturado según registro de eventos: ${formato_moneda_ar(indicadores['facturado_total'])}"
    )

    if resumen_fact['filas']:
        doc.add_paragraph(
            f"Cobrado real (según planilla contable con contaduría): ${formato_moneda_ar(resumen_fact['total_cobrado'])} "
            f"({resumen_fact['porcentaje_general']:.1f}% de lo facturado en ese circuito) — "
            f"Pendiente de cobro: ${formato_moneda_ar(resumen_fact['total_pendiente'])}"
        )
        p = doc.add_paragraph()
        run = p.add_run(
            'Nota: el monto facturado según eventos y el de la planilla de contaduría no necesariamente '
            'coinciden, ya que los cobros de un evento pueden concretarse en meses o incluso años posteriores '
            'a su realización.'
        )
        run.italic = True
        run.font.size = Pt(9)

    doc.add_paragraph(f"Margen / Balance: ${formato_moneda_ar(indicadores['margen_total'])}")
    desglose_mensual = calcular_desglose_mensual(periodo)
    if desglose_mensual:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run('Desglose mensual:').bold = True

        tabla_mensual = doc.add_table(rows=1, cols=4)
        tabla_mensual.style = 'Light Grid Accent 1'
        hdr = tabla_mensual.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = 'Mes', 'Facturado', 'Costo', 'Ganancia'

        for mes in desglose_mensual:
            fila = tabla_mensual.add_row().cells
            fila[0].text = mes['etiqueta']
            fila[1].text = f"${formato_moneda_ar(mes['facturado'])}"
            fila[2].text = f"${formato_moneda_ar(mes['costo'])}"
            fila[3].text = f"${formato_moneda_ar(mes['margen'])}"

    puntos_venta = calcular_puntos_venta_excluidos(periodo)
    if puntos_venta['filas']:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run('Puntos de Venta (excluidos del cálculo mensual):').bold = True

        tabla_pv = doc.add_table(rows=1, cols=3)
        tabla_pv.style = 'Light Grid Accent 1'
        hdr = tabla_pv.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text = 'Fecha', 'Tipo / Cliente', 'Monto de venta'

        for fila in puntos_venta['filas']:
            f = tabla_pv.add_row().cells
            f[0].text = fila['fecha'].strftime('%d/%m/%Y')
            f[1].text = f"{fila['tipo_servicio'] or '-'} — {fila['cliente'] or '-'}"
            f[2].text = f"${formato_moneda_ar(fila['monto'])}"

        fila_total = tabla_pv.add_row().cells
        fila_total[0].text = ''
        fila_total[1].text = 'Total'
        fila_total[2].text = f"${formato_moneda_ar(puntos_venta['total'])}"

        p = doc.add_paragraph()
        run = p.add_run(
            'Nota: estos eventos presentaron un error de carga en su circuito normal y se excluyeron '
            'del desglose mensual de ganancias de arriba. Se reportan aparte con su monto de venta real.'
        )
        run.italic = True
        run.font.size = Pt(9)
    if informe.presupuesto_asignado:
        porcentaje = (indicadores['costo_total'] / informe.presupuesto_asignado) * 100
        doc.add_paragraph(f"Porcentaje de ejecución del presupuesto asignado: {porcentaje:.1f}%")

    agregar_titulo('6. Logros Destacados y Mejoras Operativas')
    agregar_texto(informe.logros_destacados)

    agregar_titulo('7. Desafíos y Objetivos para el Próximo Período')
    agregar_texto(informe.desafios_proximo_periodo)

    doc.add_paragraph()
    agregar_titulo('8. Integrantes y Funciones del Área')
    funciones = FuncionActividad.objects.prefetch_related('responsables').order_by('numero')
    if funciones.exists():
        tabla_func = doc.add_table(rows=1, cols=3)
        tabla_func.style = 'Light Grid Accent 1'
        hdr = tabla_func.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text = 'Nº', 'Descripción', 'Responsable(s)'
        for f in funciones:
            fila = tabla_func.add_row().cells
            fila[0].text = str(f.numero)
            fila[1].text = f.descripcion
            fila[2].text = ', '.join(str(r) for r in f.responsables.all()) or '-'
    else:
        doc.add_paragraph('(sin funciones cargadas)')

    # Salto de página + sección aparte de Facturación y Cobros
    doc.add_page_break()
    titulo_fact = doc.add_paragraph()
    titulo_fact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo_fact.add_run('FACTURACIÓN Y COBROS POR MES')
    run.bold = True
    run.font.size = Pt(14)
    doc.add_paragraph()


    if resumen_fact['filas']:
        tabla_fact = doc.add_table(rows=1, cols=5)
        tabla_fact.style = 'Light Grid Accent 1'
        hdr = tabla_fact.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = \
            'Mes', 'Facturado', 'Cobrado', 'Pendiente', '% Cobrado'

        for fila in resumen_fact['filas']:
            f = tabla_fact.add_row().cells
            f[0].text = fila['mes']
            f[1].text = f"${formato_moneda_ar(fila['facturado'])}"
            f[2].text = f"${formato_moneda_ar(fila['cobrado'])}"
            f[3].text = f"${formato_moneda_ar(fila['pendiente'])}"
            f[4].text = f"{fila['porcentaje_cobrado']:.1f}%"

        fila_total = tabla_fact.add_row().cells
        fila_total[0].text = 'Total'
        fila_total[1].text = f"${formato_moneda_ar(resumen_fact['total_facturado'])}"
        fila_total[2].text = f"${formato_moneda_ar(resumen_fact['total_cobrado'])}"
        fila_total[3].text = f"${formato_moneda_ar(resumen_fact['total_pendiente'])}"
        fila_total[4].text = f"{fila['porcentaje_general'] if False else resumen_fact['porcentaje_general']:.1f}%"
        doc.add_paragraph()
        p = doc.add_paragraph()
        run = p.add_run(
            'Nota: Estos datos reflejan la facturación y cobros según la planilla compartida con contaduría, '
            'independientemente de en qué mes se haya realizado el evento originalmente.'
        )
        run.italic = True
    else:
        doc.add_paragraph('No hay datos de facturación importados para este período.')

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nombre_archivo = f'Informe_Gestion_{periodo.anio}_S{periodo.semestre}.docx'
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response

def solicitud_crear(request):
    if request.method == 'POST':
        form = EventoPresupuestoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            semestre = 1 if evento.fecha.month <= 6 else 2
            periodo, _ = Periodo.objects.get_or_create(anio=evento.fecha.year, semestre=semestre)
            evento.periodo = periodo
            nombre_partes = [str(evento.tipo_servicio)] if evento.tipo_servicio else []
            if evento.cliente:
                nombre_partes.append(evento.cliente)
            evento.nombre = ' - '.join(nombre_partes) or 'Solicitud sin nombre'
            evento.estado_evento = 'solicitud'
            evento.save()
            return redirect('solicitud_lista')
    else:
        form = EventoPresupuestoForm()

    return render(request, 'eventos/solicitud_form.html', {'form': form})


def solicitud_lista(request):
    solicitudes = Evento.objects.filter(estado_evento='solicitud').order_by('fecha')
    return render(request, 'eventos/solicitud_lista.html', {'solicitudes': solicitudes})

def presupuesto_confirmar(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)

    if request.method == 'POST':
        opcion_id = request.POST.get('opcion_id')
        opcion = get_object_or_404(OpcionMenu, pk=opcion_id, presupuesto=presupuesto)

        with transaction.atomic():
            presupuesto.opcion_elegida = opcion
            presupuesto.save()

            evento = presupuesto.evento
            if evento.estado_evento == 'presupuestado':
                evento.estado_evento = 'confirmado'
                evento.save()

        return redirect('presupuesto_detalle', pk=presupuesto.pk)

    return render(request, 'eventos/presupuesto_confirmar.html', {'presupuesto': presupuesto})

def presupuesto_eliminar(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == 'POST':
        presupuesto.delete()
        return redirect('presupuesto_lista')
    return render(request, 'eventos/presupuesto_confirmar_eliminar.html', {'presupuesto': presupuesto})

def rentabilidad(request):
    periodo_id = request.GET.get('periodo')
    periodos = Periodo.objects.all()
    eventos = Evento.objects.select_related('tipo_servicio').filter(excluir_de_informe=False).order_by('fecha')
    if periodo_id:
        eventos = eventos.filter(periodo_id=periodo_id)

    grupos = []
    for (anio, mes), eventos_del_mes in groupby(eventos, key=lambda e: (e.fecha.year, e.fecha.month)):
        filas = []
        for e in eventos_del_mes:
            detalle = e.detalle_costo if hasattr(e, 'detalle_costo') else None
            filas.append({
                'evento': e,
                'valor_por_persona': (e.precio_facturado / e.cantidad_personas) if e.cantidad_personas else None,
                'manteleria': detalle.manteleria if detalle else None,
                'materia_prima': detalle.materia_prima if detalle else None,
                'personal': detalle.personal if detalle else None,
                'planilla': detalle.planilla if detalle else None,
                'varios': detalle.varios if detalle else None,
            })

        total_facturado = sum(f['evento'].precio_facturado for f in filas)
        total_costo = sum(f['evento'].costo for f in filas)

        grupos.append({
            'etiqueta': f'{MESES_ES[mes]} {anio}',
            'filas': filas,
            'total_facturado': total_facturado,
            'total_costo': total_costo,
            'total_margen': total_facturado - total_costo,
        })

    total_general_facturado = sum(g['total_facturado'] for g in grupos)
    total_general_costo = sum(g['total_costo'] for g in grupos)

    context = {
        'grupos': grupos,
        'periodos': periodos,
        'periodo_seleccionado': periodo_id,
        'total_general_facturado': total_general_facturado,
        'total_general_costo': total_general_costo,
        'total_general_margen': total_general_facturado - total_general_costo,
    }
    return render(request, 'eventos/rentabilidad.html', context)

from eventos.management.commands.importar_informe2026 import (
    normalizar, buscar_columna, a_decimal, a_texto, inferir_origen, obtener_o_crear_tipo_servicio
)
from django.contrib import messages


def sincronizar_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        hojas = pd.read_excel(archivo, sheet_name=None)

        total_eliminados = 0
        total_creados = 0

        for nombre_hoja, df in hojas.items():
            columnas_normalizadas = {normalizar(c): c for c in df.columns}
            col_fecha = buscar_columna(columnas_normalizadas, 'FECHA')
            if not col_fecha:
                continue

            col_solicitante = buscar_columna(columnas_normalizadas, 'SOLICITANTE')
            col_cliente = buscar_columna(columnas_normalizadas, 'CLIENTE')
            col_tipo_serv = buscar_columna(columnas_normalizadas, 'TIPO DE EVENTO')
            col_personas = buscar_columna(columnas_normalizadas, 'CANT DE PERSONAS')
            col_total = buscar_columna(columnas_normalizadas, 'TOTAL')
            col_costo_total = buscar_columna(columnas_normalizadas, 'COSTO TOTAL')
            col_nro_fac = buscar_columna(columnas_normalizadas, 'N DE FAC', 'NRO DE FAC', 'N° DE FAC')
            col_nro_rec = buscar_columna(columnas_normalizadas, 'N DE REC', 'NRO DE REC', 'N° DE REC')
            col_expediente = buscar_columna(columnas_normalizadas, 'EXPEDIENTE')
            col_comprobante = buscar_columna(columnas_normalizadas, 'N DE COMP.', 'NRO DE COMP.', 'N° DE COMP.')
            col_manteleria = buscar_columna(columnas_normalizadas, 'MANTELERIA', 'MANTELERÍA')
            col_cmp = buscar_columna(columnas_normalizadas, 'C.M.P', 'C.M.P.')
            col_personal = buscar_columna(columnas_normalizadas, 'PERSONAL')
            col_planilla_gral = buscar_columna(columnas_normalizadas, 'PLANILLA GENERAL', 'PLANILLA GRAL')
            col_planilla_tes = buscar_columna(columnas_normalizadas, 'PLANILLA TESORERIA', 'PLANILLA TESORERÍA')
            col_varios = buscar_columna(columnas_normalizadas, 'VARIOS')

            filas_validas = []
            for _, fila in df.iterrows():
                fecha = fila.get(col_fecha)
                if pd.isna(fecha):
                    continue
                fecha = pd.to_datetime(fecha).date()
                filas_validas.append((fecha, fila))

            if not filas_validas:
                continue

            meses_presentes = {(f.year, f.month) for f, _ in filas_validas}
            for anio, mes in meses_presentes:
                eliminados, _ = Evento.objects.filter(
                    importado_automaticamente=True, fecha__year=anio, fecha__month=mes
                ).delete()
                total_eliminados += eliminados

            for fecha, fila in filas_validas:
                cliente = a_texto(fila.get(col_cliente))
                solicitante = a_texto(fila.get(col_solicitante))
                tipo_servicio_nombre = a_texto(fila.get(col_tipo_serv)) or 'Sin especificar'
                personas = fila.get(col_personas)
                personas = int(personas) if pd.notna(personas) else None

                total_facturado = a_decimal(fila.get(col_total))
                costo_total = a_decimal(fila.get(col_costo_total))
                origen = inferir_origen(cliente)

                nombre_evento = f"{tipo_servicio_nombre} - {cliente}" if cliente else tipo_servicio_nombre
                nombre_evento = nombre_evento[:200]
                semestre = 1 if fecha.month <= 6 else 2

                periodo, _ = Periodo.objects.get_or_create(anio=fecha.year, semestre=semestre)
                tipo_servicio = obtener_o_crear_tipo_servicio(tipo_servicio_nombre)

                evento = Evento.objects.create(
                    nombre=nombre_evento,
                    tipo_servicio=tipo_servicio,
                    periodo=periodo,
                    origen=origen,
                    fecha=fecha,
                    cliente=cliente,
                    solicitante=solicitante,
                    cantidad_personas=personas,
                    costo=costo_total,
                    precio_facturado=total_facturado,
                    estado_facturacion='cobrado' if a_texto(fila.get(col_nro_fac)) else 'pendiente',
                    estado_evento='realizado',
                    nro_factura=a_texto(fila.get(col_nro_fac)),
                    nro_recibo=a_texto(fila.get(col_nro_rec)),
                    expediente=a_texto(fila.get(col_expediente)),
                    nro_comprobante=a_texto(fila.get(col_comprobante)),
                    importado_automaticamente=True,
                )

                DetalleCosto.objects.create(
                    evento=evento,
                    manteleria=a_decimal(fila.get(col_manteleria)),
                    materia_prima=a_decimal(fila.get(col_cmp)),
                    personal=a_decimal(fila.get(col_personal)),
                    planilla=a_decimal(fila.get(col_planilla_gral)) + a_decimal(fila.get(col_planilla_tes)),
                    varios=a_decimal(fila.get(col_varios)),
                )
                total_creados += 1

        messages.success(
            request,
            f'Sincronización completa: se reemplazaron {total_eliminados} eventos por {total_creados} actualizados '
            f'(los eventos que editaste a mano no se tocaron).'
        )
        return redirect('sincronizar_excel')

    return render(request, 'eventos/sincronizar_excel.html')

from .models import ResumenFacturacionMensual


def calcular_resumen_facturacion(periodo):
    resumenes = ResumenFacturacionMensual.objects.filter(periodo=periodo).order_by('mes')
    filas = []
    for r in resumenes:
        porcentaje = (r.cobrado / r.facturado * 100) if r.facturado else 0
        filas.append({
            'mes': MESES_ES[r.mes],
            'facturado': r.facturado,
            'cobrado': r.cobrado,
            'pendiente': r.pendiente,
            'porcentaje_cobrado': porcentaje,
        })

    total_facturado = sum(f['facturado'] for f in filas)
    total_cobrado = sum(f['cobrado'] for f in filas)
    total_pendiente = sum(f['pendiente'] for f in filas)

    return {
        'filas': filas,
        'total_facturado': total_facturado,
        'total_cobrado': total_cobrado,
        'total_pendiente': total_pendiente,
        'porcentaje_general': (total_cobrado / total_facturado * 100) if total_facturado else 0,
    }


def facturacion_mensual(request):
    periodo_id = request.GET.get('periodo')
    periodos = Periodo.objects.all()

    resumen = None
    if periodo_id:
        periodo = get_object_or_404(Periodo, pk=periodo_id)
        resumen = calcular_resumen_facturacion(periodo)

    return render(request, 'eventos/facturacion_mensual.html', {
        'periodos': periodos,
        'periodo_seleccionado': periodo_id,
        'resumen': resumen,
    })

def inicio(request):
    return render(request, 'eventos/inicio.html')

from .models import Integrante, FuncionActividad
from .forms import IntegranteForm, FuncionActividadForm


def integrante_lista(request):
    integrantes = Integrante.objects.all()
    return render(request, 'eventos/integrante_lista.html', {'integrantes': integrantes})


def integrante_form(request, pk=None):
    integrante = get_object_or_404(Integrante, pk=pk) if pk else Integrante()
    if request.method == 'POST':
        form = IntegranteForm(request.POST, instance=integrante)
        if form.is_valid():
            form.save()
            return redirect('integrante_lista')
    else:
        form = IntegranteForm(instance=integrante)
    return render(request, 'eventos/integrante_form.html', {'form': form, 'editando': pk is not None})


def integrante_eliminar(request, pk):
    integrante = get_object_or_404(Integrante, pk=pk)
    if request.method == 'POST':
        integrante.delete()
        return redirect('integrante_lista')
    return render(request, 'eventos/integrante_confirmar_eliminar.html', {'integrante': integrante})


def funcion_lista(request):
    funciones = FuncionActividad.objects.prefetch_related('responsables').all()
    return render(request, 'eventos/funcion_lista.html', {'funciones': funciones})


def funcion_form(request, pk=None):
    funcion = get_object_or_404(FuncionActividad, pk=pk) if pk else FuncionActividad()
    if request.method == 'POST':
        form = FuncionActividadForm(request.POST, instance=funcion)
        if form.is_valid():
            form.save()
            return redirect('funcion_lista')
    else:
        form = FuncionActividadForm(instance=funcion)
    return render(request, 'eventos/funcion_form.html', {'form': form, 'editando': pk is not None})


def funcion_eliminar(request, pk):
    funcion = get_object_or_404(FuncionActividad, pk=pk)
    if request.method == 'POST':
        funcion.delete()
        return redirect('funcion_lista')
    return render(request, 'eventos/funcion_confirmar_eliminar.html', {'funcion': funcion})

from .models import Producto, Compra, ItemCompra
from .forms import ProductoForm, CompraForm, ItemCompraFormSet


def producto_lista(request):
    productos = Producto.objects.all()
    return render(request, 'eventos/producto_lista.html', {'productos': productos})


def producto_form(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk) if pk else Producto()
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('producto_lista')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'eventos/producto_form.html', {'form': form, 'editando': pk is not None})


def compra_lista(request):
    compras = Compra.objects.select_related('evento').prefetch_related('items')
    return render(request, 'eventos/compra_lista.html', {'compras': compras})


def compra_form(request, pk=None):
    compra = get_object_or_404(Compra, pk=pk) if pk else Compra()
    if request.method == 'POST':
        form = CompraForm(request.POST, instance=compra)
        formset = ItemCompraFormSet(request.POST, instance=compra)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                compra_obj = form.save()
                formset.instance = compra_obj
                formset.save()
            return redirect('compra_detalle', pk=compra_obj.pk)
    else:
        form = CompraForm(instance=compra)
        formset = ItemCompraFormSet(instance=compra)
    return render(request, 'eventos/compra_form.html', {
        'form': form, 'formset': formset, 'editando': pk is not None,
    })


def compra_detalle(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    return render(request, 'eventos/compra_detalle.html', {'compra': compra})


def compra_eliminar(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method == 'POST':
        compra.delete()
        return redirect('compra_lista')
    return render(request, 'eventos/compra_confirmar_eliminar.html', {'compra': compra})


def producto_detalle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    items = ItemCompra.objects.filter(producto=producto).select_related('compra').order_by('compra__fecha')

    historial = []
    precio_anterior = None
    for item in items:
        precio_actual = item.precio_unitario
        variacion = None
        if precio_anterior is not None and precio_anterior != 0:
            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100
        historial.append({
            'fecha': item.compra.fecha,
            'proveedor': item.compra.proveedor,
            'cantidad': item.cantidad,
            'total_pagado': item.total_pagado,
            'precio_unitario': precio_actual,
            'variacion': variacion,
        })
        precio_anterior = precio_actual

    historial.reverse()  # más reciente primero

    return render(request, 'eventos/producto_detalle.html', {
        'producto': producto,
        'historial': historial,
    })


from .models import PersonaEventual, Pago
from .forms import PersonaEventualForm, PagoForm


def persona_eventual_lista(request):
    personas = PersonaEventual.objects.all()
    return render(request, 'eventos/persona_eventual_lista.html', {'personas': personas})


def persona_eventual_form(request, pk=None):
    persona = get_object_or_404(PersonaEventual, pk=pk) if pk else PersonaEventual()
    if request.method == 'POST':
        form = PersonaEventualForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            return redirect('persona_eventual_lista')
    else:
        form = PersonaEventualForm(instance=persona)
    return render(request, 'eventos/persona_eventual_form.html', {'form': form, 'editando': pk is not None})


def pago_lista(request, tipo=None):
    pagos = Pago.objects.select_related('persona', 'evento')
    if tipo:
        pagos = pagos.filter(tipo_pago=tipo)
    pagos = pagos.order_by('-fecha')
    total = sum((p.importe for p in pagos), 0)
    return render(request, 'eventos/pago_lista.html', {
        'pagos': pagos, 'tipo_actual': tipo, 'total': total, 'tipos_pago': Pago.TIPO_PAGO,
    })


def pago_form(request, pk=None):
    pago = get_object_or_404(Pago, pk=pk) if pk else Pago()
    if request.method == 'POST':
        form = PagoForm(request.POST, instance=pago)
        if form.is_valid():
            form.save()
            return redirect('pago_lista_todos')
    else:
        form = PagoForm(instance=pago)
    return render(request, 'eventos/pago_form.html', {'form': form, 'editando': pk is not None})


def pago_eliminar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        return redirect('pago_lista_todos')
    return render(request, 'eventos/pago_confirmar_eliminar.html', {'pago': pago})

from .models import CategoriaInventario, ElementoInventario, EnvioLavanderia, Prestamo
from .forms import ElementoInventarioForm, EnvioLavanderiaForm, PrestamoForm


def inventario_lista(request):
    categoria_id = request.GET.get('categoria')
    elementos = ElementoInventario.objects.select_related('categoria')
    if categoria_id:
        elementos = elementos.filter(categoria_id=categoria_id)
    categorias = CategoriaInventario.objects.all()
    return render(request, 'eventos/inventario_lista.html', {
        'elementos': elementos, 'categorias': categorias, 'categoria_seleccionada': categoria_id,
    })


def inventario_form(request, pk=None):
    elemento = get_object_or_404(ElementoInventario, pk=pk) if pk else ElementoInventario()
    if request.method == 'POST':
        form = ElementoInventarioForm(request.POST, instance=elemento)
        if form.is_valid():
            form.save()
            return redirect('inventario_lista')
    else:
        form = ElementoInventarioForm(instance=elemento)
    return render(request, 'eventos/inventario_form.html', {'form': form, 'editando': pk is not None})


def lavanderia_lista(request):
    envios = EnvioLavanderia.objects.prefetch_related('items__elemento').all()
    return render(request, 'eventos/lavanderia_lista.html', {'envios': envios})

def lavanderia_form(request, pk=None):
    envio = get_object_or_404(EnvioLavanderia, pk=pk) if pk else EnvioLavanderia()
    if request.method == 'POST':
        form = EnvioLavanderiaForm(request.POST, request.FILES, instance=envio)
        formset = ItemEnvioLavanderiaFormSet(request.POST, instance=envio)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                envio_obj = form.save()
                formset.instance = envio_obj
                formset.save()
            return redirect('lavanderia_lista')
    else:
        form = EnvioLavanderiaForm(instance=envio)
        formset = ItemEnvioLavanderiaFormSet(instance=envio)
    return render(request, 'eventos/lavanderia_form.html', {
        'form': form, 'formset': formset, 'editando': pk is not None,
    })

def prestamo_lista(request):
    prestamos = Prestamo.objects.prefetch_related('items__elemento').all()
    return render(request, 'eventos/prestamo_lista.html', {'prestamos': prestamos})

def prestamo_form(request, pk=None):
    prestamo = get_object_or_404(Prestamo, pk=pk) if pk else Prestamo()
    if request.method == 'POST':
        form = PrestamoForm(request.POST, instance=prestamo)
        formset = ItemPrestamoFormSet(request.POST, instance=prestamo)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                prestamo_obj = form.save()
                formset.instance = prestamo_obj
                formset.save()
            return redirect('prestamo_lista')
    else:
        form = PrestamoForm(instance=prestamo)
        formset = ItemPrestamoFormSet(instance=prestamo)
    return render(request, 'eventos/prestamo_form.html', {
        'form': form, 'formset': formset, 'editando': pk is not None,
    })