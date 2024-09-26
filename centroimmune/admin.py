from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

from .models import (
    User,
    Paciente,
    PersonalMedico,
    Tratamiento,
    Cita,
    ConsentimientoInformado,
    Factura,
    Certificacion,
)

# Registro del Modelo Personalizado de Usuario
class UserAdmin(BaseUserAdmin):
    list_display = ('correo_electronico', 'get_nombre', 'get_apellidos', 'rol', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('correo_electronico', 'password')}),
        (_('Permisos'), {'fields': ('rol', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Fechas importantes'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo_electronico', 'rol', 'password1', 'password2'),
        }),
    )
    search_fields = ('correo_electronico',)
    ordering = ('correo_electronico',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_nombre(self, obj):
        if obj.rol == 'paciente' and hasattr(obj, 'paciente_profile'):
            return obj.paciente_profile.nombre
        elif obj.rol == 'medico' and hasattr(obj, 'medico_profile'):
            return obj.medico_profile.nombre
        return '-'

    def get_apellidos(self, obj):
        if obj.rol == 'paciente' and hasattr(obj, 'paciente_profile'):
            return obj.paciente_profile.apellidos
        elif obj.rol == 'medico' and hasattr(obj, 'medico_profile'):
            return obj.medico_profile.apellidos
        return '-'

    get_nombre.short_description = 'Nombre'
    get_apellidos.short_description = 'Apellidos'

admin.site.register(User, UserAdmin)

# Registro de Certificaciones
@admin.register(Certificacion)
class CertificacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


# Registro de Pacientes
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'dni', 'correo_electronico', 'telefono', 'fecha_registro')
    search_fields = ('nombre', 'apellidos', 'dni', 'correo_electronico')
    list_filter = ('genero', 'fecha_registro')

# Registro de Personal Médico
@admin.register(PersonalMedico)
class PersonalMedicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'rol', 'dni', 'correo_electronico', 'telefono', 'fecha_contratacion')
    search_fields = ('nombre', 'apellidos', 'dni', 'correo_electronico', 'rol')
    list_filter = ('rol', 'fecha_contratacion')
    filter_horizontal = ('certificaciones',)

# Registro de Tratamientos
@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'costo')  # Muestra las columnas en la lista
    search_fields = ('nombre',)  # Permite buscar por nombre
    list_filter = ('costo',)  # Agrega un filtro por costo
    ordering = ('nombre',)  # Ordena la lista por nombre ascendente
    list_editable = ('costo',)  # Permite editar el costo directamente desde la lista
    fieldsets = (
        (None, {
            'fields': ('nombre', 'descripcion', 'costo')
        }),
    )  # Organiza los campos en el formulario de edición

    def descripcion_corta(self, obj):
        return obj.descripcion[:50] + "..." if len(obj.descripcion) > 50 else obj.descripcion

    descripcion_corta.short_description = 'Descripción Corta'

    list_display_links = ('nombre',)  # Hace que solo el nombre sea un enlace para editar

# Registro de Citas
@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'personal_medico', 'fecha', 'tratamiento', 'estado')
    search_fields = ('paciente__nombre', 'personal_medico__nombre', 'tratamiento__nombre')
    list_filter = ('estado', 'fecha')
    date_hierarchy = 'fecha'

# Registro de Consentimientos Informados
@admin.register(ConsentimientoInformado)
class ConsentimientoInformadoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tratamiento', 'personal_medico', 'firmado', 'fecha_firma')
    search_fields = ('paciente__nombre', 'tratamiento__nombre', 'personal_medico__nombre')
    list_filter = ('firmado', 'fecha_firma')

# Registro de Facturas
@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'paciente', 'monto', 'pagado', 'fecha_emision', 'fecha_pago')
    search_fields = ('numero_factura', 'paciente__nombre', 'paciente__apellidos')
    list_filter = ('pagado', 'fecha_emision')
    readonly_fields = ('numero_factura',)
