from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

# Validadores
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message=_("El número de teléfono debe estar en el formato: '+999999999'. Hasta 15 dígitos permitidos.")
)

# Modelo de Usuario Personalizado para Manejar Diferentes Tipos de Usuarios
class User(AbstractUser):
    USER_ROLES = (
        ('admin', 'Administrador'),
        ('medico', 'Personal Médico'),
        ('paciente', 'Paciente'),
    )
    rol = models.CharField(max_length=10, choices=USER_ROLES)

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"

# Modelo para Pacientes
class Paciente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='paciente_profile')
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(
        max_length=10,
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')]
    )
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(validators=[phone_regex], max_length=17)
    correo_electronico = models.EmailField(unique=True)
    historial_medico = models.TextField(blank=True, null=True)
    informacion_seguro = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos} (DNI: {self.dni})"

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

# Modelo para Personal Médico
class PersonalMedico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medico_profile')
    dni = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50)
    rol = models.CharField(max_length=50, choices=[
        ('Doctor', 'Doctor'),
        ('Enfermero', 'Enfermero'),
        ('Tecnico', 'Técnico'),
        # Agrega más roles según sea necesario
    ])
    especializacion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(validators=[phone_regex], max_length=17)
    correo_electronico = models.EmailField(unique=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    licencia = models.CharField(max_length=100, blank=True, null=True)
    certificaciones = models.TextField(blank=True, null=True)  # Lista de certificaciones

    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.get_rol_display()}"

    class Meta:
        verbose_name = "Personal Médico"
        verbose_name_plural = "Personal Médico"

# Modelo para Tratamientos
class Tratamiento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    duracion = models.DurationField(null=True, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"

# Modelo para Citas
class Cita(models.Model):
    ESTADOS_CITA = (
        ('Programada', 'Programada'),
        ('Completada', 'Completada'),
        ('Cancelada', 'Cancelada'),
    )

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    personal_medico = models.ForeignKey(PersonalMedico, on_delete=models.CASCADE, related_name='citas')
    fecha = models.DateTimeField()
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.SET_NULL, null=True, related_name='citas')
    estado = models.CharField(max_length=20, choices=ESTADOS_CITA)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cita de {self.paciente} con {self.personal_medico} el {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha']

# Modelo para Consentimiento Informado
class ConsentimientoInformado(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consentimientos')
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, related_name='consentimientos')
    texto_consentimiento = models.TextField()
    fecha_firma = models.DateTimeField(auto_now_add=True)
    firmado = models.BooleanField(default=False)
    personal_medico = models.ForeignKey(PersonalMedico, on_delete=models.SET_NULL, null=True, related_name='consentimientos')

    def __str__(self):
        return f"Consentimiento de {self.paciente} para {self.tratamiento} el {self.fecha_firma.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = "Consentimiento Informado"
        verbose_name_plural = "Consentimientos Informados"

# Modelo para Facturación/Factura
class Factura(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='facturas')
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='facturas')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    numero_factura = models.CharField(max_length=20, unique=True, editable=False)

    def __str__(self):
        return f"Factura #{self.numero_factura} para {self.paciente} - {self.monto} el {self.fecha_emision.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            # Genera un número de factura único, por ejemplo, basado en el ID
            self.numero_factura = f"FAC-{self.id + 1:06d}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-fecha_emision']
