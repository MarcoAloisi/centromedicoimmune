from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import RegexValidator, ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from fernet_fields import EncryptedTextField
from django.utils import timezone
import re

# Validadores
phone_regex = RegexValidator(
    regex=r'^\+?34?\d{9}$',  # Formato español: +34 seguido de 9 dígitos
    message=_("El número de teléfono debe estar en el formato: '+34912345678'. Total de 9 dígitos.")
)

def validate_dni(value):
    dni_regex = re.compile(r'^\d{8}[A-Z]$')
    if not dni_regex.match(value):
        raise ValidationError(_('El DNI debe tener 8 números seguidos de una letra mayúscula.'))
    # Validar la letra del DNI
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    numero = int(value[:8])
    letra = value[8]
    if letras[numero % 23] != letra:
        raise ValidationError(_('La letra del DNI no es válida.'))

# Modelo de Usuario Personalizado para Manejar Diferentes Tipos de Usuarios
class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'admin', _('Administrador')
        MEDICO = 'medico', _('Personal Médico')
        PACIENTE = 'paciente', _('Paciente')

    rol = models.CharField(max_length=10, choices=Roles.choices)

    # Añadir related_name personalizado para evitar conflictos
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',
        blank=True,
        help_text=_('Los grupos a los que pertenece este usuario. Un usuario obtendrá todos los permisos otorgados a cada uno de sus grupos.'),
        verbose_name=_('grupos'),
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text=_('Permisos específicos para este usuario.'),
        verbose_name=_('permisos de usuario'),
    )

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"

# Modelo para Certificaciones (normalizado)
class Certificacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Certificación"
        verbose_name_plural = "Certificaciones"

# Modelo para Pacientes
class Paciente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='paciente_profile')
    dni = models.CharField(max_length=9, unique=True, validators=[validate_dni])
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
    historial_medico = EncryptedTextField(blank=True, null=True)
    informacion_seguro = EncryptedTextField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos} (DNI: {self.dni})"

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

# Modelo para Personal Médico
class PersonalMedico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medico_profile')
    dni = models.CharField(max_length=9, unique=True, validators=[validate_dni])
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
    certificaciones = models.ManyToManyField(Certificacion, blank=True, related_name='personal_medico')

    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.get_rol_display()}"

    class Meta:
        verbose_name = "Personal Médico"
        verbose_name_plural = "Personal Médico"

# Modelo para Categorías de Tratamientos
class CategoriaTratamiento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría de Tratamiento"
        verbose_name_plural = "Categorías de Tratamientos"

# Modelo para Tratamientos
class Tratamiento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(CategoriaTratamiento, on_delete=models.SET_NULL, null=True, blank=True, related_name='tratamientos')
    duracion = models.DurationField(null=True, blank=True)

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.costo <= 0:
            raise ValidationError({'costo': 'El costo debe ser un valor positivo.'})
        if self.duracion and self.duracion.total_seconds() <= 0:
            raise ValidationError({'duracion': 'La duración debe ser un valor positivo.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"

# Modelo para Citas
class Cita(models.Model):
    class EstadosCita(models.TextChoices):
        PROGRAMADA = 'Programada', _('Programada')
        COMPLETADA = 'Completada', _('Completada')
        CANCELADA = 'Cancelada', _('Cancelada')
        NOSHOW = 'No Show', _('No Show')
        REAGENDADA = 'Reagendada', _('Reagendada')

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    personal_medico = models.ForeignKey(PersonalMedico, on_delete=models.CASCADE, related_name='citas')
    fecha = models.DateTimeField()
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.SET_NULL, null=True, related_name='citas')
    estado = models.CharField(max_length=20, choices=EstadosCita.choices, default=EstadosCita.PROGRAMADA)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cita de {self.paciente} con {self.personal_medico} el {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    def clean(self):
        # Validar que la fecha de la cita no sea en el pasado
        if self.fecha < timezone.now():
            raise ValidationError({'fecha': 'La fecha de la cita no puede ser en el pasado.'})

        # Validar que el personal médico esté disponible en la fecha y hora
        overlapping_citas = Cita.objects.filter(
            personal_medico=self.personal_medico,
            fecha=self.fecha
        ).exclude(id=self.id)
        if overlapping_citas.exists():
            raise ValidationError('El personal médico ya tiene una cita programada en este horario.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha']

# Modelo para Consentimiento Informado
class ConsentimientoInformado(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consentimientos')
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, related_name='consentimientos')
    texto_consentimiento = EncryptedTextField()
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
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='factura')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    numero_factura = models.CharField(max_length=20, unique=True, editable=False)

    def __str__(self):
        return f"Factura #{self.numero_factura} para {self.paciente} - {self.monto} el {self.fecha_emision.strftime('%d/%m/%Y')}"

    def clean(self):
        if self.monto <= 0:
            raise ValidationError({'monto': 'El monto debe ser positivo.'})
        if self.fecha_pago and self.fecha_pago < self.fecha_emision:
            raise ValidationError({'fecha_pago': 'La fecha de pago no puede ser anterior a la fecha de emisión.'})

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            last_factura = Factura.objects.order_by('-id').first()
            if last_factura and last_factura.numero_factura:
                last_num = int(last_factura.numero_factura.split('-')[1])
            else:
                last_num = 0
            self.numero_factura = f"FAC-{last_num + 1:06d}"
        if self.fecha_pago and not self.pagado:
            self.pagado = True
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-fecha_emision']
