from django.urls import path

from . import views

app_name = 'App_usuarios'

urlpatterns = [
	path('login/', views.login_view, name='login'),
	path('registro/', views.registro_view, name='registro'),
	path('perfil/', views.perfil_view, name='perfil'),
	path('configuracion/', views.configuracion_view, name='configuracion'),
	path('logout/', views.logout_view, name='logout'),
	path('estilista/login/', views.e_login, name='e_login'),
]
