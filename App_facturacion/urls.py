from django.urls import path

from . import views

app_name = 'App_facturacion'

urlpatterns = [
	path('inventario/', views.inventario_view, name='inventario'),
	path('reportes/', views.reportes_view, name='reportes'),
]
