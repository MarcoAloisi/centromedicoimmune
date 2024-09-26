from django import forms
from .models import Cita, Tratamiento, PersonalMedico
from django.utils import timezone
from django.core.exceptions import ValidationError

class CitaForm(forms.ModelForm):
    fecha = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='Fecha y Hora'
    )
    tratamiento = forms.ModelChoiceField(
        queryset=Tratamiento.objects.all(),
        label='Tratamiento'
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
        fields = ['fecha', 'tratamiento', 'personal_medico', 'motivo']

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