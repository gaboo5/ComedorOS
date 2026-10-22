from datetime import timedelta

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from eventos.models import Evento

from .models import CategoriaVenta, ComponentePromo, Jornada, ProductoVenta, Promo, VarianteVenta
from .utils import CampoMonto


class JornadaForm(forms.ModelForm):
    copiar_de = forms.ModelChoiceField(
        queryset=Jornada.objects.all(), required=False, label='Copiar la carta de',
        empty_label='— Empezar con la carta vacía —',
        help_text='Trae los productos, precios y promos de esa jornada para que solo ajustes lo que cambió.',
    )

    class Meta:
        model = Jornada
        fields = ['fecha', 'nombre', 'evento', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Peña Día del Estudiante — Gazebo'}),
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {'evento': 'Evento de la Agenda (opcional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['copiar_de'].widget.attrs['class'] = 'form-select'
        hoy = timezone.localdate()
        # Solo eventos cercanos, para que la lista no sea eterna.
        self.fields['evento'].queryset = Evento.objects.filter(
            fecha__gte=hoy - timedelta(days=30), fecha__lte=hoy + timedelta(days=90),
        ).select_related('tipo_servicio').order_by('fecha')
        if self.instance.pk:
            del self.fields['copiar_de']
            if self.instance.evento_id:
                self.fields['evento'].queryset |= Evento.objects.filter(pk=self.instance.evento_id)


class ProductoVentaForm(forms.ModelForm):
    nueva_categoria = forms.CharField(
        required=False, label='…o crear una categoría nueva',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Peña'}),
    )

    class Meta:
        model = ProductoVenta
        fields = ['nombre', 'categoria', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cono de papas', 'autofocus': True}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False

    def clean(self):
        datos = super().clean()
        nueva = (datos.get('nueva_categoria') or '').strip()
        if nueva:
            datos['categoria'], _ = CategoriaVenta.objects.get_or_create(
                nombre__iexact=nueva, defaults={'nombre': nueva},
            )
            self.instance.categoria = datos['categoria']
        elif not datos.get('categoria'):
            self.add_error('categoria', 'Elegí una categoría o escribí una nueva.')
        return datos


class VarianteForm(forms.ModelForm):
    precio_referencia = CampoMonto(label='Precio', min_value=0)

    class Meta:
        model = VarianteVenta
        fields = ['nombre', 'precio_referencia', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Grande (vacío si es único)'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {'nombre': 'Tamaño / opción', 'precio_referencia': 'Precio'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['precio_referencia'] = None   # que arranque vacío y no en 0
            self.fields['precio_referencia'].widget.attrs['placeholder'] = 'Ej: 3500'


VarianteFormSet = inlineformset_factory(
    ProductoVenta, VarianteVenta, form=VarianteForm, extra=1, can_delete=True, min_num=1, validate_min=True,
)


class PromoForm(forms.ModelForm):
    precio = CampoMonto(label='Precio de la promo', min_value=0)

    class Meta:
        model = Promo
        fields = ['nombre', 'precio', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Hamburguesa + vaso de gaseosa'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ComponenteForm(forms.ModelForm):
    class Meta:
        model = ComponentePromo
        fields = ['variante', 'cantidad']
        widgets = {
            'variante': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
        labels = {'variante': 'Incluye'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['variante'].queryset = VarianteVenta.objects.filter(
            activo=True, producto__activo=True,
        ).select_related('producto')
        self.fields['variante'].label_from_instance = lambda v: v.nombre_completo


ComponenteFormSet = inlineformset_factory(
    Promo, ComponentePromo, form=ComponenteForm, extra=2, can_delete=True, min_num=1, validate_min=True,
)
