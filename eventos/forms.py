from django import forms
from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nombre', 'tipo', 'periodo', 'origen', 'fecha', 'costo', 'precio_facturado', 'estado_facturacion', 'cantidad_personas_celiaco']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'periodo': forms.Select(attrs={'class': 'form-select'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_facturado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado_facturacion': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_personas_celiaco': forms.NumberInput(attrs={'class': 'form-control'}),
        }

from django.forms import inlineformset_factory
from .models import Presupuesto, OpcionMenu


class EventoPresupuestoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['tipo_servicio', 'solicitante', 'cliente', 'origen', 'fecha', 'cantidad_personas', 'observaciones']
        widgets = {
            'tipo_servicio': forms.Select(attrs={'class': 'form-select'}),
            'solicitante': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Quién lo solicita'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organismo o cliente'}),
            'origen': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cantidad_personas': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Estimado (se ajusta solo al cargar el presupuesto)'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas rápidas sobre el pedido'}),
        }


class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['lugar', 'extras_incluidos', 'otros_extras',
                  'cantidad_regular', 'cantidad_vegetariano', 'cantidad_celiaco', 'observaciones']
        widgets = {
            'lugar': forms.TextInput(attrs={'class': 'form-control'}),
            'extras_incluidos': forms.CheckboxSelectMultiple(),
            'otros_extras': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'cantidad_regular': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_vegetariano': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_celiaco': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


OpcionMenuFormSet = inlineformset_factory(
    Presupuesto, OpcionMenu,
    fields=['nombre', 'detalle_menu', 'precio_regular', 'precio_vegetariano', 'precio_celiaco', 'orden'],
    widgets={
        'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Opción 1'}),
        'detalle_menu': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Un plato por línea'}),
        'precio_regular': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'precio_vegetariano': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'precio_celiaco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'orden': forms.NumberInput(attrs={'class': 'form-control'}),
    },
    extra=3, can_delete=True
)

from .models import InformeGestion


class InformeGestionForm(forms.ModelForm):
    class Meta:
        model = InformeGestion
        fields = [
            'presupuesto_asignado', 'servicios_adicionales_horas_extra',
            'resumen_ejecutivo', 'objetivos', 'logros_destacados', 'desafios_proximo_periodo',
        ]
        widgets = {
            'presupuesto_asignado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'servicios_adicionales_horas_extra': forms.NumberInput(attrs={'class': 'form-control'}),
            'resumen_ejecutivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'objetivos': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logros_destacados': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'desafios_proximo_periodo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

from .models import Integrante, FuncionActividad


class IntegranteForm(forms.ModelForm):
    class Meta:
        model = Integrante
        fields = ['nombre', 'cargo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FuncionActividadForm(forms.ModelForm):
    class Meta:
        model = FuncionActividad
        fields = ['numero', 'descripcion', 'responsables']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsables': forms.CheckboxSelectMultiple(),
        }

from .models import Producto, Compra, ItemCompra


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'unidad_medida', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['fecha', 'proveedor', 'evento', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


ItemCompraFormSet = inlineformset_factory(
    Compra, ItemCompra,
    fields=['producto', 'cantidad', 'total_pagado'],
    widgets={
        'producto': forms.Select(attrs={'class': 'form-select item-producto'}),
        'cantidad': forms.NumberInput(attrs={'class': 'form-control item-cantidad', 'step': '0.001'}),
        'total_pagado': forms.NumberInput(attrs={'class': 'form-control item-total', 'step': '0.01'}),
    },
    extra=3, can_delete=True
)