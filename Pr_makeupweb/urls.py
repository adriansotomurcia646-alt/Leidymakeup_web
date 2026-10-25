from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/usuarios/login/', permanent=False)),
    path('usuarios/', include('App_usuarios.urls')),
    path('agenda/', include('App_agenda.urls')),
    path('servicios/', include('App_servicios.urls')),
    path('facturacion/', include('App_facturacion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)