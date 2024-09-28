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
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import secrets
from django.utils.timezone import localtime
import locale
from .forms import ModificarDatosPacienteForm


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

User = get_user_model()

def inicio_sesion(request):
    if request.method == 'POST':
        # Verificar si estamos en la etapa de 2FA
        if 'token' in request.POST:
            # Etapa 2: Verificación del token de 2FA
            user_id = request.session.get('pre_2fa_user_id')
            if not user_id:
                messages.error(request, 'No se encontró una sesión de 2FA. Por favor, inicia sesión de nuevo.')
                return redirect('inicio_sesion')

            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('inicio_sesion')

            token_entered = request.POST.get('token')
            token_expected = cache.get(f'2fa_token_{user.pk}')

            # Obtener intentos de 2FA
            two_fa_key = f'2fa_attempts_{user.pk}'
            two_fa_attempts = cache.get(two_fa_key, 0)
            max_two_fa_attempts = 5

            if two_fa_attempts >= max_two_fa_attempts:
                messages.error(request, 'Has excedido el número máximo de intentos. Intenta de nuevo más tarde.')
                return redirect('inicio_sesion')

            if token_expected and token_entered == token_expected:
                # 2FA exitoso, iniciar sesión al usuario
                login(request, user)
                # Limpiar el token y la sesión de pre-2FA
                cache.delete(f'2fa_token_{user.pk}')
                cache.delete(two_fa_key)
                del request.session['pre_2fa_user_id']
                messages.success(request, 'Inicio de sesión exitoso.')
                return redirect('portal_usuario')  # Redirigir al portal del usuario
            else:
                two_fa_attempts += 1
                cache.set(two_fa_key, two_fa_attempts, timeout=600)  # Bloquear por 10 minutos
                messages.error(request, 'Código de verificación inválido o expirado.')

        else:
            # Etapa 1: Autenticación inicial
            correo_electronico = request.POST.get('correo_electronico')
            contrasena = request.POST.get('contrasena')

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
                # Resetea el contador de intentos fallidos
                cache.delete(cache_key)

                # Generar un token de 2FA
                token = str(secrets.randbelow(1000000)).zfill(6)  # Código de 6 dígitos con ceros a la izquierda

                # Almacenar el token en caché con un tiempo de expiración (por ejemplo, 10 minutos)
                cache.set(f'2fa_token_{user.pk}', token, timeout=600)

                # Enviar el token por correo electrónico
                try:
                    send_mail(
                        'Código de Verificación de 2FA',
                        f'Tu código de verificación de dos factores es: {token}',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    messages.error(request, 'Error al enviar el correo electrónico. Intenta de nuevo.')
                    return render(request, 'inicio_sesion.html')

                # Almacenar el ID del usuario en la sesión para el proceso de 2FA
                request.session['pre_2fa_user_id'] = user.pk

                # Indicar que el token ha sido enviado para activar el modal
                messages.info(request, 'Se ha enviado un código de verificación a tu correo electrónico.')
            else:
                # Incrementar el contador de intentos fallidos
                attempts += 1
                cache.set(cache_key, attempts, timeout=300)  # Bloquear la cuenta durante 5 minutos si hay 3 intentos fallidos
                if attempts >= max_attempts:
                    messages.error(request, 'Cuenta bloqueada temporalmente debido a múltiples intentos fallidos. Intenta de nuevo más tarde.')
                else:
                    messages.error(request, 'Correo electrónico o contraseña incorrectos.')

    # Determinar si mostrar el modal de 2FA
    show_2fa = False
    if 'pre_2fa_user_id' in request.session:
        show_2fa = True

    return render(request, 'inicio_sesion.html', {'show_2fa': show_2fa})

def resend_2fa_token(request):
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        messages.error(request, 'No se encontró una sesión de 2FA. Por favor, inicia sesión de nuevo.')
        return redirect('inicio_sesion')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('inicio_sesion')

    # Generar un nuevo token
    token = str(secrets.randbelow(1000000)).zfill(6)
    cache.set(f'2fa_token_{user.pk}', token, timeout=600)

    # Enviar el nuevo token por correo electrónico
    try:
        send_mail(
            'Código de Verificación de 2FA',
            f'Tu nuevo código de verificación de dos factores es: {token}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, 'Se ha enviado un nuevo código de verificación a tu correo electrónico.')
    except Exception as e:
        messages.error(request, 'Error al enviar el correo electrónico. Intenta de nuevo.')

    return redirect('inicio_sesion')

def index(request):
    return render(request, 'index.html')


def is_medico(user):
    return user.rol == 'medico'

def is_paciente(user):
    return user.rol == 'paciente'

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

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


        # Convertir la fecha de la cita a la zona horaria local y formatear
        for cita in citas:
            cita.fecha_formateada = localtime(cita.fecha).strftime('%d de %B de %Y')

                # Formulario para modificar datos del paciente
        if request.method == 'POST' and 'modificar_datos' in request.POST:
            form_modificar_datos = ModificarDatosPacienteForm(request.POST, instance=paciente)
            if form_modificar_datos.is_valid():
                form_modificar_datos.save()
                messages.success(request, 'Tus datos personales han sido modificados exitosamente.')
                return redirect('portal_usuario')
            else:
                messages.error(request, 'Hubo un error al modificar tus datos.')
        else:
            form_modificar_datos = ModificarDatosPacienteForm(instance=paciente)

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
            'form_modificar_datos': form_modificar_datos,
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
        
        for cita in citas:
            cita.fecha_formateada = localtime(cita.fecha).strftime('%d de %B de %Y')

        # Crear una lista de tuplas (cita, formulario_asignar_tratamiento)
        asignar_tratamiento_forms = []
        for cita in citas:
            # Crear formulario para asignar tratamiento
            form_asignar_tratamiento = AsignarTratamientoForm(instance=cita.tratamiento)
            asignar_tratamiento_forms.append((cita, form_asignar_tratamiento))

        context = {
            'medico': medico,
            'citas': citas,
            'asignar_tratamiento_forms': asignar_tratamiento_forms,
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