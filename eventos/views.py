from django.shortcuts import render
from django.db.models import Sum
from .models import Evento, Periodo


def agenda(request):
    periodo_id = request.GET.get('periodo')
    periodos = Periodo.objects.all()
    eventos = Evento.objects.select_related('tipo', 'periodo').order_by('fecha')
    if periodo_id:
        eventos = eventos.filter(periodo_id=periodo_id)

    context = {
        'eventos': eventos,
        'periodos': periodos,
        'periodo_seleccionado': periodo_id,
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