from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.urls import reverse


def role_required(role):
	def decorator(view_func):
		@wraps(view_func)
		def wrapped_view(request, *args, **kwargs):
			if not request.user.is_authenticated:
				login_name = 'App_usuarios:e_login' if role == 'estilista' else 'App_usuarios:login'
				return redirect_to_login(
					request.get_full_path(),
					login_url=reverse(login_name),
				)

			es_estilista = (
				request.user.rol == 'estilista'
				or request.user.is_staff
				or request.user.is_superuser
			)
			request.session['rol'] = 'estilista' if es_estilista else request.user.rol
			if request.user.rol != role and not (role == 'estilista' and es_estilista):
				messages.error(request, 'No tienes permiso para acceder a esta página.')
				return HttpResponseForbidden('No tienes permiso para acceder a esta página.')
			return view_func(request, *args, **kwargs)

		return wrapped_view

	return decorator
