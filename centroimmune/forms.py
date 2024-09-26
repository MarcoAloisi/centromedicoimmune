from django import forms
from .models import Tratamiento, Cita, PersonalMedico
from django.utils import timezone
from django.core.exceptions import ValidationError

class SolicitarCitaForm(forms.ModelForm):
    fecha = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='Fecha y Hora'
    )
    tratamiento = forms.ModelChoiceField(
        queryset=Tratamiento.objects.all(),
        label='Tratamiento'
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Motivo de la cita',
        required=False
    )
    personal_medico = forms.ModelChoiceField(
        queryset=PersonalMedico.objects.all(),
        label='Personal Médico'
    )

    class Meta:
        model = Cita
        fields = ['fecha', 'tratamiento', 'personal_medico', 'motivo']

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha < timezone.now():
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
            if overlapping_citas.exists():
                raise ValidationError('El personal médico seleccionado no está disponible en la fecha y hora seleccionadas.')
