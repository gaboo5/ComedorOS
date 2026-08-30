from django import forms
from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nombre', 'tipo', 'periodo', 'origen', 'fecha', 'costo', 'precio_facturado', 'estado_facturacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'periodo': forms.Select(attrs={'class': 'form-select'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_facturado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado_facturacion': forms.Select(attrs={'class': 'form-select'}),
        }

from django.forms import inlineformset_factory
from .models import Presupuesto, OpcionMenu


class EventoPresupuestoForm(forms.ModelForm):
    """Datos mínimos para arrancar un presupuesto: qué servicio, para quién, cuándo."""
    class Meta:
        model = Evento
        fields = ['tipo_servicio', 'solicitante', 'cliente', 'origen', 'fecha', 'cantidad_personas']
        widgets = {
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'solicitante': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Quién lo solicita'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organismo o cliente'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cantidad_personas': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['lugar', 'extras_incluidos', 'otros_extras', 'cantidad_personas_celiaco',
                  'recargo_celiaco_por_persona', 'observaciones']
        widgets = {
            'lugar': forms.TextInput(attrs={'class': 'form-control'}),
            'extras_incluidos': forms.CheckboxSelectMultiple(),
            'otros_extras': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'cantidad_personas_celiaco': forms.NumberInput(attrs={'class': 'form-control'}),
            'recargo_celiaco_por_persona': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


OpcionMenuFormSet = inlineformset_factory(
    Presupuesto, OpcionMenu,
    fields=['nombre', 'detalle_menu', 'precio_por_persona', 'orden'],
    widgets={
        'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Opción 1'}),
        'detalle_menu': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Un plato por línea'}),
        'precio_por_persona': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'orden': forms.NumberInput(attrs={'class': 'form-control'}),
    },
    extra=3, can_delete=True
)