from django.contrib import admin

from .models import Cita, CitaArchivo, Horario, Mensaje

admin.site.register((Cita, CitaArchivo, Horario, Mensaje))
