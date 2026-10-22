import json
import socket
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from eventos.models import Evento, TipoServicio
from eventos.views import periodo_para_fecha

from .forms import ComponenteFormSet, JornadaForm, ProductoVentaForm, PromoForm, VarianteFormSet
from .models import (
    CategoriaVenta,
    ComponentePromo,
    ItemCarta,
    Jornada,
    LineaTicket,
    ProductoVenta,
    Promo,
    Ticket,
    VarianteVenta,
)
from .utils import a_decimal

# ======================================================================
# HELPERS
# ======================================================================

PALABRAS_VIRTUALES = ('vethernet', 'wsl', 'virtualbox', 'vmware', 'hyper-v', 'docker', 'loopback',
                      'bluetooth', 'vpn', 'tailscale', 'zerotier', 'hamachi', 'npcap')


def ips_en_la_red():
    """Todas las direcciones IPv4 de esta computadora, de la más a la menos probable para conectar
    otro celular (primero el adaptador Wi-Fi, al final los adaptadores virtuales).
    Devuelve [{'ip': '192.168.43.20', 'interfaz': 'Wi-Fi', 'virtual': False}, ...]"""
    candidatas = {}
    try:
        import psutil  # da el nombre de cada adaptador (Wi-Fi, Ethernet, vEthernet (WSL)...)
        activas = {n for n, st in psutil.net_if_stats().items() if st.isup}
        for nombre, direcciones in psutil.net_if_addrs().items():
            if nombre not in activas:
                continue
            for d in direcciones:
                if d.family == socket.AF_INET:
                    candidatas[d.address] = nombre
    except ImportError:
        pass
    # Respaldo sin psutil: la interfaz que usaría el sistema + las del nombre del equipo
    for destino in ('192.168.255.255', '10.255.255.255', '8.8.8.8'):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((destino, 1))  # no envía nada, solo elige la interfaz de red
                candidatas.setdefault(s.getsockname()[0], '')
        except OSError:
            pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidatas.setdefault(info[4][0], '')
    except OSError:
        pass

    resultado = []
    for ip, interfaz in candidatas.items():
        if ip.startswith(('127.', '169.254.', '0.')):
            continue
        virtual = any(p in interfaz.lower() for p in PALABRAS_VIRTUALES)
        wifi = any(p in interfaz.lower() for p in ('wi-fi', 'wifi', 'wlan', 'inalámbrica', 'wireless'))
        hotspot = ip.startswith(('192.168.', '172.20.10.'))   # rangos típicos de hotspot Android / iPhone
        orden = (virtual, not wifi, not hotspot, ip)
        resultado.append({'ip': ip, 'interfaz': interfaz, 'virtual': virtual, 'orden': orden})
    resultado.sort(key=lambda r: r['orden'])
    return resultado


def qr_svg(texto):
    """Código QR en SVG (si la librería 'qrcode' está instalada)."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return None
    imagen = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return imagen.to_string(encoding='unicode')


def json_error(mensaje, status=400):
    return JsonResponse({'ok': False, 'error': mensaje}, status=status)


def carta_para_caja(jornada):
    """Arma la lista de botones de la caja: variantes de la carta + promos del día."""
    restante = jornada.stock_restante()
    categorias = []
    actual = None
    for item in jornada.carta.select_related('variante__producto__categoria'):
        cat = item.variante.producto.categoria
        if actual is None or actual['nombre'] != cat.nombre:
            actual = {'nombre': cat.nombre, 'items': []}
            categorias.append(actual)
        actual['items'].append({
            'clave': f'v{item.variante_id}',
            'tipo': 'variante',
            'id': item.variante_id,
            'producto': item.variante.producto.nombre,
            'opcion': item.variante.nombre,
            'nombre': item.variante.nombre_completo,
            'precio': float(item.precio),
            'stock': restante.get(item.variante_id),
        })
    promos = [{
        'clave': f'p{p.id}',
        'tipo': 'promo',
        'id': p.id,
        'producto': p.nombre,
        'opcion': '',
        'nombre': p.nombre,
        'detalle': p.descripcion_componentes,
        'precio': float(p.precio),
        'stock': None,
        'componentes': {str(c.variante_id): c.cantidad for c in p.componentes.all()},
    } for p in jornada.promos.filter(activo=True).prefetch_related('componentes__variante__producto')]
    if promos:
        categorias.insert(0, {'nombre': 'Promos', 'items': promos})
    return categorias


# ======================================================================
# JORNADAS
# ======================================================================

def pv_jornada_lista(request):
    jornadas = Jornada.objects.annotate(
        cantidad_tickets=Count('tickets', distinct=True),
    ).select_related('evento')
    filas = []
    for j in jornadas:
        filas.append({'jornada': j, 'total': j.totales()['total']})
    return render(request, 'ventas/jornada_lista.html', {'filas': filas})


def pv_jornada_form(request, pk=None):
    jornada = get_object_or_404(Jornada, pk=pk) if pk else Jornada(fecha=timezone.localdate())
    if request.method == 'POST':
        form = JornadaForm(request.POST, instance=jornada)
        if form.is_valid():
            with transaction.atomic():
                jornada = form.save()
                origen = form.cleaned_data.get('copiar_de') if not pk else None
                if origen:
                    for item in origen.carta.all():
                        ItemCarta.objects.create(jornada=jornada, variante=item.variante, precio=item.precio)
                    for promo in origen.promos.all():
                        promo.copiar_a(jornada)
            if pk:
                messages.success(request, 'Jornada actualizada.')
                return redirect('pv_cierre', pk=jornada.pk)
            messages.success(request, 'Jornada creada. Ahora armá la carta del día.')
            return redirect('pv_carta', pk=jornada.pk)
    else:
        form = JornadaForm(instance=jornada)
    return render(request, 'ventas/jornada_form.html', {'form': form, 'jornada': jornada if pk else None})


def pv_carta(request, pk):
    """Elegir qué se vende en la jornada, con el precio del día y (opcional) el stock que se lleva."""
    jornada = get_object_or_404(Jornada, pk=pk)
    en_carta = {i.variante_id: i for i in jornada.carta.all()}

    if request.method == 'POST':
        with transaction.atomic():
            variantes = VarianteVenta.objects.filter(activo=True, producto__activo=True) | VarianteVenta.objects.filter(
                pk__in=en_carta.keys()
            )
            for v in variantes.distinct():
                incluida = request.POST.get(f'inc_{v.pk}') == 'on'
                item = en_carta.get(v.pk)
                if not incluida:
                    if item and not LineaTicket.objects.filter(ticket__jornada=jornada, variante=v).exists():
                        item.delete()
                    continue
                precio = a_decimal(request.POST.get(f'precio_{v.pk}'), v.precio_referencia)
                stock_txt = (request.POST.get(f'stock_{v.pk}') or '').strip()
                stock = int(stock_txt) if stock_txt.isdigit() else None
                if item:
                    item.precio, item.stock_inicial = precio, stock
                    item.save()
                else:
                    ItemCarta.objects.create(jornada=jornada, variante=v, precio=precio, stock_inicial=stock)
                if v.precio_referencia != precio:
                    v.precio_referencia = precio
                    v.save(update_fields=['precio_referencia'])
            # Promos del catálogo que se suman a la jornada
            for promo_id in request.POST.getlist('sumar_promo'):
                promo = Promo.objects.filter(pk=promo_id, jornada__isnull=True).first()
                if promo:
                    promo.copiar_a(jornada)
        messages.success(request, 'Carta guardada.')
        if request.POST.get('ir_a_caja'):
            return redirect('pv_caja', pk=jornada.pk)
        return redirect('pv_carta', pk=jornada.pk)

    categorias = []
    for cat in CategoriaVenta.objects.prefetch_related('productos__variantes'):
        productos = []
        for prod in cat.productos.all():
            variantes = [v for v in prod.variantes.all() if (v.activo and prod.activo) or v.pk in en_carta]
            if not variantes:
                continue
            productos.append({'producto': prod, 'variantes': [
                {'variante': v, 'item': en_carta.get(v.pk)} for v in variantes
            ]})
        if productos:
            categorias.append({'categoria': cat, 'productos': productos})

    return render(request, 'ventas/carta.html', {
        'jornada': jornada,
        'categorias': categorias,
        'promos_dia': jornada.promos.prefetch_related('componentes__variante__producto'),
        'promos_catalogo': Promo.objects.filter(jornada__isnull=True, activo=True)
                                        .prefetch_related('componentes__variante__producto'),
    })


# ======================================================================
# CAJA
# ======================================================================

def pv_caja(request, pk):
    jornada = get_object_or_404(Jornada, pk=pk)
    if not jornada.carta.exists() and not jornada.promos.exists():
        messages.warning(request, 'Antes de vender, cargá la carta del día.')
        return redirect('pv_carta', pk=jornada.pk)

    puerto = request.get_port()
    ruta_caja = reverse('pv_caja', args=[jornada.pk])
    direcciones = [{
        **d,
        'url': f"http://{d['ip']}:{puerto}{ruta_caja}",
        'url_ping': f"http://{d['ip']}:{puerto}{reverse('pv_ping')}",
        'qr': qr_svg(f"http://{d['ip']}:{puerto}{ruta_caja}"),
    } for d in ips_en_la_red()]

    return render(request, 'ventas/caja.html', {
        'jornada': jornada,
        'carta': carta_para_caja(jornada),
        'totales': jornada.totales(),
        'cantidad_tickets': jornada.tickets_validos().count(),
        'direcciones': direcciones,
        'variantes_carta': [
            {'id': i.variante_id, 'nombre': i.variante.nombre_completo}
            for i in jornada.carta.select_related('variante__producto')
        ],
    })


def pv_ping(request):
    """Respuesta mínima para comprobar desde el navegador si una dirección de la red llega a este sistema."""
    respuesta = JsonResponse({'ok': True})
    respuesta['Access-Control-Allow-Origin'] = '*'
    return respuesta


@require_POST
def pv_api_ticket(request, pk):
    """Guarda un ticket enviado por la caja. Recibe JSON:
    {caja, lineas: [{tipo: 'variante'|'promo', id, cantidad, precio}], efectivo, qr}
    """
    jornada = get_object_or_404(Jornada, pk=pk)
    if not jornada.abierta:
        return json_error('La jornada está cerrada. Reabrila para seguir vendiendo.')
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_error('Datos inválidos.')

    lineas_ok = []
    variantes = {i.variante_id: i.variante for i in jornada.carta.select_related('variante__producto')}
    promos = {p.id: p for p in jornada.promos.all()}
    for linea in datos.get('lineas', []):
        try:
            cantidad = int(linea.get('cantidad', 0))
            obj_id = int(linea.get('id'))
        except (TypeError, ValueError):
            return json_error('Línea inválida.')
        precio = a_decimal(linea.get('precio'))
        if cantidad <= 0 or precio is None or precio < 0:
            return json_error('Cantidad o precio inválido.')
        if linea.get('tipo') == 'variante' and obj_id in variantes:
            v = variantes[obj_id]
            lineas_ok.append(dict(variante=v, descripcion=v.nombre_completo, cantidad=cantidad, precio_unitario=precio))
        elif linea.get('tipo') == 'promo' and obj_id in promos:
            p = promos[obj_id]
            lineas_ok.append(dict(promo=p, descripcion=p.nombre, cantidad=cantidad, precio_unitario=precio))
        else:
            return json_error('Hay un producto que no está en la carta de esta jornada. Recargá la caja.')
    if not lineas_ok:
        return json_error('El ticket está vacío.')

    total = sum(l['cantidad'] * l['precio_unitario'] for l in lineas_ok)
    efectivo = a_decimal(datos.get('efectivo'), Decimal('0'))
    qr = a_decimal(datos.get('qr'), Decimal('0'))
    if efectivo < 0 or qr < 0 or abs((efectivo + qr) - total) > Decimal('0.01'):
        return json_error(f'Efectivo + QR tiene que sumar el total (${total}).')

    caja = (datos.get('caja') or 'Caja 1').strip()[:30]
    with transaction.atomic():
        ultimo = jornada.tickets.aggregate(m=Max('numero'))['m'] or 0
        ticket = Ticket.objects.create(
            jornada=jornada, numero=ultimo + 1, caja=caja, total=total, pago_efectivo=efectivo, pago_qr=qr,
            usuario=request.user if request.user.is_authenticated else None,
        )
        LineaTicket.objects.bulk_create([LineaTicket(ticket=ticket, **l) for l in lineas_ok])

    totales = jornada.totales()
    return JsonResponse({
        'ok': True,
        'numero': ticket.numero,
        'stock': {str(k): v for k, v in jornada.stock_restante().items()},
        'totales': {k: float(v) for k, v in totales.items()},
        'cantidad_tickets': jornada.tickets_validos().count(),
    })


@require_POST
def pv_api_precio(request, pk):
    """Cambia el precio del día de un ítem (o promo) desde la caja. Los tickets ya cobrados no cambian."""
    jornada = get_object_or_404(Jornada, pk=pk)
    try:
        datos = json.loads(request.body)
        obj_id = int(datos.get('id'))
    except (json.JSONDecodeError, TypeError, ValueError):
        return json_error('Datos inválidos.')
    precio = a_decimal(datos.get('precio'))
    if precio is None or precio < 0:
        return json_error('Precio inválido.')
    if datos.get('tipo') == 'promo':
        promo = get_object_or_404(Promo, pk=obj_id, jornada=jornada)
        promo.precio = precio
        promo.save(update_fields=['precio'])
    else:
        item = get_object_or_404(ItemCarta, jornada=jornada, variante_id=obj_id)
        item.precio = precio
        item.save(update_fields=['precio'])
        VarianteVenta.objects.filter(pk=obj_id).update(precio_referencia=precio)
    return JsonResponse({'ok': True, 'precio': float(precio)})


@require_POST
def pv_api_promo(request, pk):
    """Crea una promo del día desde la caja. JSON: {nombre, precio, componentes: {variante_id: cantidad}, guardar_catalogo}"""
    jornada = get_object_or_404(Jornada, pk=pk)
    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Datos inválidos.')
    nombre = (datos.get('nombre') or '').strip()[:100]
    precio = a_decimal(datos.get('precio'))
    en_carta = set(jornada.carta.values_list('variante_id', flat=True))
    componentes = {}
    for vid, cant in (datos.get('componentes') or {}).items():
        try:
            vid, cant = int(vid), int(cant)
        except (TypeError, ValueError):
            continue
        if vid in en_carta and cant > 0:
            componentes[vid] = cant
    if not nombre or precio is None or not componentes:
        return json_error('Poné un nombre, un precio y al menos un producto.')

    with transaction.atomic():
        promo = Promo.objects.create(jornada=jornada, nombre=nombre, precio=precio)
        for vid, cant in componentes.items():
            ComponentePromo.objects.create(promo=promo, variante_id=vid, cantidad=cant)
        if datos.get('guardar_catalogo'):
            plantilla = Promo.objects.create(jornada=None, nombre=nombre, precio=precio)
            for vid, cant in componentes.items():
                ComponentePromo.objects.create(promo=plantilla, variante_id=vid, cantidad=cant)
    return JsonResponse({'ok': True, 'id': promo.id})


# ======================================================================
# TICKETS Y CIERRE
# ======================================================================

def pv_tickets(request, pk):
    jornada = get_object_or_404(Jornada, pk=pk)
    tickets = jornada.tickets.prefetch_related('lineas')
    return render(request, 'ventas/tickets.html', {'jornada': jornada, 'tickets': tickets})


@require_POST
def pv_ticket_anular(request, pk, numero):
    ticket = get_object_or_404(Ticket, jornada_id=pk, numero=numero)
    motivo = (request.POST.get('motivo') or '').strip()
    if not motivo:
        messages.error(request, 'Para anular un ticket hay que indicar el motivo.')
    else:
        ticket.anulado = True
        ticket.motivo_anulacion = motivo[:200]
        ticket.save(update_fields=['anulado', 'motivo_anulacion'])
        messages.success(request, f'Ticket #{numero} anulado.')
    return redirect('pv_tickets', pk=pk)


def resumen_jornada(jornada):
    vendidos = jornada.vendidos_por_variante()
    lineas = LineaTicket.objects.filter(ticket__jornada=jornada, ticket__anulado=False)
    recaudado_variante = {}
    for l in lineas.filter(variante__isnull=False):
        recaudado_variante[l.variante_id] = recaudado_variante.get(l.variante_id, 0) + l.subtotal

    productos = []
    por_categoria = {}
    for item in jornada.carta.select_related('variante__producto__categoria'):
        v = item.variante
        d = vendidos.get(v.pk, {'sueltos': 0, 'en_promos': 0})
        recaudado = recaudado_variante.get(v.pk, Decimal('0'))
        unidades = d['sueltos'] + d['en_promos']
        productos.append({
            'nombre': v.nombre_completo, 'categoria': v.producto.categoria.nombre, 'precio': item.precio,
            'sueltos': d['sueltos'], 'en_promos': d['en_promos'], 'unidades': unidades, 'recaudado': recaudado,
            'stock_inicial': item.stock_inicial,
            'sobrante': (item.stock_inicial - unidades) if item.stock_inicial is not None else None,
        })
        cat = v.producto.categoria.nombre
        por_categoria[cat] = por_categoria.get(cat, Decimal('0')) + recaudado

    promos = []
    for p in jornada.promos.all():
        q = lineas.filter(promo=p)
        cantidad = q.aggregate(c=Sum('cantidad'))['c'] or 0
        recaudado = sum((l.subtotal for l in q), Decimal('0'))
        if cantidad or p.activo:
            promos.append({'nombre': p.nombre, 'detalle': p.descripcion_componentes, 'cantidad': cantidad,
                           'recaudado': recaudado})
        if recaudado:
            por_categoria['Promos'] = por_categoria.get('Promos', Decimal('0')) + recaudado

    por_caja = jornada.tickets_validos().values('caja').annotate(
        tickets=Count('id'), efectivo=Sum('pago_efectivo'), qr=Sum('pago_qr'), total=Sum('total'),
    ).order_by('caja')

    return {
        'totales': jornada.totales(),
        'cantidad_tickets': jornada.tickets_validos().count(),
        'anulados': jornada.tickets.filter(anulado=True).count(),
        'productos': productos,
        'promos': promos,
        'por_categoria': sorted(por_categoria.items(), key=lambda x: -x[1]),
        'por_caja': list(por_caja),
        'hay_stock': any(p['stock_inicial'] is not None for p in productos),
    }


def pv_cierre(request, pk):
    jornada = get_object_or_404(Jornada, pk=pk)
    return render(request, 'ventas/cierre.html', {'jornada': jornada, **resumen_jornada(jornada)})


@require_POST
def pv_jornada_estado(request, pk):
    jornada = get_object_or_404(Jornada, pk=pk)
    jornada.estado = 'cerrada' if jornada.abierta else 'abierta'
    jornada.save(update_fields=['estado'])
    messages.success(request, 'Jornada cerrada.' if not jornada.abierta else 'Jornada reabierta: se puede volver a vender.')
    return redirect('pv_cierre', pk=pk)


@require_POST
def pv_registrar_evento(request, pk):
    """Crea (o actualiza) el evento 'Punto de Venta' en la Agenda con el total vendido."""
    jornada = get_object_or_404(Jornada, pk=pk)
    total = jornada.totales()['total']
    tipo = TipoServicio.objects.filter(nombre__iexact='Punto de Venta').first() or \
        TipoServicio.objects.create(nombre='Punto de Venta')
    evento = jornada.evento
    if evento is None:
        evento = Evento(
            nombre=f'Punto de Venta - {jornada.nombre}'[:200], tipo_servicio=tipo, periodo=periodo_para_fecha(jornada.fecha),
            fecha=jornada.fecha, cliente=jornada.nombre[:200], origen='interno', estado_evento='realizado',
            estado_facturacion='cobrado',
        )
    evento.precio_facturado = total
    evento.importado_automaticamente = False
    evento.save()
    if jornada.evento_id != evento.pk:
        jornada.evento = evento
        jornada.save(update_fields=['evento'])
    messages.success(request, f'Se registró el total vendido en la Agenda ({evento}).')
    return redirect('pv_cierre', pk=pk)


# ======================================================================
# CATÁLOGO
# ======================================================================

def pv_catalogo(request):
    categorias = CategoriaVenta.objects.prefetch_related('productos__variantes')
    return render(request, 'ventas/catalogo.html', {
        'categorias': categorias,
        'promos': Promo.objects.filter(jornada__isnull=True).prefetch_related('componentes__variante__producto'),
    })


def pv_producto_form(request, pk=None):
    """Alta/edición de producto con sus variantes. Con ?jornada=ID, al guardar lo suma a esa carta."""
    producto = get_object_or_404(ProductoVenta, pk=pk) if pk else ProductoVenta()
    jornada = Jornada.objects.filter(pk=request.GET.get('jornada') or None).first()
    if request.method == 'POST':
        form = ProductoVentaForm(request.POST, instance=producto)
        formset = VarianteFormSet(request.POST, instance=producto)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                producto = form.save()
                formset.instance = producto
                variantes = formset.save()
                for orden, f in enumerate(formset.forms):
                    if f.instance.pk and f not in formset.deleted_forms:
                        VarianteVenta.objects.filter(pk=f.instance.pk).update(orden=orden)
                if jornada:
                    for v in variantes:
                        ItemCarta.objects.get_or_create(jornada=jornada, variante=v,
                                                        defaults={'precio': v.precio_referencia})
            messages.success(request, f'"{producto}" guardado.')
            if jornada:
                return redirect('pv_carta', pk=jornada.pk)
            return redirect('pv_catalogo')
    else:
        form = ProductoVentaForm(instance=producto)
        formset = VarianteFormSet(instance=producto)
    return render(request, 'ventas/producto_form.html', {
        'form': form, 'formset': formset, 'editando': pk is not None, 'jornada': jornada,
    })


def pv_promo_form(request, pk=None):
    """Promo de catálogo (o del día, con ?jornada=ID)."""
    promo = get_object_or_404(Promo, pk=pk) if pk else Promo()
    jornada = promo.jornada if pk else Jornada.objects.filter(pk=request.GET.get('jornada') or None).first()
    if request.method == 'POST':
        form = PromoForm(request.POST, instance=promo)
        formset = ComponenteFormSet(request.POST, instance=promo)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                promo = form.save(commit=False)
                promo.jornada = jornada
                promo.save()
                formset.instance = promo
                formset.save()
            messages.success(request, f'Promo "{promo}" guardada.')
            return redirect('pv_carta', pk=jornada.pk) if jornada else redirect('pv_catalogo')
    else:
        form = PromoForm(instance=promo)
        formset = ComponenteFormSet(instance=promo)
    return render(request, 'ventas/promo_form.html', {
        'form': form, 'formset': formset, 'editando': pk is not None, 'jornada': jornada,
    })
