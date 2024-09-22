from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Paciente, PersonalMedico, Tratamiento, Cita, ConsentimientoInformado, Factura

# Registro del Modelo Personalizado de Usuario
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('rol',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')

admin.site.register(User, UserAdmin)

# Registro de otros Modelos con Personalización
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'dni', 'correo_electronico', 'telefono', 'fecha_registro')
    search_fields = ('nombre', 'apellidos', 'dni', 'correo_electronico')
    list_filter = ('genero', 'fecha_registro')

@admin.register(PersonalMedico)
class PersonalMedicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'rol', 'dni', 'correo_electronico', 'telefono', 'fecha_contratacion')
    search_fields = ('nombre', 'apellidos', 'dni', 'correo_electronico', 'rol')
    list_filter = ('rol', 'fecha_contratacion')

@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'costo', 'duracion')
    search_fields = ('nombre', 'categoria')
    list_filter = ('categoria',)

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'personal_medico', 'fecha', 'tratamiento', 'estado')
    search_fields = ('paciente__nombre', 'personal_medico__nombre', 'tratamiento__nombre')
    list_filter = ('estado', 'fecha')
    date_hierarchy = 'fecha'

@admin.register(ConsentimientoInformado)
class ConsentimientoInformadoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tratamiento', 'personal_medico', 'firmado', 'fecha_firma')
    search_fields = ('paciente__nombre', 'tratamiento__nombre', 'personal_medico__nombre')
    list_filter = ('firmado', 'fecha_firma')

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'paciente', 'monto', 'pagado', 'fecha_emision', 'fecha_pago')
    search_fields = ('numero_factura', 'paciente__nombre', 'paciente__apellidos')
    list_filter = ('pagado', 'fecha_emision')
    readonly_fields = ('numero_factura',)

# TODO