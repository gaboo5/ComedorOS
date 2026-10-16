"""Filtros y tags propios para los templates de ComedorOS.

Están registrados como 'builtins' en settings.py, así que se pueden usar en cualquier
template sin poner {% load formatos %}.
"""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def formato_moneda_ar(valor):
    """Formatea un número al estilo argentino: punto para miles, coma para decimales."""
    texto = f"{valor:,.2f}"
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


@register.filter
def moneda(valor):
    """{{ importe|moneda }} -> $1.234.567,89  (o '-' si no hay valor)."""
    if valor is None or valor == '':
        return '-'
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return valor
    signo = '-' if numero < 0 else ''
    return f"{signo}${formato_moneda_ar(abs(numero))}"


# Prefijos de nombres de URL que corresponden a cada ítem del menú lateral.
@register.simple_tag(takes_context=True)
def nav_activo(context, *prefijos):
    """Devuelve 'active' si la página actual pertenece a esa sección del menú.

    Uso: <a class="nav-link {% nav_activo 'agenda' 'evento_' %}" ...>
    """
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    nombre = getattr(match, 'url_name', '') or ''
    return 'active' if any(nombre.startswith(p) for p in prefijos) else ''
