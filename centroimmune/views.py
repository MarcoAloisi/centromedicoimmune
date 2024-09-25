from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import User, Paciente

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
        historial_medico = request.POST.get('historial_medico')
        informacion_seguro = request.POST.get('informacion_seguro')

        # Combinar dirección y dirección 2
        direccion_completa = direccion
        if direccion2:
            direccion_completa += ', ' + direccion2
        direccion_completa += ', ' + ciudad + ', ' + codigo_postal + ', ' + nacionalidad

        # Validar campos obligatorios
        campos_obligatorios = [nombre, apellidos, dni, fecha_nacimiento, genero, direccion, ciudad, codigo_postal, telefono, correo_electronico, contrasena]
        if not all(campos_obligatorios):
            messages.error(request, 'Por favor, completa todos los campos obligatorios.')
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
        return redirect('login')  # Redirige a la página de inicio de sesión o donde prefieras

    else:
        return render(request, 'registro.html')
    
def inicio_sesion(request):
    return render(request, 'inicio_sesion.html')

def index(request):
    return render(request, 'index.html')