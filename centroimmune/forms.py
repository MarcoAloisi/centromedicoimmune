# forms.py

from django import forms
from .models import Cita, Tratamiento, PersonalMedico
from django.utils import timezone
from django.core.exceptions import ValidationError

class SolicitarCitaForm(forms.ModelForm):
    fecha = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'min': timezone.now().isoformat()}),
        label='Fecha y Hora'
    )
    personal_medico = forms.ModelChoiceField(
        queryset=PersonalMedico.objects.all(),
        label='Médico'
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Motivo de la cita',
        required=False
    )

    class Meta:
        model = Cita
        fields = ['fecha', 'personal_medico', 'motivo']

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < timezone.now():
            raise ValidationError('La fecha de la cita no puede ser en el pasado.')
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        personal_medico = cleaned_data.get('personal_medico')
        if fecha and personal_medico:
            overlapping_citas = Cita.objects.filter(
                personal_medico=personal_medico,
                fecha=fecha
            )
            if self.instance.pk:
                overlapping_citas = overlapping_citas.exclude(pk=self.instance.pk)
            if overlapping_citas.exists():
                raise ValidationError('El médico seleccionado no está disponible en la fecha y hora seleccionadas.')


class AsignarTratamientoForm(forms.ModelForm):
    class Meta:
        model = Tratamiento
        fields = ['nombre', 'descripcion', 'costo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
 
        }
        labels = {
            'nombre': 'Nombre del Tratamiento',
            'descripcion': 'Descripción del Tratamiento',
            'costo': 'Costo',
        }

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo <= 0:
            raise forms.ValidationError('El costo debe ser un valor positivo.')
        return costo
