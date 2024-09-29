from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import RegexValidator, ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth.base_user import BaseUserManager
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField
from django.utils import timezone
import re

# Validadores
def validate_dni_nie(value):
    value = value.upper()
    dni_nie_regex = re.compile(r'^([XYZ]\d{7}[A-Z]|\d{8}[A-Z])$')
    
    if not dni_nie_regex.match(value):
        raise ValidationError(_('El DNI o NIE debe tener 8 números seguidos de una letra mayúscula para DNI, o una letra inicial (X, Y, Z) seguida de 7 números y una letra mayúscula para NIE.'))
    
    # Convertir NIE a un número similar al formato de DNI
    if value[0] == 'X':
        value_num = '0' + value[1:]
    elif value[0] == 'Y':
        value_num = '1' + value[1:]
    elif value[0] == 'Z':
        value_num = '2' + value[1:]
    else:
        value_num = value
    
    # Letras de control para los DNIs/NIEs
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    numero = int(value_num[:-1])
    letra_correcta = letras[numero % 23]
    
    if letra_correcta != value_num[-1]:
        raise ValidationError(_('La letra del DNI o NIE no es válida.'))

def validate_phone(value):
    phone_regex = re.compile(r'^\d{9}$')
    if not phone_regex.match(value):
        raise ValidationError(_('El número de teléfono debe tener 9 dígitos.'))


class UserManager(BaseUserManager):
    def create_user(self, correo_electronico, password=None, **extra_fields):
        """
        Crea y guarda un usuario con el correo electrónico y la contraseña proporcionados.
        """
        if not correo_electronico:
            raise ValueError('El correo electrónico debe ser proporcionado')
        correo_electronico = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo_electronico, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_electronico, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el correo electrónico y la contraseña proporcionados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        if extra_fields.get('rol') != 'admin':
            raise ValueError('El superusuario debe tener rol de admin.')

        return self.create_user(correo_electronico, password, **extra_fields)
    
# Modelo de Usuario Personalizado para Manejar Diferentes Tipos de Usuarios
class User(AbstractUser):
    username = None

    correo_electronico = models.EmailField(unique=True)

    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = []

    class Roles(models.TextChoices):
        ADMIN = 'admin', _('Administrador')
        MEDICO = 'medico', _('Personal Médico')
        PACIENTE = 'paciente', _('Paciente')

    rol = models.CharField(max_length=10, choices=Roles.choices)

    # Relación con grupos y permisos personalizados
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

    objects = UserManager()

    def __str__(self):
        return f"{self.correo_electronico} ({self.get_rol_display()})"

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
    dni = models.CharField(max_length=9, unique=True, validators=[validate_dni_nie])
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(
        max_length=10,
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')]
    )
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(validators=[validate_phone], max_length=17)
    correo_electronico = models.EmailField(unique=True)
    historial_medico = EncryptedTextField(blank=True, null=True)
    informacion_seguro = EncryptedCharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos} (DNI: {self.dni})"

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

# Modelo para Personal Médico
class PersonalMedico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medico_profile')
    dni = models.CharField(max_length=9, unique=True, validators=[validate_dni_nie])
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50)
    rol = models.CharField(max_length=50, choices=[
        ('Doctor', 'Doctor'),
        ('Enfermero', 'Enfermero'),
        ('Tecnico', 'Técnico'),
    ])
    especializacion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(validators=[validate_phone], max_length=17)
    correo_electronico = models.EmailField(unique=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    licencia = models.CharField(max_length=100, blank=True, null=True)
    certificaciones = models.ManyToManyField(Certificacion, blank=True, related_name='personal_medico')

    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.get_rol_display()}"

    class Meta:
        verbose_name = "Personal Médico"
        verbose_name_plural = "Personal Médico"


# Modelo para Tratamientos
class Tratamiento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.costo <= 0:
            raise ValidationError({'costo': 'El costo debe ser un valor positivo.'})

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
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.SET_NULL, null=True,blank=True, related_name='citas')
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
