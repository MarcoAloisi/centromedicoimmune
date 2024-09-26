from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login
from .models import User, Paciente, Cita
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import SolicitarCitaForm

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
        if User.objects.filter(username=correo_electronico).exists():
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
                    username=correo_electronico,
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
            return redirect('portal_paciente')
        else:
            # Incrementa el contador de intentos fallidos
            attempts += 1
            cache.set(cache_key, attempts, timeout=300)  # Bloquea la cuenta durante 5 minutos si hay 3 intentos fallidos
            if attempts >= max_attempts:
                messages.error(request, 'Cuenta bloqueada temporalmente debido a múltiples intentos fallidos. Intenta de nuevo más tarde.')
            else:
                messages.error(request, 'Correo electrónico o contraseña incorrectos')

    return render(request, 'inicio_sesion.html')



@login_required
def portal_paciente(request):
    # Verificar que el usuario tiene el rol de paciente
    if request.user.rol != 'paciente':
        return HttpResponse("No tienes permisos para acceder a esta página.")

    # Intentar obtener el perfil de paciente asociado al usuario
    try:
        paciente = request.user.paciente_profile
    except Paciente.DoesNotExist:
        return HttpResponse("No tienes un perfil de paciente.")

    # Obtener las próximas citas del paciente
    citas = Cita.objects.filter(
        paciente=paciente,
        fecha__gte=timezone.now()
    ).order_by('fecha')

    context = {
        'paciente': paciente,
        'citas': citas,
    }

    return render(request, 'principal_clientes.html', context)


@login_required
def solicitar_cita(request):
    if request.user.rol != 'paciente':
        return HttpResponse("No tienes permisos para acceder a esta página.")

    try:
        paciente = request.user.paciente_profile
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
            return redirect('portal_paciente')
    else:
        form = SolicitarCitaForm()

    context = {
        'form': form
    }
    return render(request, 'solicitar_cita.html', context)

def index(request):
    return render(request, 'index.html')