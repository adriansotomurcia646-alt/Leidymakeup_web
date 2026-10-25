from django.urls import path
from . import views

app_name = 'App_agenda'

urlpatterns = [
    # --- RUTAS CLIENTE ---
    path('inicio/', views.c_inicio_view, name='c_inicio'),
    path('reservar/', views.reservar_cita_view, name='c_reservar'),
    path('reservar/', views.reservar_cita_view, name='reservar_cita'),
    path('reservar/horarios/', views.horarios_disponibles_view, name='horarios_disponibles'),
    path('mis-citas/', views.mis_citas_view, name='c_mis_citas'),
    path('mis-citas/', views.mis_citas_view, name='mis_citas'),
    path('mis-citas/<int:cita_id>/cancelar/', views.cancelar_cita_view, name='cancelar_cita'),
    path('mensajes/', views.mensajes_cliente_view, name='c_mensajes'),
    path('mensajes/', views.mensajes_cliente_view, name='mensajes_cliente'),
    path('calendario/', views.calendario_cliente_view, name='c_calendario'),

    # --- RUTAS ESTILISTA ---
    path('estilista/', views.inicio_estilista_view, name='e_inicio'),
    path('estilista/solicitudes/', views.solicitudes_view, name='e_solicitudes'),
    path('estilista/solicitudes/<int:cita_id>/<str:estado>/', views.actualizar_solicitud_view, name='actualizar_solicitud'),
    path('estilista/calendario/', views.calendario_view, name='e_calendario'),
    path('estilista/calendario/<int:cita_id>/completar/', views.completar_cita_view, name='completar_cita'),
    path('estilista/clientes/', views.clientes_view, name='e_clientes'),
    path('estilista/mensajes/', views.mensajes_estilista_view, name='e_mensajes'),
]