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