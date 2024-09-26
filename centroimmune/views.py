from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login
from .models import User, Paciente, Cita, PersonalMedico
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import SolicitarCitaForm, AsignarTratamientoForm


def registro(request):
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.POST.get('nombre')
        apellidos = request.POST.get('apellidos')
        dni = request.POST.get('dni')
        fecha_nacimiento = request.POST.get('fecha_nacimiento')
        genero = request.POST.get('genero')
        nacionalidad = request.POST.get('nacionalidad')
        direccion = request.POST.get('direccion')
        direccion2 = request.POST.get('direccion2')
        ciudad = request.POST.get('ciudad')
        codigo_postal = request.POST.get('codigo_postal')
        telefono = request.POST.get('telefono')
        correo_electronico = request.POST.get('correo_electronico')
        contrasena = request.POST.get('contrasena')
        confirmar_contrasena = request.POST.get('confirmar_contrasena')
        historial_medico = request.POST.get('historial_medico')
        informacion_seguro = request.POST.get('informacion_seguro')

        # Combinar dirección y dirección 2
        direccion_completa = direccion
        if direccion2:
            direccion_completa += ', ' + direccion2
        direccion_completa += ', ' + ciudad + ', ' + codigo_postal + ', ' + nacionalidad

        # Validar campos obligatorios
        campos_obligatorios = [nombre, apellidos, dni, fecha_nacimiento, genero, direccion, ciudad, codigo_postal, telefono, correo_electronico, contrasena, confirmar_contrasena]
        if not all(campos_obligatorios):
            messages.error(request, 'Por favor, completa todos los campos obligatorios.')
            return render(request, 'registro.html')

        # Verificar si las contraseñas coinciden
        if contrasena != confirmar_contrasena:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'registro.html')

        # Validar la seguridad de la contraseña
        try:
            validate_password(contrasena)
        except DjangoValidationError as e:
            messages.error(request, f'Error en la contraseña: {e}')
            return render(request, 'registro.html')

        # Verificar si el correo electrónico o DNI ya existen
        if User.objects.filter(correo_electronico=correo_electronico).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return render(request, 'registro.html')

        if Paciente.objects.filter(dni=dni).exists():
            messages.error(request, 'El DNI ya está registrado.')
            return render(request, 'registro.html')

        # Parsear la fecha de nacimiento
        try:
            fecha_nacimiento_parsed = datetime.strptime(fecha_nacimiento, '%d-%m-%Y').date()
        except ValueError:
            messages.error(request, 'Formato de fecha de nacimiento inválido. Usa el formato DD-MM-YYYY.')
            return render(request, 'registro.html')

        try:
            with transaction.atomic():
                # Crear el usuario
                user = User.objects.create_user(
                    correo_electronico=correo_electronico,
                    email=correo_electronico,
                    password=contrasena,
                    first_name=nombre,
                    last_name=apellidos,
                    rol=User.Roles.PACIENTE,
                )

                # Crear el perfil de paciente
                paciente = Paciente(
                    user=user,
                    dni=dni,
                    nombre=nombre,
                    apellidos=apellidos,
                    fecha_nacimiento=fecha_nacimiento_parsed,
                    genero=genero,
                    direccion=direccion_completa,
                    telefono=telefono,
                    correo_electronico=correo_electronico,
                    historial_medico=historial_medico,
                    informacion_seguro=informacion_seguro,
                    fecha_registro=timezone.now(),
                )
                # Validar y guardar el paciente
                paciente.full_clean()
                paciente.save()
        except ValidationError as e:
            # Si hay un error, eliminar el usuario creado y mostrar el error
            user.delete()
            messages.error(request, f'Error al crear el usuario: {e}')
            return render(request, 'registro.html')
        except Exception as e:
            messages.error(request, f'Ha ocurrido un error: {e}')
            return render(request, 'registro.html')

        # Registro exitoso
        messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
        return redirect('inicio_sesion')

    else:
        return render(request, 'registro.html')


def inicio_sesion(request):
    if request.method == 'POST':
        correo_electronico = request.POST['correo_electronico']
        contrasena = request.POST['contrasena']
        
        # Identificador único para los intentos basados en el correo electrónico
        cache_key = f'login_attempts_{correo_electronico}'
        max_attempts = 3
        attempts = cache.get(cache_key, 0)

        if attempts >= max_attempts:
            messages.error(request, 'Cuenta bloqueada temporalmente debido a múltiples intentos fallidos. Intenta de nuevo más tarde.')
            return render(request, 'inicio_sesion.html')

        # Autenticar al usuario
        user = authenticate(request, username=correo_electronico, password=contrasena)
        
        if user is not None:
            login(request, user)
            # Resetea el contador de intentos fallidos
            cache.delete(cache_key)
            return redirect('portal_usuario')
        else:
            # Incrementa el contador de intentos fallidos
            attempts += 1
            cache.set(cache_key, attempts, timeout=300)  # Bloquea la cuenta durante 5 minutos si hay 3 intentos fallidos
            if attempts >= max_attempts:
                messages.error(request, 'Cuenta bloqueada temporalmente debido a múltiples intentos fallidos. Intenta de nuevo más tarde.')
            else:
                messages.error(request, 'Correo electrónico o contraseña incorrectos')

    return render(request, 'inicio_sesion.html')


def index(request):
    return render(request, 'index.html')


def is_medico(user):
    return user.rol == 'medico'

def is_paciente(user):
    return user.rol == 'paciente'

@login_required
def portal_usuario(request):
    user = request.user

    if user.rol == 'paciente':
        try:
            paciente = user.paciente_profile
        except Paciente.DoesNotExist:
            return HttpResponse("No tienes un perfil de paciente.")

        # Obtener las próximas citas del paciente
        citas = Cita.objects.filter(
            paciente=paciente,
            fecha__gte=timezone.now()
        ).select_related('tratamiento', 'personal_medico').order_by('fecha')

        # Inicializar el formulario para solicitar nueva cita
        form_nueva_cita = SolicitarCitaForm()

        # Crear una lista de tuplas (cita, formulario_modificar)
        citas_modificar_forms = []
        for cita in citas:
            form_modificar = SolicitarCitaForm(instance=cita)
            citas_modificar_forms.append((cita, form_modificar))

        context = {
            'paciente': paciente,
            'citas': citas,
            'form_nueva_cita': form_nueva_cita,
            'citas_modificar_forms': citas_modificar_forms,
            'rol': 'paciente',
        }

    elif user.rol == 'medico':
        try:
            medico = user.medico_profile
        except PersonalMedico.DoesNotExist:
            return HttpResponse("No tienes un perfil de médico.")

        # Obtener todas las citas del médico
        citas = Cita.objects.filter(
            personal_medico=medico,
            fecha__gte=timezone.now()
        ).select_related('tratamiento', 'paciente').order_by('fecha')

        # Crear una lista de tuplas (cita, formulario_modificar)
        citas_modificar_forms = []
        for cita in citas:
            form_modificar = SolicitarCitaForm(instance=cita)
            citas_modificar_forms.append((cita, form_modificar))

        context = {
            'medico': medico,
            'citas': citas,
            'citas_modificar_forms': citas_modificar_forms,
            'rol': 'medico',
        }

    else:
        return HttpResponse("Rol de usuario no reconocido.")

    return render(request, 'principal_clientes.html', context)

@login_required
@user_passes_test(is_medico)
def asignar_tratamiento(request, cita_id):
    user = request.user
    try:
        medico = user.medico_profile
    except PersonalMedico.DoesNotExist:
        return HttpResponse("No tienes un perfil de médico.")

    cita = get_object_or_404(Cita, id=cita_id, personal_medico=medico)

    if request.method == 'POST':
        form = AsignarTratamientoForm(request.POST)
        if form.is_valid():
            tratamiento = form.save()
            cita.tratamiento = tratamiento
            cita.save()
            messages.success(request, 'Tratamiento asignado exitosamente.')
            return redirect('portal_usuario')
        else:
            messages.error(request, 'Error al asignar el tratamiento.')
    else:
        form = AsignarTratamientoForm()

    # Redirigir de vuelta al portal con los mensajes
    return redirect('portal_usuario')

@login_required
def solicitar_cita(request):
    user = request.user

    if user.rol != 'paciente':
        return HttpResponse("No tienes permisos para acceder a esta página.")

    try:
        paciente = user.paciente_profile
    except Paciente.DoesNotExist:
        return HttpResponse("No tienes un perfil de paciente.")

    if request.method == 'POST':
        form = SolicitarCitaForm(request.POST)
        if form.is_valid():
            nueva_cita = form.save(commit=False)
            nueva_cita.paciente = paciente
            nueva_cita.estado = Cita.EstadosCita.PROGRAMADA
            nueva_cita.save()
            messages.success(request, 'Su cita ha sido solicitada exitosamente.')
            return redirect('portal_usuario')
        else:
            messages.error(request, 'Hubo un error al solicitar la cita.')
    else:
        form = SolicitarCitaForm()

    # En caso de error, renderizar nuevamente el portal con los errores
    citas = Cita.objects.filter(
        paciente=paciente,
        fecha__gte=timezone.now()
    ).select_related('tratamiento', 'personal_medico').order_by('fecha')
    form_nueva_cita = form
    citas_modificar_forms = []
    for cita in citas:
        form_modificar = SolicitarCitaForm(instance=cita)
        citas_modificar_forms.append((cita, form_modificar))
    context = {
        'paciente': paciente,
        'citas': citas,
        'form_nueva_cita': form_nueva_cita,
        'citas_modificar_forms': citas_modificar_forms,
        'rol': 'paciente',
    }
    return render(request, 'principal_clientes.html', context)

@login_required
def modificar_cita(request, cita_id):
    user = request.user

    if user.rol != 'paciente':
        return HttpResponse("No tienes permisos para acceder a esta página.")

    try:
        paciente = user.paciente_profile
    except Paciente.DoesNotExist:
        return HttpResponse("No tienes un perfil de paciente.")

    cita = get_object_or_404(Cita, id=cita_id, paciente=paciente)

    if request.method == 'POST':
        form = SolicitarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cita modificada exitosamente.')
            return redirect('portal_usuario')
        else:
            messages.error(request, 'Hubo un error al modificar la cita.')
    else:
        form = SolicitarCitaForm(instance=cita)

    # En caso de error, renderizar nuevamente el portal con los errores
    citas = Cita.objects.filter(
        paciente=paciente,
        fecha__gte=timezone.now()
    ).select_related('tratamiento', 'personal_medico').order_by('fecha')
    form_nueva_cita = SolicitarCitaForm()
    citas_modificar_forms = []
    for cita in citas:
        form_modificar = SolicitarCitaForm(instance=cita)
        citas_modificar_forms.append((cita, form_modificar))
    context = {
        'paciente': paciente,
        'citas': citas,
        'form_nueva_cita': form_nueva_cita,
        'citas_modificar_forms': citas_modificar_forms,
        'rol': 'paciente',
    }
    return render(request, 'principal_clientes.html', context)

@login_required
def cancelar_cita(request, cita_id):
    user = request.user
    try:
        paciente = user.paciente_profile
    except Paciente.DoesNotExist:
        return HttpResponse("No tienes un perfil de paciente.")

    cita = get_object_or_404(Cita, id=cita_id, paciente=paciente)

    if request.method == 'POST' or request.method == 'GET':
        cita.estado = Cita.EstadosCita.CANCELADA
        cita.save()
        messages.success(request, 'La cita ha sido cancelada exitosamente.')
        return redirect('portal_usuario')

    return redirect('portal_usuario')