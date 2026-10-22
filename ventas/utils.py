import re
from decimal import Decimal, InvalidOperation

from django import forms


def a_decimal(valor, por_defecto=None):
    """Convierte lo que escribe el usuario ('3500', '3.500', '3500,50') a Decimal."""
    if valor is None:
        return por_defecto
    texto = str(valor).strip().replace('$', '').replace(' ', '')
    if not texto:
        return por_defecto
    if ',' in texto:  # formato argentino: 3.500,50
        texto = texto.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+', texto):  # '4.200' es cuatro mil doscientos, no 4,2
        texto = texto.replace('.', '')
    try:
        return Decimal(texto)
    except InvalidOperation:
        return por_defecto


class CampoMonto(forms.DecimalField):
    """DecimalField que entiende cómo escribimos los precios: '4.200', '4200', '4.200,50', '$ 4200'."""
    widget = forms.TextInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 10)
        kwargs.setdefault('decimal_places', 2)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        normalizado = a_decimal(value)
        return super().to_python(str(normalizado) if normalizado is not None else value)

    def prepare_value(self, value):
        # Mostrar 4200 en vez de 4200.00 al editar
        if isinstance(value, Decimal) and value == value.to_integral_value():
            return str(value.quantize(Decimal('1')))
        return super().prepare_value(value)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs.pop('step', None)
        attrs.update({'inputmode': 'decimal', 'class': 'form-control'})
        return attrs
