from django.urls import path
from . import views

app_name = 'App_servicios'

urlpatterns = [
    path('', views.lista_servicios_view, name='lista'),
    path('', views.lista_servicios_view, name='catalogo'),
    path('crear/', views.crear_servicio_view, name='crear'),
    path('editar/<int:pk>/', views.editar_servicio_view, name='editar'),
    path('eliminar/<int:pk>/', views.eliminar_servicio_view, name='eliminar'),
]
