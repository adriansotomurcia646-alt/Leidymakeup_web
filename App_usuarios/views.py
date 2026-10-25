from django.contrib import messages
from django.contrib.auth import (
	REDIRECT_FIELD_NAME,
	authenticate,
	login,
	logout,
	password_validation,
)
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from App_agenda.models import Horario

from .decorators import role_required
from .models import Cliente, Estilista, Persona


def dashboard_url(usuario):
	if usuario.is_staff or usuario.is_superuser or usuario.rol == 'estilista':
		return 'App_agenda:e_inicio'
	return 'App_agenda:c_inicio'


def login_view(request, rol=None):
	rol_seleccionado = request.POST.get(
		'rol',
		request.GET.get('rol', rol or 'cliente'),
	)

	if request.user.is_authenticated:
		return redirect(dashboard_url(request.user))

	if request.method == 'POST':
		username = request.POST.get('username', '').strip()
		if not Persona.objects.filter(username=username).exists():
			username = Persona.objects.filter(
				email__iexact=username,
			).values_list('username', flat=True).first() or username
		password = request.POST.get('password', '')
		usuario = authenticate(request, username=username, password=password)

		if rol_seleccionado not in ('cliente', 'estilista'):
			messages.error(request, 'Selecciona un tipo de cuenta válido.')
		elif usuario is None:
			messages.error(request, 'Credenciales incorrectas.')
		elif not (usuario.is_staff or usuario.is_superuser) and usuario.rol != rol_seleccionado:
			messages.error(request, 'El tipo de cuenta seleccionado no corresponde al usuario.')
		else:
			login(request, usuario)
			request.session['rol'] = (
				'estilista'
				if usuario.is_staff or usuario.is_superuser
				else usuario.rol
			)
			next_url = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(
				REDIRECT_FIELD_NAME
			)
			if next_url and url_has_allowed_host_and_scheme(
				next_url,
				allowed_hosts={request.get_host()},
				require_https=request.is_secure(),
			):
				return redirect(next_url)
			return redirect(dashboard_url(usuario))

	return render(
		request,
		'App_usuarios/C_login.html',
		{'rol_seleccionado': rol_seleccionado},
	)


def registro_view(request):
	if request.method == 'POST':
		nombre = request.POST.get('nombre', '').strip()
		apellido = request.POST.get('apellido', '').strip()
		email = request.POST.get('email', '').strip().lower()
		telefono = request.POST.get('telefono', '').strip()
		password = request.POST.get('password', '')

		if not nombre or not email or not password:
			messages.error(request, 'Completa nombre, correo y contraseña.')
		else:
			try:
				validate_email(email)
				password_validation.validate_password(password)
				if Persona.objects.filter(email__iexact=email).exists():
					raise ValidationError('Ya existe una cuenta con ese correo.')

				with transaction.atomic():
					persona = Persona.objects.create_user(
						username=email,
						email=email,
						password=password,
						first_name=nombre,
						last_name=apellido,
						rol='cliente',
					)
					Cliente.objects.create(persona=persona, telefono=telefono)
			except ValidationError as error:
				for error_message in error.messages:
					messages.error(request, error_message)
			except IntegrityError:
				messages.error(request, 'No fue posible crear la cuenta con esos datos.')
			else:
				messages.success(request, 'Cuenta creada. Ya puedes iniciar sesión.')
				return redirect('App_usuarios:login')

	return render(request, 'App_usuarios/C_registro.html')


@role_required('cliente')
def perfil_view(request):
	cliente = Cliente.objects.filter(persona=request.user).first()
	if request.method == 'POST':
		email = request.POST.get('email', '').strip().lower()
		try:
			validate_email(email)
		except ValidationError as error:
			for error_message in error.messages:
				messages.error(request, error_message)
			return render(request, 'App_usuarios/C_perfil.html', {'cliente': cliente})

		if Persona.objects.exclude(pk=request.user.pk).filter(email__iexact=email).exists():
			messages.error(request, 'Ese correo ya está asociado a otra cuenta.')
			return render(request, 'App_usuarios/C_perfil.html', {'cliente': cliente})

		request.user.first_name = request.POST.get('first_name', '').strip()
		request.user.last_name = request.POST.get('last_name', '').strip()
		request.user.email = email
		request.user.save(update_fields=['first_name', 'last_name', 'email'])
		if cliente:
			cliente.telefono = request.POST.get('telefono', '').strip()
			cliente.save(update_fields=['telefono'])
		messages.success(request, 'Tu perfil fue actualizado.')
		return redirect('App_usuarios:perfil')

	return render(request, 'App_usuarios/C_perfil.html', {'cliente': cliente})


@role_required('estilista')
def configuracion_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	if request.method == 'POST':
		estilista.especialidad = request.POST.get('especialidad', '').strip()
		estilista.save(update_fields=['especialidad'])
		messages.success(request, 'La configuración fue actualizada.')
		return redirect('App_usuarios:configuracion')

	return render(
		request,
		'App_usuarios/E_configuracion.html',
		{
			'estilista': estilista,
			'horarios': Horario.objects.filter(
				estilista=estilista,
				activo=True,
			).order_by('dia_semana', 'hora_inicio'),
		},
	)


@login_required
@require_POST
def logout_view(request):
	logout(request)
	return redirect('App_usuarios:login')


def e_login(request):
	return login_view(request, rol='estilista')
